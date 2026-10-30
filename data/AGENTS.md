# Local data instructions

- Since 21.10.2026 all new M1-04A work lives under `m1/m1-04a/`:
  `documents/{development,reserved,pool/<batch>}/<slug>/` hold hash-verified
  copies of originals (`document.pdf` + `source.json`) built by
  `docs/assets/build_m1_04a_catalog.py`; `ocr/<slug>/<run>/`, `gold/<slug>/` and
  `experiments/<YYYYMMDD>-<name>/` hold derived outputs, one new folder per run.
  Never open `reserved/` bodies before Task 3. Earlier M1-04A material was not
  moved (pinned paths); `m1/m1-04a/LEGACY.md` maps it.

- M1-04A naming (owner decision 27.10.2026, full rule in `docs/AGENTS.md`): step N -> prototype П<N> -> scan batch N.
  Data paths keep the old names (owner decision 27.10.2026: never rename them): `experiments/<date>-prototype-v<k>-freeze/`
  holds П<k+1> from v7 on (v7 = П8, v8 = П9, v9 = П10, v10 = П11); `documents/pool/batch-NN` = «сканы, партия N»;
  `json-corpus/20261025-v1` = «официальные деревья от 25.10», `json-corpus/20261026-v2` = «деревья от 26.10».

- Check-pool batch 1 (21.10.2026): originals in `m1/m1-04a/documents/pool/batch-01/`
  (slug = `<type>-<number>-<year>`, ministry orders `prikaz-<ministry>-<n>-<year>`;
  `selection.json` frozen before PDFs, superseded `attempt-01` kept), OCR in
  `ocr/<slug>/run-01/`, agent gold `gold/<slug>/agent-<slug>.gold.txt` frozen by
  `experiments/20261021-batch-01-gold-freeze/freeze.json` before any parser run.
  First pass: `experiments/20261021-batch-01-first-pass/` (`freeze.json` written
  before `run`, all regions scored); `-first-pass-conv-v1/` rescores the same
  saved outputs under annotation convention v1 (Picture not scored) with split
  error classes. Annotator input `-annotation-input/` carried stage-2 `P`/`join`
  (continuation not blind); future inputs come from
  `docs/assets/build_m1_04a_annotation_input.py` (v1). `attempt-02-superseded-receipts/`
  keeps acquisition receipts frozen by a broad `ValueError` catch; superseded,
  not used. `pool/batch-01/status.json` records measured -> development;
  indexes stay write-once. IPS gives its single edition `rdk = 0`, so
  `official_binding` refuses those bundles; only pp-884 would import a tree.

- Check-pool batch 2: `m1/m1-04a/documents/pool/batch-02/selection.json` (frozen, quotas code 1→0 / federal_law 3→4 recorded as `quota_change`); its `--min-days 120`, exact command, feed-cache hash and the meaning of `attempt-01-partial-unfilled.json` are in the write-once sidecar `selection-provenance.json`.

- Check-pool batch 4: `m1/m1-04a/documents/pool/batch-04/selection.json` (frozen, sha256 bf4bde02…,
  seed 20261024, 120 days not sampled by batches 1-3, pool/2, no code quota, 11 acts, 5 long; feed cache
  `feed-cache-b4.json` and command in `selection-provenance.json`). Ukaz 481/2016 is an award decree:
  personal names stay out of docs.
  Acquired 23.10 (pool/2, 11/11 `new` then `unchanged`, no refill; target date = run date as batch 3);
  OCR `ocr/<slug>/run-01` (264 pages, all replays equal), summary
  `experiments/20261023-batch-04-ocr/summary.json`; `summary.raw.failed-attempt1-slug-argument.json`
  is a no-OCR attempt (slugs passed as one string via `-File`): pass `-Slugs` as an array via `-Command`.
  Gold (convention v2, 11 acts, 2465 regions, no parts, no `exceptions.json`) frozen in
  `experiments/20261023-batch-04-gold-freeze/` (`freeze.json` f1ac8818…; its `annotation_convention`
  v1 is the script constant, `freeze-addendum.json` records v2, `--single-annex` default, doubts and
  the 107/136 blind-pair check). No format fixes were needed.

- Check-pool batch 5: `m1/m1-04a/documents/pool/batch-05/selection.json` (frozen 23.10, sha256 ab90d9c9…,
  profile `batch-05`, seed 20261025, 120 days 2011-2025 not sampled by batches 1-4, pool/2, 11 acts, 7 long,
  `soft_fallbacks` 0; feed cache `feed-cache-b5.json` 0ebdaedd…, command in `selection-provenance.json`, code e4a82d0).
  Without `one_per_issuer_day` FZ 334+335/2019 (same day) would both be picked; 395-FZ/2023 replaced 335.
  Ukaz 669/2016 is an appointment decree (judges): personal names stay out of docs. RP 3721-r has an empty feed name.
  Acquired 23.10 (pool/2, 11/11 `new` then `unchanged`, no refill; RP 3721-r passed despite its empty feed name;
  catalog `pool/batch-05/index.json`, batches 1-4 indexes unchanged). OCR `ocr/<slug>/run-01` (10 acts, 476 pages,
  2922 regions, all replays equal; rp-1099-2014 holds 45%), summary `experiments/20261023-batch-05-ocr/summary.json` (3efdfd3b…).
  prikaz-minfinansov-141-2023 (54 p.) failed OCR: dots.mocr hit the token limit (`length`) on pages 25, 30, 42;
  its `run-01` holds only the failure record (native output kept in OCR-Lab `results/legal-rag/0cc7ac41…`).
  The run script skips an existing `run-01`, so any retry or refill of that slot is a separate decision.
  Refill (controller ruling: OCR failure = acquisition failure): hand-written `failures/<eo>-ocr-run-01.json`
  (`stage: ocr`, reason `ocr_failed: ...`) + `refill` (plain rule; every pick also met the soft preferences).
  `selection-refill-01..03`: minselskogo-235-2016 (47 p.) and fst-155-2015 (9 p.) failed extraction on the
  project table check (`span exceeds its rows` / `overlapping cells`; dots.mocr completed all pages), attempt 3
  prikaz-minnauki-697-2023 (12 p., 85 regions) passed: `experiments/20261023-batch-05-ocr-refill-0{1,2,3}/`.
  Measured set = the 10 acts of `20261023-batch-05-ocr` + minnauki-697 (488 p., 3007 regions, rp-1099 43.8%);
  pass these 11 slugs explicitly to annotation/gold/first pass. The three failed acts keep PDFs, inputs and
  failed `run-01` as evidence. `index.json` now lists 14 originals; `index-superseded-{11,12,13}-acts.json` kept.
  Re-run after the per-table grid fix (not part of the measured set): `experiments/20261023-dense-table-ocr/`
  (`summary.json`; 235 and 155 complete, 141n still `length`; `rotation-probe-minfinansov-141/`).
  141n with the opt-in rotation retry (`m1/ocr.rotation-retry.local.json`): `experiments/20261023-rotation-retry-ocr/`
  (complete, pages 25/30/42 cw90, replay equal; `upright-forced-retry-probe/` 0/12 accepted).
  Owner decision 23.10.2026: batches after 5 use `m1/ocr.rotation-retry.local.json` (`ocr.local.json` +
  `rotation_retry: true`; keep both files in step), the default of `run_m1_04a_ocr.ps1 -OcrConfig`.
  Gold (v2 incl. §5-§6, 7 Codex jobs, 11 acts, 2268 regions, 78 `+`, no `exceptions.json`, no format fixes) frozen in
  `experiments/20261023-batch-05-gold-freeze/` (`freeze.json` 9c90fde3…; `freeze-addendum.json` 5a532f8b… records v2,
  `single_annex` + `attached_ordinal` defaults, doubts, findings, refill history and hashes the rp-1099 parts).
  rp-1099-2014 = 2 page-range parts in `gold/rp-1099-2014/chunks/` stitched unchanged (seam `S/III/6` consistent);
  65.1-65.2 carry the first pool alternatives `S/III|S/III/7` (evaluator accepts `|`).

- Check-pool batch 6: `m1/m1-04a/documents/pool/batch-06/selection.json` (frozen 23.10, sha256 5d4f598a…,
  profile `batch-06`, seed 20261026, 120 days 2011-2025 not sampled by batches 1-5, pool/2, 11 acts, 6 long,
  `soft_fallbacks` 0; feed cache `feed-cache-b6.json` 745d009d…, command in `selection-provenance.json`, code 916f323).
  Ukaz 1711/2012 sets a commission's membership: personal names stay out of docs. RP 2390-r and 356-r have empty feed names.
  Acquired 23.10 (pool/2, 11/11 `new` then `unchanged`, no refill; first run stopped at the 5th act, FNS «ЕД-7-20/957@»,
  with no slug rule; after the fix (`prikaz-fns-957-2020`) acts 5-11 `new`; catalog `pool/batch-06/index.json`, batches 1-5 indexes unchanged).
  OCR with the rotation retry (`ocr.rotation-retry.local.json` ec2ba2ee…, OCR-Lab client 6beed388…) `ocr/<slug>/run-01`:
  11/11 complete, 337 pages, 2482 regions, 140 tables, 0 `grid: "unresolved"`, 0 rotation retries, all replays equal;
  pp-887-2023 holds 31%. Summary `experiments/20261023-batch-06-ocr/summary.json` (32e77daa…, `--table-stats`). No refill.
  Gold (v2 incl. §5-§6, 7 Codex jobs, 11 acts, 1925 regions, 117 `+`, no parts, no `exceptions.json`, no format fixes) frozen in
  `experiments/20261023-batch-06-gold-freeze/` (`freeze.json` 9d9f6ec2…; `freeze-addendum.json` e205d88b… records v2,
  `single_annex` + `attached_ordinal` defaults, doubts and the blindness limitation: every job read Codex memory about
  earlier annotation jobs before its job file; no sign of influence in the notes). minek-37 27.1-28.2 carry
  `S/AN5|S/AN5/5.2`; its flat `S/AN5/5.N` are not §5 exceptions (annex 5 has no point «5.»).

- Check-pool batch 7: `m1/m1-04a/documents/pool/batch-07/selection.json` (frozen 24.10, sha256 4e7736e4…,
  profile `batch-07`, seed 20261027, 120 days 2011-2025 not sampled by batches 1-6, pool/2, 11 acts, 5 long,
  `soft_fallbacks` 1: 411-FZ/2016 (3 p., same issuer-day as 410-FZ); feed cache `feed-cache-b7.json` 2b619823…,
  command in `selection-provenance.json`, code 144760e). Its `scripts_dirty: true` is the uncommitted
  `build_m1_04a_catalog.py` `POOL_BATCHES` edit; selection code and `src/legal_rag/sources` equal 144760e.
  Ukaz 410/2021 is an appointment decree (judges): personal names stay out of docs.
  Acquired 24.10 (pool/2, 11/11 `new` then `unchanged`, no refill; catalog `pool/batch-07/index.json`, batches 1-6
  indexes unchanged). OCR with the rotation retry (`ocr.rotation-retry.local.json` ec2ba2ee…, OCR-Lab client 6beed388…,
  `git apply -R --check` passes) `ocr/<slug>/run-01`: 11/11 complete, 178 pages, 1703 regions, 19 tables,
  0 `grid: "unresolved"`, 0 rotation retries, all replays equal; prikaz-minenergetiki-90-2019 holds 19%.
  Summary `experiments/20261024-batch-07-ocr/summary.json` (54204f10…, `--table-stats`). No refill.
  Gold (v2 incl. §5-§6, 6 Codex jobs run with `codex exec -c features.memories=false`, 11 acts, 1477 regions, 96 `+`,
  no parts, no `exceptions.json`, no format fixes) frozen in `experiments/20261024-batch-07-gold-freeze/`
  (`freeze.json` d8c5abbc…; `freeze-addendum.json` b5e636ef… records v2, `single_annex` + `attached_ordinal` defaults,
  doubts and strict blindness: all 11 notes say «Память Codex: не загружалась», job logs show no memory reads).
  prikaz-minenergetiki-90-2019 30.8-31.8 (12 regions) carry `S/AN3|S/AN3/I` or `|S/AN3/II` (form headings outside the grid).

- JSON-vs-Codex pilot (24.10.2026, owner request): `m1/m1-04a/experiments/20261024-json-codex-pilot/`.
  PP 491 IPS HTML + structure JSON (rdk 21) -> Chrome PDF -> image-only "scan" -> dots.mocr -> JSON owners projected
  onto OCR regions by word alignment (`freeze-json-gold.json` written before the Codex run) vs one blind Codex job:
  282/282 owners equal. Synthetic, not a pool batch; report `docs/milestones/m1/04a/M1_04A_JSON_CODEX_PILOT_2026-10-24.md`.

- Second-layer corpus v1 (25.10.2026): `m1/m1-04a/json-corpus/20261025-v1/` from
  `docs/assets/acquire_m1_04a_json_corpus.py` (phases write once). 100 IPS federal acts with structure JSON + HTML,
  frozen `selection.json` (ec9322a0…) and `split.json` (bea6a9be…, 69 dev / 31 holdout). Never open or tune on
  holdout bodies. Range ends may be `<tr id="r<N>">`; fetch attempts 01/02 (false rejections) kept as superseded.
  No IPS trees for treaties, KS, osnovy; no ministry orders/SanPiN. Report `M1_04A_JSON_CORPUS_2026-10-25.md`.

- Second-layer baseline (25.10.2026, dev only): `m1/m1-04a/experiments/20261025-json-baseline-dev/` (projection 1,
  freeze 331012b2…) and `…-dev-proj2/` (projection 2, freeze 1dbbeca9…; «N.» in an article -> `ч<N>`), both from
  `docs/assets/m1_04a_json_baseline.py`; frozen v5 79.8% regions / 89.4% macro on projection 2; frozen v6.1 (`v6-1-results.json`) gives identical
  owners in all 22344 regions (no cycle-7 rule fired), so the second-layer base is v6.1 = v5 there. Pseudo extractions
  keep <br> as line breaks and CSS superscript spans (W9/WB) as «¹»; projection 1 reproduces byte for byte.

- Cycle 8 (25.10.2026): JSON corpus runs `20261025-json-baseline-dev-proj2/c8-{c1,c2,c2-r2,c3}-results.json`
  (`c8-c2` is the attempt that missed «Дополнение»), pool regressions `experiments/20261025-dev-regression-cycle8-
  {c1,c2,c2-r2,c3}/` against `20261024-dev-regression-v6-1/summary.json` (no drops, errors equal).
  C4-C12: JSON runs `…-proj2/c8-{c4,c5,c5-r2,c5-r3,c5-r4,c6,c7,c7-r2,c8,c9,c9-r2}` and on projection 3
  `20261025-json-baseline-dev-proj3/` (freeze 6df9bb99…; `v6-1` base 79.8%, `c8-{c10,c11,c12}`, c12 96.3%);
  pool `20261025-dev-regression-cycle8-c8-*`, failed attempts `…-c8-c5-attempt1-failed`, `…-c8-c9-attempt1-failed`.
  Projection 4 (owner decisions 25.10.2026): `20261025-json-baseline-dev-proj4/` (freeze 6c8a36a3…; `v6-1`, `c8-c12`, `v7`).
  Prototype v7 freeze `20261025-prototype-v7-freeze/`, pool regression `20261025-dev-regression-v7`.
  JSON holdout measured once on 25.10.2026: `20261025-json-holdout-proj4/` (freeze 42f82227…, `run-receipt.json`,
  `v7`/`v6-1` outputs and results); never re-run; the holdout is now development.
  Cycle 9 baselines of frozen v7 (26.10.2026; track B gates against them): pool `20261026-dev-regression-89-v7/`
  (89 docs, 16632/16917 no_section, `cross_scope_v2` 188 — all in batch 8; the 78 old rows equal
  `…-dev-regression-v7`); JSON `20261026-json-all-proj4/` (`--split all`, 200 files byte-equal to the frozen dev and
  holdout projections; `v7` 36994/38337 = 96.5%, dev 21472/21908, holdout 15522/16429, 75/100 perfect).
  The corpus baseline of cycle 9 is projection 5 (owner decision 26.10.2026, «1.» in a concept section is a point):
  `20261026-json-all-proj5/` — gold differs from proj4 only in rp-1000000000602087490 (218 rows; the header line
  names the projection), `v7` 37212/38337 = 97.1%, 76/100 perfect.
  Cycle 9 runs: proj5 `c9-b1`; projection 6 (article notes transparent) `20261026-json-all-proj6/` with `c9-b1`
  (37215, the cycle-9 step baseline there), `c9-b2` (attempt 1, failed), `c9-b2-r2`, later steps `c9-<step>`; pool
  `20261026-dev-regression-cycle9-<step>`.

- Check-pool batch 9 (26.10.2026): `m1/m1-04a/documents/pool/batch-09/selection.json` (dffabeca…, profile `batch-09`,
- Scan batch 12 (27.10.2026): `m1/m1-04a/documents/pool/batch-12/selection.json` (profile `batch-12`, seed 20261101, code
  3297760, sha 66812fc2…); acquired 11/11 `new` then `unchanged`, no refill. OCR `experiments/20261027-batch-12-ocr/`
  (11/11, replays equal, 6 unresolved grids, 1 rotation-retry page). Gold 7 Codex jobs (FSB-641 in 2 parts under
  `gold/prikaz-fsb-641-2020/chunks/`), 1782 regions, frozen `experiments/20261027-batch-12-gold-freeze/` (1a705901…,
  addendum bdd4d356…). Check `experiments/20261027-batch-12-first-pass/` (freeze be979e6f…, v11 = П12 + v10 = П11,
  git_head a95aa1c), run once 13:01 UTC 27.10; never re-run. Not yet in the dev regression. Rework rescore with the
  evaluator fix (owner 27.10.2026): `experiments/20261027-batch-12-rescore-ordinal-single/` (summary 75bf36d7…).
  In the dev regression since step 13 (`20261027-dev-regression-133-v11` and `…-step13-*`); JSON step-13 runs are
  `s13-*` labels inside `20261026-json-all-proj6/` and `20261027-json-v2-all-proj6/`.
- Scan batch 14 (28.10.2026): `m1/m1-04a/documents/pool/batch-14/selection.json` (681988a7…, profile `batch-14`,
  seed 20261103, `--from 2011-01-01 --to 2019-12-31`, code 4cc42dc). SanPiN list `batch-14/sanpin/selection.json`
  (5aee8725…; 567 acts of the Chief State Sanitary Doctor, 48 SanPiN/SP approvals: 26 of 2014-2019, 22 of 2020+,
  5 already used, 2 over 200 pages). 120 feed days, 0 failed; IPS tree filter: 55 acts checked, 23 rejected with a
  tree (decrees 14, resolutions 8, law 1), 4-5 checked reserves per category. Selected: 2 SP/SanPiN 2015, SP 2020,
  SP 2026 (93 p.), law 24-FZ/2013 (3 p., soft fallback), decree 225/2016, resolutions 469/2017 and 1250/2018,
  government order 774-r/2017, orders 1412/2015 and 134/2016; 6 long acts.
  Acquired 11/11 `new` then `unchanged` (code 494c5c2 lists batch 14 in the catalog). OCR
  `experiments/20261028-batch-14-ocr/` (summary.json, replays match): 10 acts complete; sanpin-20-2015 (SP 3.1.3263-15)
  failed on p. 24 of 24 (two journal forms with vertical column headings: `length` after the rotation retry,
  deterministic) -> `failures/0001201507240005-ocr-run-01.json`, refill 01 (4d55051d…, from the checked no-tree
  reserve) -> sanpin-124-2017 (SanPiN 2.6.1.3488-17, `…-ocr-refill-01`, complete). The batch index was first
  built before the refill: that 11-row file is kept as `batch-14/index.pre-refill-01.json`, `index.json` has 12
  rows like batch 13. Build the catalog after refills. `-ReplayOnly` skips acts whose `run-01-replay` exists, so its
  `summary.raw.replay-*.json` files here are empty; summaries use `--replay-raw summary.raw.json`. 11 measured acts,
  292 pages, 2658 regions; sanpin-20-2026 93 p. / 851 regions / 33 tables.
  Annotation input `experiments/20261028-batch-14-annotation-input/` (2293 regions; sanpin-20-2026 in 2 parts,
  pages 1-34 / 35-93, 40 context rows). 7 Codex jobs `.superpowers/sdd/2026-10-28-m1-04a-pool-batch-14/` (batch-13
  template with batch-14 paths, no SanPiN hints); b14-07 first ended «model at capacity» (log
  `b14-07.attempt1-capacity.log`), re-run complete. Gold 2293 regions, 74 `+`, 0 alternatives, seam 34.11
  `S/VI/73/23` | 35.1 `S/VI/73/24`; frozen `experiments/20261028-batch-14-gold-freeze/` (62271520…, addendum
  f6d4a0b6…). Check `experiments/20261028-batch-14-first-pass/` (freeze 1735da04…, v12 = П13 + v11 = П12, git_head
  ef87216, `ordinal_single_annex` on), run once 28.10; never re-run. 2289/2293 (v11 2287), summary cc3a2eb0…,
  error classes v12 8715c086… / v11 d375154b…, sample-30 702872b5… (seed 20261103, 30/30). Pass the 11 slugs
  explicitly.

- Scan batch 23 (30.10.2026, the check of П23 = v23): profile `batch-23` (seed 20261123, `--from 2020-01-01`), 12 acts;
  OCR `experiments/20261030-batch-23-ocr/`: prikaz-minpromyshlennosti-463-2020 failed on pp. 30, 33 (`length`) ->
  failure record, refill 01 (a1400e02…) -> prikaz-minvnutrennikh-677-2020 (`…-ocr-refill-01`, 73 p.);
  `index.pre-refill-01.json` kept. 5 Codex jobs `.superpowers/sdd/2026-10-30-m1-04a-pool-batch-23/`; gold 2497 regions
  frozen `…-batch-23-gold-freeze/` (427b9535…); check `…-batch-23-first-pass/` (49223697…, summary c2ee2852…), run once:
  П23 2450/2497, П22 2450.
- Step 24 development (31.10.2026): batch 23 is now development; frozen inputs/gold/П23 and first-pass outputs stay
  intact. `experiments/20261031-dev-regression-237-v23/` reproduces 51600/51704 (batch 23 2450/2497);
  `…-step24-a/` retains the failed broad bare-number attempt; final `…-step24-c/` scores 51624/51704 (batch 23 2474/2497,
  99.08%, strict equal, cross_scope_v2 0 there), all previous 225 error lists unchanged. Official-tree outputs
  `20261026-json-all-proj6/step24-c-results.json` and `20261027-json-v2-all-proj6/step24-c-results.json` equal v23
  per document. Owner clarified EACH act >99%: continuation `…-step24-f/` scores 51640/51704 (batch 23 2490/2497,
  99.72%; MVD 915/921, RP-1301 24/24; all 12 >99% strict/no_section). Previous 225 error lists exact; official-tree
  `step24-f-results.json` equal v23 per document. `acceptance.json` pins per-document counts, prototype and checks.
  No new scan batch, prototype freeze or gold derivation.
- Scan batch 22 (30.10.2026, the check of П22 = v22): profile `batch-22` (seed 20261122, `--from 2020-01-01 --to
  2026-10-29`, `tree_allowed` for resolutions; first run without it: `b22-select.attempt1.log`), 12 acts; OCR
  `experiments/20261030-batch-22-ocr/` (first start failed: Docker Desktop was not running, log
  `b22-ocr.attempt1-no-docker.log`): prikaz-minkultury-1928-2025 (189 p.) timed out on p. 19 -> failure record,
  refill 01 (71e76a9d…) -> prikaz-fsin-447-2023 (`…-ocr-refill-01`); `index.pre-refill-01.json` kept. 5 Codex jobs
  `.superpowers/sdd/2026-10-30-m1-04a-pool-batch-22/`; gold 2019 regions frozen `…-batch-22-gold-freeze/`
  (d9d55a46…); check `…-batch-22-first-pass/` (cd7575b3…, summary 78d60150…), run once: П22 1893/2019, П21 1893.
  Scripts with dated paths need 20261030 (scratchpad `gcheck30.py`, `gfreeze30.py`, `gpass22.sh`).
- Scan batch 21 (29.10.2026, the check of П21 = v21): profile `batch-21` (seed 20261121, `--min-days 120`; the first
  run with 2 laws left `quotas not filled`, log `b21-select.attempt1.log`), 10 acts without an IPS tree; acquired 10/10
  `new` then `unchanged`; OCR `experiments/20261029-batch-21-ocr/` complete, replays equal; 6 Codex jobs
  `.superpowers/sdd/2026-10-29-m1-04a-pool-batch-21/` (batch-16 template + the 29.10 decisions); gold 1834 regions,
  frozen `…-batch-21-gold-freeze/` (9bf08be2…); check `…-batch-21-first-pass/` (fbc12889…, summary 8f71bcd9…), run
  once: П21 1721/1834, П20 1711.
- Scan batch 20 (29.10.2026, the check of П20 = v20, owner «один документ на 469 страниц»): sanpin-2-2021 = SanPiN
  1.2.3685-21, OCR `experiments/20261029-batch-20-ocr/` (42edfef8…, 469 p., 2243 regions, 582 tables); 1771 scored
  (468 noise); 5 Codex jobs `.superpowers/sdd/2026-10-29-m1-04a-pool-batch-20/` by page range, stitched; gold freeze
  1296d528… (addendum 10b1bf97…); check `…-batch-20-first-pass/` (fec6db9e…, summary 66b7b6c0…): 1051/1771, П17 1059;
  both in `alarms`. Note: dated 20261029 folders (scripts that assume 20261028 need the date).
- Scan batches 17-19 (28.10.2026, the checks of П17 = v17, owner go-ahead «30 SanPiN at once»): profiles
  `batch-17..19` (SanPiN only, 6+4 / 5+2 / 6+1, seeds 20261117-19, `--min-days 0`); the frozen SanPiN list of
  batch 14 is now exhausted (left: 2 acts over 200 p. and sanpin-6-2025). A batch's `index.json` must exist before
  the next batch is selected (build the catalog after acquiring). OCR `experiments/20261028-batch-17-ocr/`
  (342cf9cf…): sanpin-6-2025 (144 p.) failed on p. 106 (native `length`), no reserve, batch 17 = 9 acts; the
  partial first annotation input is kept as `…-batch-17-annotation-input.attempt-01-failed-ocr`. Batches 18
  (658daac0…) and 19 (7231ee26…) complete. Gold: 6 / 4 / 5 Codex jobs (`.superpowers/sdd/2026-10-28-m1-04a-pool-
  batch-17..19/`, batch-16 template), sanpin-81-2016 in 2 parts (1-28 / 29-72); freezes f535afc3… / 3ca56089… /
  41e882a9… (addenda 7091bcce… / 4bb93fb5… / b0ecec3f…). Checks (v17 + v13, run once): 2466/2469, 1386/1395,
  1346/2256 (sanpin-81-2016 14/914: the approval caption «Приложение ⏎ Утверждены …» in one region opens no `S`).
- Scan batch 16 (28.10.2026, the check of П16 = v13): `m1/m1-04a/documents/pool/batch-16/selection.json`
  (186797b8…, profile `batch-16` = batch-15 excluding batches 1-15, seed 20261105, `--from 2011-01-01 --to
  2019-12-31`, code 961ab2e, SanPiN list reused from batch 14). 120 feed days; IPS tree filter: 32 acts checked, 2
  decrees with a tree rejected. Selected: SanPiN 2.6.1.3288-15, SP 2.3.4.3258-15, SanPiN 2.1.7.3550-19, SP
  2.5.3650-20 (101 p.), SP 3.1.3271-21, SP 2.5.4286-26 (113 p.), law 108-FZ/2015 (3 p., soft fallback), decree
  843/2013 (awards), resolution 705/2018, government order 2240-r/2014 (173 p., title from IPS), orders
  Mintrans 100/2015 (estimate norms) and 603/2015 (Rospatent regulation); 7 long acts.
  Acquired 12/12 `new` then `unchanged`. OCR `experiments/20261028-batch-16-ocr/` (summary.json 9cb70166…): 12/12
  complete, replays match, no refill, index.json 295d628d… built once after OCR (catalog also wrote batch-14/15
  `status.json`). 619 pages, 5566 regions, 444 tables (172 in rp-2240-2014), one rotation retry (sanpin-31-2015
  p. 55); 2206 s of OCR (3.56 s/page).
  Annotation input `experiments/20261028-batch-16-annotation-input/` (4752 regions; sanpin-16-2026 pages 1-34 /
  35-113 and sanpin-30-2020 pages 1-36 / 37-101, 40 context rows). 10 Codex jobs
  `.superpowers/sdd/2026-10-28-m1-04a-pool-batch-16/` (batch-15 template with batch-16 paths plus the 28.10
  footnote decision of convention v2 §6.1, no SanPiN hints), all complete first time. Gold 4752 regions, 176 `+`, 0
  alternatives, seams 34.19 `S/IV/22/23` | 35.1 `S/IV/22/24` and 36.17 `S/IV/4.5/4.5.2` | 37.1 `S/IV/4.5/4.5.3`;
  executed commands read only allowed files. Frozen `experiments/20261028-batch-16-gold-freeze/` (5dd0ae39...,
  addendum 8e4c4437...). Check `experiments/20261028-batch-16-first-pass/` (freeze dc2831da..., v13 = П16 + v12 = П13,
  git_head f531431), run once 28.10; never re-run. П16 4723/4752 (99.39%), П13 4736; summary 0fdef057..., classes
  v13 e452e7e1... / v12 3c9433e6..., sample-30 da098639... (seed 20261105, 30/30).
  Owner 28.10.2026: a paragraph after the last dotted subpoint belongs to it -> batch-15 maps
  `gold/<slug>/agent-<slug>.dotted-map.json` (sanpin-61-2015 11.13, sanpin-69-2016 11.6, pinned to `gold-footnotes`)
  and `agent-<slug>.gold-dotted.{txt,sha256}` for all 12 batch-15 acts (10 exact copies); batch 16 gold unchanged.

- Scan batch 15 (28.10.2026): `m1/m1-04a/documents/pool/batch-15/selection.json` (d01b7b4a…, profile `batch-15`,
  seed 20261104, `--from 2011-01-01 --to 2019-12-31`, code 8a290f3, SanPiN list reused from batch 14). Attempt 1
  (code 58a3aea, 43ec9076…) is kept as `selection.attempt-01.*`: it drew law 252-FZ «О внесении дополнения …» and
  its feed-only title rule rejected 524 of 617 government orders (empty feed `name`); attempt 2 reuses its feed
  cache. 120 feed days; IPS tree filter: 50 acts checked, 18 with a tree (laws 8, decrees 6, resolutions 3, order 1),
  1 government order amending by its IPS title. Selected: SP 2.6.1.3247-15, SP 2.1.2.3358-16, SP 2.1.2.3304-15,
  SP 2.4.2.4283-26 (56 p.), SP 3.1/2.4.3598-20, SP 2.2.1.4111-25, law 16-FZ/2014 (24 p.), decree 258/2015 (awards),
  resolution 737/2019, government order 1838-r/2013 (title from IPS `description`), orders 220n/2017 and 728/2015;
  5 long acts, no soft fallbacks.
  Acquired 12/12 `new` then `unchanged` (code 2e1a2c4 lists batch 15 in the catalog). OCR
  `experiments/20261028-batch-15-ocr/` (summary.json 00763590…): 12/12 complete, replays match, no refill, so the
  batch `index.json` (9d7e70b6…, 12 rows) was built once after OCR. 258 pages, 2812 regions, 151 tables (138 in
  prikaz-mintruda-220-2017, 1 grid unresolved there), no rotation retries; 952 s of OCR (3.7 s/page). Do not start
  dotsmocr before `run_m1_04a_ocr.ps1`: the runner starts it and refuses a busy GPU (first attempt, log kept in
  the session scratchpad as gpu-busy, wrote nothing).
  Annotation input `experiments/20261028-batch-15-annotation-input/` (2513 regions; sanpin-19-2026 in 2 parts,
  pages 1-30 / 31-56, 40 context rows). 7 Codex jobs `.superpowers/sdd/2026-10-28-m1-04a-pool-batch-15/` (batch-14
  template with batch-15 paths, no SanPiN hints), all complete first time. Gold 2513 regions, 118 `+`, 14
  alternatives (10 endnotes in prikaz-mintruda-220-2017, 4 in sanpin-19-2026 17.4-17.7), seam 30.11 `S/III/24/3` |
  31.1 `S/III/24/3 +`; frozen `experiments/20261028-batch-15-gold-freeze/` (44dd8339…, addendum 0ddd2044…).
  First pass `experiments/20261028-batch-15-first-pass/` (freeze b63f675c…, git_head ea21bc3; summary f986379e…,
  classes v12 042d2a55…, v11 9c3ab914…, sample-30 2bbccd8b… seed 20261104, 29/30): П13 2442/2513, П12 2440. The
  38 source-footnote regions of sanpin-69-2016/sanpin-61-2015 had the root `S` in this gold. Owner 28.10.2026: a
  footnote belongs to the point with its mark -> maps `gold/<slug>/agent-<slug>.footnotes-map.json` (19 + 19 regions,
  each with its mark region) and `agent-<slug>.gold-footnotes.{txt,sha256}` for all 12 acts (10 exact copies);
  rescore `experiments/20261028-batch-15-rescore-footnotes/` (summary 73416656…, classes v12 a44a77c4…, v11
  65147ad5…), rework only: П13 2479/2513, П12 2477.

- Scan batch 13 (27.10.2026): `m1/m1-04a/documents/pool/batch-13/selection.json` (profile `batch-13`, seed 20261102, code
  6e90f50, sha 30d034fc…); acquired 11/11 `new` then `unchanged`. OCR `experiments/20261027-batch-13-ocr/` was stopped
  on the owner's request (GPU memory 15939/16303 MiB): 9 acts complete, raw summary reconstructed
  (`summary.raw.reconstructed.json`, no per-act seconds), replays in `summary.raw.replay-*.json`; favt-150 and ukaz-732
  kept as `ocr/<slug>/run-01-failed-attempt1/` and re-run in `…-ocr-r2` (ukaz complete; favt-150 all 67 pages OCRed but
  rejected: nested OCR table on p. 63) -> `failures/0001202306290007-ocr-run-01.json`, refill 01 (1212b151…) ->
  prikaz-fadm-313-2016 (`…-ocr-refill-01`). Pool PDF copies exist only after `build_m1_04a_catalog.py` lists the
  batch: build the catalog before annotation (job b13-04 stopped without them; log kept). Gold 7 Codex jobs (fsvng-63
  in 2 parts under `gold/prikaz-fsvng-63-2019/chunks/`), 2430 regions, frozen
  `experiments/20261027-batch-13-gold-freeze/` (0587b3c8…, addendum 23b3e2f9…). Check
  `experiments/20261027-batch-13-first-pass/` (freeze 7ccd89d7…, v12 = П13 + v11 = П12, git_head 34358b4,
  `ordinal_single_annex` on), run once 18:28 UTC 27.10; never re-run. Pass the 11 measured slugs explicitly.

- IPS tree coverage (28.10.2026): `m1/m1-04a/experiments/20261028-ips-tree-coverage/` — `frame/<type>.json` (full
  search lists of 32 types, 252,381 acts), `sample.json` (207dbc7a…, seed 20261028, 99 strata, 4190 acts),
  `screened/<nd>.json` (one record per act; 149 from the 25-26.10 corpus screens, `source` says which),
  `estimate.json` (84e04321…), `coverage.md` (64151e7a…), `requests.jsonl` (9401, 0 errors); about 151 MB, local only.
  Write-once: `estimate` refuses to overwrite; a rerun goes to a new dated folder.

- Scan batch 11 (27.10.2026): `m1/m1-04a/documents/pool/batch-11/selection.json` (profile `batch-11`, seed 20261031, code
  b537d37); ukaz-1615-2011 is ZIP-only on publication.pravo.gov.ru -> `failures/0001201112140012-*.json`, refill 01
  (bd772553…) -> ukaz-137-2025. OCR `experiments/20261027-batch-11-ocr/summary.json` (11/11, replays equal). Gold 7
  Codex jobs (FNS-93 in 2 parts under `gold/prikaz-fns-93-2015/chunks/`), 1998 regions, frozen
  `experiments/20261027-batch-11-gold-freeze/` (0c649860…, addendum 5542841e…). Check
  `experiments/20261027-batch-11-first-pass/` (freeze 5af0ed44…, v10 = П11 + v9 = П10, git_head 8deadaa), run once
  08:34 UTC 27.10; never re-run. In the dev regression since step 12 (`BATCH_11` on `gold-quoted`); step-12 runs
  `experiments/20261027-dev-regression-122-v10` (baseline) and `…-step12-b1`, `-b2`, `-b3`, `-b3-r2`, `-b4`; JSON
  `s12-b4` in `20261026-json-all-proj6/` and `20261027-json-v2-all-proj6/`.
  Quoted-document decision 27.10.2026: `gold/rp-2417-2015/agent-rp-2417-2015.quoted-map.json`, `agent-<slug>.gold-quoted.{txt,sha256}`
  for all 11 acts; rescore `experiments/20261027-batch-11-rescore-quoted/` (summary ec091fcd…), rework only.

- Check-pool batch 10 (26.10.2026): `m1/m1-04a/documents/pool/batch-10/selection.json` (13b0d4f6…, profile `batch-10`,
  seed 20261030, code ed57f20); minkultury-2782 OCR timed out -> `failures/0001201512010017-ocr-run-01.json`, refill 01
  (ac7be193…) -> prikaz-fas-690-2022 (OCR `experiments/20261026-batch-10-ocr-refill-01/`). OCR
  `experiments/20261026-batch-10-ocr/summary.json`. Gold 7 Codex jobs (pp-728 in 3 parts), 2454 regions, frozen
  `experiments/20261026-batch-10-gold-freeze/` (b3c431be…, addendum f38dd21d…). First pass
  `experiments/20261026-batch-10-first-pass/` (freeze 1564edcc…, v9 + v8, git_head d33708f), run once 19:00 UTC 26.10;
  never re-run. In the dev regression since cycle 11 (`BATCH_10`, 11 acts without minkultury-2782).

- JSON corpus v2 (26.10.2026): `m1/m1-04a/json-corpus/20261026-v2/` (`--profile v2`, 146 acts, selection f075720e…, split
  80370800…: 102 dev / 44 holdout). Holdout measured once: `experiments/20261026-json-v2-holdout-proj6/` (freeze 3747fb31…,
  `run-receipt.json` first, `v9`/`v8` results equal, 12152/12219); never re-run; the holdout is now development.

  seed 20261029, code d713d75, `scripts_dirty` false, no soft fallbacks); acquired 11/11 `new` then `unchanged`. OCR
  `ocr/<slug>/run-01` (rotation retry config, 304 pages, 2846 regions, 220 tables, 1 `grid: unresolved` in
  prikaz-mintruda-687-2018 p. 23, 0 rotations, replays equal), summary `experiments/20261026-batch-09-ocr/summary.json`
  (2a3f5d84…). Gold: 6 blind Codex jobs (memory off), 2324 regions, 107 `+`, no alternatives, frozen in
  `experiments/20261026-batch-09-gold-freeze/` (freeze 59df7e2e…, addendum 41b9b971… with the `files` map). First pass
  `experiments/20261026-batch-09-first-pass/` (freeze d996d5a1…, v8 + v7, git_head 376041e), run once 10:00 UTC; never
  re-run. Cycle 10 A3 baseline of frozen v8 on 100 documents: `experiments/20261026-dev-regression-100-v8/` (summary
  45ecd43b…): 18930/19241 no_section, `cross_scope_v2` 42 (all orders: batch 9 35, FAS 7); the 89 earlier rows and
  errors equal `…-dev-regression-v8`. Cycle-10 rules gate with `--baseline` it and `--frozen-families`;
  `…-cycle10-gate-check` (working code = v8) exits 0 with no changes. JSON corpus baseline stays
  `20261026-json-all-proj6/v8-results.json` (37762/38337).

- Check-pool batch 8 (25.10.2026): `m1/m1-04a/documents/pool/batch-08/selection.json` (14b7020a…, profile `batch-08`,
  seed 20261028, code af20afa, `scripts_dirty` false, soft fallbacks 123-FZ issuer-day and 517-FZ 3 pages); acquired
  11/11 `new` then `unchanged`. OCR `ocr/<slug>/run-01` (rotation retry config, 243 pages, 2003 regions, 168 tables,
  11 `grid: unresolved` all in prikaz-mintruda-141-2023, 0 rotations, replays equal), summary
  `experiments/20261025-batch-08-ocr/summary.json` (f4a1f713…). Two launch attempts failed before OCR (Docker Desktop
  not running; script not started from the repo root). Gold: 6 blind Codex jobs (memory off), 1710 regions, 62 `+`, 1
  alternative, frozen in `experiments/20261025-batch-08-gold-freeze/` (freeze d2668fa1…; addendum f1f511c5…, which
  supersedes `freeze-addendum.attempt1-no-files.json` written before any run). First pass
  `experiments/20261025-batch-08-first-pass/` (freeze 6dc51ce9…, v7 + v6.1, git_head 38a6843), run once 16:06 UTC;
  never re-run. Ukaz 1428/2012 appoints judges: names stay out of docs (sample-30 stays local).
  §6.1 forms decision: `gold/<slug>/agent-<slug>.gold-forms.{txt,sha256}` for all 11 acts (only FAS changed, map
  `agent-prikaz-fas-553-2015.forms-map.json` 745f4ce4…); rescore `experiments/20261025-batch-08-rescore-forms/`
  (summary e565cf7a…); development only.

- Check-pool batch 7 first pass: `m1/m1-04a/experiments/20261024-batch-07-first-pass/` (`freeze.json` /3 4378b883…,
  v5 + v4 frozen copies, `git_head` d4fac12, both equivalences). Run once (24.10 05:33 UTC); never re-run.
  `error-classes-{v5,v4}.json` with `cross_scope_v2`; `sample-30.json` (seed 20261027) has one ukaz-410 row with a
  judge's name that stays out of docs. `pool/batch-07/status.json` records measured -> development.

- Check-pool batch 6 first pass: `m1/m1-04a/experiments/20261024-batch-06-first-pass/` (`freeze.json` /3 fe1d356b…,
  v4 + v3-1 frozen copies, `git_head` 78f4ac0, both equivalences). Run once (23.10 19:00 UTC); never re-run.
  `error-classes-{v4,v3-1}.json` with `cross_scope_v2`; `sample-30.json` (seed 20261026, no ukaz-1711 rows) stays
  local. `pool/batch-06/status.json` records measured -> development.

- Check-pool batch 5 first pass: `m1/m1-04a/experiments/20261023-batch-05-first-pass/` (`freeze.json` /3 3da171ed…,
  v3-1 + v2 frozen copies, `git_head` b0aa2f7, both batch-5 equivalences). Run once (12:20 UTC); never re-run.
  `error-classes-{v3-1,v2}.json` with `cross_scope_v2`; `sample-30.json` (seed 20261025) has ukaz-669 name rows that
  stay out of docs. `pool/batch-05/status.json` records measured -> development.

- Check-pool batch 4 first pass: `m1/m1-04a/experiments/20261023-batch-04-first-pass/` (`freeze.json` /3 f5dd824a…,
  v2 + v1, `git_head` 51e6648, `single_annex_equivalence` true, gold addendum hashed). Run once (05:24 UTC); never
  re-run. `error-classes-{v2,v1}.json` carry `cross_scope_v2`; `sample-30.json` has three ukaz-481 name rows that
  stay out of docs (the sample doc redacts them). `pool/batch-04/status.json` records measured -> development.
  Cycle 4: `20261023-batch-04-rescore-cycle4/` rescores the saved outputs with `--attached-ordinal` (+ single annex;
  `summary.json` ab0abb2d…, `error-classes-{v2,v1,current}.json`); development only, never replaces the first pass.

- Check-pool batch 3 first pass: `m1/m1-04a/experiments/20261022-batch-03-first-pass/`
  (`freeze.json` /3, v1 + `code-final`, `git_head` 17d4de9; it hashes the gold
  freeze `20261022-batch-03-gold-freeze/freeze.json` but not its
  `freeze-addendum.json`, which was verified separately before the run). Run once;
  never re-run. `sample-30.json` has no ukaz-980 rows; ukaz-980 personal names
  stay out of docs. `pool/batch-03/status.json` records measured -> development.

- Check-pool batch 2 first pass: `m1/m1-04a/experiments/20261022-batch-02-first-pass/`
  (`freeze.json` schema /3 with v1 and `code-final` prototype hashes, written
  before `run`; outputs `prototype-v1/`, `prototype-code-final/`, `current/`;
  `error-classes-{v1,code-final}.json`, `sample-30.json` with ukaz-919 personal
  names that must not be copied into docs). Gold frozen in
  `20261022-batch-02-gold-freeze/`. `pool/batch-02/status.json` records
  measured -> development.
- Convention v2 (22.10.2026): `gold/<slug>/agent-<slug>.gold-v2.txt` is derived
  write-once from the frozen v1 gold by `docs/assets/derive_m1_04a_gold_v2.py`
  with the hand-written annex map `agent-<slug>.v2-map.json` (pinned to the v1
  gold hash) and receipt `.gold-v2.sha256`; only batch 2 has them (pp-931 and
  favt changed, batch 1 would not change). `experiments/20261022-batch-02-rescore-v2/`
  rescores the saved first-pass outputs against it (no system re-run); development only.

- Prototype regressions: `m1/m1-04a/experiments/20261021-dev-regression-<tag>/`
  (baseline, a2, a3 to a3-r4, a4, a4-r2, v1; `summary.json` + `errors.json`, one
  new folder per run; failed attempts a3 and a3-r3 are kept). The `-v1` run is the
  last on the frozen prototype. `20261021-prototype-v1-freeze/` holds the
  prototype copy, `code-v1.sha256` and `freeze.json`; write-once. `code-final`
  (sha256 a7b81b59...) stays for comparison.
  Cycle 3: `20261022-dev-regression-cycle3-<tag>/` (baseline = v1, b2, b2-r2, b3, b4 failed and kept, b4-r2,
  b4-r3), final `20261022-dev-regression-v2/` (+ `baseline-comparison.json`), and the write-once
  `20261022-prototype-v2-freeze/` (prototype copy, `code-v2.sha256` with sha256 and git blob ids, `freeze.json`).
  Cycle 4: `20261023-dev-regression-<tag>/` over 45 documents; `-cycle4-baseline` = frozen v2 (`summary.json`
  5a273ed6…, `baseline-comparison.json` against `20261022-dev-regression-v2`: no drops, batch 4 not in baseline).
  Cycle 5: over 56 documents; `20261023-dev-regression-cycle5-baseline/` = frozen v3.1 (`summary.json` a290a161…,
  no comparison file; old 45 rows and errors checked equal to `20261023-dev-regression-v3-1`). Track B runs
  `-cycle5-b<n>[-r<k>]` with `--baseline` it; failed runs are kept.
  Cycle 6: over 67 documents; `20261024-dev-regression-cycle6-baseline/` = frozen v4 (`summary.json` b22d8af9…,
  no comparison file; old 56 rows and errors equal to `20261023-dev-regression-v4`). Track B runs `-cycle6-b<n>[-r<k>]`.
  Cycle 7: over 78 documents; `20261024-dev-regression-cycle7-baseline/` = frozen v5 (`summary.json` 20f70825…,
  no comparison file; old 67 rows and errors equal to `20261024-dev-regression-v5`). Track B runs `-cycle7-b<n>[-r<k>]`.
  `20261024-batch-07-classes-cycle7/error-classes-{v5,v4}.json`: batch-7 first-pass classes re-run after the
  cycle-7 B2 label (`POINT_TAIL`); the first-pass folder's own class files stay as written.

- `m1/experiments/m1-04a-20261017-logical-v1/` retains the logical-paragraph
  experiment: copied extractions, hand-made owner gold with freeze hashes written
  before each evaluated run, all code snapshots, attempt/holdout/final runs and
  current/Dedoc owner exports. `comparisons-04` keeps the adapter namespace bug;
  `eval-05/summary.json` is the corrected result. Empty `runs/attempt-01/02`
  are crash leftovers (deletion is not permitted), not results.

- `m1/experiments/m1-04a-20261017-two-pdf-v1/` retains two additional official
  PDFs, permissions, metadata and new/unchanged acquisition on frozen f98b637.
  All 26 pages have fresh dots.mocr, exact saved replay and two identical actual
  compiler builds. Keep the pre-output selected image controls and No.416's
  false approval/cascaded unresolved tail; no document-specific fixes were made.
  Separate 782 preservation checks from 47/50 selected semantic checks and
  direct Dedoc/Docling API probes. No.416 was previously known on the native
  route; original four reserved bodies and legal admission remain separate.

- `m1/experiments/m1-04a-20261017-scope-v1/` retains the complete 12-document
  development scope inventory before reusable boundary changes. Keep reason
  counts distinct from reviewed severity, cascaded blocks from root causes and
  physical-heading candidates from confirmed semantic boundaries. Native inputs,
  prior failures, reserved bodies and closed gold remain unchanged.
  `reviewed/` and `compiler-reviewed/` are the final version-7 direct/permission-
  checked replays. Keep `after-*`, the first compiler harness date failure and
  interrupted pre-review official replay as superseded attempts. Typed-reference
  conflicts exposed by the final rule must remain visible, not treated as repaired
  by their previous numeric-only match or a smaller unresolved counter.

- `m1/experiments/m1-04a-20261017-footnotes-v1/` retains the initial footnote
  heuristic; `footnotes-v2/` retains the reviewed, narrower Text rule and actual
  Dedoc replay. Keep the joined logical sidecars, source hashes, raw native
  files, code snapshots and before/after owner checks. A corrected continuation
  owner is a bounded development fix, not general footnote/annex qualification.

- `m1/experiments/m1-04a-20261017-json-v1/` freezes the unchanged native JSON
  and source-bound table topology for all 12 development PDFs/205 pages.
  Keep Dedoc/Docling raw and prefix-only attempts, code/runtime freezes and
  source/output maps. Sidecar retention is distinct from engine output fidelity;
  no production parser or legal/G13 acceptance is changed by these diagnostics.

- M1-04A `development-ocr/` retains new complete SP3678 (79-page) and
  Resolution1156 (23-page) dots.mocr evidence. `shared-verified-v5/` binds the
  actual `ocr-layout-structure/5` code and three full compiler cohorts: baseline
  103 pages plus these 102 pages, two identical outputs and unchanged replay.
  Preserve earlier shared-v1/v2/v3/v4/v5 attempts separately. Both new acts and
  the baseline still have unresolved structure; four reserved acts are not
  qualified or consumed for rule design. None of these artifacts admits an edition.

- `m1/experiments/m1-04a-20261017-v1/` retains the 103-page legacy baseline,
  isolated Dedoc trials and six additional official acquisitions (222 pages by
  source metadata). Split hash `272ad4033e1b3d8178c3ddc43a62fc380da63b13e3160f6a6df25ab2cb6fda46`
  predates PDF bodies: SP3678/Resolution1156 are development; SanPiN3590,
  SP3648 and Resolutions2314/564 are reserved. Keep the recorded development
  search exposure, original metadata/receipts, exact permission hashes and
  `new`/`unchanged` evidence. Acquisition is not OCR/structure qualification.

- `m1/pilot_runs/m1-04-seal-recovery-20261016-v1/` retains the actual owner
  scope record and source-bound quality policy, the new 10-PDF/103-page run,
  deterministic saved replay, both target-date compile repeats and passing scoped
  qualification. Keep before/before-review client versions. The full run used
  the pre-review immutable streaming/retry snapshot; a later persistence-only
  fix was verified on authored retry errors and final real three-seal/date
  checks in OCR-Lab/results/legal-rag-seal-recovery-final/20261016-v1.
  Owner scope accepts inaccurate round-seal text and excludes only the original
  page-75 table's quality. All pages, errors, attempts and historical failures
  remain stored. This is diagnostic M1-04 acceptance, not legal admission.

- `m1/experiments/m1-04-region-probe-20261016-v1/` retains the owner-approved
  30-request diagnostic on two seals, the original date and page-75 row bands.
  Preserve the pre-inference plan/91-cell controls, post-screen amendments,
  all baseline/analysis versions, outcome-final, scorer selfcheck and manifest.
  `comparison.html` embeds eight inert image/response pairs. Native requests
  are in OCR-Lab/results/legal-rag-region-probe/20261016-v1, with separate
  prompt-stack probes. This changes no production model/config/extraction.
  Loop termination is not correct seal transcription; all 13 conditional signs
  still fail despite recovery of six ordinary minus cells. No gate waiver.

- `m1/pilot_runs/m1-04-20261016-v1/` retains preliminary failed pass-1 and two
  final complete dots.mocr passes on all 10 permitted SanPiN PDFs / 103 pages.
  Preserve native evidence, images, extraction indexes, runtime freeze, model
  hashes and offline/memory observations. `qualification-final/report.json`
  records open acceptance: output drift, 0/13 critical table signs and incomplete
  Picture OCR. No source text was repaired and no legal edition was admitted.
  `human-transcription-review/human-review.json` records the owner's actual
  page-1 confirmation; the old reference remains human_review=false. No duration
  was supplied. The report-only change after this answer is explicitly recorded
  in `final-evidence-summary.json`; the original freeze/report remain immutable.
  Both target-date diagnostic compilations, 19 retained v2 replays and four
  byte-identical v1 manifests are separate from OCR accuracy qualification.

- `m1/pilot_runs/official-source-import-20261016-v3/` is the source-preserving
  M1-03A closure replay on the three retained cohorts (not fresh heldout acts).
  Preserve attempts v1/v2, code/input freezes, both builds and repeat receipts.
  Raw rows/ranges stay unchanged, including source defects in the older cohort.
  Owner acceptance changes the official-JSON contract; it does not turn earlier
  semantic-parser failures into passing qualification or admit legal editions.

- `m1/pilot_runs/official-json-qualification-20261016-v1/` is the distinct
  pre-body selected `/5` cohort after commit `3b2c6c6`: all six acquired with
  correctly attributed diagnostic-selected-cohort/2 wrappers and bundle/v2.
  `official-json-qualification-20261016-validation-v1/parser-transfer-report.json`
  records 2/6 full-control passes (3/6 technical builds), 14 caught mutations and
  105 unchanged input files. Preserve paragraph-unit, titled-part and subsection
  refusals plus the separate quoted-article control-reader failure. No parser or
  verifier tuning/replacements occurred during qualification; this is not G13
  completion or admission. Postrun diagnoses live under
  `m1/reviews/official-json-qualification-20261016/`.

- `m1/pilot_runs/official-normalization-20261016/` retains `/5` development
  probes and immutable full builds. `full-04/results.json` is the final six-act
  control revalidation (6/6, 43 caught mutations); `full-01` holds the two full
  builds/repeat. Preserve failed verifier attempts 02/03 and their explanations.
  `regressions-02` passes seven retained inputs and four byte-identical v1 drafts.
  HTML-only printed contexts and DOM replay of sidecar claims are distinct;
  hidden source ordinals are not independently legally verified. This cohort
  cannot be reused as fresh qualification after tuning.

Scope: local corpora, raw downloads, fixtures, manifests, and generated databases.

- `m1/pilot_runs/official-json-transfer-20261016-v1/` retains a pre-body selected
  six-act cohort for official-structure/4: all acquired with bundle/v2, final G13
  fail 2/6. Use `parser-transfer-report-reviewed.json` plus per-law payload checks;
  preserve original controls/report, three control-reader failures, four parser
  failures and identical repeats/diagnoses. `diagnostic-wrapper-receipt.json`
  corrects adapter attribution without rewriting immutable metadata. Do not reuse
  this failed cohort as new heldout evidence after tuning rules on its bodies.

- `m1/pilot_runs/independent-structure-audit-20261015-v2/` is the final frozen-code
  seven-input replay for official-structure/4: 3906 source nodes plus two derived
  siblings, preserved raw pointers/text/media, ten witnesses and three injected
  faults. V1 is preliminary because code changed during execution; retain its
  attempt-status record and all earlier audit probes. These are development
  controls, not G13 heldout acts, source corrections or legal admission.

- `m1/experiments/official-structure-20261015-v1/` is the owner-authorized local
  follow-up to the sidecar research. `preflight.json` fixes seven permitted inputs
  and 147 protected hashes; retain attempts 01–05 and their adapter snapshots.
  Final attempt 05 preserves all 3,906 source nodes, text/media and explicit
  numbering, but exposes missing quote/form subtrees. Its `index-v2.html` is
  an offline review aid, not human approval; raw HTML is sandboxed for display.
  Never overwrite old attempts, turn heuristic candidate counts into verified
  error counts, or treat the experimental source bundle as production admission.

- `m1/research/parser-search-20261015-v2/` retains the broader parser search,
  pinned external code/frontend snapshots and official structure sidecars for
  seven existing diagnostic inputs. Keep `official-structure-anchor-checks.json`
  separate from `official-fresh-text-checks.json`: valid anchors do not by
  themselves prove an unchanged edition. All seven text responses matched the
  retained raw assets exactly. This is bounded source research, not a compiler
  input-contract update, legal admission or full semantic qualification.

- `data/` content is ignored by default; only this instruction file is tracked.
- Never commit secrets, licensed aggregator exports, private case files, or large generated indexes.
- Treat raw assets as immutable. Store derived artifacts separately and link them by hash and build metadata.
- M1-02's original inventory/review packet under `m1/inputs/m1-02/` remains
  immutable. The owner's explicit consent is a separate record under
  `m1/reviews/m1-02-owner-consent/`, with allowed exact-asset permissions and
  hash-identical archive-local copies for compiler references. The permitted
  59-FZ manifest under `m1/inputs/m1-02-permitted/` supports only the diagnostic
  control target; it does not establish historical or legal admission.
- The owner-facing M1-02 packet under `m1/reviews/m1-02-review-v1/` contains
  separate bounded research acquisitions, raw evidence, readable derived views,
  page images and a blank human response form. Preserve the original inventory,
  owner consent and source pointers. Store returned findings separately; verify
  their packet hash and scope before applying a human decision. Changed evidence
  needs a new packet version. These readable exports are review aids, not compiler
  inputs, approved reconstructed text or qualified production OCR.
- `m1/reviews/m1-02-review-v2/` is the focused standalone successor to v1.
  Its embedded content and one proposed legal classification are hash-bound;
  rendered PDF pages are review aids linked to the unchanged original hashes.
  Preserve v1, its consent and user responses. A v2 reply concerns only its named
  question; never treat it as approval of unrelated missing evidence or the ten
  unfinished editions. Browser QA answers are synthetic and must not be imported.
- The actual v2 human response received on 12.10.2026 is retained separately as
  `human-review.json`, with its hash/scope validation in
  `human-review-verification.json`. Preserve the reviewer's supplied timestamp
  and rationale. It confirms only `59-ks19p-after-80` at both targets;
  `edition_admission` remains false. Keep original inventory/packets immutable
  and distinguish this received decision from synthetic browser QA or a later
  runtime relation import.
- `m1/inputs/m1-02-completion/` retains the 12 October routing result, separate
  official acquisitions, source research, ten exact-asset diagnostic permission
  records and a hash-bound closure matrix. Permissions record continuing owner
  authorization and actual record-creation time; they are not fresh human legal
  admission decisions. Validate all 463 bindings before using the result. Preserve
  earlier inventories, permissions, packets and the rejected/stale M0 candidates.
  Every matrix row still carries explicit edition-admission blockers and its next
  M1 slice; new acquisition does not approve a `LegalEdition`.
  Six exact `corpus-input/1` diagnostic manifests are under `inputs/`; their
  archive-local permission copies match the row records. Four historical research
  candidates are separate and are not silently registered as approved inputs.
- M1-03 diagnostic native drafts, full replay observations and browser QA remain
  under `m1/pilot_runs/m1-03/`. Preserve successive development outputs; compiler
  artifacts are immutable and a changed report needs a fresh output directory.
  The permitted 59-FZ input and original admission blockers remain read-only.
  Native coordinates refer to `/redtext` scalar characters; these local drafts
  are neither legally admitted editions nor historical reconstruction evidence.
- The Housing Code parser controls are retained under
  `m1/experiments/dedoc-housing-code-20261012-v1/` and
  `m1/experiments/parser-alternatives-housing-code-20261012-v1/`. The latter uses
  the same immutable HTML for isolated Docling, Unstructured and DocSlicer runs;
  installed environments are under `m1/tool-environments/`. Preserve raw outputs
  and read `COMPARISON.md` / `comparison.json` before interpreting counts. Generic
  text blocks or heading trees are not legal article/part/item nodes. DocSlicer's
  browser mode omits two CSS-hidden editorial paragraphs; its static control
  keeps the text but collapses this document to one block. New settings/runs need
  separate outputs; this experiment is not production integration or admission.
- The follow-up chain probe is under
  `m1/experiments/parser-pipeline-housing-code-20261013-v1/`. A fresh Unstructured
  pass feeds separately retained HTML/TXT inputs to pinned Dedoc and DocSlicer.
  Plain TXT restores all Housing Code article boundaries in Dedoc. The best
  experimental branch adds 41 canonical article-number dots only where original
  W9 ranges prove superscript semantics; its ledger and paragraph alignment remain
  separate from raw inputs. Its 243 article/number/section-chapter controls pass;
  nested provisions, legal paragraphs, note scope and other documents remain
  unqualified. Attribute this source-specific adapter to the experiment, not to
  native library features, and retain the weaker plain/HTML branches as evidence.
- The direct simplification probe is under
  `m1/experiments/bs4-dedoc-housing-code-20261013-v1/`. BeautifulSoup alone retains
  source paragraph IDs/W9 ranges and produces the same normalized TXT content
  as the previous best chain, excluding whitespace. Pinned Dedoc passes the
  same 243 article/number/section-chapter controls and retains 996 notes;
  Unstructured adds no measured benefit for this exact HTML. Use dotted article
  numbers as strings with explicit article kind and parent scope; retain the
  source-number components/display ledger. Bare strings are not provision IDs.
  This is not production integration, nested-structure qualification or admission.
- The two-document follow-up benchmark is under
  `m1/experiments/parser-benchmark-html-20261013-v1/`. The unchanged normalizer
  and pinned Dedoc run three sequential passes on Decrees 354/491 and repeat
  the Housing Code. Warm normalization-plus-parse times are about 1.40/0.18/1.56
  seconds, excluding process startup and JSON IO. Text/notes survive, but attached
  rules stay raw text under preceding provisions, and superscript point/subpoint
  numbers remain unqualified. Independent prefix controls are not full AST
  accuracy. TXT flattens 354's table and omits embedded formula images; retain
  their source controls. Do not promote the pipeline from article-only scores.
- The parser-independent preparation replay is under
  `m1/experiments/html-preparation-20261014-v1/`. `verification.json` names four
  passing content-addressed outputs; retain earlier failed prototypes separately.
  Original JSON scalar HTML, prepared HTML, source/output opening anchors and
  validated input are separate files. Preserve source status and permission;
  this replay checks text/notes/indices/tables/images/references and determinism,
  not legal hierarchy, date validity, admission or non-pilot G13 transfer.
- `m1/experiments/html-preparation-parsers-housing-code-20261014-v1/` retains a
  fresh raw/prepared HTML pair for Docling 2.138.0 and pinned Dedoc 2.8. Dedoc's
  native article count stays 228/243 while correct numbers improve 189 to 228.
  Docling retains 419 native super-script fragments; an experimental native
  inline-group fold recovers 243/243 article numbers, without legal heading
  classification. Keep raw native outputs distinct from that evaluation export.
  Preservation/number gains do not qualify hierarchy, full nested provisions or
  G13. M1-03A now supplies the shared legal structure engine; its native transfer evidence is separate from these preparer experiments.
- Small redistributable test fixtures may be committed only after their source, license, and expected hash are documented.
- M0-11 questions, labels and evidence remain local. Only a legally approved
  working export may be used for implementation; the closed set is reserved for
  gate evaluation. Keep exact source hashes and spans with every positive label.
- The tracked M0-11 manifest fixes IDs, split membership and local-file hashes.
  Any content change creates a new draft and requires fresh Legal Reviewer
  approval; a hash match alone is not approval.
- Name annexed rules separately from the approving act: use “Rules approved by
  Government Resolution No. 354/491”, never “Rules No. 354/491”. The number
  belongs to the resolution, not to the rules.
- Audit each M0-11 label for one unambiguous question and one matching failure
  mode. Expected values must be user-facing answers or refusals, not evaluator
  instructions; evidence spans must stop at the last provision needed to
  support the answer.
- Keep the expected article, part, clause, subclause, or annex address in the
  hidden label. Do not disclose it in the user-shaped query merely as a lookup
  hint; retain a document identifier only when it is the subject of an
  applicability/date question or is needed to disambiguate the request.


- M1-03A historical law/code replay is `m1/pilot_runs/m1-03a-shared-v4/`;
  transfer cohorts `/m1-03a-transfer-v1` through `v4` retain frozen code,
  permissions, full source assets, independent controls, failures and repeat
  outputs. `m1-03a-transfer-v4-controls-v2` corrects only the DOM reference's
  dropped br whitespace; it uses the unchanged v4 production code and original
  v4 input/archive bindings. Its `parser-transfer-report.json` is historical
  law/code evidence. Earlier code failures replay successfully under
  `shared-v4/former-failure-replays.json` but are not new qualification acts.
  Housing item `1.1-1` and its inline note have a documented semantic correction;
  preserve both the original and corrected drafts. No edition admission changes.

- `m1/pilot_runs/m1-03a-original-four-status-v1/acceptance.json` records the
  historical corrected acceptance: fail, 2/4. Keep that failure immutable.
  `m1-03a-original-four-v8/acceptance.json` now passes all four complete compiler
  paths with two identical fresh builds, unchanged repeats and 345 protected
  prior/source files unchanged. Resolution354 retains 2 approved texts, 5 annexes,
  a 28-row/64-cell table and 93 images; Resolution491 retains 2 approved texts,
  an annex and 6 images. Source images are not transcribed mathematical content.
- `m1-03a-resolution-transfer-v1` through `v3` retain failed/unqualified shapes:
  quoted entire annex, Cyrillic-lookalike Roman heading, legacy merged paragraphs
  and an independent numeric-footnote reader stopped by an asterisk. Never
  relabel those acts as qualification. Resolution25 was retained but unparsed in
  v1; its first frozen-code full validation in v3 passed. It and Resolution416
  remain held-out validation bodies; no rules were developed from their text.
- Final current native matrix: `m1-03a-resolution-transfer-v5/parser-transfer-report.json`
  passes two laws, two codes and Resolutions25/416 with `legal-structure/7`,
  government profile `/3`. Six final-version full builds repeat identically;
  57 protected source records remain unchanged. Earlier bodies remain held-out
  validation, not newly acquired acts or legal admissions; keep all failures.
- The owner-requested 15 October expansion experiment is
  `m1/pilot_runs/native-expansion-20261015-v1/`. Six acts were preselected and
  downloaded using frozen M0 transport/validators/persistence, with unchanged
  compiler `55b93ca`: 3/6 pass (323-FZ, Merchant Shipping Code81-FZ, Inland Water
  Transport Code24-FZ); 261-FZ, Resolutions410/47 fail structural checks. Each has
  two identical fresh builds and an unchanged repeat; source text/integrity is
  retained even for failed legal structure. Keep the initial full failures and
  independent-reader errors immutable. Unknown annex references and quoted
  amendments require future common rules; do not repair or replace these bodies
  inside the frozen baseline. This probe limits general coverage claims and
  does not cancel or broaden the earlier exact-input acceptance evidence.

- The authorized Documind schema-layer experiment is retained under
  `m1/experiments/documind-housing-code-20261015-v1/`, with the upstream checkout
  pinned at `f258286fc1026c1a6cd2b3f624906453681e7c87`. Preserve complete input,
  paragraph maps, token/memory preflights, every raw LLM response and unsuccessful
  generated schema. Full Housing Code stock requests exceed the declared context
  windows of the tested local Gemma/Qwen models; the smaller complete 59-FZ
  schema controls do not replace that gate or the four original-document checks.
  This profile supplies complete retained text directly to Documind autoschema;
  it does not qualify its PDF/OCR front end, full extraction, production parsing,
  transfer or legal admission. Read the dated Documind report before interpreting
  an HTTP 200 or `finish_reason=stop` as a usable legal schema.
- Pool selection's actual.pravo lookup hit 0 of 311 (batch-1 `selection.json`: `looked_up_in_official_tree` 311, no `official_source: actual`) because of a query defect: the `AttrId 999` filter hides acts such as 22-FZ and No.884; without it both are found (21.10.2026, `m1/m1-04a/experiments/20261021-actual-lookup-diagnosis/`). The fix landed in Task B1 (`select_m1_04a_pool.py`, commit `48f3b7c`: the `AttrId 999` filter was removed) and was used for batch 2 (7 of 9 acts found in actual); batch 1 stays frozen.
- Batch-2 PDF permissions (`m1/m1-04a/documents/pool/batch-02/archive/reviews/*-permission.json`) carry a `rights_basis` that speaks of an automatic gold standard from the official pravo.gov.ru text. That text is stale: batch 2 was acquired without `--with-official` and its gold is agent annotation of OCR text. The files are write-once and are left as is; `acquire_m1_04a_pool.py` now writes `AUTHORIZATION_OCR_GOLD` for batches without `--with-official` and takes target dates from `TARGET_DATES` (batch 1 and 2: 2026-10-21; a new batch: the UTC run date).
- Pool acquisition-failure refill (batch 2): a failed slot is replaced deterministically by `select_m1_04a_pool.py refill` (next same-category candidate in the frozen seeded order, max 3 attempts per slot, write-once `selection-refill-NN.json`; the frozen `selection.json` stays). Known failure classes under the frozen publication validator: empty card `name` (all government orders tried, 4 of 4) and early-2011 `File/Pdf` that is not a PDF by signature, so batch 2 is biased against 2011 and `government_order`.
- Owner decision 22.10.2026: codes may have up to 500 pages (KAS RF 480). `select_m1_04a_pool.py` applies `CODE_PAGES_MAX = 500` to the `code` category only when the code quota is positive and records `code_pages_max` in the selection/refill; other categories keep the profile ceiling.
- Code census 22.10.2026 (`m1/m1-04a/documents/pool/batch-03/codes/census.json`, run 1 in `m1/m1-04a/experiments/20261022-code-census/run-1/`): of 29 reference codes only KAS RF (21-FZ, EO 0001201503090041, 480 pages) has an original publication on the portal; the other 28 (adopted 1994-2006) have no portal entry in actual.pravo and the portal day feed for their first publication day is empty (0 items for every checked day 1994-12-08..2006-12-21). Batch-03 `selection.json` holds only KAS.
