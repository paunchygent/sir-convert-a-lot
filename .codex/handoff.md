---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-06-14'
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
- Task 361 is implemented and marked completed:
  `docs/backlog/tasks/task-361-consume-huleedu-internalidentitycontextv1-trust-profile-and-acceptance-smoke.md`.
  Sir Convert now consumes HuleEdu sanitized internal-identity trust profiles
  through typed runtime config, compares active key canonical DER SPKI
  fingerprint to the profile fingerprint, and uses the profile key id,
  issuer, audience, TTL, and skew in the existing verifier path. Local/prod
  compose require sanitized `HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON`.
  Acceptance smoke is content-safe test-material proof only; no live HuleEdu
  signed headers were retained.
- Active speech-to-text lane: Epic 12; ADR-0013 accepted; Story 53 JSON
  runtime is live after accepted Tasks 355, 356, and 357 plus Reviews 41-43.
- STT production remediation Task 362 is completed:
  `docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md`.
  The production sidecar now requires FasterWhisper
  `BatchedInferencePipeline`, passes `batch_size=8` during chunk transcription,
  exposes sanitized `/capabilities` truth with
  `backend_family=faster_whisper` and `batch_size=8`, and pins prod compose
  `SIR_STT_SIDECAR_BATCH_SIZE=8`. RCA: the observed 34-second first response
  was not solved by Gateway timeout alone; production must use batched
  inference.
- Task 363 fast replay architecture remediation is implemented and approved in
  independent Review 48; commit/push/redeploy/live verification closeout is
  still pending:
  `docs/backlog/tasks/task-363-fast-transcript-formatter-replay-lane-outside-heavy-conversion-queue.md`.
  It exists because Skriptoteket production/manual export evidence showed the
  browser-owned replay path can spend about 119 seconds waiting across
  Sir Convert submit/poll/artifact fetch/complete. The current implementation
  makes `transcript_json -> transcript_bundle` a producer-owned fast lane under
  the existing `/v2/convert/jobs` contract: admitted `wait_seconds=0` replay
  jobs terminalize synchronously as `succeeded` or fail-closed `failed`, replay
  no longer dispatches through the generic heavy conversion worker queue, and
  bounded sanitized admission/execution telemetry is emitted without transcript
  text, display names, source content, credentials, or signed headers.
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
  named artifacts. Replay does not emit `transcript_json`; `/result` returns
  metadata for the primary `transcript_replay_bundle_manifest.json` artifact,
  while singular `/artifact` streams the content-safe
  `transcript_formatter_replay_result_v1` manifest body. No bespoke endpoint,
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
1. Next transcript replay work is Task 363 commit/push and Hemma deploy/live
   verification closeout after approved Review 48. Run
   `pdm run hemma-deploy-and-verify --expected-revision <approved-sha> --lane host --api-key <redacted>`;
   retain deploy evidence without API keys, transcript text, display names, or
   signed headers. Skriptoteket PR-0350 can consume the producer fast-lane replay
   contract without a browser-owned submit/poll/artifact-download/
   base64-complete saga. HuleEdu should continue forwarding the existing
   `/sir-convert/v2/convert/jobs*` lifecycle without rewriting Sir Convert
   replay responses.
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
- Task 361 red-first evidence on 2026-06-13:
  `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py -q`
  first failed with `4 failed, 5 passed` because trust-profile config was
  missing and missing-key / SPKI-mismatch / PEM-byte-fingerprint drift were not
  fail-closed. Green focused proof later passed with `39 passed`:
  `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py tests/sir_convert_a_lot/test_structured_llm_settings_route_v2.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`.
  `pdm run typecheck-all`, `pdm run format-all`, and `pdm run lint-fix` also
  passed before final docs/skills/handoff/diff gates.
- Task 362 red-first evidence on 2026-06-13:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_compose_contract.py -q`
  first failed with `9 failed, 17 passed` because sidecar settings had no
  `batch_size` and prod compose omitted `SIR_STT_SIDECAR_BATCH_SIZE`.
  Focused green proof later passed with `27 passed` via
  `tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py`,
  `tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`, and
  `tests/sir_convert_a_lot/test_compose_contract.py` after runtime batching,
  capability, startup-wrapper, and compose-contract changes.
  `pdm run format-all`, `pdm run typecheck-all`, and `pdm run lint-fix` passed;
  docs/skills/handoff/diff gates passed after docs sync.
- Task 363 red-first evidence on 2026-06-14:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py -q`
  first failed with `4 failed` because replay returned `202 Accepted`/queued
  for `wait_seconds=0` and no fast-lane timing telemetry existed. Focused
  replay/OpenAPI proof later passed with `36 passed`:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py tests/sir_convert_a_lot/test_transcript_replay_observability_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`.
  Neighboring route/supervisor/metrics proof passed with `10 passed`:
  `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_api_metrics_v2.py -q`.
  `pdm run coverage-gate` passed with `1716 passed, 6 skipped`; required
  coverage `90.0%` was reached at `95.34%`.
  Downstream smoke proof command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py::test_downstream_replay_fast_lane_smoke_fetches_overlay_artifact -q`.
  Independent Review 48 approval proof on 2026-06-14: reviewer reran
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py tests/sir_convert_a_lot/test_transcript_replay_observability_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  with `36 passed`, and
  `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_api_metrics_v2.py -q`
  with `10 passed`.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence.
- Stop before changing service runtime, Hemma deploy, artifact retention, or provider experiment semantics without governed task authority.
- Do not cancel or abort live conversions as part of formula-quality work.
