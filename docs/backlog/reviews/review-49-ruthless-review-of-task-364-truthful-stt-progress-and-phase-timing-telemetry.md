---
id: review-49-ruthless-review-of-task-364-truthful-stt-progress-and-phase-timing-telemetry
title: Ruthless review of task 364 truthful STT progress and phase timing telemetry
type: review
status: completed
priority: high
created: '2026-06-14'
last_updated: '2026-06-14'
related:
  - docs/backlog/tasks/task-364-truthful-stt-progress-and-phase-timing-telemetry.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/downstream_integration_contract_v2.md
labels:
  - review
  - approved
  - task-364
  - stt
  - progress
  - telemetry
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Fixed independent ruthless review for Task 364. This reviewer did not
implement Task 364 and did not commit, push, deploy, rebase, amend, reset,
delete data, revert work, or modify production code. The only intentional
mutation from this review pass is this retained review artifact plus any
generated docs index refresh required by validation.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/backlog/tasks/task-364-truthful-stt-progress-and-phase-timing-telemetry.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/downstream_integration_contract_v2.md`

Implementation and contract files inspected:

- `scripts/sir_convert_a_lot/application/contracts_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py`
- `scripts/sir_convert_a_lot/infrastructure/audio_transcript_phase_timing.py`
- `scripts/sir_convert_a_lot/infrastructure/audio_transcript_progress.py`
- `scripts/sir_convert_a_lot/infrastructure/audio_transcript_runtime_types.py`
- `scripts/sir_convert_a_lot/infrastructure/job_events_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/job_store_manifest_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/job_store_models_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/job_store_v2_core.py`
- `scripts/sir_convert_a_lot/infrastructure/phase_timings_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/progress_fields_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_job_runner_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_models_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_job_record_response_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_job_events_v2.py`
- `tests/sir_convert_a_lot/test_audio_transcript_phase_progress_v2.py`
- `tests/sir_convert_a_lot/test_audio_transcript_phase_timing_telemetry_v2.py`
- `tests/sir_convert_a_lot/test_audio_transcript_progress_redaction_v2.py`
- `tests/sir_convert_a_lot/test_audio_transcript_progress_v2.py`
- `tests/sir_convert_a_lot/test_openapi_contract_v2.py`
- `tests/sir_convert_a_lot/test_phase_timings_v2.py`
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `.codex/handoff.md`

Public surfaces affected:

- Service API v2 `job.progress` for `audio -> transcript_bundle` create/poll
  responses.
- Service API v2 lifecycle events/SSE progress payloads for the additive
  pipeline progress and ETA fields.
- OpenAPI `JobProgressV2` and `JobEventProgressV2` schemas.
- Converter/downstream docs for Skriptoteket `PR-0351`.

Compatibility posture:

- The public changes are additive nullable fields:
  `audio_pipeline_percent_complete` and `audio_pipeline_eta_seconds`.
- Existing Task 357 chunk fields are preserved and remain monotonic.
- No chunk size, chunk overlap, chunk count planning, or sidecar batch-size
  semantics were changed.

## Findings

None.

Reviewer conclusions:

- `diarizing` is emitted before the blocking `sidecar.diarize(...)` call starts:
  the runtime records probe/normalize timing, emits `emit_diarizing_progress`,
  checks cancellation, and only then calls `sidecar.diarize`
  (`scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:164`,
  `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:169`,
  `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:174`,
  `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:178`).
- Chunk semantics are unchanged. `plan_audio_chunks` still defaults to
  `300.0` seconds with `0.0` overlap and
  `audio_chunk_v1_300s_global_diarization`; sidecar batch-size settings and
  runtime files had no Task 364 diff.
- The observed chunk fields remain monotonic through the existing job-store
  updater and Task 357 regression coverage. Heartbeat updates only touch
  diagnostics; they do not call the audio progress updater.
- The additive pipeline fields are typed, persisted, projected to job records,
  projected to lifecycle events, and OpenAPI-documented
  (`scripts/sir_convert_a_lot/application/contracts_v2.py:52`,
  `scripts/sir_convert_a_lot/infrastructure/progress_fields_v2.py:95`,
  `scripts/sir_convert_a_lot/interfaces/http_job_record_response_v2.py:48`,
  `scripts/sir_convert_a_lot/interfaces/http_routes_job_events_v2.py:73`,
  `tests/sir_convert_a_lot/test_audio_transcript_phase_timing_telemetry_v2.py:131`).
- Pipeline percent is bounded by Pydantic/OpenAPI and monotonic in persistence;
  ETA is nonnegative and calculated only when explicit phase timing/progress
  events provide a measured basis. Heartbeat-only freshness is covered by the
  blocking diarization test
  (`tests/sir_convert_a_lot/test_audio_transcript_phase_progress_v2.py:104`).
- Canonical Task 364 timing keys are registered in the strict phase timing
  key set and are persisted for successful and failed audio jobs:
  `audio_probe_normalize_ms`, `audio_diarization_ms`,
  `audio_transcription_ms`, `audio_alignment_ms`, and
  `audio_packaging_ms`
  (`scripts/sir_convert_a_lot/infrastructure/phase_timings_v2.py:25`,
  `tests/sir_convert_a_lot/test_audio_transcript_phase_timing_telemetry_v2.py:30`,
  `tests/sir_convert_a_lot/test_audio_transcript_phase_timing_telemetry_v2.py:82`,
  `tests/sir_convert_a_lot/test_audio_transcript_phase_timing_telemetry_v2.py:107`).
- `final_artifact_persist_ms` and `conversion_total_ms` are still added by the
  existing terminal store/runner paths and remain present in success and
  failure timing tests.
- Content-safety is preserved for public progress/timing telemetry. The
  redaction test injects transcript text, a speaker-like display token, raw
  filename, media hash, handle, signed-header marker, and artifact-byte marker,
  then asserts none appear in serialized `job.progress`
  (`tests/sir_convert_a_lot/test_audio_transcript_progress_redaction_v2.py:86`).
- The Service API v2 docs, route-specific audio contract, downstream handoff,
  and generated OpenAPI agree on the additive field names and semantics for
  Skriptoteket `PR-0351`.

Residual risk:

- This review reran the requested focused bundle plus docs/diff gates. I did
  not rerun the implementer-reported `coverage-gate`, `format-all`,
  `lint-fix`, `typecheck-all`, `skills-validate`, or `handoff-validate` in
  this independent pass. Their green status is retained in `.codex/handoff.md`
  as implementer evidence.
- Downstream copy says `audio_current_chunk_index` is the most recently
  accepted chunk index, while the existing Task 357 behavior exposes `0`
  before the first chunk is accepted. Because the exact observed completion
  fields still remain `audio_processed_media_seconds=0.0` and
  `audio_percent_complete=0.0`, this is not a Task 364 approval blocker, but
  the overseer may choose to tighten the wording in a later docs-only cleanup.

## Decision

`approved`.

## Response

Task 364 is approved by this retained review. No production code fixes are
required by this review. The implementation can proceed to overseer closeout,
staging, and downstream handoff handling without this reviewer marking Task
364 itself completed.

## Follow-up Actions

1. Overseer should complete the Task 364 closeout separately and keep the task
   status/checklist synchronized; this review intentionally does not mark the
   task completed.
1. Optional docs-only cleanup: clarify whether
   `audio_current_chunk_index=0` before first accepted chunk means "current
   chunk index" or "most recently accepted chunk index" for downstream copy.
   This is not a requested production fix.

## Validation Evidence

Reviewer-rerun commands:

- `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_phase_progress_v2.py tests/sir_convert_a_lot/test_audio_transcript_phase_timing_telemetry_v2.py tests/sir_convert_a_lot/test_audio_transcript_progress_redaction_v2.py tests/sir_convert_a_lot/test_audio_transcript_progress_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed with `10 passed`.
- `pdm run docs-validate` passed with `Validated 484 backlog files` and
  `Validated docs=559 rules=11` before this artifact edit.
- `git diff --check` passed before this artifact edit.

Implementation evidence inspected in `.codex/handoff.md`:

- Task 364 focused trio first failed with `5 failed` because `diarizing`,
  timing keys, and pipeline fields were absent.
- Focused green proof later passed with `5 passed`.
- Requested regression bundle plus phase timing helper proof passed with
  `20 passed`.
- `coverage-gate` passed with `1721 passed, 6 skipped` and `95.37%` coverage.
- Format, lint, type, docs, skills, handoff, and diff gates were reported
  green.

Post-artifact validation after this review edit:

- `pdm run docs-sync`
  refreshed `docs/backlog/INDEX.md`.
- `pdm run docs-validate`
  passed with `Validated 484 backlog files` and `Validated docs=559 rules=11`.
- `git diff --check`
  passed with no whitespace errors.

## Completion

Review retained as approved/completed on 2026-06-14.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
