"""Independent HTML marker inventory and reconciliation with the resulting AST."""

from collections import Counter, defaultdict
import re

from bs4 import BeautifulSoup

from .compiler import content_hash


VERSION = "html-structure-audit/3"
NUMBER = r"[0-9]+(?:[.^-][0-9]+)*"
ROMAN = r"[IVXLCDM]+(?:[.^-][0-9]+)*"
SUPERSCRIPT = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
HEADINGS = {"статья": "article", "глава": "chapter", "раздел": "section", "часть": "part", "§": "subchapter", "приложение": "annex"}
PART_WORDS = "ПЕРВАЯ ВТОРАЯ ТРЕТЬЯ ЧЕТВЕРТАЯ ПЯТАЯ ШЕСТАЯ СЕДЬМАЯ ВОСЬМАЯ ДЕВЯТАЯ ДЕСЯТАЯ".split()


def scan_html(html):
    """Read raw HTML only: no sidecar, AST, or traversal-parser marker rules."""
    soup = BeautifulSoup(html, "html.parser")
    markers = []
    for paragraph, p in enumerate(soup.find_all("p"), 1):
        if not p.name or set(p.get("class", [])) & {"A", "F", "N"} or p.find_parent(["label", "script", "style"]):
            continue
        html_id, table = p.get("id"), p.find_parent("table") is not None
        for note in list(p.select(".mark, .markx, label, script, style")):
            note.decompose()
        superscripts = [s for s in p.select("sup, .W9, .WB") if not any(
            a.name == "sup" or set(a.get("class", [])) & {"W9", "WB"} for a in s.parents if a is not p)]
        for s in superscripts:
            s.replace_with("^" + s.get_text().strip())
        for br in list(p.find_all("br")):
            br.replace_with("\x00")
        for line, raw in enumerate(p.get_text("", strip=False).split("\x00")):
            text = " ".join(raw.split())
            quoted = text.startswith(('"', '«', '“'))
            prefix = text[1:] if quoted else text
            heading = re.match(rf"^(Статья|Глава|Раздел|Часть|§)\s+({NUMBER}|{ROMAN})(?=[.\s]|$)", prefix, re.I)
            part = re.fullmatch(r"(?:ЧАСТЬ ([А-Я]+)|(?:ОБЩАЯ|ОСОБЕННАЯ) ЧАСТЬ)", prefix.upper())
            annex = re.match(rf"^Приложение\s+(?:№\s*)?({NUMBER})(?=[.\s]|$)", prefix, re.I)
            numeric = re.match(rf"^({NUMBER})([.)])(?:\s|$)", prefix)
            letter = re.match(r"^([а-яa-z](?:\^[0-9]+)?)\)(?:\s|$)", prefix, re.I)
            if heading and heading[1].islower() and not prefix[heading.end():].startswith("."):
                continue
            if heading and heading[1].casefold() == "часть" and heading.end() != len(prefix):
                continue
            if heading:
                kind, number, delimiter = HEADINGS[heading[1].casefold()], heading[2], None
            elif annex:
                kind, number, delimiter = "annex", annex[1], None
            elif part:
                kind = "part" if part[1] is None or part[1] in PART_WORDS else "unknown_heading"
                number = str(PART_WORDS.index(part[1]) + 1) if part[1] in PART_WORDS else None
                delimiter = None
            elif numeric:
                kind, number, delimiter = "numbered", numeric[1], numeric[2]
            elif letter:
                kind, number, delimiter = "letter", letter[1].casefold(), ")"
            elif re.match(r"^[0-9]+(?:\^[^\s]+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)[.)](?:\s|$)", prefix):
                kind, number, delimiter = "unknown_numbered", None, None
            elif re.match(r"^(?:Статья|Глава|Раздел|§)(?:\s|$)", prefix, re.I):
                kind, number, delimiter = "unknown_heading", None, None
            else:
                continue
            base, _, exponent = (number or "").partition("^")
            markers.append({"paragraph": paragraph, "html_id": html_id, "line": line,
                "kind_hint": kind, "number_raw": number, "number_canonical": number.replace("^", ".") if number else None,
                "number_display": base + exponent.translate(SUPERSCRIPT) if number else None,
                "number_components": {"base": base, "superscript": exponent or None},
                "delimiter": delimiter, "quoted": quoted, "in_table": table, "excerpt": text[:320]})
    return markers


def audit_tree(candidates, nodes, unresolved, excluded):
    by_address = {n["address"]: n for n in nodes}
    paragraphs = defaultdict(list)
    for b in [*nodes, *unresolved, *excluded]:
        if b.get("block_id") is not None and not b.get("exclusion_reason") and b.get("text") and b.get("kind") != "note":
            paragraphs[b.get("paragraph")].append(b)
    starts = defaultdict(list)
    for n in nodes:
        if n.get("block_id") is None and (n.get("number_canonical") is not None or n["kind"] == "normative_note" or n.get("structural_role") == "upper_division"):
            starts[n["source_span"]["char_start"]].append(n)
    findings, statuses = [], Counter()

    def finding(code, severity, candidate=None, block=None, node=None):
        item = {"code": code, "severity": severity}
        if candidate:
            item.update({k: candidate[k] for k in ("html_id", "paragraph", "line", "kind_hint", "number_canonical", "excerpt")})
        entry = block or node
        if entry:
            item.update(block_id=entry.get("block_id"), address=entry.get("address"),
                        parent_address=entry.get("parent_address", entry.get("source_container_address", "act")),
                        source_span=entry["source_span"])
        findings.append(item)
        statuses[code] += 1

    for candidate in candidates:
        bs = sorted(paragraphs.get(candidate["paragraph"], []), key=lambda b: b["block_id"])
        if not bs:
            finding("marker_without_lexical_evidence", "critical", candidate)
            continue
        block = bs[0]
        chain, seen = [], set()
        parent = by_address.get(block.get("parent_address", block.get("source_container_address")))
        while parent and parent["address"] not in seen:
            seen.add(parent["address"])
            chain.append(parent)
            parent = by_address.get(parent["parent_address"])
        form = any(n.get("content_context") == "form" or n["kind"] == "annex" and "(форма)" in n.get("caption", "").casefold() for n in chain)
        quoted = any(n["kind"] == "quote" for n in chain)
        matched = []
        for n in starts.get(block["html_start"], []):
            note = re.fullmatch(r"примечание\s+([0-9]+)", n.get("caption", ""), re.I) if n["kind"] == "normative_note" else None
            number = note[1] if note else n.get("number_canonical")
            if number == candidate["number_canonical"] and candidate["line"] == 0:
                matched.append(n)
        if quoted:
            finding("quoted_payload_preserved", "warning", candidate, block)
        elif form and candidate["kind_hint"] in {"numbered", "letter"}:
            finding("form_content_preserved", "warning", candidate, block)
        elif candidate["in_table"]:
            finding("table_content_preserved", "warning", candidate, block)
        elif matched:
            expected = {"numbered": {"point", "part", "item", "subitem", "normative_note"}, "letter": {"item", "subitem"}}
            kinds = expected.get(candidate["kind_hint"], {candidate["kind_hint"]})
            if not any(n["kind"] in kinds for n in matched):
                finding("marker_kind_conflict", "critical", candidate, block)
            else:
                statuses["matched"] += 1
        else:
            finding("unmatched_marker", "critical", candidate, block)

    for node in nodes:
        if any(e["rule"] in {"confirmed-parent-boundary/1", "confirmed-next-boundary/1"}
               for e in node.get("normalization_evidence", [])):
            finding("source_range_reconciled", "info", node=node)
        if node.get("structure_origin") == "html_recovery":
            finding("explicit_sibling_recovered", "info", node=node)
        if node.get("content_context") == "amendment_payload" and node.get("block_id") is not None:
            finding("amendment_payload_preserved", "warning", node=node)
        parent = by_address.get(node["parent_address"])
        if parent is None and node["parent_address"] != "act":
            finding("missing_parent", "critical", node=node)
        if parent:
            p, s = parent["source_span"], node["source_span"]
            if not p["char_start"] <= s["char_start"] <= s["char_end"] <= p["char_end"]:
                finding("child_outside_parent", "critical", node=node)
        seen, ancestor = {node["address"]}, parent
        while ancestor:
            if ancestor["address"] in seen:
                finding("parent_cycle", "critical", node=node)
                break
            seen.add(ancestor["address"])
            ancestor = by_address.get(ancestor["parent_address"])
    # Reconcile lexical ownership independently of the traversal's Owners index.
    units = sorted([n for n in nodes if n.get("source_id") or n.get("structure_origin") == "html_recovery"],
                   key=lambda n: (n["source_span"]["char_start"], -n["source_span"]["char_end"]))
    active, index = [], 0
    lexical = sorted([n for n in nodes if n.get("block_id") is not None and n["kind"] != "note"],
                     key=lambda n: n["source_span"]["char_start"])
    for block in lexical:
        start, end = block["source_span"]["char_start"], block["source_span"]["char_end"]
        while index < len(units) and units[index]["source_span"]["char_start"] <= start:
            active.append(units[index])
            index += 1
        active = [n for n in active if n["source_span"]["char_end"] >= end]
        expected = max(active, key=lambda n: n["address"].count("/"))["address"] if active else "act"
        actual, seen = (block["source_container_address"] if block["kind"] == "table_cell"
                        else block["parent_address"]), set()
        while actual != "act" and actual not in seen:
            seen.add(actual)
            ancestor = by_address.get(actual)
            if ancestor is None or ancestor.get("source_id") or ancestor.get("structure_origin") == "html_recovery":
                break
            actual = ancestor["parent_address"]
        if actual != expected:
            finding("lexical_owner_conflict", "critical", block=block)
    counts = Counter(f["severity"] for f in findings)
    return {"schema_version": "structure-audit/1", "scanner_version": VERSION,
            "candidates_checked": len(candidates), "candidates_sha256": content_hash(candidates),
            "critical_count": counts["critical"], "warning_count": counts["warning"], "info_count": counts["info"],
            "counts_by_status": dict(statuses), "findings": findings}
