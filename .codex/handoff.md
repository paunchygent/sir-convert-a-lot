---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-06-13'
---

## Purpose

Keep volatile Sir Convert-a-Lot state, blockers, validation evidence, and next
actions. Durable session history lives in `.codex/long-term-memory/entries/`;
durable implementation authority lives in governed docs.

## Current State

- Generated docs doorway is `docs/index.md`; durable session history starts at
  `.codex/long-term-memory/entries/session-2026-06-05-handoff-compaction.md`.
  STT, formatter, and formula-lane history is compacted under
  `.codex/long-term-memory/entries/`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active Gateway cutover lane: `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Active speech-to-text lane: Epic 12; ADR-0013 accepted; Story 53 JSON
  runtime is live after accepted Tasks 355, 356, and 357 plus Reviews 41-43.
- Story 54 / Task 358 is complete and accepted in Review 44. Product-neutral
  TXT, Markdown, WebVTT, and SRT artifacts are implemented over validated
  canonical `transcript_json`; downstream apps own product meaning, durable
  saves, filenames, and workflow-specific derivatives.
- Story 56 plus Tasks 359/360 are implemented for overlay-aware transcript
  formatter replay. Service API v2 now supports
  `transcript_json -> transcript_bundle` over uploaded canonical
  `transcript_json_v1`, strict `transcript_formatter_replay_v1` options,
  closed requested artifacts `txt|md|vtt|srt`, typed
  `speaker_label_overrides`, and returned `transcript_txt`/`md`/`vtt`/`srt`
  named artifacts. Replay does not emit `transcript_json`; `/result` and
  singular `/artifact` return a content-safe
  `transcript_formatter_replay_result_v1` manifest. No bespoke endpoint,
  downstream formatter, source-audio replay, or Gateway rewriting is part of
  the contract.
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

Durable formula-lane findings are retained in
`.codex/long-term-memory/entries/session-2026-06-13-handoff-trimmed-formula-history.md`.
Active carry-forward: Task 345 owns source-backed formula authority, Task 342
presents safe authority metadata, and Task 343 consumes it for later
decision/performance work.

## Next Actions

1. Downstream HuleEdu Gateway and Skriptoteket JSON transcript consumption has
   been proven live through the product path. Next STT product work is
   Skriptoteket durable transcript saves from canonical `transcript_json`;
   Sir Convert Story 54 formatter artifacts are complete in accepted Task 358
   as a separate product-neutral formatter authority.
1. Next transcript replay work is downstream consumption: HuleEdu TASK-0675 can
   forward the implemented `transcript_json -> transcript_bundle` route through
   Gateway, and Skriptoteket PR-0347 can consume overlay-aware formatter replay
   artifacts without local formatter logic.
1. Treat the Sir Convert 120-minute STT progress UX backend contract as
   accepted; keep downstream durable transcript saves separate from Task 358
   formatter artifact implementation.
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

- Durable validation history is in the governed task/review docs. STT runtime
  acceptance is recorded in Reviews 40-43. Task 358 formatter acceptance is
  recorded in Review 44 after the `specs_v2.py` module split.
- Task 359/360 implementation evidence on 2026-06-13: red-first replay/OpenAPI
  suite first failed with missing `transcript_json` enum, missing
  `transcript_formatter_options`, HTTP `415` for `.json`, and missing OpenAPI
  components. After implementation and OpenAPI export, focused suite
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  passed with `31 passed` after retained Review 45 strictness fixes.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence.
- Stop before changing service runtime, Hemma deploy, artifact retention, or provider experiment semantics without governed task authority.
- Do not cancel or abort live conversions as part of formula-quality work.
