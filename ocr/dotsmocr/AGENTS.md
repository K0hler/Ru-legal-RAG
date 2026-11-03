# dots.mocr runtime instructions

- The service is under construction for M1-04B. It is not the default provider
  until its qualification is reviewed and accepted by the owner.
- See `../../docs/milestones/m1/04b/M1_04B_RUNTIME_CONTRACT.md` for the current
  OCR profile, evidence contract, dependency inventory and inherited limits.
- Keep the model mount read-only and use only this runtime's input and results.
  Do not install GPU libraries on the host or alter OCR-Lab and old evidence.
- The base image and every added package use explicit versions; the added
  orientation package contains the hash-checked CPU classifier model.
- `pip check` reports the same two metadata issues in both the original and
  new images: RapidOrientation names `opencv-python`, while the working image
  supplies `opencv-python-headless`; the base image's PyGObject lacks pycairo.
  Verify actual imports and orientation inference rather than installing two
  OpenCV distributions into the same Python namespace.
- The first clean build and synthetic GPU inference were verified on 3 November
  2026. The model copy was manually checked against all 16 source-manifest hashes;
  automatic pre-start hash refusal is still Task 4 and must not be assumed.
  A synthetic check is not runtime qualification or owner approval to switch.
- `scripts/new_ocr_pdf.py` and `config/` contain only the dots.mocr client and
  its pinned settings. Preserve streaming Picture/loop recovery, rotation retries,
  confidence-gated page orientation and `dotsmocr-layout/2` native sidecars.
  The host may snapshot these files; a real synthetic PDF result has passed the
  existing normalizer under `data/ocr/dotsmocr/results/task3-client-20261103/`.
