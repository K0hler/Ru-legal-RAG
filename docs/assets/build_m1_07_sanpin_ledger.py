"""Build or check the retained M1-07 SanPiN review proposal."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from legal_rag.corpus.amendment_ledger import _require, bind_operations, check_review
from legal_rag.corpus.compiler import _date, _inside, _read, _reference, _write_once, content_hash, json_bytes, load_input
from legal_rag.corpus.structure_completion import quote_end

from validate_m1_02_closure import validate as validate_m1_02
from validate_ocr_structure import validate_source

ROOT = Path(__file__).resolve().parents[2]
ROUTES = Path("data/m1/inputs/m1-02-completion")
PILOT = Path("data/m1/pilot_runs/m1-06-20261104")
V1 = Path("data/m1/reviews/m1-02-review-v1")
DATES = ["2025-01-01", "2026-10-01"]
ACT = "sanpin-2.1.3684-21"
TABLE_REVIEW = {
    "path": (PILOT / "table-correction-acceptance/table-review.json").as_posix(),
    "sha256": "409b72a975af7022aa62eb8c0497e1424ccb81d8cf1408de23f110a06e12caf1",
}


def file_ref(path, expected=None):
    digest = hashlib.sha256(_inside(ROOT, path.as_posix()).read_bytes()).hexdigest()
    _require(expected is None or expected == digest, f"evidence hash mismatch: {path}")
    return {"path": path.as_posix(), "sha256": digest}


def span(node, pdf_sha256):
    spans = node["source_spans"]
    _require(node["kind"] in {"text", "requisite"} and node["text"] and spans
             and all(s["source_asset_sha256"] == pdf_sha256 and type(s["page"]) is int and s["page"] > 0
                     and s["locator"] for s in spans), f"missing text or PDF spans at {node['address']}")
    return {"address": node["address"], "node_id": node["node_id"], "text": node["text"], "spans": spans}


def quoted_payload(text):
    if text.startswith("«"):
        closing, _ = quote_end(text, "«", 0)
        _require(closing is not None and closing > 1 and text[closing + 1:] in {".", ";"},
                 "invalid outer quotation")
        return text[1:closing]
    matches = re.findall(r"«([^«»]+)»", text)
    _require(len(matches) == 1, "ambiguous quoted payload")
    return matches[0]


def bind_amendment(spec, document, temporal_sources):
    pdf_sha256 = document["pdf"]["sha256"]
    nodes = document["nodes"]
    effect = dict(spec["date"])
    clause = effect.pop("clause")
    effect["start"] = _date(effect["start"])
    if effect["end"] is not None:
        effect["end"] = _date(effect["end"])
        _require(effect["start"] < effect["end"], "invalid proposed dates")
    evidence = [span(nodes[clause], pdf_sha256)] if clause else temporal_sources
    if "end_clause" in spec:
        evidence = [*evidence, span(nodes[spec["end_clause"]], pdf_sha256)]
    effect["evidence"] = [document["card"], *evidence]
    other = []
    for item in spec["other"]:
        source = span(nodes[item["address"]], pdf_sha256)
        _require(item["exact"] in source["text"], "out-of-scope locator mismatch")
        other.append({"rationale": item["change"], "evidence": source})
    operations = []
    for row in spec["operations"]:
        op = {k: row[k] for k in ("id", "kind", "target", "owner")}
        op["target"] = "act/" + op["target"]
        op.update(publication=document["publication"], requires=row.get("requires", []),
                  condition=row.get("condition"), effect=effect,
                  scope="approving_resolution" if row["owner"].split("/")[0] == "A" else "sanitary_rules")
        op["evidence"] = [span(nodes[a], pdf_sha256) for a in row["source"]]
        _require(len(set(row["source"])) == len(op["evidence"]), "duplicate source address")
        quote = row.get("quote")
        if quote is not None:
            _require(quote in row["source"], "payload quote has no directive evidence")
            after = quoted_payload(nodes[quote]["text"])
        else:
            after = row.get("after")
            if row["kind"] == "replace_text":
                _require(any(f"«{row['before']}»" in e["text"] and f"«{after}»" in e["text"]
                             for e in op["evidence"]), "word replacement does not match the directive")
        if row["kind"] == "insert_after":
            payload = {"address": "act/" + row["destination"], "number": row["number"], "text": after}
        elif row["kind"] == "delete_unit":
            payload = None
        else:
            if row["kind"] == "insert_text":
                op.update(position=row["position"], punctuation=row["punctuation"], paragraph=row.get("paragraph"))
                if row["position"] == "end":
                    after = " " + after
            payload = {"before": row.get("before", ""), "after": after}
        op["payload"] = payload
        operations.append(op)
    _require(operations, "amendment without operation proposals")
    return operations, other


def build_ledger():
    closure_path = ROOT / ROUTES / "closure.json"
    validate_m1_02(closure_path)
    closure = _read(closure_path)
    route_refs = {}
    for target in DATES:
        route = next(r for r in closure["rows"] if (r["act_id"], r["target_date"]) == (ACT, target))
        path = Path(route["compiler_input"])
        manifest, _, _ = load_input(ROOT / path, target)
        _require(set(route["source_sha256s"]) == {a["sha256"] for a in manifest["assets"]},
                 "dated route asset coverage mismatch")
        route_refs[target] = file_ref(path)
    assets = {asset["sha256"]: asset for asset in manifest["assets"]}

    table_review, _ = _reference(ROOT, TABLE_REVIEW)
    draft, _ = _reference(ROOT, table_review["pilot_manifest"])
    bundle, _ = _reference(ROOT, table_review["bundle_review"])
    _require(bundle["status"] == "pass" and table_review["draft_id"] == draft["draft_id"] == bundle["draft_id"]
             and table_review["content_hash"] == draft["content_hash"] == bundle["content_hash"]
             and draft["content_hash"] == content_hash(draft["content"]), "unbound M1-06 pilot draft")
    draft_path = Path(table_review["pilot_manifest"]["path"])
    original = next(t for t in draft["content"]["trees"] if t["role"] == "original")
    original_sha256 = original["source_asset_sha256"]
    trees = {t["source_asset_sha256"]: t for t in draft["content"]["trees"]}
    _require(len(trees) == len(draft["content"]["trees"]) == 10 and set(trees) == assets.keys(),
             "M1-06 tree coverage differs from M1-02 inventory")
    _require(all({a["sha256"]: a["role"] for a in _read(ROOT / r["path"])["assets"]}
                 == {sha: tree["role"] for sha, tree in trees.items()} for r in route_refs.values()),
             "dated routes differ from the pilot original and amendments")

    packet = _read(ROOT / V1 / "packet.json")
    views = {doc["id"]: doc for doc in packet["documents"]}
    documents = {}
    for sha, tree in trees.items():
        requisites = draft["official_requisites"][sha]
        publication = requisites["source_item"].split(":")[-1]
        card_sha = requisites["card_asset_sha256"]
        card_path = ROUTES / "acquisition/raw" / card_sha
        card_ref = file_ref(card_path, card_sha)
        card = _read(ROOT / card_path)
        number = requisites["values"]["document_number"]
        _require(number not in documents and card["eoNumber"] == publication
                 and requisites["source_item"] == assets[sha]["source_item"], "official card binding mismatch")
        pdf_path = V1 / views[publication]["file"]
        _require(views[publication]["sha256"] == sha, "review PDF differs from the retained original")
        extraction = draft_path.parents[2] / "extractions" / (tree["extraction_id"] + ".json")
        extracted = _read(ROOT / extraction)
        _require(extracted["extraction_id"] == content_hash({k: v for k, v in extracted.items() if k != "extraction_id"})
                 and extracted["coverage"]["all_source_pages"], "corrupt or incomplete retained extraction")
        validate_source(extracted, tree)
        documents[number] = {
            "publication": publication, "number": number, "role": tree["role"],
            "document_date": requisites["values"]["document_date"], "source_url": assets[sha]["source_url"],
            "publication_date": _date(card["publishDateShort"].split("T")[0]),
            "pdf": file_ref(pdf_path, sha), "card": {**card_ref, "url": requisites["source_url"],
                                                    "locator": "publishDateShort"},
            "ast_sha256": content_hash(tree), "extraction": file_ref(extraction),
            "nodes": {n["address"].removeprefix(tree["namespace"] + "/content/"): n
                      for n in tree["nodes"]},
        }

    tables, _ = _reference(ROOT, table_review["tables"])
    pdf_ref = file_ref(Path(table_review["source_pdf"]["path"]), original_sha256)
    regions = {}
    for page in table_review["pages"]:
        node = documents["3"]["nodes"][page["address"].removeprefix("act/content/")]
        table = next(t for t in tables["tables"] if t["page"] == page["page"])
        _require(node["kind"] == "table" and node["owner_path"] == page["owner_path"]
                 and node["source_region_id"] == page["region_id"] == table["region_id"]
                 and table["source_asset_sha256"] == original_sha256
                 and table["extraction_id"] == original["extraction_id"], "reviewed table binding mismatch")
        file_ref(Path(page["source_image"]["path"]), page["source_image"]["sha256"])
        regions[page["address"]] = {**page, "table_sha256": content_hash(table["table"])}
    _require(len(regions) == len(tables["tables"]) == 4, "expected four reviewed table fragments")

    decree = views["decree763"]
    temporal_sources = [
        {**file_ref(V1 / decree["raw_file"], decree["sha256"]), "url": decree["url"], "locator": "п. 12"},
        {**file_ref(ROUTES / "acquisition/raw/31917d7a6dc2d90fb131dd35056c8bcbd76ebc26e369b8a2bad7ce274f627d4e",
                    "31917d7a6dc2d90fb131dd35056c8bcbd76ebc26e369b8a2bad7ce274f627d4e"),
         "url": "http://publication.pravo.gov.ru/document/0001202007310002", "locator": "ст. 3 247-ФЗ"},
        {**file_ref(ROUTES / "raw/ff307c2b7e49edbc996f589bd7e4528c959da681eeb84317efd483699dc59ac8",
                    "ff307c2b7e49edbc996f589bd7e4528c959da681eeb84317efd483699dc59ac8"),
         "url": "https://www.vsrf.ru/lk/practice/stor_pdf/2515680", "locator": "АПЛ25-373, материал для проверки"},
    ]
    spec_path = Path("docs/assets/m1_07_sanpin_proposal.json")
    specs = json.loads((ROOT / spec_path).read_bytes())
    amendments = {row["number"]: row for row in specs}
    _require(len(amendments) == len(specs) == 9 and set(amendments) == documents.keys() - {"3"},
             "proposals must cover all nine retained amendment publications")
    proposed_operations = []
    inventory = []
    for number, spec in amendments.items():
        document = documents[number]
        operations, other = bind_amendment(spec, document, temporal_sources)
        inventory.append({**{k: v for k, v in document.items() if k != "nodes"},
                          "operations": [op["id"] for op in operations], "other_act_evidence": other})
        proposed_operations.extend(operations)
    operations = bind_operations(original, proposed_operations)
    for op in operations:
        op["proposed_dispositions"] = {date: "include" if date >= op["effect"]["start"] else "not_yet_effective"
                                       for date in DATES}
    coverage = {
        "closure": file_ref(ROUTES / "closure.json"),
        "citation_chain": span(documents["25"]["nodes"]["8"], documents["25"]["pdf"]["sha256"]),
        "feed": [file_ref(ROUTES / f"sanpin-{name}.json")
                 for name in ("search-findings", "feed", "feed-research", "feed-tail")],
        "retained_findings": closure["sanpin_completeness_check"],
    }
    return {"schema_version": "amendment-ledger/1", "status": "proposal", "act": ACT,
            "scope": "Текст постановления № 3 и утверждённого им СанПиН 2.1.3684-21 с условиями применения.",
            "primary_legal_reviewer": "legal-reviewer-owner",
            "target_dates": DATES, "routes": route_refs, "proposal_spec": file_ref(spec_path),
            "original": {k: v for k, v in documents["3"].items() if k != "nodes"},
            "pilot_manifest": table_review["pilot_manifest"], "coverage_evidence": coverage,
            "tables": {"review": TABLE_REVIEW, "data": table_review["tables"], "source_pdf": pdf_ref,
                       "regions": regions},
            "temporal_research": temporal_sources, "amendments": inventory, "operations": operations}


def review_template(ledger):
    return {"schema_version": "amendment-ledger-review/1", "ledger_sha256": content_hash(ledger),
            "role": "Legal Reviewer", "reviewer": "", "reviewed_at": "", "rationale": "",
            "operations": {op["id"]: "unresolved" for op in ledger["operations"]},
            "dates": {date: {"complete": "unresolved", "rationale": "",
                             "dispositions": {op["id"]: {"status": "unresolved", "rationale": ""}
                                              for op in ledger["operations"]}}
                      for date in ledger["target_dates"]}}


def review_markdown(ledger, directory):
    def link(ref, label, page=None):
        path = Path(os.path.relpath(ROOT / ref["path"], directory)).as_posix()
        return f"[{label}]({path}{f'#page={page}' if page else ''})"

    def pdf_pages(pdf, spans):
        return ", ".join(link(pdf, f"стр. {p}", p) for p in sorted({s["page"] for s in spans}))

    status = {"include": "учесть в цепочке", "not_yet_effective": "ещё не действует"}
    lines = ["# М1-07. СанПиН 2.1.3684-21", "",
             "Проект реестра для проверки юристом. Даты и статусы ниже предложены для проверки.", "",
             f"Хеш реестра `{content_hash(ledger)}`", "",
             f"{link(ledger['original']['pdf'], 'Исходное постановление и СанПиН, PDF')}. "
             "[Реестр](ledger.json). [Форма решения](review-template.json).", "",
             "## Полнота и даты", "",
             "Отдельно подтвердите полноту на **01.01.2025** и **01.10.2026**. "
             "Проверьте специальные сроки, территориальные условия и последствия истечения срока.",
             "", f"{link(ledger['coverage_evidence']['closure'], 'Инвентаризация М1-02')}. "
             f"{link(ledger['coverage_evidence']['feed'][0], 'Результаты ограниченного поиска')}.", "",
             "№ 25 на стр. 2 перечисляет восемь предыдущих постановлений. Поиск М1-02 охватывал "
             "24.09.2026–01.10.2026, 26 страниц. На трёх страницах строгая проверка ленты дала ошибки.", "",
             "Источники для проверки сроков. " + ", ".join(f"[{r['locator']}]({r['url']})"
                                                         for r in ledger["temporal_research"]) + ".", "",
             "## Операции", ""]
    for amendment in ledger["amendments"]:
        pdf = amendment["pdf"]
        ops = [op for op in ledger["operations"] if op["id"] in amendment["operations"]]
        effect = ops[0]["effect"]
        dated = " · ".join(f"{d} — {status[v]}" for d, v in ops[0]["proposed_dispositions"].items())
        lines.extend([f"### № {amendment['number']} от {amendment['document_date']}", "",
                      f"Опубликовано {amendment['publication_date']}. "
                      f"Предлагаемое начало {effect['start']}."
                      + (f" В тексте постановления указан срок до {effect['end']}." if effect["end"] else ""),
                      "", dated + ".", ""])
        if effect["note"]:
            lines.extend([effect["note"], ""])
        temporal_spans = [s for entry in effect["evidence"] for s in entry.get("spans", [])]
        if temporal_spans:
            lines.extend([f"Положение о сроке действия. {pdf_pages(pdf, temporal_spans)}.", ""])
        for op in ops:
            refs = pdf_pages(pdf, [s for entry in op["evidence"] for s in entry["spans"]])
            lines.extend([f"**{op['id']}** — `{op['target']}`. Поправка, {refs}.", ""])
            base_spans = [s for n in op["expected_before"]["nodes"]
                          for s in (n.get("source_spans") or n.get("anchor_source_spans", []))]
            if base_spans:
                lines.extend([f"Исходный текст, {pdf_pages(ledger['original']['pdf'], base_spans)}.", ""])
            if op["requires"]:
                lines.extend(["После " + ", ".join(op["requires"]) + ".", ""])
            before = op["expected_before"]["nodes"][0]["text"]
            if op["kind"] == "insert_after":
                lines.extend([f"Вставить после указанного узла. `{op['payload']['address']}`", "",
                              "> " + op["payload"]["text"], ""])
            elif op["kind"] == "delete_unit":
                first_text = next(n["text"] for n in op["expected_before"]["nodes"] if n["text"])
                lines.extend(["Предлагается исключить пункт и его подпункты.", "", "> " + first_text, ""])
            else:
                start, end = op["range"]
                after = before[:start] + op["payload"]["after"] + before[end:]
                lines.extend(["До", "", "> " + before, "", "После", "", "> " + after, ""])
            if op["condition"]:
                lines.extend([op["condition"], ""])
        if amendment["other_act_evidence"]:
            lines.append("Положения о других актах")
            lines.append("")
            for item in amendment["other_act_evidence"]:
                lines.append(f"- {item['rationale']} {pdf_pages(pdf, item['evidence']['spans'])}.")
            lines.append("")
    lines.extend(["## Таблицы и приложения", "",
                  "В девяти публикациях выявлены изменения пунктов и абзацев. "
                  "Изменений нумерации, таблиц и приложений самого СанПиН в проекте не выявлено. "
                  "Пункт 4(1) затрагивает приложения 1–3 СП 2.1.5.1059-01.", "",
                  f"Значения и адреса ячеек на четырёх сверенных фрагментах. "
                  f"{link(ledger['tables']['data'], 'Таблицы М1-06')}.", ""])
    return "\n".join(lines).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "check"))
    parser.add_argument("--directory", type=Path, default=ROOT / "data/m1/reviews/m1-07-review-v1")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--independent-review", type=Path)
    args = parser.parse_args()
    try:
        ledger = build_ledger()
        directory = args.directory.resolve()
        files = {"ledger.json": json_bytes(ledger), "review-template.json": json_bytes(review_template(ledger)),
                 "review.md": review_markdown(ledger, directory)}
        decisions = check_review(ledger, _read(args.review) if args.review else None,
                                 _read(args.independent_review) if args.independent_review else None)
        for name, payload in files.items():
            path = directory / name
            if args.command == "check" or path.exists():
                _require(path.read_bytes() == payload, f"artifact differs from verified proposal: {path}")
        if args.command == "build":
            for name, payload in files.items():
                path = directory / name
                if not path.exists():
                    _write_once(path, payload)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(error, file=sys.stderr)
        return 2
    print(json.dumps({"amendments": len(ledger["amendments"]), "operations": len(ledger["operations"]),
                      "ledger_sha256": content_hash(ledger), "dates": decisions}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
