"""Authored controls for the M1-04A check-pool batch tools; no corpus files or OCR engine."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[3] / "docs" / "assets"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


B = load_script("build_m1_04a_annotation_input")
R = load_script("run_m1_04a_first_pass")
F = load_script("freeze_m1_04a_gold")


def extraction():
    """Two pages: picture, title, text; page 2 has a bare page-number header (noise)."""
    pages = [
        [("Picture", ""), ("Title", "ФЕДЕРАЛЬНЫЙ ЗАКОН"), ("Text", "Статья 1\nТекст\tнормы")],
        [("Page-header", "2"), ("Text", "продолжение нормы."), ("Picture", "2 100039 06204 3")],
    ]
    out = {"pages": [], "blocks": [], "text_nodes": []}
    for pno, regions in enumerate(pages, start=1):
        page = {"page": pno, "regions": []}
        for index, (category, text) in enumerate(regions):
            rid = f"r{pno}-{index}"
            page["regions"].append({"region_id": rid, "category": category, "bbox": [100, 100 + 50 * index, 900, 140]})
            if text:
                out["text_nodes"].append({"text_node_id": f"t{rid}", "raw_text": text})
                out["blocks"].append({"source_region_id": rid, "original_text": text, "text_node_ids": [f"t{rid}"]})
        out["pages"].append(page)
    return out


def test_v1_input_has_no_stage2_columns_and_skips_pictures_and_noise():
    data, info = B.v1_tsv("act", extraction())
    lines = data.decode("utf-8").splitlines()
    assert lines[1] == "# key\tcategory\ttext"
    rows = [line.split("\t") for line in lines if not line.startswith("#")]
    assert rows == [["1.1", "Title", "ФЕДЕРАЛЬНЫЙ ЗАКОН"],
                    ["1.2", "Text", "Статья 1 ⏎ Текст нормы"],
                    ["2.1", "Text", "продолжение нормы."]]
    assert "P=" not in lines[0] and "join" not in lines[0]
    assert info == {"regions": 3, "excluded": {"picture": ["1.0", "2.2"], "noise": ["2.0"]}}
    assert lines[-2] == "# not annotated (Picture): 1.0 2.2"
    assert lines[-1] == "# not annotated (noise: page numbers/running text): 2.0"


def test_legacy_input_still_carries_stage2_columns():
    from legal_rag.corpus.logical_text import build_logical_text

    lines = B.legacy_tsv("act", build_logical_text(extraction())).decode("utf-8").splitlines()
    assert lines[1] == "# key\tcategory\tP\tjoin\ttext"
    assert any(line.startswith("1.0\tPicture\tP") for line in lines)


def test_convention_filter_excludes_pictures_and_noise_only_in_v1():
    gold = {key: {"owners": ["A"], "continuation": False} for key in ("1.0", "1.1", "1.2", "2.1", "2.2")}
    kept, removed = R.apply_convention(gold, extraction(), "v1")
    assert list(kept) == ["1.1", "1.2", "2.1"] and removed == ["1.0", "2.2"]
    kept, removed = R.apply_convention(gold, extraction(), "all-regions")
    assert kept == gold and removed == []
    assert R.excluded_keys(extraction(), "v1") == {"1.0", "2.2", "2.0"}
    with pytest.raises(ValueError):
        R.apply_convention(gold, extraction(), "v2")


def test_gold_freeze_hashes_annotation_input_and_is_write_once(tmp_path):
    gold = tmp_path / "data" / "m1" / "m1-04a" / "gold" / "act"
    gold.mkdir(parents=True)
    (gold / "agent-act.gold.txt").write_text("1.1 A\n", encoding="utf-8")
    (gold / "annotation-notes.md").write_text("notes\n", encoding="utf-8")
    inp = tmp_path / "input"
    inp.mkdir()
    (inp / "act.regions.tsv").write_bytes(b"# key\tcategory\ttext\n1.1\tText\tx\n")
    (inp / "manifest.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "freeze"
    record = F.freeze(out, ["act"], inp, "test annotator", root=tmp_path)
    assert set(record["annotation_input"]) == {"input/act.regions.tsv", "input/manifest.json"}
    assert record["annotation_convention"] == "m1-04a-annotation/v1"
    assert json.loads((out / "freeze.json").read_text(encoding="utf-8"))["files"] == record["files"]
    assert (gold / "agent-act.sha256").read_text(encoding="utf-8").endswith("  agent-act.gold.txt\n")
    with pytest.raises(FileExistsError):
        F.freeze(out, ["act"], inp, "again", root=tmp_path)
    (gold / "agent-act.gold.txt").write_text("1.1 S\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        F.freeze(tmp_path / "freeze-2", ["act"], inp, "changed gold", root=tmp_path)


D = load_script("run_m1_04a_dev_regression")

FAKE_PROTOTYPE = """
VERSION = "fake/1"


def build(extraction):
    owners = {"1.1": "S", "1.2": "S/1", "2.1": "S/2"}
    return {"parser_version": VERSION, "regions": [
        {"page": p["page"], "index": i, "owner": owners.get(f'{p["page"]}.{i}'), "continuation": False}
        for p in extraction["pages"] for i, _ in enumerate(p["regions"])]}
"""


def authored_documents(tmp_path):
    docs = []
    for name, gold in (("one", "1.0 A\n1.1 S\n1.2 S/1\n2.1 S/2\n2.2 A\n"),
                       ("two", "1.1 S\n1.2 S/2\n2.1 S/2\n")):
        ext = tmp_path / f"{name}.extraction.json"
        ext.write_text(json.dumps(extraction()), encoding="utf-8")
        g = tmp_path / f"{name}.gold.txt"
        g.write_text(gold, encoding="utf-8")
        docs.append({"name": name, "group": "authored", "extraction": ext, "gold": g})
    return docs


def test_dev_regression_on_authored_pair(tmp_path):
    proto = tmp_path / "fake_prototype.py"
    proto.write_text(FAKE_PROTOTYPE, encoding="utf-8")
    out = tmp_path / "run"
    summary = D.run_dev_regression(proto, out, documents=authored_documents(tmp_path))
    rows = {r["name"]: r for r in summary["rows"]}
    # v1 drops Picture 1.0 / 2.2 from "one"; the fake prototype is right on all three kept regions.
    assert rows["one"]["regions"] == 3 and rows["one"]["not_scored"] == ["1.0", "2.2"]
    assert (rows["one"]["strict"], rows["one"]["no_section"], rows["one"]["numbers"]) == (3, 3, 3)
    assert rows["two"]["regions"] == 3 and rows["two"]["strict"] == 2
    assert summary["total"] == {"regions": 6, "strict": 5, "no_section": 5, "numbers": 5}
    assert summary["parser_version"] == "fake/1"
    errors = json.loads((out / "errors.json").read_text(encoding="utf-8"))
    assert errors["two"] == [{"region": "1.2", "gold": "S/2", "predicted": "S/1", "category": "Text"}]
    assert errors["one"] == []
    assert json.loads((out / "summary.json").read_text(encoding="utf-8")) == summary
    with pytest.raises(FileExistsError):
        D.run_dev_regression(proto, out, documents=authored_documents(tmp_path))


def test_first_pass_explicit_prototypes_and_per_system_totals(tmp_path):
    got = R.parse_prototypes([f"v1={tmp_path / 'a.py'}", f"code-final={tmp_path / 'b.py'}"])
    assert list(got) == ["v1", "code-final"] and got["v1"] == (tmp_path / "a.py").resolve()
    assert R.parse_prototypes(None) == {}
    for bad in (["v1"], ["=x.py"], ["v1=a.py", "v1=b.py"], ["a/b=x.py"]):
        with pytest.raises(SystemExit):
            R.parse_prototypes(bad)
    zero = {"strict": 0, "no_section": 0, "numbers": 0, "false_exclusion": 0}
    one = {"strict": 1, "no_section": 1, "numbers": 1, "false_exclusion": 0}
    rows = [{"slug": "a", "regions": 2, "prototype-v1": one, "prototype-code-final": zero, "current": zero},
            {"slug": "b", "regions": 1, "prototype-v1": one, "prototype-code-final": one, "current": zero}]
    assert R.systems(rows) == ["prototype-v1", "prototype-code-final", "current"]
    total = R.totals(rows)
    assert total["regions"] == 3 and total["prototype-v1"]["no_section"] == 2
    assert total["prototype-code-final"]["strict"] == 1 and total["current"]["strict"] == 0
    # Batch-1 summaries (single ``prototype`` key) keep their totals shape.
    legacy = [{"slug": "a", "regions": 1, "prototype": one, "current": zero}]
    assert set(R.totals(legacy)) == {"regions", "prototype", "current"}


C = load_script("classify_m1_04a_errors")


def test_batch2_error_classes_from_evidence_only():
    def cls(gold, predicted, category="Text", text="текст", single=False):
        return C.classify_evidence({"gold": gold, "predicted": predicted}, category, text, single)

    assert cls("A/AN2", "A") == (C.LAW_ANNEX, [])
    assert cls("S3/5", "S/AN2/5") == (C.NESTED_ANNEX, [])
    assert cls("S3", "S/AN2/8", "List-item", "8. Файл обмена") == (C.NESTED_ANNEX, [C.SCHEME_LIST])
    assert cls("S/II/4.1", "A/AN/II/4/4.1", single=True) == (C.DOTTED, [])
    assert cls("S/II/4.2", "A/AN", "Caption", "Таблица 1.1", single=True) == (C.CAPTION_ROOT, [])
    assert cls("S/2", "S", text="значении, определенном", single=True) == (C.PAGE_CONTINUATION, [])
    assert cls("A/ст12", "A/ст12/ч1") == (C.QUOTE, [])
    assert cls("A/ст13/6", "A/ст13/5/б/б", text="б) пункт 7") == (C.OCR_MARKER, [])
    assert cls("A/ст1", "A/7") == (C.ARTICLE, [])
    assert cls("A/AN1", None, "Footnote") == (C.FOOTNOTE, [])
    assert cls("S", "A/AN/5", text="(место для подписи должностного лица)", single=True) == (C.SIGNATURE, [])


def test_batch3_error_classes_from_evidence_only():
    def cls(gold, predicted, category="Text", text="Текст", single=False):
        return C.classify_evidence({"gold": gold, "predicted": predicted}, category, text, single)

    assert cls("A/II", "A/гл10/ст115", "Section-header", "РАЗДЕЛ II МЕРЫ") == (C.SECTION_MARKER, [])
    assert cls("A/I/гл1/ст1/ч1", "A/гл1/ст1/ч1", text="1. Настоящий Кодекс") == (C.SECTION_MARKER, [])
    assert cls("S/AN1/2", "S/AN/2") == (C.UNNUMBERED_ANNEX, [])
    assert cls("S/AN1/I", "S/I", "Caption", "Раздел I. Поступления") == (C.ATTACHED_ANNEX, [])
    assert cls("S/AN1", "S/IV/47", text="Приложение к Порядку") == (C.ATTACHED_ANNEX, [])
    assert cls("S/II", "S/II/11/5", "Section-header", "Сроки предоставления") == (C.SUBHEADING, [])
    assert cls("S/II/8", "S/II/8/б", text="По решению руководителя") == (C.CLOSING, [])
    assert cls("S/I/8.1/1", "S/I/8/4/8.1/1", text="1) по письменному обращению") == (C.CLOSING, [C.DOTTED])
    assert cls("S/AN3/11", "S/AN3", text="(серия, номер, дата выдачи)") == (C.CAPTION_ROOT, [])
    # A region that starts with a point marker is not an unnumbered subheading.
    assert cls("S/II", "S/II/9", text="9. Государственная услуга")[0] != C.SUBHEADING


def test_rescore_scoring_single_annex_is_opt_in():
    ev = load_script("evaluate_ocr_owner_gold")
    gold = {"1.1": {"owners": ["S/AN1/2"], "continuation": False}, "1.2": {"owners": ["S/3"], "continuation": False}}
    owners = {"1.1": "S/AN/2", "1.2": "S/AN1/3"}
    res, row = R.score(ev, gold, owners)
    assert row["strict"] == 0 and "single_annex_documents" not in res
    res, row = R.score(ev, gold, owners, single_annex=True)
    assert row["strict"] == 1 and res["single_annex_documents"] == ["S"]
    # The remaining error is a transfer from the attached document's body into its annex.
    (error,) = res["errors"]
    assert ev.cross_scope_v2(error["gold"], error["predicted"], res["attached_count"], frozenset({"S"}))
    assert ev.first_scope(error["gold"]) == ev.first_scope(error["predicted"])  # the old check misses it


def test_classifier_reads_single_annex_paths_before_evidence_rules():
    ev = load_script("evaluate_ocr_owner_gold")
    single = frozenset({"S"})
    error = {"gold": "S/AN1/2", "predicted": "S/AN/2/а"}
    read = {"gold": ev.number_single_annex(error["gold"], single),
            "predicted": ev.number_single_annex(error["predicted"], single)}
    assert read == {"gold": "S/AN1/2", "predicted": "S/AN1/2/а"}
    assert C.classify_evidence(read, "Text", "По решению", False) == (C.CLOSING, [])
    # Without the equivalence the same error is the unnumbered-annex class (batch-3 reading).
    assert C.classify_evidence({"gold": "S/AN1/2", "predicted": "S/AN/2"}, "Text", "Т", False) == (
        C.UNNUMBERED_ANNEX, [])


# ---- cycle 3 / A2: freeze coverage and single-annex defaults for new batches


def _stub_freeze_world(monkeypatch, tmp_path):
    """Run do_freeze / do_run on a throw-away root with a fake prototype and no git."""
    import types

    monkeypatch.setattr(R, "ROOT", tmp_path)
    proto = tmp_path / "proto.py"
    proto.write_text("print('p')\n", encoding="utf-8")
    code_final = tmp_path / "code-final.sha256"
    code_final.write_text(f"{R.sha(proto)} *docs/assets/ocr_logical_structure.py\n", encoding="utf-8")
    monkeypatch.setattr(R, "PROTOTYPE", proto)
    monkeypatch.setattr(R, "CODE_FINAL", code_final)
    monkeypatch.setattr(R, "tracked", lambda batch, slugs, gold_freeze, extra=(): {R.rel(proto): R.sha(proto)})
    monkeypatch.setattr(R.subprocess, "run", lambda *a, **k: types.SimpleNamespace(stdout="abc123\n"))
    gold_file = tmp_path / "gold.txt"
    gold_file.write_text("1.1 S\n", encoding="utf-8")
    freeze = tmp_path / "gold-freeze" / "freeze.json"
    freeze.parent.mkdir()
    freeze.write_text(json.dumps({"files": {"gold.txt": R.sha(gold_file)}}), encoding="utf-8")
    return freeze, gold_file


def test_single_annex_is_default_only_after_batch_3():
    assert [R.default_single_annex(b) for b in ("batch-01", "batch-02", "batch-03", "batch-04")] == [
        False, False, False, True]


def test_freeze_records_single_annex_for_batch_4_but_not_batch_3(monkeypatch, tmp_path):
    freeze, _ = _stub_freeze_world(monkeypatch, tmp_path)
    R.do_freeze(tmp_path / "run3", "batch-03", ["a"], freeze, "v1")
    R.do_freeze(tmp_path / "run4", "batch-04", ["a"], freeze, "v1")
    R.do_freeze(tmp_path / "run4x", "batch-04", ["a"], freeze, "v1", single_annex=False)
    R.do_freeze(tmp_path / "run3x", "batch-03", ["a"], freeze, "v1", single_annex=True)
    rec = {n: json.loads((tmp_path / n / "freeze.json").read_text(encoding="utf-8"))
           for n in ("run3", "run4", "run4x", "run3x")}
    assert "single_annex_equivalence" not in rec["run3"] and "single_annex_equivalence" not in rec["run4x"]
    assert rec["run4"]["single_annex_equivalence"] is True and rec["run3x"]["single_annex_equivalence"] is True
    assert "gold_freeze_addendum" not in rec["run4"]


def test_freeze_hashes_and_run_checks_the_gold_addendum(monkeypatch, tmp_path):
    freeze, gold_file = _stub_freeze_world(monkeypatch, tmp_path)
    extra = tmp_path / "exceptions.json"
    extra.write_text("{}", encoding="utf-8")
    addendum = freeze.with_name("freeze-addendum.json")
    addendum.write_text(json.dumps({"base_freeze_sha256": "wrong", "files": {"exceptions.json": R.sha(extra)}}),
                        encoding="utf-8")
    with pytest.raises(SystemExit, match="base_freeze_sha256"):
        R.do_freeze(tmp_path / "bad", "batch-04", ["a"], freeze, "v1")
    addendum.write_text(json.dumps({"base_freeze_sha256": R.sha(freeze), "files": {"exceptions.json": R.sha(extra)}}),
                        encoding="utf-8")
    out = tmp_path / "run"
    R.do_freeze(out, "batch-04", ["a"], freeze, "v1")
    record = json.loads((out / "freeze.json").read_text(encoding="utf-8"))
    assert record["gold_freeze_addendum"] == "gold-freeze/freeze-addendum.json"
    assert record["gold_freeze_addendum_sha256"] == R.sha(addendum)
    assert record["files"]["gold-freeze/freeze-addendum.json"] == R.sha(addendum)
    R.check_addendum(addendum, freeze)
    extra.write_text("changed", encoding="utf-8")
    with pytest.raises(SystemExit, match="exceptions.json"):
        R.check_addendum(addendum, freeze)
    with pytest.raises(SystemExit, match="gold changed after freeze addendum|changed after freeze"):
        R.do_run(out)


class _FakeEvaluator:
    calls = []

    @staticmethod
    def load_gold(path):
        return {"1.1": {"owners": ["S"], "continuation": False}}

    @staticmethod
    def from_logical(data):
        return {"1.1": "S"}, {}

    @classmethod
    def evaluate(cls, g, owners, cont=None, single_annex=False):
        cls.calls.append(single_annex)
        return {k: {"correct": 1} for k in R.METRICS} | {"errors": []}


class _FakeExporter:
    @staticmethod
    def export_current(ext, claim, mode):
        return {"1.1": "S"}, {}


def _run_with(monkeypatch, tmp_path, batch):
    import types

    tmp_path = tmp_path / batch
    tmp_path.mkdir()
    freeze, _ = _stub_freeze_world(monkeypatch, tmp_path)
    ext = tmp_path / "ext.json"
    ext.write_text("{}", encoding="utf-8")
    src = tmp_path / "src.json"
    src.write_text(json.dumps({"declared_identity": "x"}), encoding="utf-8")
    monkeypatch.setattr(R, "extraction", lambda slug: ext)
    monkeypatch.setattr(R, "gold", lambda slug, suffix="gold": ext)
    monkeypatch.setattr(R, "source", lambda b, slug: src)
    monkeypatch.setattr(R, "load", lambda name, path: _FakeEvaluator if "evaluate" in name else _FakeExporter)
    monkeypatch.setattr(R, "apply_convention", lambda g, e, c: (g, []))
    monkeypatch.setattr(R, "export_current", lambda exporter, e, claim: ({"1.1": "S"}, {"route": "x"}))

    def fake_run(cmd, **kw):
        if "rev-parse" in cmd:
            return types.SimpleNamespace(stdout="abc123\n")
        Path(cmd[cmd.index("--output") + 1]).write_text(json.dumps({"regions": []}), encoding="utf-8")

    monkeypatch.setattr(R.subprocess, "run", fake_run)
    out = tmp_path / f"run-{batch}"
    R.do_freeze(out, batch, ["a"], freeze, "v1")
    _FakeEvaluator.calls.clear()
    R.do_run(out)
    return json.loads((out / "summary.json").read_text(encoding="utf-8")), list(_FakeEvaluator.calls)


def test_synthetic_batch_4_run_scores_with_single_annex_and_batch_3_does_not(monkeypatch, tmp_path):
    summary4, calls4 = _run_with(monkeypatch, tmp_path, "batch-04")
    assert summary4["single_annex_equivalence"] is True and calls4 == [True, True]
    summary3, calls3 = _run_with(monkeypatch, tmp_path, "batch-03")
    assert "single_annex_equivalence" not in summary3 and calls3 == [False, False]


def test_classifier_cross_scope_v2_defaults_on_for_new_batches():
    src = (ASSETS / "classify_m1_04a_errors.py").read_text(encoding="utf-8")
    assert 'batch not in ("batch-01", "batch-02", "batch-03")' in src
