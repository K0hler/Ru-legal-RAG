"""Project-authored synthetic fixtures; no gold labels or downloaded corpus."""

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from legal_rag.corpus.housing_html import extract_html  # noqa: E402


# Authored educational provisions, not quotations of the real Code.
HTML = """<html><body><p class="Z">Жилищный кодекс Российской Федерации</p>
<p class="T">РАЗДЕЛ III<span class="W9">1</span><br/>Учебный раздел</p>
<p class="H">Глава 8<span class="W9">1</span>. Учебная глава</p>
<p class="H" id="a">Статья 32<span class="W9">1</span>. Учебная статья</p>
<p id="part">1. Вводная норма.<span class="mark"> (В редакции учебного закона)</span></p>
<p>1) Учебный пункт;</p><p>а) Учебный подпункт.</p>
<p>Следующий абзац подпункта.</p>
<p>2. Другая часть.</p><p>Второй абзац части.</p>
<p class="A"><span class="mark">(Особенности применения части 1)</span></p>
<p class="F"><span class="mark">(Изменение с 01.03.2028)</span></p>
<p class="H">Статья 33. Другая учебная статья</p>
<p>Вводный текст.</p><p>5<span class="W9">1</span>) Учебный пункт.</p>
<p>Президент Российской Федерации В.Путин</p><p>Москва, Кремль</p>
<p>29 декабря 2004 года</p><p>№ 188-ФЗ</p></body></html>"""


def parse(html=HTML):
    from legal_rag.corpus.housing_html import build_tree

    claim = 'Кодекс Российской Федерации от 29.12.2004 № 188-ФЗ "Жилищный кодекс Российской Федерации"'
    return build_tree(extract_html(html.encode("utf-8")), claim)


def test_block_locator_covers_all_tokens_and_validation_rejects_stale_coordinates():
    from legal_rag.corpus.housing_html import build_tree, validate

    payload = HTML.replace("Вводный текст.", "1. Alpha <span>Beta</span>.").encode()
    extraction = extract_html(payload)
    block = next(b for b in extraction["blocks"] if "Alpha" in b["text"])
    span = block["source_span"]
    assert span["locator"] == (
        f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
    )
    tree = build_tree(extraction)
    assert validate(extraction, tree, payload)["integrity_pass"]
    span["locator"] = f"{span['html_locator']}:chars:0:1"
    assert not validate(extraction, tree, payload)["integrity_pass"]
    token_span = extraction["text_nodes"][0]["source_span"]
    token_span["locator"] = f"{token_span['html_locator']}:chars:0:1"
    assert any(
        p.startswith("token_locator:")
        for p in validate(extraction, tree, payload)["problems"]
    )
    import copy

    clean = extract_html(payload)
    corrupt_tree = copy.deepcopy(build_tree(clean))
    node_span = next(n for n in corrupt_tree["nodes"] if "Alpha" in n["text"])["source_span"]
    node_span["locator"] = f"{node_span['html_locator']}:chars:0:1"
    assert not validate(clean, corrupt_tree, payload)["integrity_pass"]


@pytest.mark.parametrize("target", ["extraction", "ast", "ast_token_references"])
def test_validation_rejects_self_consistent_span_or_token_reference_corruption(target):
    import copy
    from legal_rag.corpus.housing_html import build_tree, validate

    payload = HTML.encode()
    extraction = extract_html(payload)
    tree = copy.deepcopy(build_tree(extraction))
    assert validate(extraction, tree, payload)["integrity_pass"]
    if target == "ast_token_references":
        first, second = tree["nodes"][:2]
        first["text_node_ids"], second["text_node_ids"] = (
            second["text_node_ids"], first["text_node_ids"]
        )
    else:
        entries = extraction["blocks"] if target == "extraction" else tree["nodes"]
        span = entries[0]["source_span"]
        span["char_start"], span["char_end"] = 0, 1
        span["locator"] = f"{span['html_locator']}:chars:0:1"
    validation = validate(extraction, tree, payload)
    assert not validation["integrity_pass"]
    assert any(
        problem.startswith("block_token_span:" if target == "extraction" else "ast_block_mapping:")
        for problem in validation["problems"]
    )


def boundary_document(fragment):
    return (
        '<html><body><p class="Z">Жилищный кодекс Российской Федерации</p>'
        '<p class="T">РАЗДЕЛ I Первый</p><p class="H">Глава 1. Первая</p>'
        '<p class="H">Статья 1. Первая</p>'
        + fragment
        + '<p>Президент Российской Федерации В.Путин</p>'
        '<p>29 декабря 2004 года</p><p>№ 188-ФЗ</p></body></html>'
    )


@pytest.mark.parametrize(
    "boundary", ["Статья 2. Другая статья", "Глава 2. Другая глава", "РАЗДЕЛ II Другой"]
)
@pytest.mark.parametrize("note", ["", '<span class="mark">(Примечание)</span>'])
def test_multiple_boundaries_across_paragraph_groups_stop_targeting(boundary, note):
    html = boundary_document(f"<p>1. Норма{note}<br/>{boundary}</p><p>2. Далее</p>")
    tree = parse(html)
    assert any(
        b["reason"] == "multiple_provision_markers" for b in tree["unresolved_blocks"]
    )
    assert not any(n["text"] in {"1. Норма", "2. Далее"} for n in tree["nodes"])
    assert any(b["text"] == "2. Далее" for b in tree["unresolved_blocks"])
    assert tree["accounting"]["exactly_once"]


@pytest.mark.parametrize("note_class", ["mark", "markx"])
def test_note_contained_break_rejects_whole_paragraph_and_stops_targeting(note_class):
    from legal_rag.corpus.housing_html import build_tree, validate

    payload = boundary_document(
        '<p class="H">Статья 2. Вторая'
        f'<span class="{note_class}">(Примечание)<br/></span>'
        'Статья 3. Третья</p><p>1. Далее</p>'
    ).encode()
    extraction = extract_html(payload)
    tree = build_tree(extraction)
    paragraph = next(b["paragraph"] for b in extraction["blocks"] if "Вторая" in b["text"])
    rejected = [b for b in tree["unresolved_blocks"] if b["paragraph"] == paragraph]
    assert {b["block_id"] for b in rejected} == {
        b["block_id"] for b in extraction["blocks"] if b["paragraph"] == paragraph
    }
    assert all(b["reason"] == "multiple_provision_markers" for b in rejected)
    assert not any(n["paragraph"] == paragraph or n["text"] == "1. Далее" for n in tree["nodes"])
    assert any(b["text"] == "1. Далее" for b in tree["unresolved_blocks"])
    assert tree["accounting"]["exactly_once"]
    validation = validate(extraction, tree, payload)
    assert validation["integrity_pass"]
    assert not validation["structure_complete"]


@pytest.mark.parametrize("wrapper", ["table", "ul", "ol"])
@pytest.mark.parametrize("boundary", ["chapter", "section"])
def test_rejected_wrapped_boundary_clears_higher_context(wrapper, boundary):
    heading = (
        '<p class="H">Глава 2. Другая</p>'
        if boundary == "chapter"
        else '<p class="T">РАЗДЕЛ II Другой</p>'
    )
    content = f"<tr><td>{heading}</td></tr>" if wrapper == "table" else f"<li>{heading}</li>"
    following = '<p class="H">Статья 2. Другая</p>'
    if boundary == "section":
        following = '<p class="H">Глава 3. Третья</p>' + following
    tree = parse(boundary_document(f"<{wrapper}>{content}</{wrapper}>" + following))
    article = next(n for n in tree["nodes"] if n["address"] == "act/article/2")
    assert article["parent_address"] == (
        "act/section/I" if boundary == "chapter" else "act/chapter/3"
    )
    if boundary == "section":
        chapter = next(n for n in tree["nodes"] if n["address"] == "act/chapter/3")
        assert chapter["parent_address"] == "act"
    assert not any(n["address"] in {"act/chapter/2", "act/section/II"} for n in tree["nodes"])


@pytest.mark.parametrize(
    "fragment,tags",
    [
        ('<p><img src="formula.png"/></p>', ["img"]),
        ('<p>1. Норма<img src="formula.png"/> продолжение</p>', ["img"]),
        ('<table><tr><td><img src="formula.png"/></td></tr></table>', ["table", "img"]),
        ("<table></table>", ["table"]),
        ("<ul><li></li></ul>", ["ul"]),
        ("<ol><li></li></ol>", ["ol"]),
    ],
)
def test_nontext_regions_are_retained_and_independently_accounted(fragment, tags):
    import copy
    from legal_rag.corpus.housing_html import build_tree, render_report, validate

    payload = boundary_document(fragment + "<p>2. Далее</p>").encode()
    html = payload.decode()
    extraction = extract_html(payload)
    regions = extraction.get("unsupported_regions", [])
    assert [r["tag"] for r in regions] == tags
    for region in regions:
        span = region["source_span"]
        assert html[span["char_start"] : span["char_end"]] == region["original_html"]
        assert span["locator"].endswith(f":chars:{span['char_start']}:{span['char_end']}")
        assert "text_node_ids" not in region
    tree = build_tree(extraction)
    assert tree["unresolved_regions"] == regions
    assert not any(n["text"] == "2. Далее" or "Норма" in n["text"] for n in tree["nodes"])
    validation = validate(extraction, tree, payload)
    assert validation["integrity_pass"]
    assert not validation["structure_complete"]
    assert tree["accounting"]["exactly_once"]
    assert tree["accounting"]["regions_exactly_once"]
    assert "&lt;" + tags[0] in render_report(tree, validation)
    missing = copy.deepcopy(extraction)
    missing["unsupported_regions"] = []
    missing_validation = validate(missing, build_tree(missing), payload)
    assert not missing_validation["integrity_pass"]
    # Empty text-free regions cannot disappear from the completeness decision.
    assert not missing_validation["structure_complete"]
    corrupt = copy.deepcopy(tree)
    corrupt["unresolved_regions"][0]["original_html"] = "wrong"
    assert not validate(extraction, corrupt, payload)["integrity_pass"]
    corrupt = copy.deepcopy(tree)
    corrupt["unresolved_regions"] *= 2
    assert not validate(extraction, corrupt, payload)["integrity_pass"]


@pytest.mark.parametrize("field", ["date", "number", "president", "title"])
@pytest.mark.parametrize("note_class", ["A", "F", "mark", "markx"])
def test_identity_evidence_cannot_come_from_notes(field, note_class):
    html = boundary_document("<p>1. Норма</p>")
    text = {
        "date": "29 декабря 2004 года",
        "number": "№ 188-ФЗ",
        "president": "Президент Российской Федерации В.Путин",
        "title": "Жилищный кодекс Российской Федерации",
    }[field]
    if field == "title":
        html = html.replace('class="Z"', f'class="Z {note_class}"')
    elif note_class in {"A", "F"}:
        html = html.replace(f"<p>{text}</p>", f'<p class="{note_class}">{text}</p>')
    else:
        html = html.replace(text, f'<span class="{note_class}">{text}</span>')
    extraction = extract_html(html.encode())
    tree = parse(html)
    assert tree["identity_decision"]["status"] == "unresolved"
    assert not tree["nodes"]
    note_ids = {
        b["block_id"] for b in extraction["blocks"]
        if b["note"] or set(b["classes"]) & {"A", "F"}
    }
    assert not note_ids.intersection(tree["identity_decision"]["evidence_block_ids"])


def test_literal_hierarchy_and_notes():
    tree = parse()
    assert tree["identity_decision"]["status"] == "claim_matches_header"
    assert tree["edition_admission"] is False
    assert tree["valid_from"] is None
    nodes = tree["nodes"]
    provisions = [
        (n["kind"], n["address"], n["parent_address"])
        for n in nodes
        if n["kind"] not in {"header", "note"}
    ]
    assert provisions == [
        ("section", "act/section/III.1", "act"),
        ("chapter", "act/chapter/8.1", "act/section/III.1"),
        ("article", "act/article/32.1", "act/chapter/8.1"),
        ("part", "act/article/32.1/part/1", "act/article/32.1"),
        ("item", "act/article/32.1/part/1/item/1", "act/article/32.1/part/1"),
        (
            "subitem",
            "act/article/32.1/part/1/item/1/subitem/а",
            "act/article/32.1/part/1/item/1",
        ),
        (
            "paragraph",
            "act/article/32.1/part/1/item/1/subitem/а/paragraph/1",
            "act/article/32.1/part/1/item/1/subitem/а",
        ),
        ("part", "act/article/32.1/part/2", "act/article/32.1"),
        ("paragraph", "act/article/32.1/part/2/paragraph/1", "act/article/32.1/part/2"),
        ("article", "act/article/33", "act/chapter/8.1"),
        ("paragraph", "act/article/33/paragraph/1", "act/article/33"),
        ("item", "act/article/33/item/5.1", "act/article/33"),
    ]
    article = next(n for n in nodes if n["address"] == "act/article/32.1")
    assert article["number_display"] == "32¹"
    assert article["number_components"] == {"base": "32", "superscript": "1"}
    notes = [n for n in nodes if n["kind"] == "note"]
    assert len(notes) == 3
    assert notes[0]["parent_address"] == "act/article/32.1/part/1"
    assert notes[1]["parent_address"] == notes[2]["parent_address"] == "act"
    assert notes[1]["scope_status"] == "unresolved"
    assert notes[2]["note_type"] == "future_change"
    assert notes[2]["effective_date_claim"] == "2028-03-01"
    assert not tree["unresolved_blocks"]
    assert tree["accounting"]["exactly_once"]


def test_raw_html_coordinates_and_source_numbering():
    html = '<html><head><style>.x{}</style></head><body><p class="H" id="a">Статья 32<span class="W9">1</span>. Не &lt;склеивать&gt;<br/>слова.</p></body></html>'
    payload = html.encode("utf-8")
    extraction = extract_html(payload)
    assert extraction["source_asset_sha256"] == hashlib.sha256(payload).hexdigest()
    block = next(b for b in extraction["blocks"] if b["html_id"] == "a")
    assert block["classes"] == ["H"]
    assert block["numbering_text"].startswith("Статья 32^1.")
    assert block["text"] == "Статья 321. Не <склеивать> слова."
    assert block["display_text"] == "Статья 32¹. Не <склеивать> слова."
    assert block["original_html"] == html[block["html_start"] : block["html_end"]]
    for token in extraction["text_nodes"]:
        span = token["source_span"]
        assert "json_pointer" not in span
        assert span["offset_unit"] == "unicode_codepoints_in_utf8_html"
        assert html[span["char_start"] : span["char_end"]] == token["raw_text"]
    assert (
        "".join(m["before"] for m in block["cleanup_mapping"]) == block["original_text"]
    )
    assert "".join(m["after"] for m in block["cleanup_mapping"]) == block["text"]


@pytest.mark.parametrize(
    "fragment,reason",
    [
        ("<p>1. Повторная часть.</p>", "duplicate_address"),
        ('<p id="part">3. Повторный HTML anchor.</p>', "duplicate_html_id"),
        ('<p class="H">Подраздел 1. Нераспознанная граница</p>', "unknown_heading"),
        ("<p>0. Неподдерживаемая нумерация.</p>", "unknown_numbering"),
        ("<p>3. Первая часть.<br/>4. Вторая часть.</p>", "multiple_provision_markers"),
        (
            "<table><tr><td><p>Текст таблицы.</p></td></tr></table>",
            "unsupported_table_or_list",
        ),
        ("<ul><li><p>Текст списка.</p></li></ul>", "unsupported_table_or_list"),
        ("Текст вне абзаца.", "unaddressed_document_text"),
    ],
)
def test_ambiguous_content_stops_targeting(fragment, reason):
    html = HTML.replace(
        "<p>1) Учебный пункт;</p>", fragment + "<p>Последующий неизвестный текст.</p>"
    )
    tree = parse(html)
    assert reason in [b["reason"] for b in tree["unresolved_blocks"]]
    assert any(
        b["text"] == "Последующий неизвестный текст." for b in tree["unresolved_blocks"]
    )
    assert tree["accounting"]["exactly_once"]
    assert len({n["address"] for n in tree["nodes"]}) == len(tree["nodes"])


@pytest.mark.parametrize(
    "html",
    [
        HTML.replace("№ 188-ФЗ", "№ 189-ФЗ"),
        HTML.replace("29 декабря 2004 года", "30 декабря 2004 года"),
        HTML.replace("Жилищный кодекс Российской Федерации", "Другой кодекс"),
        HTML.replace("№ 188-ФЗ", "№ 188-ФЗ</p><p>№ 189-ФЗ"),
    ],
)
def test_identity_conflicts_leave_all_provisions_unresolved(html):
    tree = parse(html)
    assert tree["identity_decision"]["status"] == "unresolved"
    assert not tree["nodes"]
    assert tree["accounting"]["exactly_once"]


def test_repeal_is_retained_as_claim_not_inferred_legal_status():
    tree = parse(
        HTML.replace(
            "(В редакции учебного закона)", "(Часть утратила силу - учебный закон)"
        )
    )
    note = next(n for n in tree["nodes"] if n["kind"] == "note")
    assert note["note_type"] == "repeal_notice"
    part = next(n for n in tree["nodes"] if n["address"] == note["parent_address"])
    assert part["legal_status"] == "unverified"
    assert part["status_claims"] == ["repeal_notice"]


def test_command_links_and_normalization_maps_are_retained():
    html = HTML.replace(
        "1. Вводная норма.",
        '1. Ссылка <span class="cmd" cmdprm="gohash=abc goparaid=p3">на норму</span>.',
    )
    extraction = extract_html(html.encode())
    block = next(
        b for b in extraction["blocks"] if b["html_id"] == "part" and not b["note"]
    )
    assert block["references"][0]["command"] == "gohash=abc goparaid=p3"
    assert block["references"][0]["text"] == "на норму"
    for b in extraction["blocks"]:
        assert "".join(m["before"] for m in b["cleanup_mapping"]) == b["original_text"]
        assert "".join(m["after"] for m in b["cleanup_mapping"]) == b["text"]


def test_adjacent_annotation_elements_are_distinct_notes():
    tree = parse(
        HTML.replace(
            "(В редакции учебного закона)</span>",
            '(В редакции учебного закона)</span><span class="markx">(Дополнение учебным законом)</span>',
        )
    )
    assert len([n for n in tree["nodes"] if n["kind"] == "note"]) == 4
    assert tree["accounting"]["exactly_once"]


def test_marker_only_repealed_article_and_item_remain_addressable():
    html = HTML.replace("Статья 33. Другая учебная статья", "Статья 33.").replace(
        '5<span class="W9">1</span>) Учебный пункт.',
        '5<span class="W9">1</span>)<span class="mark">(Пункт утратил силу)</span>',
    )
    tree = parse(html)
    nodes = {n["address"]: n for n in tree["nodes"]}
    assert nodes["act/article/33"]["title"] is None
    assert nodes["act/article/33/item/5.1"]["status_claims"] == ["repeal_notice"]
    assert not tree["unresolved_blocks"]


def test_cli_deterministic_artifacts_and_conflict_refusal(tmp_path, capsys):
    import json
    from legal_rag.corpus.housing_html import main

    source = tmp_path / "source" / "code.html"
    source.parent.mkdir()
    source.write_text(HTML, encoding="utf-8")
    payload = source.read_bytes()
    output = tmp_path / "derived"
    args = ["--input", str(source), "--output-dir", str(output)]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["result"] == "new"
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert set(before) == {
        "extraction.json",
        "ast.json",
        "validation.json",
        "report.html",
    }
    validation = json.loads(before["validation.json"])
    assert validation["integrity_pass"]
    assert validation["structure_complete"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["result"] == "unchanged"
    assert source.read_bytes() == payload
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    assert (
        main(["--input", str(source), "--output-dir", str(tmp_path / "independent")])
        == 0
    )
    capsys.readouterr()
    assert before == {
        p.name: p.read_bytes() for p in (tmp_path / "independent").iterdir()
    }
    (output / "ast.json").write_text("corrupted", encoding="utf-8")
    assert main(args) == 2
    assert json.loads(capsys.readouterr().err)["result"] == "failed"
    assert (output / "ast.json").read_text() == "corrupted"


def test_cli_refuses_source_overlap_and_retains_unresolved_draft(tmp_path, capsys):
    import json
    from legal_rag.corpus.housing_html import main

    source = tmp_path / "code.html"
    source.write_text(HTML.replace("№ 188-ФЗ", "№ 189-ФЗ"), encoding="utf-8")
    assert main(["--input", str(source), "--output-dir", str(tmp_path)]) == 2
    capsys.readouterr()
    output = tmp_path / "derived"
    claim = 'Кодекс Российской Федерации от 29.12.2004 № 188-ФЗ "Жилищный кодекс Российской Федерации"'
    assert main(["--input", str(source), "--output-dir", str(output), "--identity", claim]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["result"] == "new"
    assert not result["structure_complete"]
    assert (output / "report.html").exists()


def test_report_never_executes_source_html():
    from legal_rag.corpus.housing_html import render_report, validate

    payload = HTML.replace("Вводный текст.", "Вводный &lt;script&gt; текст.").encode()
    extraction = extract_html(payload)
    tree = parse(payload.decode())
    report = render_report(tree, validate(extraction, tree, payload))
    assert "<script" not in report
    assert "<iframe" not in report
    assert "&lt;p" in report
    assert "act/article/32.1" in report


@pytest.mark.parametrize(
    "html",
    ["<html><body><p>x", "<html><p>x</p></html>", "<html><body><p>x</body></html>"],
)
def test_malformed_html_is_rejected(html):
    with pytest.raises(ValueError):
        extract_html(html.encode())
