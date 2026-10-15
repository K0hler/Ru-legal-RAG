"""Bounded offline sidecar experiment; never writes production or source archives."""

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import copy
from datetime import UTC, datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time

from bs4 import BeautifulSoup

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from legal_rag.corpus.compiler import load_input  # noqa: E402
from legal_rag.corpus.native_text import extract_native  # noqa: E402
from legal_rag.corpus.structure import _identity  # noqa: E402

VERSION = "official-structure-experiment/1"
DEFAULT_ROOT = PROJECT / "data/m1/experiments/official-structure-20261015-v1"
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
KINDS = {"раздел": "section", "глава": "chapter", "статья": "article",
         "часть": "part", "пункт": "item", "подпункт": "subitem", "приложение": "annex"}
SUPERSCRIPT = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
INTRO = re.compile(r"(?:следующего\s+содержания|в\s+следующей\s+редакции)\s*:", re.I)
MARKER = re.compile(r'^(?:["«]?Статья\s+\d|["«]?Глава\s+\d|["«]?\d+(?:[.\-^]\d+)*[.)]\s|["«]?[а-яa-z]\)\s)')


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def retain(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"immutable artifact conflict: {path}")
        return "unchanged"
    path.write_bytes(data)
    return "new"


class Anchors(HTMLParser):
    """Full raw element spans, independently of the existing text extractor."""

    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.html = html
        self.lines = [0, *(m.end() for m in re.finditer("\n", html))]
        self.stack, self.ids = [], {}
        self.feed(html)
        self.close()
        if self.stack:
            raise ValueError("unclosed HTML elements")

    def scalar_offset(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        row = {"tag": tag, "start": self.scalar_offset(),
               "end": self.scalar_offset() + len(self.get_starttag_text())}
        if attrs.get("id"):
            if attrs["id"] in self.ids:
                raise ValueError("duplicate HTML id")
            self.ids[attrs["id"]] = row
        if tag not in VOID:
            self.stack.append(row)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1]["tag"] != tag:
            raise ValueError("unbalanced HTML")
        row = self.stack.pop()
        row["end"] = self.html.index(">", self.scalar_offset()) + 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)


def numbering_markup(markup):
    soup = BeautifulSoup(markup, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for note in list(soup.select(".mark, .markx, label, script, style")):
        note.decompose()
    for sup in list(soup.select("sup, .W9, .WB")):
        sup.replace_with("^" + sup.get_text().strip())
    return " ".join(soup.get_text("", strip=False).split()).lstrip("$")


def explicit_number(text, unit):
    patterns = {
        "статья": r"^Статья\s+(\d+(?:[.\-^]\d+)*)",
        "часть": r"^часть\s+(\d+(?:[.\-^]\d+)*)",
        "пункт": r"^пункт\s+(\d+(?:[.\-^]\d+)*)",
        "подпункт": r'^(?:подпункт\s+)["«]?([а-яa-z0-9]+(?:[.\-^]\d+)*)',
        "глава": r"^Глава\s+([0-9IVXLCDM]+(?:[.\-^]\d+)*)",
        "раздел": r"^(?:РАЗДЕЛ\s+)?([0-9IVXLCDM]+(?:[.\-^]\d+)*)(?=[.\s]|$)",
        "приложение": r"^ПРИЛОЖЕНИЕ\s+(?:№\s*)?(\d+(?:[.\-^]\d+)*)",
    }
    m = re.match(patterns.get(unit, r"(?!)"), text, re.I)
    return m[1] if m else None


def source_marker_number(text, unit):
    if unit in {"пункт", "часть", "подпункт"}:
        m = re.match(r'^["«]?([0-9]+(?:[.\-^]\d+)*|[а-яa-z](?:\^\d+)?)[.)](?:\s|$)', text, re.I)
        return m[1] if m else None
    return explicit_number(text, unit)


def normalized_units(html, rows, family):
    anchors = Anchors(html).ids
    soup = BeautifulSoup(html, "html.parser")
    dom = {p["id"]: p for p in soup.find_all(id=True)}
    nodes, stack, seen = [], [], set()
    sibling_end = {}
    marker_checks = []
    for row in rows:
        if row["id"] in seen:
            raise ValueError("duplicate sidecar id")
        seen.add(row["id"])
        if row["np"] not in anchors or row["npe"] not in anchors:
            raise ValueError("missing HTML anchor")
        while stack and stack[-1]["level"] >= row["lvl"]:
            stack.pop()
        parent = stack[-1] if stack else None
        if row["lvl"] != (parent["level"] + 1 if parent else 0):
            raise ValueError("sidecar level jump")
        if parent and not row["id"].startswith(parent["source_id"] + "_"):
            raise ValueError("sidecar parent prefix conflict")
        start, end = anchors[row["np"]]["start"], anchors[row["npe"]]["end"]
        if start >= end or parent and not parent["html_start"] <= start < end <= parent["html_end"]:
            raise ValueError("invalid or non-nested sidecar range")
        pid = parent["source_id"] if parent else None
        if start < sibling_end.get(pid, -1):
            raise ValueError("overlapping sibling ranges")
        sibling_end[pid] = end
        caption = numbering_markup(row["caption"])
        source_text = numbering_markup(str(dom[row["np"]]))
        kind = KINDS.get(row["unit"], "unresolved_attachment")
        if row["unit"] == "вложение":
            if re.fullmatch(r"Примечания\s*[:.]?", caption, re.I):
                kind = "notes_section"
            elif re.fullmatch(r"примечание\s+\d+", caption, re.I):
                kind = "normative_note"
            elif row["lvl"] == 0 and re.match(r"^(ПРАВИЛА|ПОЛОЖЕНИЕ|ИЗМЕНЕНИЯ)\b", caption):
                kind = "approved_text"
        if family == "government_resolution" and row["unit"] == "пункт":
            kind = "item" if re.match(r"^\d+(?:[.\-^]\d+)*\)\s", source_text) else "point"
        number = explicit_number(caption, row["unit"])
        canonical = number.replace("^", ".") if number else None
        base, _, exponent = (number or "").partition("^")
        display = base + exponent.translate(SUPERSCRIPT) if number else None
        source_number = source_marker_number(source_text, row["unit"])
        mismatch = number is not None and (source_number or "").replace("^", ".") != canonical
        marker_checks.append({"source_id": row["id"], "html_id": row["np"],
                              "expected_number": canonical,
                              "dom_number": source_number.replace("^", ".") if source_number else None,
                              "matches": not mismatch,
                              "source_prefix": source_text[:160]})
        path = [*(parent["provision_path"] if parent else []),
                {"kind": kind, "number": canonical, "source_id": row["id"]}]
        n = {"source_id": row["id"], "parent_source_id": pid,
             "kind": kind, "number_canonical": canonical, "number_display": display,
             "caption": row["caption"], "level": row["lvl"], "source_state": row.get("state"),
             "source_unit": row["unit"], "np": row["np"], "npe": row["npe"],
             "html_start": start, "html_end": end, "provision_path": path,
             "own_block_ids": [], "region_ids": []}
        nodes.append(n)
        stack.append(n)
    return nodes, marker_checks, soup


class Owners:
    """Resolve raw spans to the deepest containing unit; report crossing boundaries."""

    def __init__(self, nodes):
        self.rows = sorted(nodes, key=lambda n: (n["html_start"], n["level"]))
        self.starts = [n["html_start"] for n in self.rows]
        self.by_id = {n["source_id"]: n for n in nodes}

    def find(self, start, end):
        i = bisect_right(self.starts, start) - 1
        if i < 0:
            return None
        n = self.rows[i]
        while n:
            if n["html_start"] <= start and end <= n["html_end"]:
                return n["source_id"]
            n = self.by_id.get(n["parent_source_id"])
        return None


def quote_candidates(blocks):
    """Independent diagnostics only: do not silently manufacture quoted legal trees."""
    paragraphs = {}
    for b in blocks:
        if b["role"] not in {"technical", "editorial_note"} and b["text"].strip():
            paragraphs.setdefault(b["paragraph"], []).append(b)
    ps = [{"paragraph": key, "text": " ".join(b["text"] for b in bs),
           "block_ids": [b["block_id"] for b in bs], "html_id": bs[0]["html_id"],
           "owner": bs[0]["owner_source_id"]} for key, bs in paragraphs.items()]
    found, starts = [], set()
    for i, p in enumerate(ps):
        for m in INTRO.finditer(p["text"]):
            j, tail = i, p["text"][m.end():].lstrip()
            if not tail and i + 1 < len(ps):
                j, tail = i + 1, ps[i + 1]["text"].lstrip()
            if not tail.startswith(('"', '«', '“')) or (j, tail) in starts:
                continue
            starts.add((j, tail))
            opening = tail[0]
            closing = {'"': '"', '«': '»', '“': '”'}[opening]
            balance, finish = 0, None
            for k in range(j, len(ps)):
                text = tail if k == j else ps[k]["text"]
                if opening == closing:
                    balance ^= text.count(opening) % 2
                else:
                    balance += text.count(opening) - text.count(closing)
                if balance == 0:
                    finish = k
                    break
            selected = ps[j:(finish + 1 if finish is not None else j + 1)]
            found.append({"reason": "amendment_quote_not_typed_by_sidecar",
                          "intro_html_id": p["html_id"], "start_html_id": ps[j]["html_id"],
                          "end_html_id": ps[finish]["html_id"] if finish is not None else None,
                          "owner_source_id": ps[j]["owner"], "closed_heuristically": finish is not None,
                          "paragraph_count": len(selected), "prefix": tail[:240],
                          "block_ids": [x for q in selected for x in q["block_ids"]]})
    return found


def build(record, raw, sidecar):
    asset = {"sha256": record["source_sha256"], "evidence": {"locator": record["locator"]}}
    if digest(raw) != asset["sha256"] or digest(sidecar) != record["response_sha256"]:
        raise ValueError("source or sidecar hash mismatch")
    html = json.loads(raw)[record["locator"][2:]]
    response = json.loads(sidecar)
    expected_status = 200 if record["url"].startswith("http://ips.pravo.gov.ru/") else 0
    if response.get("error") or response.get("status") != expected_status or not isinstance(response.get("data"), list):
        raise ValueError("invalid source response")
    extraction = extract_native(asset, raw)
    source_blocks = extraction["pages"][0]["blocks"]
    identity = _identity(source_blocks, record["declared_identity"])
    if identity["status"] != "claim_matches_header":
        raise ValueError("source identity is not resolved against the input claim")
    nodes, marker_checks, soup = normalized_units(html, response["data"], identity["family"])
    owners = Owners(nodes)
    by_id = owners.by_id
    byte_offsets, total_bytes = [0], 0
    for char in html:
        total_bytes += len(char.encode())
        byte_offsets.append(total_bytes)
    html_bytes = html.encode()
    blocks, token_ids, token_errors, byte_errors = [], [], [], []
    for original in source_blocks:
        b = copy.deepcopy(original)
        span = b["source_span"]
        owner = owners.find(span["char_start"], span["char_end"])
        previous = owners.find(span["char_start"], span["char_start"])
        role = ("technical" if b["exclusion_reason"] else
                "editorial_note" if b["note"] or set(b["classes"]) & {"A", "F"} else
                "table_cell" if b.get("table_cell") is not None else
                "provision_text" if owner else "document_context")
        b.update(owner_source_id=owner, role=role,
                 adjacent_source_id=previous if role == "editorial_note" else None)
        span.update(utf8_byte_start=byte_offsets[span["char_start"]],
                    utf8_byte_end=byte_offsets[span["char_end"]],
                    byte_offset_unit="utf8_bytes_in_decoded_html_scalar")
        if html_bytes[span["utf8_byte_start"]:span["utf8_byte_end"]].decode() != html[span["char_start"]:span["char_end"]]:
            byte_errors.append(b["block_id"])
        if owner:
            by_id[owner]["own_block_ids"].append(b["block_id"])
        for tid in b["text_node_ids"]:
            token_ids.append(tid)
            t = extraction["text_nodes"][tid]
            s = t["source_span"]
            if html[s["char_start"]:s["char_end"]] != t["raw_text"]:
                token_errors.append(tid)
        blocks.append(b)
    regions = copy.deepcopy(extraction["unsupported_regions"])
    for region in regions:
        s = region["source_span"]
        owner = owners.find(s["char_start"], s["char_end"])
        region["owner_source_id"] = owner
        if owner:
            by_id[owner]["region_ids"].append(region["region_id"])
        if html[s["char_start"]:s["char_end"]] != region["original_html"]:
            raise ValueError("region locator mismatch")
    starts = {n["np"] for n in nodes}
    marker_gaps = []
    for b in blocks:
        if b["role"] != "provision_text" or b["html_id"] in starts:
            continue
        ancestor = by_id.get(b["owner_source_id"])
        in_notes = False
        while ancestor:
            in_notes |= ancestor["kind"] in {"notes_section", "normative_note"}
            ancestor = by_id.get(ancestor["parent_source_id"])
        if not in_notes and "N" not in b["classes"] and MARKER.match(b["numbering_text"]):
            marker_gaps.append({"html_id": b["html_id"], "block_id": b["block_id"],
                                "owner_source_id": b["owner_source_id"],
                                "prefix": b["numbering_text"][:240]})
    quotes = quote_candidates(blocks)
    issues = []
    if any(not x["matches"] for x in marker_checks):
        issues.append("caption_number_disagrees_with_html")
    if any(n["kind"].startswith("unresolved") for n in nodes):
        issues.append("unknown_source_unit_role")
    if marker_gaps:
        issues.append("numbered_units_without_sidecar_nodes")
    if quotes:
        issues.append("amendment_quote_scope_not_supplied")
    tokens = extraction["text_nodes"]
    by_paragraph = defaultdict(list)
    for b in blocks:
        by_paragraph[b["paragraph"]].extend(b["text_node_ids"])
    paragraph_errors = []
    for i, p in enumerate(soup.body.find_all("p"), 1):
        observed = "".join(tokens[t]["decoded_text"] for t in by_paragraph[i])
        if "".join(observed.split()) != "".join(p.get_text().split()):
            paragraph_errors.append(i)
    exactly_once = sorted(token_ids) == list(range(len(tokens))) and len(set(token_ids)) == len(tokens)
    body = copy.copy(soup.body)
    for tag in body.select("label, script, style"):
        tag.decompose()
    body_text = "".join(body.get_text().split())
    reconstructed_body = "".join("".join(b["original_text"].split()) for b in blocks if b["role"] != "technical")
    body_matches = body_text == reconstructed_body
    dom_tables = soup.body.find_all("table")
    parsed_tables = [r for r in regions if r["tag"] == "table"]
    table_matches = len(dom_tables) == len(parsed_tables) and all(
        len(t.find_all("tr")) == len(r["rows"]) and
        sum(len(row["cells"]) for row in r["rows"]) == len(t.find_all(["td", "th"]))
        for t, r in zip(dom_tables, parsed_tables)
    )
    dom_images = [i.get("src") for i in soup.body.find_all("img")]
    image_matches = dom_images == [r["attributes"].get("src") for r in regions if r["tag"] == "img"]
    technical = exactly_once and not token_errors and not paragraph_errors and not byte_errors and body_matches and table_matches and image_matches
    role_counts = Counter(b["role"] for b in blocks)
    char_counts = Counter()
    for b in blocks:
        char_counts[b["role"]] += sum(len(tokens[t]["decoded_text"]) for t in b["text_node_ids"])
    summary = {"document": record["document"], "family": identity["family"],
               "source_nodes": len(nodes), "counts_by_kind": dict(Counter(n["kind"] for n in nodes)),
               "blocks": len(blocks), "text_nodes": len(tokens), "decoded_chars": sum(char_counts.values()),
               "block_roles": dict(role_counts), "chars_by_role": dict(char_counts),
               "regions": dict(Counter(r["tag"] for r in regions)),
               "table_rows": sum(len(r.get("rows", [])) for r in regions),
               "table_cells": sum(len(row["cells"]) for r in regions for row in r.get("rows", [])),
               "technical_accounting_pass": technical, "tokens_exactly_once": exactly_once,
               "paragraph_text_errors": paragraph_errors, "token_locator_errors": token_errors,
               "utf8_locator_errors": byte_errors, "whole_body_text_matches_dom": body_matches,
               "body_text_compact_sha256": digest(body_text.encode()),
               "table_structure_matches_dom": table_matches, "image_sources_match_dom": image_matches,
               "editorial_notes_without_span_owner": sum(b["role"] == "editorial_note" and b["owner_source_id"] is None for b in blocks),
               "editorial_note_legal_scope_reviewed": False,
               "numbered_node_checks": sum(m["expected_number"] is not None for m in marker_checks),
               "number_checks": len(marker_checks), "number_mismatches": sum(not m["matches"] for m in marker_checks),
               "marker_gap_candidates": len(marker_gaps), "quote_candidates": len(quotes),
               "semantic_readiness": "unresolved" if issues else "no_detected_gap_in_bounded_checks",
               "semantic_issues": issues, "legal_admission": False, "g13_qualified": False}
    for n in nodes:
        n["source_span"] = {"source_asset_sha256": asset["sha256"],
                            "json_pointer": record["locator"].replace("$.", "/"),
                            "char_start": n["html_start"], "char_end": n["html_end"],
                            "offset_unit": "unicode_codepoints_in_decoded_html_scalar",
                            "utf8_byte_start": byte_offsets[n["html_start"]],
                            "utf8_byte_end": byte_offsets[n["html_end"]]}
        n["structure_evidence"] = {"source_asset_sha256": record["response_sha256"],
                                   "source_id": n["source_id"], "url": record["url"]}
    tree = {"schema_version": VERSION, "source_asset_sha256": asset["sha256"],
            "structure_asset_sha256": record["response_sha256"], "identity": identity,
            "scope": "experimental_source_tree_not_production_LegalEdition",
            "admission_blockers": record["admission_blockers"], "nodes": nodes, "blocks": blocks,
            "regions": regions, "text_nodes": tokens, "summary": summary}
    controls = {"marker_checks": marker_checks, "unrepresented_marker_candidates": marker_gaps,
                "amendment_quote_candidates": quotes,
                "method": "Independent BeautifulSoup DOM marker checks and paragraph-text comparison; quote and marker scans are diagnostics, not legal review."}
    return tree, controls, html


def self_check():
    html = '<html><body><p id="p1">Статья 1. Тест</p><p id="p2">1. Часть</p><p id="p3">2. Часть</p></body></html>'
    rows = [{"id": "a1", "np": "p1", "npe": "p3", "caption": "Статья 1. Тест", "unit": "статья", "lvl": 0},
            {"id": "a1_c1", "np": "p2", "npe": "p2", "caption": "$часть 1", "unit": "часть", "lvl": 1},
            {"id": "a1_c2", "np": "p3", "npe": "p3", "caption": "$часть 2", "unit": "часть", "lvl": 1}]
    nodes, checks, _ = normalized_units(html, rows, "federal_law")
    assert len(nodes) == 3 and all(r["matches"] for r in checks)
    cases = []
    for name, mutate in [
        ("missing_anchor", lambda r: r[1].update(np="absent")),
        ("duplicate_sidecar_id", lambda r: r[2].update(id="a1_c1")),
        ("parent_prefix", lambda r: r[1].update(id="a2_c1")),
        ("level_jump", lambda r: r[1].update(lvl=2)),
        ("sibling_overlap", lambda r: r[1].update(npe="p3")),
        ("reverse_bounds", lambda r: r[1].update(np="p3", npe="p2")),
    ]:
        r = copy.deepcopy(rows)
        mutate(r)
        try:
            normalized_units(html, r, "federal_law")
        except ValueError:
            cases.append(name)
        else:
            raise AssertionError(name)
    changed = copy.deepcopy(rows)
    changed[1]["caption"] = "$часть 9"
    assert not normalized_units(html, changed, "federal_law")[1][1]["matches"]
    try:
        Anchors(html.replace('id="p3"', 'id="p2"'))
    except ValueError:
        cases.append("duplicate_html_id")
    else:
        raise AssertionError("duplicate_html_id")
    assert explicit_number(numbering_markup('$пункт 2<sup>1-1</sup>'), "пункт") == "2^1-1"
    assert source_marker_number("9)", "пункт") == "9"
    assert explicit_number(numbering_markup('<p>РАЗДЕЛ I<br>ОБЩИЕ ПОЛОЖЕНИЯ</p>'), "раздел") == "I"
    assert explicit_number("IV. Порядок", "раздел") == "IV"
    assert Owners(nodes).find(html.index("1. Часть"), html.index("1. Часть") + 1) == "a1_c1"
    assert Owners(nodes).find(html.index("1. Часть"), html.index("2. Часть") + 1) == "a1"
    return {"positive_tree": True, "rejected_mutations": cases,
            "number_mismatch_detected": True, "superscript_preserved": True,
            "cross_child_region_uses_parent": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_ROOT / "attempt-01")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        print(json.dumps(self_check(), ensure_ascii=False))
        return
    preflight_path = DEFAULT_ROOT / "preflight.json"
    preflight = json.loads(preflight_path.read_bytes())
    if args.output.exists():
        raise ValueError("use a fresh attempt directory; preserve every earlier result")
    args.output.mkdir(parents=True)
    retain(args.output / "adapter.py", Path(__file__).read_bytes())
    retain(args.output / "self-check.json", encoded(self_check()))
    results, witnesses = [], []
    for record in preflight["records"]:
        t0 = time.monotonic()
        manifest, payloads, _ = load_input(PROJECT / record["input"], record["target_date_claim"])
        record = {**record, "declared_identity": manifest["act_identity_claim"]["declared_identity"]}
        raw = payloads[record["source_sha256"]]
        sidecar = (PROJECT / record["response_file"]).read_bytes()
        a, c, html = build(record, raw, sidecar)
        b, d, _ = build(record, raw, sidecar)
        path = args.output / record["document"]
        for run, tree, controls in [("run-a", a, c), ("run-b", b, d)]:
            retain(path / run / "tree.json", encoded(tree))
            retain(path / run / "controls.json", encoded(controls))
        assert encoded(a) == encoded(b) and encoded(c) == encoded(d)
        assert retain(path / "run-a/tree.json", encoded(a)) == "unchanged"
        baseline = json.loads((PROJECT / record["baseline"]).read_bytes())["content"]["trees"][0]
        previous_quotes = [n for n in baseline["nodes"] if n["kind"] == "quote"]
        comparisons = {"old_counts": dict(Counter(n["kind"] for n in baseline["nodes"])),
                       "old_quote_nodes": len(previous_quotes),
                       "old_quote_examples": [{k: n[k] for k in ["address", "parent_address", "text", "paragraph"]} for n in previous_quotes[:3]],
                       "warning": "Historical parser is a comparison, not an independent correctness oracle. Source and native counts can legitimately differ."}
        retain(path / "baseline-comparison.json", encoded(comparisons))
        retain(path / "source-binding.json", encoded(record))
        result = {**a["summary"], "deterministic": True, "unchanged_repeat": True,
                  "tree_sha256": digest(encoded(a)), "controls_sha256": digest(encoded(c)),
                  "elapsed_seconds": round(time.monotonic() - t0, 3),
                  "old_quote_nodes": len(previous_quotes)}
        results.append(result)
        witnesses.append({"document": record["document"], "nodes": a["nodes"],
                          "html": html, "summary": result, "controls": c})
        print(json.dumps(result, ensure_ascii=False), flush=True)
    protected = preflight["protected_files_sha256"]
    drift = [p for p, h in protected.items() if digest((PROJECT / p).read_bytes()) != h]
    assert not drift, drift
    summary = {"schema_version": VERSION, "recorded_at": datetime.now(UTC).isoformat(),
               "adapter_sha256": digest(Path(__file__).read_bytes()),
               "scope_sha256": digest(preflight_path.read_bytes()), "documents": results,
               "source_nodes": sum(r["source_nodes"] for r in results),
               "technical_pass_count": sum(r["technical_accounting_pass"] for r in results),
               "no_detected_semantic_gap_count": sum(not r["semantic_issues"] for r in results),
               "protected_files_unchanged": len(protected), "production_integration": False,
               "legal_admission": False, "g13_qualified": False}
    retain(args.output / "results.json", encoded(summary))
    retain(args.output / "viewer-data.json", encoded(witnesses))
    print(json.dumps({k: v for k, v in summary.items() if k != "documents"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
