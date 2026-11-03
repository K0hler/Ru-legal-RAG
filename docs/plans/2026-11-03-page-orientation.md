# Automatic page orientation

**Goal:** Use an existing local classifier before dots.mocr; preserve the selected recognizer and original page evidence.

**Design:** RapidOrientation 0.0.11 packages a four-way PaddleClas classifier (Apache-2.0) with its preprocessing and voting. Reuse it unchanged on CPU through the existing ONNX Runtime. A small adapter reads the selected class's minimum crop probability; only scores >=0.85 apply a turn. Install only its pinned wheel in the dots client image; retain Transformers 4.57.0. An explicit `page_orientation` flag enables it in the recovery configuration. Source PNGs remain unchanged; exported boxes map back to them. Native sidecars keep orientation metadata and both coordinate systems. Existing recovery runs on the oriented image.

**Why this module:** PaddleOCR's standalone PP-LCNet is also suitable, but adds Paddle/PaddleX or newer Transformers. RapidOrientation reuses dependencies already in our image. The bounded spike correctly classified two sideways tables and three upright pages at all four rotations (20/20). This is no general accuracy claim.

**Implementation plan:**

- [x] Add failing checks for 0/90/180/270 mappings, metadata corruption, retry composition, and runtime flag forwarding.
- [x] Patch OCR-Lab's client/image/compose and extend the Legal RAG importer; preserve the prior recognition path when the flag is absent and exact saved-result replays.
- [x] Run fresh OCR on both complete affected acts and three previous controls; compare semantics on the two target pages and unchanged upright control content. Check saved import/replay and existing tests.
- [x] Record concise results, update nearest AGENTS.md, and commit the completed integration on main.

**Ruling:** Require confidence >=0.85 after the first 66-page control exposed a false 180 on sparse `pp-1455-2022` p4 (score0.267). The two target pages score0.92–0.93. Keep the ready module's vote; a second CPU forward reads its otherwise discarded scores. This adds milliseconds per page and avoids replacing its classifier/preprocessing/voting.

**Evidence:** `data/m1/m1-04a/experiments/20261103-ocr-fix-orientation-01/` retains the failed control; `...-02/` checks the confidence gate. The classifier can misclassify or abstain on mixed-direction/sparse pages; exact Latin transcription and cross-page table continuation remain separate tasks.
