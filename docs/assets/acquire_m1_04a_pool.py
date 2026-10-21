"""M1-04A check pool: acquire original PDFs (and optionally official IPS trees) for a frozen batch.

`--batch batch-01|batch-02` (a name under `documents/pool/` or a path); official trees only with
`--with-official` (batch 1 was acquired with them, batch 2 without). Examples below say batch-01.

Reads only `selection.json` (verified against `selection.sha256`). For every selected act:

1. Original PDF through `acquire_publication` + `PublicationPravoConnector` into the shared
   content-addressed archive `documents/pool/batch-01/archive/`; the card must match the
   selection (EO number, number, date, pages) and the PDF length must equal the card's
   `pdfFileLength` before anything is persisted. Two runs: `new`, then `unchanged`.
2. `documents/pool/batch-01/<slug>/input.json` (`corpus-input/1`, role `original`) with a
   diagnostic processing permission scoped to the exact PDF SHA-256.
3. (`--with-official`) Official text + structure through `StructureConnector` + `acquire_bundle` (IPS) into
   `gold/<slug>/official/archive/`. Before any request for text the card must carry the
   selected `official_hash`, the act number/date and exactly the one complete edition the
   selection counted (`edition_count`): current, labelled original (`исходная`), dated not
   before the act date. Otherwise `EditionMismatch` is raised before any file is written and
   only that error is recorded as an official-validation failure; any other error propagates.
4. `gold/<slug>/official/input.json` (`corpus-input/2`) with its own diagnostic permission
   (text + structure hashes) and `official-tree.json` from `import_official_tree`
   (`legal-ast/2`). An import refusal is recorded in the receipt, never patched.

Slug: `<kind>-<number digits>-<year>`, kind `fz|ukaz|pp|rp|prikaz`. Orders add the main
signatory authority from the publication card: "Министерство X ..." -> `min` + X; any
other authority -> initials of its significant words (without "Российской Федерации" and
short prepositions/conjunctions). "Российской Федерации" is removed wherever it stands;
"Министерство" must be the first remaining word. Lowercase ASCII transliteration: see `TRANSLIT`.

Receipts `documents/pool/batch-01/receipts/<eo>.json` are written once; a repeated run
verifies every recorded file hash without network access and reports `unchanged`.
Network: existing connectors only, request_interval 1 s.
"""

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from legal_rag.corpus.compiler import json_bytes, load_input, manifest_digest  # noqa: E402
from legal_rag.sources.acquisition import acquire_publication  # noqa: E402
from legal_rag.sources.legislation_russia import LegislationRussiaConnector  # noqa: E402
from legal_rag.sources.publication_pravo import PublicationPravoConnector  # noqa: E402
from legal_rag.sources.structure_bundle import StructureConnector, acquire_bundle  # noqa: E402

M1_04A = PROJECT / "data/m1/m1-04a"
POOL = M1_04A / "documents/pool"
BATCH = POOL / "batch-01"
GOLD = M1_04A / "gold"
TARGET_DATE = "2026-10-21"
AUTHORIZATION = (
    "Owner decision of 21 October 2026 (docs/milestones/m1/04a/M1_04A_EVALUATION_PROTOCOL_2026-10-20.md, "
    "section 9, item 3 'Pool'): diverse official acts are acquired for the M1-04A check pool and an "
    "automatic gold standard is built by matching OCR against the official pravo.gov.ru structured text. "
    "Diagnostic processing of these exact source assets only; not a legal admission, no dated-edition "
    "admission, no external document transmission."
)
AUTHORIZED_BY = "project-owner-decision-2026-10-21-recorded-by-agent"
KIND_PREFIX = {"federal_law": "fz", "presidential_decree": "ukaz", "government_resolution": "pp",
               "government_order": "rp", "ministry_order": "prikaz"}
TRANSLIT = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s",
     "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"], strict=True))
# IPS labels the published edition "на <date>, исходная, актуальная"; its date may be the
# publication/entry date rather than the signing date (seen for ПП № 884: 29.06 vs 05.07.2024).
ORIGINAL_MARK = "исходная"
STOPWORDS = {"и", "по", "в", "во", "на", "о", "об", "для", "за", "при", "с", "со", "к"}
COUNTRY = ("российской", "федерации")


class EditionMismatch(ValueError):
    """The IPS card does not expose exactly the selected single, current, original edition."""


class PublicationMismatch(ValueError):
    """The publication card or PDF differs from the selected act (raised before persistence)."""


# ------------------------------------------------------------------ pure rules

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def translit(text):
    return "".join(TRANSLIT.get(char, char) for char in text.lower())


def authority_short(name):
    words = re.findall(r"[А-Яа-яЁё]+", name)
    kept, index = [], 0
    while index < len(words):
        if tuple(w.lower() for w in words[index:index + 2]) == COUNTRY:
            index += 2
        else:
            kept.append(words[index])
            index += 1
    words = kept
    if not words:
        raise ValueError(f"empty signatory authority: {name!r}")
    if words[0] == "Министерство" and len(words) > 1:
        return "min" + translit(words[1])
    return "".join(translit(word[0]) for word in words if word.lower() not in STOPWORDS)


def slug(act, authority=None):
    digits = re.match(r"\d+", act["number"].strip())
    if digits is None:
        raise ValueError(f"act number has no leading digits: {act['number']!r}")
    prefix = KIND_PREFIX[act["act_type"]]
    if act["act_type"] == "ministry_order":
        if not authority:
            raise ValueError("ministry order slug needs the signatory authority")
        prefix += "-" + authority_short(authority)
    return f"{prefix}-{digits[0]}-{act['date'][:4]}"


def dmy(iso):
    return ".".join(reversed(iso.split("-")))


def check_publication(fetched, act):
    """Publication card must be the selected act; raised before persistence."""
    declared = fetched["declared_publication"]
    card = json.loads(fetched["publication_card_bytes"].decode("utf-8-sig"))
    if (declared["electronic_publication_number"] != act["eo_number"]
            or declared["document_number"].strip().upper() != act["number"].upper()
            or declared["document_date"][:10] != act["date"]
            or declared["pages_count"] != act["pages"]):
        raise PublicationMismatch(f"publication card does not match selection: {act['eo_number']}")
    if type(card.get("pdfFileLength")) is int and card["pdfFileLength"] != len(fetched["raw_bytes"]):
        raise PublicationMismatch(f"PDF length differs from card pdfFileLength: {act['eo_number']}")


def check_edition(card, act):
    """The IPS card must expose exactly the selected single, current, original edition."""
    if card.get("hash") != act["official_hash"]:
        raise EditionMismatch("official card hash differs from selection")
    adoption = " ".join(str(card.get("adoption", "")).split())
    if f"от {dmy(act['date'])} " not in adoption or not adoption.upper().endswith("№ " + act["number"].upper()):
        raise EditionMismatch("official card adoption differs from selection")
    if not isinstance(card.get("nd"), str) or not card["nd"].isdigit() or not isinstance(card.get("baseid"), str):
        raise EditionMismatch("official card identity fields are invalid")
    redactions = card.get("redactions")
    completed = [e for e in redactions if isinstance(e, dict) and e.get("completed") is True] \
        if isinstance(redactions, list) else []
    if len(completed) != act["edition_count"] or act["edition_count"] != 1:
        raise EditionMismatch(f"edition count {len(completed)} differs from selection {act['edition_count']}")
    edition = completed[0]
    if (type(card.get("actualrdk")) is not int or card["actualrdk"] != edition.get("id")
            or edition.get("actual") is not True or edition.get("status") != "актуальная"):
        raise EditionMismatch("selected edition is not the single current edition")
    if not isinstance(edition.get("redname"), str) or ORIGINAL_MARK not in edition["redname"].split(", "):
        raise EditionMismatch(f"single edition is not labelled as the original: {edition.get('redname')!r}")
    try:
        edition_day = datetime.strptime(edition["date"], "%d.%m.%Y").date().isoformat()
    except (KeyError, TypeError, ValueError):
        raise EditionMismatch("edition date is invalid") from None
    if edition_day < act["date"]:
        raise EditionMismatch(f"edition date {edition['date']} precedes act date {dmy(act['date'])}")
    return edition


# ------------------------------------------------------------------ connectors

class PoolPublication(PublicationPravoConnector):
    act = None

    def fetch(self, eo_number):
        fetched = super().fetch(eo_number)
        check_publication(fetched, self.act)
        return fetched


class PoolIPS(LegislationRussiaConnector):
    """Diagnostic fetch for the frozen selection only; production allowlists stay unchanged."""

    act = None

    def fetch(self, document_hash):
        self._meter.reset()
        if document_hash != self.act["official_hash"]:
            raise EditionMismatch("requested hash is not the selected official hash")
        card_url = self._api_base + "/document_card.json?" + urlencode({"hash": document_hash})
        card_bytes, card_transport = self._get(card_url)
        card = self._parse_json(card_bytes, "invalid_card", card_url)
        edition = check_edition(card, self.act)
        text_url = self._api_base + "/documenttext?" + urlencode(
            {"nd": card["nd"], "rdk": edition["id"], "bpa": card["baseid"]})
        body, transport = self._get(text_url)
        self._validate_text(self._parse_json(body, "invalid_text", text_url), card, edition, text_url)
        source_url = f"{self.base_url}/search/{document_hash}"
        return {"adapter_version": "m1-04a-pool-diagnostic/1", "captured_at": datetime.now(UTC).isoformat(),
                "declared_act_identity": " ".join(card["adoption"].split()) + ' "' + card["name"] + '"',
                "declared_edition_label": edition["redname"], "declared_publication": None,
                "external_id": document_hash, "request_cursor": document_hash, "source_system": self.source_system,
                "source_url": source_url, "media_type": "application/json", "raw_bytes": body,
                "raw_asset_role": "legislation_text", "transport_metadata": transport,
                "rights_status": "Owner-authorized M1-04A pool diagnostic; no legal admission or bulk synchronization.",
                "supporting_assets": [{"role": "legislation_card", "raw_bytes": card_bytes,
                                       "media_type": "application/json", "source_url": source_url,
                                       "transport_metadata": card_transport}],
                "unresolved_items": [{"reason": "temporal_coverage_unknown"}]}


# ------------------------------------------------------------------ persistence

def write(path, value):
    payload = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable output conflict: {path}")
        return "unchanged"
    with path.open("xb") as stream:
        stream.write(payload)
    return "new"


def read(path):
    return json.loads(Path(path).read_bytes())


def rel(path):
    return Path(path).resolve().relative_to(PROJECT).as_posix()


def permission(path, identity, hashes):
    if not path.exists():
        write(path, {"schema_version": "processing-permission/1", "decision": "allowed", "scope": "diagnostic",
                     "act_identity": identity, "source_asset_sha256s": sorted(hashes),
                     "authorized_by": AUTHORIZED_BY, "authorized_at": datetime.now(UTC).isoformat(),
                     "rights_basis": AUTHORIZATION})
    record = read(path)
    if record["act_identity"] != identity or record["source_asset_sha256s"] != sorted(hashes):
        raise ValueError(f"existing permission has another scope: {path}")
    return {"path": None, "sha256": sha(path)}


def twice(acquire):
    """First run `new` (or `unchanged` when resuming), second run must be `unchanged`."""
    runs = [acquire()]
    if runs[0]["result"] in ("new", "unchanged"):
        runs.append(acquire())
    ok = runs[0]["result"] in ("new", "unchanged") and len(runs) == 2 and runs[1]["result"] == "unchanged"
    return ok, runs


def item_of(archive, source_item):
    return read(archive / "items" / (hashlib.sha256(source_item.encode()).hexdigest() + ".json"))


def acquire_pdf(act, connector, batch):
    archive = batch / "archive"
    connector.act = act
    ok, runs = twice(lambda: acquire_publication(connector, act["eo_number"], archive))
    if not ok:
        return {"status": "failed", "stage": "pdf_acquisition", "runs": runs}
    item = item_of(archive, runs[0]["source_item"])
    digest = item["latest_successful_asset"]
    asset = read(archive / "assets" / (digest + ".json"))
    if asset["sha256"] != digest or sha(archive / asset["archive_key"]) != digest:
        raise ValueError(f"archived PDF hash mismatch: {act['eo_number']}")
    card = json.loads((archive / "raw" / item["declared_publication_asset"]).read_bytes().decode("utf-8-sig"))
    main = [a["name"] for a in card["signatoryAuthorities"] if a.get("isMain")] or \
        [a["name"] for a in card["signatoryAuthorities"]]
    return {"status": "ok", "runs": runs, "item": item, "sha256": digest, "asset": asset,
            "authority": main[0], "card_sha256": item["declared_publication_asset"],
            "pdf_file_length": card.get("pdfFileLength")}


def write_pdf_input(act, key, pdf, batch):
    archive = batch / "archive"
    item, digest = pdf["item"], pdf["sha256"]
    identity = item["declared_act_identity"]
    permission_path = archive / "reviews" / (key + "-permission.json")
    reference = permission(permission_path, identity, [digest])
    reference["path"] = permission_path.relative_to(archive).as_posix()
    url = pdf["asset"]["source_url"]
    manifest = {"schema_version": "corpus-input/1", "kind": "original_amendments", "archive_root": "../archive",
                "act_identity_claim": {"declared_identity": identity}, "target_dates": [TARGET_DATE],
                "admission_status": "unresolved",
                "admission_blockers": ["m1_04a_pool_diagnostic_only", "legal_admission_not_requested"],
                "unresolved_questions": ["Original publication for the M1-04A check pool; legal admission is not requested."],
                "processing_permission": reference,
                "assets": [{"role": "original", "sha256": digest, "source_item": item["source_item"], "source_url": url,
                            "declared_identity": identity,
                            "evidence": {"source_asset_sha256": digest, "source_url": url, "locator": "pdf:whole-document"}}]}
    manifest["manifest_hash"] = manifest_digest(manifest)
    path = batch / key / "input.json"
    write(path, manifest)
    normalized, _, _ = load_input(path, TARGET_DATE)
    assert normalized["manifest_hash"] == manifest["manifest_hash"]
    return path, permission_path


def import_tree(input_path):
    from legal_rag.corpus.native_text import extract_native
    from legal_rag.corpus.official_import import import_official_tree

    normalized, raw, _ = load_input(input_path, TARGET_DATE)
    asset = next(a for a in normalized["assets"] if a["role"] == "consolidated")
    binding = normalized["structure_bundle"]
    extraction = extract_native(asset, raw[asset["sha256"]])
    field = asset["evidence"]["locator"].removeprefix("$.").removeprefix("/")
    html = json.loads(raw[asset["sha256"]])[field]
    return import_official_tree(asset, extraction, html, raw[binding["structure_sha256"]],
                                binding["structure_sha256"], binding["source_system"])


def acquire_official(act, key, base, gold):
    """Bundle + corpus-input/2. Edition mismatches raise before any write."""
    official = gold / key / "official"
    archive = official / "archive"
    base.act = act
    ok, runs = twice(lambda: acquire_bundle(StructureConnector(base), act["official_hash"], archive))
    if not ok:
        return {"status": "failed", "stage": "official_acquisition", "runs": runs}
    bundle_path = Path(runs[-1]["structure_bundle"])
    bundle = read(bundle_path)
    item = item_of(archive, bundle["source_item"])
    claim = item["declared_act_identity"]
    permission_path = archive / "reviews" / "permission.json"
    reference = permission(permission_path, claim, [bundle["text_sha256"], bundle["structure_sha256"]])
    reference["path"] = "reviews/permission.json"
    manifest = {"schema_version": "corpus-input/2", "kind": "official_consolidated", "archive_root": "archive",
                "act_identity_claim": {"declared_identity": claim}, "target_dates": [TARGET_DATE],
                "admission_status": "unresolved",
                "admission_blockers": ["m1_04a_auto_gold_source_only", "temporal_coverage_unknown",
                                       "legal_admission_not_requested"],
                "unresolved_questions": ["Official single-edition snapshot for the M1-04A automatic gold standard; no dated applicability decision."],
                "processing_permission": reference,
                "structure_bundle": {"path": bundle_path.relative_to(archive).as_posix(), "sha256": sha(bundle_path)},
                "assets": [{"role": role, "sha256": bundle[field], "source_item": bundle["source_item"],
                            "source_url": bundle["source_url"], "declared_identity": claim,
                            "evidence": {"source_asset_sha256": bundle[field], "source_url": bundle["source_url"],
                                         "locator": locator}}
                           for role, field, locator in [("consolidated", "text_sha256", "$.doctext"),
                                                        ("official_structure", "structure_sha256", "$.data")]]}
    manifest["manifest_hash"] = manifest_digest(manifest)
    input_path = official / "input.json"
    write(input_path, manifest)
    card = read(archive / "raw" / item["supporting_assets"]["legislation_card"])
    edition = check_edition(card, act)
    result = {"status": "ok", "runs": runs, "identity": claim,
              "edition": {"id": edition["id"], "date": edition["date"], "label": edition["redname"],
                          "selector": bundle["selector"]},
              "bundle": rel(bundle_path), "input": rel(input_path), "permission": rel(permission_path),
              "text_sha256": bundle["text_sha256"], "structure_sha256": bundle["structure_sha256"]}
    return result


TREE_CODE = [PROJECT / "src/legal_rag/corpus" / name for name in (
    "official_import.py", "official_binding.py", "official_structure.py", "structure.py", "native_text.py",
    "housing_html.py", "compiler.py")]


def build_tree(official):
    """Derived local step: `official-tree.json`, or a refusal record keyed by the importer code hash."""
    tree_path = official / "official-tree.json"
    if not tree_path.exists():
        code = hashlib.sha256("".join(sha(p) for p in TREE_CODE).encode()).hexdigest()
        refusal_path = official / f"import-refusal-{code[:12]}.json"
        if refusal_path.exists():
            return {"status": "refused", "result": "unchanged", **read(refusal_path)}
        try:
            tree = import_tree(official / "input.json")
        except ValueError as error:
            record = {"reason": str(error), "code_sha256": code, "path": rel(refusal_path)}
            write(refusal_path, record)
            return {"status": "refused", "result": "new", **record}
        write(tree_path, tree)
        result = "new"
    else:
        result = "unchanged"
    tree = read(tree_path)
    return {"status": "ok", "result": result, "path": rel(tree_path), "sha256": sha(tree_path),
            "schema_version": tree["schema_version"],
            "source_units": sum(n["kind"] == "source_unit" for n in tree["nodes"]), "nodes": len(tree["nodes"])}


# ------------------------------------------------------------------ driver

def frozen_selection(batch, with_official=False):
    path = batch / "selection.json"
    recorded = (batch / "selection.sha256").read_text(encoding="utf-8").split()[0]
    if sha(path) != recorded:
        raise ValueError("selection.json differs from selection.sha256")
    selection = read(path)
    if not selection["quotas_filled"]:
        raise ValueError("selection is incomplete")
    if with_official and any(a.get("official_source") != "ips" for a in selection["selected"]):
        raise ValueError("selection is outside the IPS official tree")
    # Failed acquisitions are refilled by write-once `selection-refill-NN.json` (see
    # select_m1_04a_pool.py refill): replacements join the act list, replaced acts leave it.
    replaced = set()
    for refill in sorted(batch.glob("selection-refill-??.json")):
        digest = (refill.with_suffix(".sha256")).read_text(encoding="utf-8").split()[0]
        if sha(refill) != digest:
            raise ValueError(f"{refill.name} differs from its sha256")
        record = read(refill)
        replaced.update(item["failed_eo_number"] for item in record["replaced"])
        selection["selected"] = selection["selected"] + record["selected"]
    selection["selected"] = [a for a in selection["selected"] if a["eo_number"] not in replaced]
    return selection, recorded


def files_of(receipt):
    return receipt["files_sha256"]


def verify_receipt(receipt):
    for path, digest in files_of(receipt).items():
        if sha(PROJECT / path) != digest:
            raise ValueError(f"recorded output changed: {path}")


def retryable(failure):
    """A failed run with a retryable transport error is retried on the next invocation."""
    if failure.get("stage") == "official_validation":
        return False
    report = read(failure["runs"][-1]["report"])
    return any(error.get("retryable") for error in report.get("errors", []))


def run(batch, gold, with_official=False):
    selection, selection_sha = frozen_selection(batch, with_official)
    publication = PoolPublication(timeout=60, request_interval=1)
    ips = PoolIPS(timeout=40, request_interval=1)
    failed = 0
    for act in selection["selected"]:
        receipt_path = batch / "receipts" / (act["eo_number"] + ".json")
        if receipt_path.exists():
            receipt = read(receipt_path)
            verify_receipt(receipt)
            status = "unchanged"
        else:
            try:
                pdf = acquire_pdf(act, publication, batch)
            except PublicationMismatch as error:
                pdf = {"status": "failed", "stage": "publication_check", "reason": str(error),
                       "runs": [{"run_id": "none"}]}
            if pdf["status"] != "ok":
                failed += 1
                write(batch / "failures" / f"{act['eo_number']}-{pdf['runs'][-1]['run_id']}.json", pdf)
                print(json.dumps({"eo": act["eo_number"], "result": "failed", "stage": pdf["stage"]}), flush=True)
                continue
            key = slug(act, pdf["authority"] if act["act_type"] == "ministry_order" else None)
            input_path, pdf_permission = write_pdf_input(act, key, pdf, batch)
            if not with_official:
                official = {"status": "not_requested"}
            else:
                try:
                    official = acquire_official(act, key, ips, gold)
                except EditionMismatch as error:
                    official = {"status": "failed", "stage": "official_validation", "reason": str(error)}
            if with_official and official["status"] != "ok":
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                write(batch / "failures" / f"{act['eo_number']}-official-{stamp}.json", official)
                if retryable(official):
                    failed += 1
                    print(json.dumps({"eo": act["eo_number"], "slug": key, "result": "failed_retryable",
                                      "stage": official["stage"]}, ensure_ascii=False), flush=True)
                    continue
                if "runs" in official:
                    official["reason"] = read(official["runs"][-1]["report"])["errors"]
            outputs = [input_path, pdf_permission, batch / "archive" / pdf["asset"]["archive_key"]]
            if official["status"] == "ok":
                outputs += [PROJECT / official[k] for k in ("bundle", "input", "permission")]
            receipt = {"schema_version": "m1-04a-pool-acquisition/1", "selection_sha256": selection_sha,
                       "eo_number": act["eo_number"], "slug": key, "act_type": act["act_type"],
                       "authority": pdf["authority"],
                       "pdf": {"sha256": pdf["sha256"], "byte_length": pdf["asset"]["byte_length"],
                               "card_pdf_file_length": pdf["pdf_file_length"], "declared_pages": act["pages"],
                               "card_sha256": pdf["card_sha256"], "input": rel(input_path),
                               "permission": rel(pdf_permission), "runs": [r["result"] for r in pdf["runs"]],
                               "run_ids": [r["run_id"] for r in pdf["runs"]]},
                       "official": {**{k: v for k, v in official.items() if k != "runs"},
                                    "runs": [r["result"] for r in official.get("runs", [])],
                                    "run_ids": [r["run_id"] for r in official.get("runs", [])]},
                       "files_sha256": {rel(p): sha(p) for p in outputs}}
            write(receipt_path, receipt)
            status = "new"
        line = {"eo": act["eo_number"], "slug": receipt["slug"], "result": status,
                "pdf": receipt["pdf"]["sha256"], "official": receipt["official"]["status"]}
        if receipt["official"]["status"] == "not_requested":
            pass
        elif receipt["official"]["status"] == "ok":
            tree = build_tree(PROJECT / Path(receipt["official"]["input"]).parent)
            line["tree"] = {k: tree[k] for k in ("status", "result", "source_units", "reason") if k in tree}
        else:
            line["official_failure"] = receipt["official"].get("stage")
        print(json.dumps(line, ensure_ascii=False), flush=True)
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batch", type=Path, default=BATCH,
                        help="batch name under documents/pool (e.g. batch-02) or a path")
    parser.add_argument("--gold", type=Path, default=GOLD)
    parser.add_argument("--with-official", action="store_true",
                        help="also acquire the IPS official text/structure and build the tree")
    args = parser.parse_args(argv)
    batch = POOL / args.batch if len(args.batch.parts) == 1 else args.batch
    return run(batch.resolve(), args.gold.resolve(), args.with_official)


if __name__ == "__main__":
    raise SystemExit(main())
