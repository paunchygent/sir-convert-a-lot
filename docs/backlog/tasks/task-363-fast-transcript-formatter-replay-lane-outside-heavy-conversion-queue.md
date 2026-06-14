---
id: task-363-fast-transcript-formatter-replay-lane-outside-heavy-conversion-queue
title: Fast transcript formatter replay lane outside heavy conversion queue
type: task
status: completed
priority: high
created: '2026-06-14'
last_updated: '2026-06-14'
related:
  - docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md
  - docs/backlog/tasks/task-359-define-transcript-speaker-overlay-formatter-replay-contract.md
  - docs/backlog/tasks/task-360-implement-transcript-speaker-overlay-formatter-replay-artifacts.md
  - docs/backlog/reviews/review-48-ruthless-review-of-task-363-fast-transcript-formatter-replay-lane.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0350-st-21-08-product-owned-transcript-replay-export-boundary.md
labels:
  - transcript
  - formatter-replay
  - latency
  - service-api-v2
  - queue-boundary
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make `transcript_json -> transcript_bundle` replay a bounded fast producer lane
instead of a generic heavy conversion job that can sit behind upload, STT, PDF,
or inline `wait_seconds` behavior before the caller receives usable export
state.

This route renders deterministic TXT/Markdown/WebVTT/SRT artifacts from saved
canonical transcript JSON plus display-name overlays. It must not behave like a
source-media conversion. A product export click should either get completed
formatter artifacts within the small replay budget or get an explicit producer
latency failure/progress state; it must not hide behind the normal heavy job
queue.

## PR Scope

- Add a producer-owned fast replay execution contract for
  `source.format=transcript_json` and
  `conversion.output_format=transcript_bundle`.
- Keep the existing strict JobSpec, `transcript_formatter_replay_v1` options,
  closed artifact set, overlay validation, and `transcript_replay_bundle`
  result/manifest semantics.
- Remove replay dependence on the generic heavy conversion queue for normal
  product replay. Acceptable implementation shapes are a synchronous bounded
  replay path or a dedicated fast-lane queue with its own capacity and
  admission metrics; generic STT/PDF queue contention is not acceptable.
- Ensure `wait_seconds=0` create/admission returns promptly for replay and does
  not run or wait on unrelated heavy work before returning a job id or terminal
  fast-lane result.
- Add latency telemetry for replay admission and replay execution using
  sanitized route/job metadata only.
- Provide a smoke/proof surface that downstream products can run before browser
  proofs: submit replay, get terminal result or explicit fast-lane failure,
  list named artifacts, fetch at least one artifact, and verify overlay labels.
- Do not add a bespoke downstream-only endpoint, API-key identity fallback,
  self-signed product identity, CPU fallback, loose parsing, `Any`, casts, type
  ignores, or compatibility shims.

## Deliverables

- [x] Fast replay producer path for `transcript_json -> transcript_bundle`.
- [x] Route/admission latency instrumentation for replay.
- [x] Focused behavior tests proving the new fast replay contract returns
  overlay-aware artifacts within the accepted replay budget.
- [x] Downstream-safe smoke command or test fixture for the Skriptoteket
  product-owned export boundary.
- [x] Updated docs/handoff describing replay as deterministic formatter work,
  not heavy conversion work.

## Acceptance Criteria

- [x] With a valid canonical transcript fixture and speaker overlays, replay
  produces requested TXT/Markdown/WebVTT/SRT artifacts through the producer
  contract without entering the generic heavy conversion queue.
- [x] Replay admission and execution are owned by the new fast replay contract,
  not by browser foreground orchestration.
- [x] `POST /v2/convert/jobs?wait_seconds=0` for replay returns a job id or
  terminal replay result without waiting on unrelated conversion workers.
- [x] Replay execution records bounded, sanitized admission/execution timing
  evidence and never logs transcript text, utterances, speaker display
  names, source content, credentials, or signed headers.
- [x] Existing malformed transcript, partial diarization, unknown speaker
  label, duplicate overlay, unrequested artifact, and missing-artifact
  fail-closed behavior remains covered.
- [x] The downstream smoke proves submit/result/manifest/artifact fetch with
  overlay display names and no canonical fallback labels.
- [x] No downstream product is required to run a browser-owned submit/poll/
  artifact-download/base64-complete saga to use replay.

## Test Requirements

- [x] Focused contract tests for successful fast replay output, result
  metadata, manifest entries, and named artifact downloads.
- [x] Bounded smoke proof that the replay contract completes within the
  accepted replay budget for the canonical fixture.
- [x] Focused replay contract tests for success and fail-closed cases.
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Implementation Evidence

- Added a replay-only fast-lane runner in
  `scripts/sir_convert_a_lot/infrastructure/transcript_formatter_replay_fast_lane_v2.py`.
  It claims only `transcript_json -> transcript_bundle` jobs, stamps a
  `transcript_replay_fast_lane` running stage, reuses
  `execute_transcript_formatter_replay_job`, terminalizes the normal Service
  API v2 job record, and never enters the generic worker/supervisor path.
- `SERVICE_ROUTE_POLICIES_V2` now marks replay as
  `dispatches_runtime_jobs=false`, while `POST /v2/convert/jobs` runs replay
  immediately after normal job persistence and idempotency recording.
- `wait_seconds=0` replay now returns terminal state for admitted replay jobs:
  `succeeded` with result/manifest/named artifacts for valid replay and
  `failed` for fail-closed replay execution errors. Request-shape validation
  still returns the existing v2 error envelope before job creation.
- Added bounded replay fast-lane telemetry metric
  `sir_convert_a_lot_v2_transcript_replay_fast_lane_duration_seconds` with
  static `phase` and `status` labels plus content-safe completion logs with
  correlation id, job id, route, status, admission milliseconds, and execution
  milliseconds.
- Red-first proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py -q`
  first failed with `4 failed` because replay returned `202 Accepted`/queued
  for `wait_seconds=0` and no fast-lane timing telemetry existed.
- Focused green replay/OpenAPI proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py tests/sir_convert_a_lot/test_transcript_replay_observability_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed with `36 passed`.
- Neighboring route/supervisor/metrics proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_api_metrics_v2.py -q`
  passed with `10 passed`.
- Coverage-gate proof:
  `pdm run coverage-gate` passed with `1716 passed, 6 skipped`; required
  coverage `90.0%` was reached at `95.34%`.
- Downstream-safe smoke proof command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py::test_downstream_replay_fast_lane_smoke_fetches_overlay_artifact -q`.

## Closeout Gate

Implementation, local validation, independent Review 48, commit/push, and
Hemma deploy/live verification are complete. The implementation specialist did
not self-approve Review 48.

Post-review closeout readiness commands:

- Commit/push after reviewer approval and final status check:
  `git status --short`, then stage only Task 363-owned files, commit, and push.
- Hemma deploy/live verification after push, using the approved commit SHA and
  a redacted operator-provided API key:
  `pdm run hemma-deploy-and-verify --expected-revision <approved-sha> --lane host --api-key <redacted>`.
- Downstream replay smoke remains:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py::test_downstream_replay_fast_lane_smoke_fetches_overlay_artifact -q`.

Deploy readiness notes:

- The production API container is enqueue-only for heavy conversion work, but
  this replay route runs deterministic formatter replay in the Service API v2
  admission process and should not require GPU-worker capacity.
- Do not change GPU/offload policy or add CPU fallback for this task.
- Do not record API keys or transcript/display content in retained deploy
  evidence. Keep deploy proof to revision parity, readiness, metrics, terminal
  replay job state, manifest/artifact availability, and overlay-label behavior.

Closeout evidence:

- Feature branch commit:
  `015fb694c9214a7f69675d3878cf7c16cb16862f`.
- Merge commit on `main`:
  `e2bf342110571fa07e082b4bb340cac5ca511f90`.
- Feature branch and `main` were pushed to `origin`.
- Hemma deploy/live verification command:
  `pdm run hemma-deploy-and-verify --expected-revision e2bf342110571fa07e082b4bb340cac5ca511f90 --lane host`.
- Hemma deploy report:
  `build/verification/hemma-deploy-verify/report.md`.
- Deploy status: `passed`; `remote_revision` and `service_revision` both
  matched `e2bf342110571fa07e082b4bb340cac5ca511f90`.
- Deploy checks passed: expected revision parity, service revision parity,
  structured LLM reachability/microprobe, v2 live smoke, metrics safety scan,
  public HTTPS reserved route, TLS certificate, nginx public host registration,
  and default-host reserved placeholder.

## Notes

This task intentionally does not solve the Skriptoteket browser-saga cleanup by
itself. Skriptoteket `PR-0350` owns removing the browser-owned orchestration
anti-pattern and consuming this producer fast-lane contract through a
product-owned workflow boundary.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
- [x] Independent Review 48 approved and retained
- [x] Approved changes committed and pushed
- [x] Hemma redeploy completed
- [x] Live deploy evidence retained without secrets or transcript content
