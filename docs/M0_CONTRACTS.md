# M0 contracts — frozen version 1

**Frozen:** 1 October 2026. **Contract bundle:** `m0-contracts/1`.

This records implemented acquisition and `edition-candidate/1` behavior.
The [freeze manifest](M0_CONTRACT_FREEZE.json) pins implementation and fixture
SHA-256 values. A freeze is a reproducible baseline, not M0 acceptance or legal
approval. The [M0 gate](M0_GATE_REPORT.md) controls entry to M1.
Tracked text-file hashes normalise CRLF to LF so Windows checkout conversion
does not change the frozen content. Local evidence hashes always use raw bytes.
The frozen byte-for-byte handoff fixture is excluded from Git newline conversion.

## Acquisition boundary

The CLI in `src/legal_rag/sources/__main__.py` consumes a fixture, publication
number, approved consolidated-document hash, claims file, or retained
reconciliation. Network adapters return raw bytes, source claims and transport
metadata to the shared acquisition lifecycle. They never produce `LegalEdition`
or assert legal applicability.

| Format | Implemented version | Persistent boundary |
|---|---|---|
| Source item, asset, acquisition run, exception, relation, reconciliation | No embedded `schema_version`; existing shape frozen by `m0-contracts/1` | `items/`, `assets/`, `runs/`, `exceptions/`, `relations/`, `reconciliations/` |
| Candidate handoff | `edition-candidate/1` | `candidates/<candidate_id>.json` |
| Pilot report / pass | `m0-pilot-report/1`, `m0-pilot-pass/1` | `pilot_runs/<pilot_id>/` |
| Publication discovery / event | `publication-discovery/1`, `publication-event/1` | `discoveries/`, `publication_events/` |
| Gate decision | `m0-gate/1` | local `data/m0-12-gate/gate.json` |

`SourceSystem` is represented by connector constants and source provenance;
M0 does not persist a separate SourceSystem registry. Do not invent embedded
schema versions for historical records. A later incompatible migration must
explicitly version the record format and retain the old evidence.

| Adapter | Version | Source contract |
|---|---|---|
| Fixture | `fixture/1` | Project-authored fixture bytes and metadata |
| PublicationPravoConnector | `publication-pravo/1` | Explicit HTTP official publication API |
| ActualPravoConnector | `actual-pravo/2` | Public UI plus private JSON routes for the two approved acts |
| LegislationRussiaConnector | `legislation-russia/3` | New `ips.pravo.gov.ru` test bank, private card/documenttext routes |
| Relation reconciliation | `relation-reconciliation/1` | Evidence-backed claims, canonical source items |

Acquisition returns `run_id`, `source_item`, `result`, and an absolute report
path. Results are exactly `new`, `unchanged`, `changed`, `failed`. A run records
UTC start/finish, adapter, source/cursor, result counts, errors, request count
and received bytes. Changed runs additionally record old/new hashes and changed
asset roles. Failed runs link standalone exceptions and retain the last success.
Runs are UUID observations; they are not deterministic content identities.

Raw bytes live at `raw/<SHA-256>`. Asset metadata records `sha256`, `byte_length`,
`archive_key`, `captured_at`, `media_type`, `source_url`, `rights_status`,
`transport_metadata` and optional `role`. Source items retain identity, edition
claims, latest-success pointer and complete asset history. Asset metadata and
raw files are written once; mutable source pointers use atomic replace.
Format comes from bytes. Identity conflicts fail before new evidence is written.

Relations record `relation_id`, from/to items, `relation_type`, `asserted_by`,
`review_state`, and an evidence reference containing locator, source URL and
archived SHA-256. Evidence must match the current role pointer, asset metadata
and raw bytes. Unmatched/ambiguous targets become exceptions. Discovery marks
affected candidates `stale`; acquisition preserves that marker and evidence.

## M1 handoff

`build-candidate --reconciliation <path> --data-dir <archive>` loads persisted
items, relations, exceptions and raw assets. Exactly one evidence-backed
`edition_candidate -> consolidates -> act` path is required. It refuses stale
candidates and validates every referenced archived asset before serialization.

The project-authored [frozen example](../tests/legal_rag/sources/fixtures/edition_candidate_v1.json)
is reproduced byte-for-byte by `test_candidate_handoff.py`. It contains synthetic
metadata and stubs, no official consolidated text; redistribution is permitted.
Origin: this repository's `_write_records` test fixture, captured 1 October 2026.
Its expected hash and the existing replay-fixture hashes are in the freeze manifest.

| Handoff field | Meaning |
|---|---|
| `schema_version`, `candidate_id`, `reconciliation_id` | Contract version, deterministic content ID and retained reconciliation |
| `act_identity_claim` | Declared identity and source item, asset hashes and relation IDs |
| `edition_claim` | Claimed date/label, capture time, snapshot hash and evidence references |
| `temporal_evidence` | Explicit status, nullable `valid_from/to`, supporting hashes and relations |
| `source_evidence.assets` | Allowlist: archive key, length, capture time, media type, rights, hash, URL |
| `source_evidence.items` | Allowlist: declared identity, kind, label, source item/system, optional URL |
| `source_evidence.relations` | Relation identifiers, endpoints, asserting source/state and public evidence |
| `source_evidence.exceptions`, `unresolved_items` | Exception IDs and explicit reasons with evidence references |
| `review_status`, `review_decision` | `unreviewed`/null by default; explicit `reviewed` or `rejected` decision |

An explicit decision requires `Legal Reviewer`, reviewer ID, timestamp with UTC
offset, rationale, matching candidate scope and asset/relation references. Its
normalised content gets a deterministic decision ID. This validates attribution
and scope; it does not independently establish legal sufficiency. M0-10's
recorded admission blockers remain binding even for a snapshot benchmark label.

Connector internals (`adapter_version`, `baseid`, `nd`, `rdk`, asset role and
transport metadata) never enter the shared handoff. JSON uses UTF-8, sorted keys,
two-space indentation and a final LF. Candidate identity hashes the payload
without `candidate_id`, using sorted keys and compact JSON with `ensure_ascii=False`.
References and collections are deterministically sorted by the existing builder.
Repeated identical input returns the same ID and `unchanged`.

## Reproduction and change rule

```powershell
python -m unittest discover -s tests/legal_rag/sources -p "test_*.py" -v
python docs/assets/generate_m0_gate.py
```

Default tests are offline and do not consume private gold labels. Gate generation
checks pinned local evidence and frozen code/fixtures, renders every current
plan criterion, writes a machine decision, and exits `2` unless all criteria pass.
Missing or changed evidence blocks the gate. The closed gold file is hashed as
bytes only; its queries and expected labels are never deserialized.

The retained live replay is under `data/m0-12-gate/handoff-replay/`, copied from
`data/m0-06-v2` without its output candidates. It is a contract exercise using
the rejected PP No. 354 snapshot, not legal admission. Both CLI builds must
retain candidate `ebf7b535637837e4ef24dcf99c47f3790001797b60f18f23a02f6a05ec6664d9`
with `new` then `unchanged`; the original retained candidate must remain identical.

Do not refresh freeze hashes to hide drift. An incompatible contract change
requires a new version, an explicit migration decision and updated contract
replay. A compatible code change requires a reviewed freeze update and offline
checks. M1 starts only after the separately reassessed M0 gate passes.
