# dots.mocr runtime instructions

- `scripts/verify_model.py` must verify all weights before launching any command.
  Use `subprocess.call` with the argument list on Windows and propagate its status:
  Windows `os.execvp` does not escape spaces/quotes and can report success after
  a broken launch. Linux keeps `os.execvp` for the same PID and signal behavior.
  A verifier change requires rebuilding the image because the host checks its
  baked hash; keep earlier images/evidence for replay. The 4 November fix has
  actual Windows argument/exit-code tests and a Linux image/PID control.

- Owner decision 04.11.2026 makes this service the default OCR provider.
  The integration switch does not depend on identical OCR outputs.
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
  2026. The container entrypoint checks all files against the 16 hashes in
  `config/new_ocr_models.json` before starting its command, rejecting missing,
  changed, extra or symlinked files. Do not bypass the entrypoint for inference.
  A synthetic check is not runtime qualification or owner approval to switch.
- `scripts/new_ocr_pdf.py` and `config/` contain only the dots.mocr client and
  its pinned settings. Preserve streaming Picture/loop recovery, rotation retries,
  confidence-gated page orientation and `dotsmocr-layout/2` native sidecars.
  The host may snapshot these files; a real synthetic PDF result has passed the
  existing normalizer under `data/ocr/dotsmocr/results/task3-client-20261103/`.
- On interrupted or malformed SSE, retain complete chunks and unfinished bytes
  (`unparsed_sse_base64`) with `client_error`; never accept a response with that
  error as finished. Picture failures remain recorded per attempt and, under
  `retain_unresolved`, produce an explicit unresolved region rather than text.
- The 4 November qualification has not passed: with page orientation enabled,
  SanPiN page 59 changes a weekly interval and Minfin page 26 loops; a separate
  without-orientation control finishes the latter but does not validate its empty
  table. Keep both orientations' evidence. The owner subsequently authorized
  switching the integration without further OCR quality runs.
