"""Raw UTF-8 legal HTML adapter and diagnostic report; no edition admission."""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from html import escape
from pathlib import Path

from .native_text import _cleanup, _NativeHTML
from .structure import SUP_DIGITS, build_structure

EXTRACTOR_VERSION = "raw-legal-html/1"


class _RawHTML(_NativeHTML):
    def __init__(self, html: str, digest: str):
        super().__init__(html, digest)
        self.paragraphs: dict = {}
        self.unsupported_regions: list[dict] = []

    def handle_starttag(self, tag, attrs):
        start = self.scalar_offset()
        super().handle_starttag(tag, attrs)
        if self.stack and self.stack[-1]["tag"] == tag:
            self.stack[-1]["raw_start"] = start
        tags = {entry["tag"] for entry in self.stack}
        if tag in {"img", "table", "ul", "ol"} and "body" in tags and not tags & {
            "script", "style", "label"
        }:
            paragraph = next(
                (e["paragraph"] for e in reversed(self.stack) if e["tag"] == "p"),
                None,
            )
            locator = "/html/" + "/".join(e["tag"] for e in self.stack[1:])
            if tag == "img":
                locator += "/img"
            region = {
                "region_id": len(self.unsupported_regions),
                "tag": tag,
                "paragraph": paragraph,
                "reason": "unsupported_nontext_or_structure",
                "source_span": {
                    "source_asset_sha256": self.digest,
                    "html_locator": locator,
                    "char_start": start,
                    "char_end": start + len(self.get_starttag_text()),
                    "offset_unit": "unicode_codepoints_in_utf8_html",
                },
            }
            self.unsupported_regions.append(region)
            if tag == "img":
                self.finish_region(region, region["source_span"]["char_end"])
            else:
                self.stack[-1]["unsupported_region"] = region
        if tag == "p":
            self.paragraphs[self.paragraph_count] = {
                "start": start,
                "classes": dict(attrs).get("class", "").split(),
            }

    def finish_region(self, region, end):
        span = region["source_span"]
        span["char_end"] = end
        span["locator"] = (
            f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
        )
        region["original_html"] = self.html[span["char_start"] : end]

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1]["tag"] == tag:
            region = self.stack[-1].get("unsupported_region")
            if region is not None:
                end = self.html.index(">", self.scalar_offset()) + 1
                self.finish_region(region, end)
        if tag == "p":
            self.paragraphs[self.paragraph_count]["end"] = (
                self.html.index(">", self.scalar_offset()) + 1
            )
        super().handle_endtag(tag)

    def token(self, raw, decoded, kind="text"):
        annotation = next(
            (
                e.get("raw_start")
                for e in self.stack
                if set(e["attrs"].get("class", "").split()) & {"mark", "markx"}
            ),
            None,
        )
        if self.groups and self.groups[-1]["tokens"]:
            if self.groups[-1]["tokens"][-1].get("annotation_start") != annotation:
                self.groups[-1]["key"] = None
        super().token(raw, decoded, kind)
        token = self.text_nodes[-1]
        token["annotation_start"] = annotation
        token["references"] = [
            {
                "start": e.get("raw_start"),
                "command": e["attrs"].get("cmdprm"),
                "href": e["attrs"].get("href"),
            }
            for e in self.stack
            if e["attrs"].get("cmdprm") or e["tag"] == "a"
        ]
        token["superscript"] = any(
            entry["tag"] == "sup"
            or set(entry["attrs"].get("class", "").split()) & {"W9", "WB"}
            for entry in self.stack
        )
        span = token["source_span"]
        span.pop("json_pointer")
        span["html_locator"] = span["html_locator"].removeprefix("/redtext")
        span["offset_unit"] = "unicode_codepoints_in_utf8_html"
        span["locator"] = (
            f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
        )


def extract_html(payload: bytes) -> dict:
    """Retain every token, decoding/cleanup map and original paragraph range."""
    html = payload.decode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    parser = _RawHTML(html, digest)
    parser.feed(html)
    parser.close()
    if parser.stack or not parser.saw_body:
        raise ValueError("incomplete HTML document")
    blocks: list[dict] = []
    for group in parser.groups:
        tokens = group["tokens"]
        original = "".join(t["decoded_text"] for t in tokens)
        text, mapping = _cleanup(original)
        numbering = "".join(
            (
                "^"
                if t["superscript"] and (i == 0 or not tokens[i - 1]["superscript"])
                else ""
            )
            + t["decoded_text"]
            for i, t in enumerate(tokens)
        )
        paragraph = parser.paragraphs.get(group["paragraph"], {})
        start = paragraph.get("start", tokens[0]["source_span"]["char_start"])
        end = paragraph.get("end", tokens[-1]["source_span"]["char_end"])
        decoded_offset = 0
        decoding = []
        for token in tokens:
            decoding.append(
                {
                    "text_node_id": token["text_node_id"],
                    "decoded_start": decoded_offset,
                    "decoded_end": decoded_offset + len(token["decoded_text"]),
                }
            )
            decoded_offset += len(token["decoded_text"])
        references = {}
        for token in tokens:
            for reference in token["references"]:
                key = reference["start"]
                if key not in references:
                    references[key] = {**reference, "text": "", "text_node_ids": []}
                references[key]["text"] += token["decoded_text"]
                references[key]["text_node_ids"].append(token["text_node_id"])
        span = {
            **tokens[0]["source_span"],
            "char_end": tokens[-1]["source_span"]["char_end"],
        }
        span["locator"] = (
            f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
        )
        blocks.append(
            {
                "references": list(references.values()),
                "block_id": len(blocks),
                "paragraph": group["paragraph"],
                "html_id": group["html_id"],
                "classes": paragraph.get("classes", []),
                "text": text,
                "display_text": _cleanup(
                    "".join(
                        t["decoded_text"].translate(SUP_DIGITS)
                        if t["superscript"]
                        else t["decoded_text"]
                        for t in tokens
                    )
                )[0],
                "original_text": original,
                "numbering_text": _cleanup(numbering)[0],
                "original_html": html[start:end],
                "html_start": start,
                "html_end": end,
                "source_span": span,
                "text_node_ids": [t["text_node_id"] for t in tokens],
                "cleanup_mapping": mapping,
                "decoding_mapping": decoding,
                "note": group["note"],
                "unsupported_structure": group["unsupported"],
                "exclusion_reason": group["reason"],
            }
        )
    return {
        "schema_version": "raw-html-extraction/1",
        "extractor_version": EXTRACTOR_VERSION,
        "source_asset_sha256": digest,
        "text_nodes": parser.text_nodes,
        "unsupported_regions": parser.unsupported_regions,
        "blocks": blocks,
    }


def build_tree(extraction: dict, declared_identity: str | None = None) -> dict:
    """Compatibility envelope for the raw HTML diagnostic command."""
    tree = build_structure(extraction, declared_identity)
    return {**tree, "schema_version": "housing-html-ast/1"}


def validate(extraction: dict, tree: dict, payload: bytes) -> dict:
    """Check technical invariants independently of reported AST counters."""
    html = payload.decode("utf-8")
    problems = []
    digest = hashlib.sha256(payload).hexdigest()
    if (
        extraction["source_asset_sha256"] != digest
        or tree["source_asset_sha256"] != digest
    ):
        problems.append("source_hash_mismatch")
    # Re-discover source regions from the payload, not saved lists/counters.
    region_parser = _RawHTML(html, digest)
    region_parser.feed(html)
    region_parser.close()
    expected_regions = region_parser.unsupported_regions
    if extraction.get("unsupported_regions", []) != expected_regions:
        problems.append("source_region_coverage")
    if tree.get("unresolved_regions", []) != expected_regions:
        problems.append("region_accounting_or_mapping")
    tokens = extraction["text_nodes"]
    if [t["text_node_id"] for t in tokens] != list(range(len(tokens))):
        problems.append("token_id_sequence")
    for token in tokens:
        span = token["source_span"]
        if (
            html[span["char_start"] : span["char_end"]] != token["raw_text"]
            or span["locator"]
            != f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
        ):
            problems.append(f"token_locator:{token['text_node_id']}")
    tokens_by_id = {t["text_node_id"]: t for t in tokens}
    for block in extraction["blocks"]:
        span = block["source_span"]
        referenced = [
            tokens_by_id[i] for i in block["text_node_ids"] if i in tokens_by_id
        ]
        if not referenced or len(referenced) != len(block["text_node_ids"]):
            problems.append(f"block_token_span:{block['block_id']}")
        else:
            expected_span = {
                **referenced[0]["source_span"],
                "char_end": referenced[-1]["source_span"]["char_end"],
            }
            expected_span["locator"] = (
                f"{expected_span['html_locator']}:chars:"
                f"{expected_span['char_start']}:{expected_span['char_end']}"
            )
            if span != expected_span:
                problems.append(f"block_token_span:{block['block_id']}")
        if (
            span["locator"]
            != f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
        ):
            problems.append(f"block_locator:{block['block_id']}")
        if (
            "".join(m["before"] for m in block["cleanup_mapping"])
            != block["original_text"]
            or "".join(m["after"] for m in block["cleanup_mapping"]) != block["text"]
            or re.sub(r"\s", "", block["original_text"])
            != re.sub(r"\s", "", block["text"])
            or html[block["html_start"] : block["html_end"]] != block["original_html"]
        ):
            problems.append(f"block_mapping:{block['block_id']}")
    entries = [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]
    blocks_by_id = {b["block_id"]: b for b in extraction["blocks"]}
    for entry in entries:
        span = entry["source_span"]
        source_block = blocks_by_id.get(entry["block_id"])
        if (
            source_block is None
            or span != source_block["source_span"]
            or entry["text_node_ids"] != source_block["text_node_ids"]
        ):
            problems.append(f"ast_block_mapping:{entry['block_id']}")
        if (
            span["locator"]
            != f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
        ):
            problems.append(f"ast_block_locator:{entry['block_id']}")
    assigned = [i for b in entries for i in b["text_node_ids"]]
    if Counter(assigned) != Counter(range(len(tokens))):
        problems.append("token_accounting")
    if Counter(b["block_id"] for b in entries) != Counter(
        b["block_id"] for b in extraction["blocks"]
    ):
        problems.append("block_accounting")
    by_address = {n["address"]: n for n in tree["nodes"]}
    if len(by_address) != len(tree["nodes"]):
        problems.append("duplicate_addresses")
    for node in tree["nodes"]:
        parent = node["parent_address"]
        if parent != "act" and parent not in by_address:
            problems.append(f"missing_parent:{node['address']}")
        seen = {node["address"]}
        while parent in by_address:
            if parent in seen:
                problems.append(f"parent_cycle:{node['address']}")
                break
            seen.add(parent)
            parent = by_address[parent]["parent_address"]
    return {
        "schema_version": "housing-html-validation/1",
        "source_asset_sha256": digest,
        "integrity_pass": not problems,
        "problems": problems,
        "structure_complete": not expected_regions
        and not tree.get("unresolved_regions", [])
        and not tree["unresolved_blocks"]
        and tree["identity_decision"]["status"] in {"source_identity_matches", "claim_matches_header"},
        "counts_by_kind": dict(Counter(n["kind"] for n in tree["nodes"])),
        "text_node_count": len(tokens),
        "unresolved_block_count": len(tree["unresolved_blocks"]),
        "unresolved_region_count": len(tree.get("unresolved_regions", [])),
        "standalone_note_scope_unresolved": sum(
            n["kind"] == "note" and n["scope_status"] == "unresolved"
            for n in tree["nodes"]
        ),
        "edition_admission": False,
        "limitations": [
            "Shared native federal-law/code grammar; unsupported structures remain unresolved; no PDF qualification.",
            "Unnumbered paragraph ordinals and parents are syntactic diagnostics, not certified legal paragraph numbers.",
            "Standalone note scope is unresolved; source claims do not establish legal applicability.",
            "Complete token accounting is not independent legal AST accuracy; dated admission remains blocked.",
        ],
    }


LABELS = {
    "section": "Раздел",
    "chapter": "Глава",
    "subchapter": "Параграф главы",
    "article": "Статья",
    "part": "Часть",
    "item": "Пункт",
    "subitem": "Подпункт",
    "paragraph": "Абзац (диагностический)",
    "header": "Реквизиты",
    "note": "Примечание",
}


def render_report(tree: dict, validation: dict) -> str:
    """An inert offline tree: original HTML is escaped, never executed."""
    nodes = {n["address"]: n for n in tree["nodes"]}
    title = escape(tree["identity_decision"].get("title") or "Документ")

    def render(node):
        kind = node["kind"]
        label = LABELS[kind] + " " + node.get("number_display", "")
        label += " — " + (node.get("title") or node["display_text"][:100])
        opened = " open" if kind in {"section", "chapter"} else ""
        scope = (
            " | Область применения не установлена"
            if node.get("scope_status") == "unresolved"
            else ""
        )
        children = "".join(render(nodes[a]) for a in node["children"])
        return (
            f'<details class="node {kind}" id="n{node["block_id"]}"{opened}>'
            f"<summary>{escape(label)}</summary><p>{escape(node['display_text'])}</p>"
            f"<small>{escape(node['address'])} | источник: {escape(str(node['html_id']))} | "
            f"символы {node['html_start']}:{node['html_end']}{escape(scope)}</small>"
            '<details class="source"><summary>Исходный HTML</summary><pre>'
            + escape(node["original_html"])
            + "</pre></details>"
            + children
            + "</details>"
        )

    toc = " ".join(
        f'<a href="#n{n["block_id"]}">{escape(n["number_display"])}</a>'
        for n in tree["nodes"]
        if n["kind"] == "article"
    )
    roots = "".join(render(n) for n in tree["nodes"] if n["parent_address"] == "act")
    unresolved = "".join(
        "<details><summary>"
        + escape(b["reason"])
        + "</summary><pre>"
        + escape(b["original_html"])
        + "</pre></details>"
        for b in [*tree["unresolved_blocks"], *tree.get("unresolved_regions", [])]
    )
    summary = escape(json.dumps(validation, ensure_ascii=False, indent=2))
    return (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
        f"<title>{title} — диагностика структуры</title><style>"
        "body{font:16px/1.5 system-ui,sans-serif;color:#17212e;background:#f7f9fc;max-width:1200px;padding:24px;margin:auto}"
        "h1{font-size:27px}.warning{border-left:4px solid #bd7621;padding:12px;background:#fff0d8}"
        ".node{margin:8px 0 8px 16px;padding:8px;border-left:2px solid #cbd5e1}"
        "summary{cursor:pointer;overflow-wrap:anywhere}.section>summary,.chapter>summary,.article>summary{font-weight:650}"
        "small{color:#576579}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}"
        ".note{background:#eef2f6}.source{margin-top:8px}nav a{display:inline-block;padding:3px 8px;color:#17499a}"
        ":target{outline:2px solid #3980dc}</style></head><body>"
        f'<h1>{title}: дерево документа</h1><p class="warning">Диагностический разбор, не юридически допущенная редакция. '
        "Даты действия не установлены. Ненумерованные абзацы и их родители требуют контрольной проверки.</p>"
        "<details><summary>Проверки и счётчики</summary><pre>"
        + summary
        + "</pre></details>"
        "<h2>Статьи</h2><nav>"
        + toc
        + "</nav><h2>Структура и исходные фрагменты</h2>"
        + roots
        + "<h2>Неразобранные блоки</h2>"
        + (unresolved or "<p>Не обнаружены.</p>")
        + "</body></html>"
    )


def parse_file(source: Path, output: Path, declared_identity: str | None = None) -> dict:
    source, output = source.resolve(), output.resolve()
    if source.is_relative_to(output) or output == source.parent:
        raise ValueError("output overlaps source directory")
    payload = source.read_bytes()
    extraction = extract_html(payload)
    tree = build_tree(extraction, declared_identity)
    validation = validate(extraction, tree, payload)
    if not validation["integrity_pass"]:
        raise ValueError(
            "integrity validation failed: " + ", ".join(validation["problems"])
        )
    artifacts = {
        name: (
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        for name, value in (
            ("extraction.json", extraction),
            ("ast.json", tree),
            ("validation.json", validation),
        )
    }
    artifacts["report.html"] = render_report(tree, validation).encode("utf-8")
    if output.exists():
        if not output.is_dir() or {p.name for p in output.iterdir()} != set(artifacts):
            raise ValueError(
                "existing output is incomplete or conflicting; choose a fresh directory"
            )
        for name, data in artifacts.items():
            if (output / name).read_bytes() != data:
                raise ValueError("immutable output conflict: " + name)
        result = "unchanged"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="housing-parser-", dir=output.parent
        ) as temporary:
            stage = Path(temporary) / "artifacts"
            stage.mkdir()
            for name, data in artifacts.items():
                (stage / name).write_bytes(data)
            os.replace(stage, output)
        result = "new"
    return {
        "result": result,
        "output_dir": str(output),
        "source_asset_sha256": extraction["source_asset_sha256"],
        "integrity_pass": validation["integrity_pass"],
        "structure_complete": validation["structure_complete"],
        "counts_by_kind": validation["counts_by_kind"],
        "unresolved_block_count": validation["unresolved_block_count"],
        "edition_admission": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--identity", help="Optional identity claim to compare with source signing fields")
    args = parser.parse_args(argv)
    try:
        result = parse_file(args.input, args.output_dir, args.identity)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(
            json.dumps({"result": "failed", "error": str(error)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["structure_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
