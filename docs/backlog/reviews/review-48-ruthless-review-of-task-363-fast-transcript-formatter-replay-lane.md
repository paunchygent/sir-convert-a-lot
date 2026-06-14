---
id: review-48-ruthless-review-of-task-363-fast-transcript-formatter-replay-lane
title: Ruthless review of task 363 fast transcript formatter replay lane
type: review
status: completed
priority: high
created: '2026-06-14'
last_updated: '2026-06-14'
related:
  - docs/backlog/tasks/task-363-fast-transcript-formatter-replay-lane-outside-heavy-conversion-queue.md
  - docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md
  - docs/backlog/tasks/task-359-define-transcript-speaker-overlay-formatter-replay-contract.md
  - docs/backlog/tasks/task-360-implement-transcript-speaker-overlay-formatter-replay-artifacts.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
labels:
  - review
  - approved
  - task-363
  - transcript-formatters
  - replay
  - fast-lane
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Review the Task 363 implementation that makes `transcript_json -> transcript_bundle`
formatter replay a bounded fast producer lane under the existing Service API v2
job contract. The review must verify that replay no longer depends on generic
heavy conversion queue contention, preserves the accepted strict replay
contract from Tasks 359/360, and provides downstream-safe smoke evidence for
Skriptoteket PR-0350.

Reviewer independence: fixed independent reviewer only. This reviewer did not
author the Task 363 implementation, tests, or contract docs. The intentional
review edits in this pass are this retained artifact, the Task 363 review-gate
checkbox, handoff state, and generated docs index updates from `docs-sync`.

Files inspected:

- `scripts/sir_convert_a_lot/domain/service_routes_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/transcript_formatter_replay_fast_lane_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_telemetry_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_capacity_telemetry_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_supervision_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/transcript_formatter_replay_runtime.py`
- `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_artifacts.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
- `tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py`
- `tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py`
- `tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py`
- `tests/sir_convert_a_lot/test_transcript_replay_observability_v2.py`
- `tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
- `tests/sir_convert_a_lot/test_runtime_supervision_v2.py`
- `tests/sir_convert_a_lot/test_api_metrics_v2.py`
- `.codex/handoff.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/backlog/tasks/task-363-fast-transcript-formatter-replay-lane-outside-heavy-conversion-queue.md`

Public surfaces affected:

- `POST /v2/convert/jobs?wait_seconds=0` for
  `transcript_json -> transcript_bundle`.
- `GET /v2/convert/jobs/{job_id}`, `/result`, `/artifact`, `/artifacts`, and
  `/artifacts/{artifact_key}` for replay jobs.
- Runtime metrics
  `sir_convert_a_lot_v2_transcript_replay_fast_lane_duration_seconds`.
- Converter/downstream docs for Skriptoteket/HuleEdu replay consumption.

## Findings

- None.

Reviewer conclusions:

- The implementation keeps replay under the existing `/v2/convert/jobs`
  lifecycle and does not add a bespoke downstream endpoint.
- `SERVICE_ROUTE_POLICIES_V2` marks the replay route with
  `dispatches_runtime_jobs=False`, and both submit-time dispatch and the
  runtime supervisor respect that policy, so normal replay does not enter the
  generic heavy conversion worker path or `processing_delay_seconds`.
- The create-job handler persists a normal v2 job, records idempotency, runs
  the replay fast lane synchronously for admitted replay jobs, and returns
  `200` with terminal `succeeded` or `failed` state for `wait_seconds=0`.
  Request-shape validation failures still use the existing v2 error envelope
  before job creation.
- The fast-lane runner reuses `execute_transcript_formatter_replay_job`, so
  malformed canonical JSON, partial transcript state, unknown speaker labels,
  requested-artifact strictness, and no-`transcript_json` replay output remain
  governed by the accepted Tasks 359/360 replay contract.
- Logs and metrics are sanitized: the new completion log includes correlation
  id, job id, static route label, status, and timing only; the Prometheus
  histogram uses bounded `phase` and `status` labels only. Tests cover absence
  of transcript tokens, display-name tokens, API key values, correlation IDs in
  metrics, and `job_id` metric labels.
- The tests are behavioral/public-boundary enough for this slice. The core
  proofs use real FastAPI/TestClient requests, persisted job state, result and
  artifact retrieval, metrics output, and supervisor/route policy behavior.
  The sidecar interaction assertion is contract-relevant because replay must
  not call STT/source-audio execution.
- Docs and handoff are truthful for the producer contract and downstream
  handoff. The downstream contract is sufficient for Skriptoteket PR-0350:
  HuleEdu forwards `/sir-convert/v2/convert/jobs*` without rewriting, and
  Skriptoteket consumes terminal replay jobs plus named
  `transcript_txt`/`transcript_md`/`transcript_vtt`/`transcript_srt` artifacts.
- Line-count guardrails are satisfied for reviewed modules:
  `service_routes_v2.py` 369 lines, `http_routes_jobs_v2.py` 492 lines,
  `runtime_telemetry_v2.py` 415 lines,
  `transcript_formatter_replay_fast_lane_v2.py` 294 lines, and
  `test_transcript_formatter_replay_fast_lane_v2.py` 236 lines.

Residual risk:

- I did not rerun the full implementer-reported `coverage-gate` or formatting /
  typecheck matrix in this review pass. I reran the focused replay/OpenAPI and
  route/supervisor/metrics suites listed below and inspected the claimed full
  gate evidence retained in Task 363 and `.codex/handoff.md`.

## Decision

`approved`.

## Response

No Task 363 implementation changes are requested by this review. The task can
proceed to commit, push, Hemma redeploy, and live verification closeout by the
overseer/implementer. This reviewer did not commit, push, deploy, rebase,
amend, reset, delete data, or revert work.

## Follow-up Actions

1. Overseer/implementer should stage only Task 363-owned files, commit, push,
   redeploy with the approved commit SHA, and retain sanitized live evidence.
1. Skriptoteket PR-0350 may consume the approved producer contract through the
   existing Gateway-forwarded v2 job lifecycle.

## Validation Evidence

Reviewer-rerun commands:

- `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py tests/sir_convert_a_lot/test_transcript_replay_observability_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed with `36 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_api_metrics_v2.py -q`
  passed with `10 passed`.

Implementer-reported gates inspected in Task 363 / handoff:

- Focused replay/OpenAPI proof passed with `36 passed`.
- Neighboring route/supervisor/metrics proof passed with `10 passed`.
- `pdm run coverage-gate` passed with `1716 passed, 6 skipped`, total coverage
  `95.34%`.
- `format-all`, `lint-fix`, `typecheck-all`, `docs-sync`, `docs-validate`,
  `skills-validate`, `handoff-validate`, and `git diff --check` were reported
  green.

Reviewer docs closeout:

- `pdm run docs-sync` refreshed generated docs indexes after the review
  artifact moved from `pending` to `completed`.
- `pdm run docs-validate` passed with `Validated 482 backlog files` and
  `Validated docs=557 rules=11`.
- `pdm run skills-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.

## Completion

Review retained as approved/completed on 2026-06-14.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
