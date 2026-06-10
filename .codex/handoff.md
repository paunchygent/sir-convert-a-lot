---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-06-10'
---

## Purpose

Keep volatile Sir Convert-a-Lot state, blockers, validation evidence, and next
actions. Durable session history lives in `.codex/long-term-memory/entries/`;
durable implementation authority lives in governed docs.

## Current State

- Generated docs doorway: `docs/index.md`.
- Active planning and session handoff: `.codex/handoff.md`.
- Long-term handoff history compacted on 2026-06-05:
  `.codex/long-term-memory/entries/session-2026-06-05-handoff-compaction.md`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active Gateway cutover lane: `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Active speech-to-text lane: Epic 12; ADR-0013 accepted; Story 51 accepted in
  Review 26; Story 52 accepted in Review 27 as governed profile rejection; Task
  351 adds the preflight runner; Story 53 remains blocked until live Hemma proof.
- STT Task 352 is in progress; Review 31 approved `benchmark:stt-sidecar-profile-proof` as the content-safe runner/contract slice. The post-deploy Hemma live proof has now been run from committed/pushed/deployed code at `5e63c9ce1bf2dbd7fc96d3525b9abb85294a4145`. Review 33 records `changes_requested`: codec boundary, sidecar launch, backend imports, HF token/cache presence, ROCm GPU/no CPU fallback, content safety, and 120-minute lifecycle are proven, but Story 53 remains blocked because `faster-whisper` fails on the Hemma ROCm lane with a CUDA runtime/driver mismatch and `pyannote.audio` pipeline loading fails with `GatedRepoError`.
- Active exam artifact conversion/authoring lane: `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`.
- Active public-edge recovery/follow-up tasks: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md` and `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`.
- Active dependency-image cleanup task: `docs/backlog/tasks/task-340-prune-superseded-sir-convert-dependency-image-tags-after-successful-deps-builds.md`.

## Conversion Remediation

- Epic 06 is the active long-PDF reliability, progress, and throughput epic:
  `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`.
- Task 342 owns CLI live progress, manifest, idempotent replay, and recovery
  visibility:
  `docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md`.
- Task 343 owns PDF conversion decision logic and GPU/CPU performance
  attribution:
  `docs/backlog/tasks/task-343-investigate-pdf-conversion-decision-logic-and-gpu-cpu-performance-attribution.md`.
- Task 344 owns the Docling/Granite formula VLM generation-stability root
  cause:
  `docs/backlog/tasks/task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking.md`.
- Task 345 owns source-layer formula authority for born-digital PDFs and must
  align implementation with Task 342 user feedback and Task 343 conversion
  decisioning:
  `docs/backlog/tasks/task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs.md`.
- Task 346 owns the pre-infrastructure specialist formula/OCR candidate
  evaluation on the established Task 344 incident pages/crops and is completed:
  `docs/backlog/tasks/task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure.md`.
- Task 347 owns the Hemma runtime-enablement evidence for PaddleOCR and
  DeepSeek-OCR-2:
  `docs/backlog/tasks/task-347-enable-hemma-specialist-ocr-runtimes-for-task-346-candidate-replay.md`.
- Task 348 owns the native PaddleOCR/PaddleX AMD GPU container probe for
  formula recognition:
  `docs/backlog/tasks/task-348-probe-paddleocr-vl-and-paddlex-amd-gpu-container-support-for-formula-recognition-on-hemma.md`.
- Task 350 owns the governed DeepSeek-OCR-2 HF eager Task 346 replay:
  `docs/backlog/tasks/task-350-integrate-deepseek-ocr-2-hf-eager-candidate-replay-for-task-346.md`.

Task 344 localized the slow chunk to Docling formula VLM generation and fixed
the deterministic Granite-Docling repetition loop with governed stop strings
and deterministic Transformers generation controls.

Task 344 does not close formula-output quality. Post-fix pages `13-16` replay
completed without token-ceiling exhaustion but persisted Markdown still failed
correctness review with leaked `</formula` fragments and hallucinated formula
text. Task 345 is the active follow-up: source-layer formula evidence must be
authoritative when usable, VLM output must be advisory/rejected unless accepted
by a governed source-backed gate, and the CLI/manifest must expose safe formula
authority reasons. Task 345 must land the shared evidence/authority data model
first; Task 342 presents that metadata, and Task 343 consumes it for later
decision-policy work without reimplementing source-layer extraction or formula
authority decisions. The task must preserve the larger best-effort conversion
contract: every formula region needs an explicit artifact representation
decision, and `partial_or_unusable` / `absent` cannot become silent omission.
The 2026-06-06 Task 345 pre-implementation scrutiny gate is complete and passed
in qualified form: PyMuPDF provides usable coordinate-backed source evidence on
incident pages `13-16`, Poppler bbox extraction crashes on page `14`, and the
implementation must preserve explicit `usable`, `partial_or_unusable`, and
`absent` evidence states.

Task 345 formula hardening checkpoint 2026-06-10: source-backed formula
authority now skips formula VLM before generation when PyMuPDF
coordinate/raw/text evidence is `usable`, while preserving accurate table mode.
The current production reconciliation unit is page-window: accepted Markdown
gets a deterministic `sir-convert-a-lot:formula-authority` marker, and backend
results / `ConversionMetadata` / page-window replay reports carry safe
structured `formula_authority` metadata with no raw prompts, crops, or
generated formula internals. No-source/absent-source behavior is preserved:
CodeFormulaV2 -> Granite fallback remains available and can commit a
structurally clean generated candidate; runtime-unavailable formula enrichment
falls back to source-layer Markdown with explicit `fallback` metadata. The
candidate harness module
`scripts/sir_convert_a_lot/devops/formula_candidate_eval_candidates.py` was
split into focused spec/command/output/execution modules before any further
DeepSeek integration work. Hemma accepted-output replay for pages `13-16`:
`build/verification/task-345-source-backed-formula-authority-replay/docling-page-window-replay-20260610T055608Z/report.json`.
The replay succeeded with `table_mode=accurate`, `formula_enrichment=false`,
`formula_vlm_batch_count=0`, `transformers_call_count=0`,
`formula_authority.action=skipped`, and
`formula_authority.source_evidence_state=usable`. Accepted Markdown review
found no recurrence of leaked `</formula`, `\mathbmath`, repeated `\mathbf`,
spaced `l o o l y`, `<loc_`, `<formula>`, or observed DeepSeek/vLLM repetition
markers. Initial Task 342 terminal status/result/manifest presentation now
surfaces the same `formula_authority` metadata without adding a second
authority policy. Task 342 now also writes the v2 CLI manifest incrementally
when a job id is observed, emits submitted/replayed job lines, atomically
refreshes terminal entries, and records `client_interrupted` running entries on
KeyboardInterrupt after submission. Remaining governed work: first-class Task
342 status/recovery UX, richer safe idempotency/request diagnostics, Task 343
decision/performance use, and
optional future per-region merge once stable final-Markdown formula identifiers
exist.

Task 346/350 final candidate-evaluation state: Granite baseline still shows
known malformed formula markers; PyMuPDF source-layer extraction is fast,
coordinate-backed evidence only, not semantic LaTeX restoration; PaddleOCR pip
CUDA wheel is blocked on Hemma ROCm, `paddleocr-vl:latest-amd-gpu` exposes
formula APIs but aborts in native Paddle GPU kernels, and
`paddlex-paddle-vllm-amd-gpu:3.4.0-0.14.0rc2` lacks PaddleOCR formula APIs.
DeepSeek-OCR-2 vLLM is rejected for the current Hemma ROCm lane: it loads only
after adapter fixes but finishes pages `13-16` by length with repeated
impossible tokens. Task 350 replaced the default Task 346 DeepSeek candidate
with HF eager and reran pages `13-16` on Hemma:
`build/verification/task-350-deepseek-hf-eager-task346-replay/formula-candidate-eval-20260606T201448Z/report.json`.
HF eager succeeded on four pages in `676555 ms`, wrote `result.mmd` and
`result_with_boxes.jpg`, recorded eager attention in host/inner metadata, and
had no observed vLLM markers or Task 344 malformed markers. Manual review found
coherent but imperfect output: page `14` has malformed inline math/prose,
page `13` has an incomplete equation-boundary continuation, page `15` has
OCR-like model-name errors, and page `16` has HTML table/entity artifacts.
Recommendation: promote DeepSeek-OCR-2 HF eager to a later governed integration
design only behind Task 345 source-backed authority, page-window reconciliation,
and best-effort representation policy; do not blindly overwrite born-digital
formula evidence with VLM output.

## Next Actions

1. For STT Task 352, do not start Story 53 yet. Govern the next backend decision first: either replace faster-whisper for the Hemma ROCm STT lane, provide a CUDA/NVIDIA execution lane for faster-whisper, or explicitly reject faster-whisper as the Hemma profile; then provision/accept the required Hugging Face gated access for the pyannote diarization pipeline or govern an alternative diarization backend that satisfies exact and min/max speaker hints.
1. For PaddleOCR, do not reopen the tested official/native AMD container lanes
   without a new runtime image or governed compatibility hypothesis. Task 348's
   image exposes formula APIs but aborts in native Paddle GPU kernels; Task
   349's image is ROCm-enabled but lacks PaddleOCR formula APIs.
1. If vLLM remains desired, first prove a different vLLM/ROCm runtime whose
   DeepSeek-OCR-2 decode path produces coherent output on page-14. Do not reuse
   the current Hemma vLLM lane as a candidate.
1. Feed Task 345 formula-authority metadata into Task 343 conversion-decision
   metrics when broader conversion decisioning resumes.
1. Any DeepSeek-OCR production integration must be a governed follow-up: keep
   HF eager as the viable candidate, keep current vLLM/ROCm rejected until a
   different coherent path is proven, use DeepSeek only advisory or for
   absent/unusable source evidence, and never blindly overwrite born-digital
   source-backed formula evidence.
1. Continue Story 46 with Tasks 288/289 before further Exam.net runtime.
1. Continue HuleEdu/Skriptoteket cutover only through governed Gateway and
   artifact-route tasks; do not widen the DigiExam migration lane.

## Validation

- Older STT and Task 344 validation history is durable in governed task/review
  docs; this handoff keeps only current conversion remediation evidence below.
- Task 348/349 validation and artifacts are recorded in their task docs.
- Task 350 local and Hemma focused tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_formula_candidate_eval.py tests/sir_convert_a_lot/test_deepseek_ocr2_hf_command.py`
  -> `9 passed`.
- Task 345/350 local focused validation 2026-06-10:
  `pdm run pytest-root tests/sir_convert_a_lot/test_runtime_conversion_quality_warnings.py tests/sir_convert_a_lot/test_docling_formula_authority.py tests/sir_convert_a_lot/test_docling_backend.py tests/sir_convert_a_lot/test_formula_candidate_eval.py tests/sir_convert_a_lot/test_deepseek_ocr2_hf_command.py`
  -> `40 passed, 2 skipped`; focused `ruff check` -> `All checks passed!`;
  focused mypy -> `Success: no issues found in 17 source files`.
- Task 345/350 Hemma focused validation 2026-06-10:
  `/home/paunchygent/.local/bin/pdm run pytest-root tests/sir_convert_a_lot/test_runtime_conversion_quality_warnings.py tests/sir_convert_a_lot/test_docling_formula_authority.py tests/sir_convert_a_lot/test_docling_backend.py tests/sir_convert_a_lot/test_formula_candidate_eval.py tests/sir_convert_a_lot/test_deepseek_ocr2_hf_command.py`
  -> `42 passed`.
- Task 345 Hemma accepted-output replay 2026-06-10:
  `build/verification/task-345-source-backed-formula-authority-replay/docling-page-window-replay-20260610T055608Z/report.json`;
  accepted Markdown marker scan for `</formula`, `\mathbmath`, `\mathbf`,
  spaced `l o o l y`, `<loc_`, `<formula>`, and observed DeepSeek/vLLM markers
  -> no matches.
- Task 342 formula-authority presentation slice 2026-06-10:
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py::test_pdf_to_md_lifecycle_result_and_artifact tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py::test_convert_upload_to_artifact_auto_reruns_terminal_failed_idempotent_replay tests/sir_convert_a_lot/test_v2_pdf_chunk_conversion.py tests/sir_convert_a_lot/test_pdf_checkpoint_metadata_v2.py`
  -> `6 passed`.
- Task 342 incremental manifest/replay visibility slice 2026-06-10:
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py::test_convert_upload_to_artifact_reports_submitted_replay_to_progress_callback tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py::test_convert_upload_to_artifact_reports_fresh_running_submit_to_progress_callback`
  -> `8 passed`; Review 32 approved the slice after one remediation pass.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence.
- Stop before changing service runtime, Hemma deploy, artifact retention, or provider experiment semantics without governed task authority.
- Do not cancel or abort live conversions as part of formula-quality work.
