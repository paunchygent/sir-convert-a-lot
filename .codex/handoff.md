---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-06-09'
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
- Active DevOps story:
  `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active Gateway cutover lane:
  `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Active speech-to-text planning lane: Epic 12; ADR-0013/audio contract are
  remediated drafts pending Review 25 re-review.
- Active exam artifact conversion/authoring lane:
  `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`.
- Active public-edge recovery/follow-up tasks:
  `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`
  and
  `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`.
- Active dependency-image cleanup task:
  `docs/backlog/tasks/task-340-prune-superseded-sir-convert-dependency-image-tags-after-successful-deps-builds.md`.

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

Task 344 evidence localized the slow chunk to Docling formula VLM generation.
The concrete root cause for the non-returning page-14 crop was a deterministic
Granite-Docling greedy-decoding repetition loop on crop `#/texts/5`. The
implemented remediation forwards active stop strings and adds deterministic
Transformers generation controls for formula VLM calls
(`no_repeat_ngram_size=64`, `renormalize_logits=true`) while preserving
`do_sample=false`, `temperature=0.0`, `max_new_tokens=2048`, and active stop
criteria.

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

Task 345 implementation checkpoint 2026-06-06: the initial source-layer
formula authority substrate is implemented. The new module
`scripts/sir_convert_a_lot/infrastructure/docling_formula_authority.py`
classifies document source evidence as `usable`, `partial_or_unusable`, or
`absent` using PyMuPDF coordinate words/rawdict/text extraction. The Docling
fallback boundary now rejects generated formula candidates when source evidence
is `usable` and the formula-generation path has already shown structural
quality defects, rerunning the same Docling conversion with
`formula_enrichment=false` and warning
`docling_formula_source_backed_vlm_rejected`. Absent-source behavior is
preserved: CodeFormulaV2 -> Granite fallback remains available and can commit
a structurally clean generated candidate. Remaining Task 345 work: per-region
best-effort Markdown representation/merge, formula-authority metadata for
Task 342, conversion-decision metrics for Task 343, and incident pages `13-16`
accepted-output replay.
Task 345 now contains the durable internal tranche contract: substrate first,
representation ladder second, reconciliation third, runtime metadata fourth,
Task 342 presentation fifth, Task 343 decision/performance consumption sixth,
and incident replay/accepted-artifact review last.

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
`build/verification/task-350-deepseek-hf-eager-task346-replay/task346-formula-candidate-eval-20260606T201448Z/report.json`.
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

1. Continue Task 345 by implementing the best-effort formula representation
   ladder and per-region/page-window reconciliation on top of the new
   `docling_formula_authority` substrate. Do not create a second source-layer
   extractor or authority policy.
1. For PaddleOCR, do not reopen the tested official/native AMD container lanes
   without a new runtime image or governed compatibility hypothesis. Task 348's
   image exposes formula APIs but aborts in native Paddle GPU kernels; Task
   349's image is ROCm-enabled but lacks PaddleOCR formula APIs.
1. If vLLM remains desired, first prove a different vLLM/ROCm runtime whose
   DeepSeek-OCR-2 decode path produces coherent output on page-14. Do not reuse
   the current Hemma vLLM lane as a candidate.
1. Extend Task 345 metadata so rejected/accepted/advisory/skipped formula
   authority decisions can be surfaced by Task 342 CLI/manifest work, but only
   after representation and reconciliation decisions exist.
1. Decouple accurate table mode from committing generative formula VLM output.
1. Feed Task 345 formula-authority metadata into Task 342 CLI/manifest progress
   and Task 343 conversion-decision metrics.
1. Re-run the Task 344 incident pages `13-16` replay and inspect accepted
   Markdown for known hallucination/leakage recurrence.
1. Continue Story 46 with Tasks 288/289 before further Exam.net runtime.
1. Continue HuleEdu/Skriptoteket cutover only through governed Gateway and
   artifact-route tasks; do not widen the DigiExam migration lane.

## Validation

- ADR-0013/audio docs-only remediation: `docs-sync`, `docs-validate`
  (`440 backlog`, `docs=515 rules=11`), `skills-validate`,
  `handoff-validate`, and `git diff --check` passed.
- Task 344 focused local tests passed:
  `pdm run test tests/sir_convert_a_lot/test_docling_formula_diagnostics.py tests/sir_convert_a_lot/test_task344_page_window_replay.py`
  -> `20 passed`.
- Task 344 live Hemma GPU replays:
  page/window `14`
  `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T110626Z/report.json`
  and incident window `13-16`
  `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T110852Z/report.json`.
- Both live replays ran without target filtering or no-repeat env override; all
  Granite formula generate calls recorded `no_repeat_ngram_size=64`,
  `renormalize_logits=true`, terminal stop counts matching decoded rows, and
  `max_new_tokens_exhausted=false`.
- Timing interpretation remains split: the stopless page-14 loop now exits by
  stop string, while the `13-16` replay still spent `200977 ms` inside
  correctly completed Granite formula generation calls. Treat remaining latency
  as GPU/runtime/model-throughput work for Task 343/Task 74.
- Output correctness remains open under Task 345. Markdown persistence replay:
  `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T112725Z/report.json`.
- Task 348/349 validation and artifacts are recorded in their task docs.
- Task 350 local and Hemma focused tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_task346_formula_candidate_eval.py tests/sir_convert_a_lot/test_task347_deepseek_ocr2_hf_command.py`
  -> `9 passed`.
- Task 345 red/green local validation:
  `pdm run pytest tests/sir_convert_a_lot/test_docling_formula_authority.py tests/sir_convert_a_lot/test_docling_backend.py`
  -> `25 passed, 2 skipped`.
- Task 345 focused static validation:
  `pdm run ruff check scripts/sir_convert_a_lot/infrastructure/docling_formula_authority.py scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py tests/sir_convert_a_lot/test_docling_formula_authority.py tests/sir_convert_a_lot/test_docling_backend.py`
  -> `All checks passed!`;
  `pdm run mypy scripts/sir_convert_a_lot/infrastructure/docling_formula_authority.py scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py tests/sir_convert_a_lot/test_docling_formula_authority.py tests/sir_convert_a_lot/test_docling_backend.py`
  -> `Success: no issues found in 4 source files`.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence.
- Stop before changing service runtime, Hemma deploy, artifact retention, or
  provider experiment semantics without governed task authority.
- Do not cancel or abort live conversions as part of formula-quality work.
