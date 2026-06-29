---
id: task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2
title: Centralize retryable-failed idempotency reattempts in Service API v2
type: task
status: proposed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/tasks/task-367-remediate-stt-sidecar-idle-unload-fasterwhisper-lifecycle-regression.md
  - docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md
  - docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/sir_convert_a_lot.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - v2
  - idempotency
  - retry
  - service-boundary
  - stt
  - production-remediation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Move retryable-failed idempotency recovery to the Service API v2 boundary so a
matching `Idempotency-Key` plus request fingerprint can never poison all future
submissions with an old terminal retryable failure.

The production incident behind this task was the 2026-06-28 STT sidecar
idle-unload failure. Task 367 fixed the runtime root cause, but the same
Skriptoteket upload still replayed the old failed Sir Convert job until the
runtime idempotency pointer was manually quarantined. That loop is unacceptable
for production: all callers must receive centrally governed retry semantics from
Sir Convert instead of inventing filename changes, idempotency-key salts, or
client-side compatibility wrappers.

Design intent:

- Sir Convert may stay file-backed; this task does not require a database.
- The idempotency record is still service-owned state and must become rich
  enough to distinguish active, successful, retryable-failed, and
  non-retryable-failed attempts.
- Client wrappers must not own this behavior. Task 369 is the immediate
  follow-up that removes the historical CLI-side failed-replay workaround after
  this service fix lands.

## PR Scope

- Change `POST /v2/convert/jobs` replay policy after a matching idempotency
  fingerprint dereferences the active job:
  - `queued`/`running`: replay the active job as today.
  - `succeeded`: replay the successful job as today.
  - `failed` with `failure_retryable=false`: replay the failed job, but expose
    enough failure metadata for callers and operators to understand why it is
    not a service-owned retry candidate.
  - `failed` with `failure_retryable=true`: atomically admit one fresh attempt
    for the same logical request, update/version the idempotency pointer, retain
    lineage to the failed job, and return the newly admitted job.
  - `canceled`: keep strict replay unless a later accepted decision separates
    system-canceled from user-canceled jobs.
- Extend the idempotency store from a single opaque `job_id` pointer to an
  auditable attempt state, for example `active_job_id`, `attempt_count`, and
  previous attempt lineage. Preserve the existing 24h TTL and
  same-key/different-fingerprint `409` behavior.
- Make the reattempt operation race-safe for concurrent identical submissions:
  two callers replaying the same terminal retryable failure must converge on
  one new active attempt.
- Add explicit JSON response metadata for idempotency state; do not rely on
  `X-Idempotent-Replay` alone because Gateway/browser callers may not see it.
  The body must distinguish replayed jobs from service-admitted reattempts and
  include sanitized previous-attempt status, retryability, and job lineage.
- Preserve fail-closed artifact behavior: failed/canceled jobs must not expose
  partial transcript artifacts, and a new reattempt must not duplicate
  transcript segments, diarization windows, or artifacts.
- Update normative contracts and downstream docs for the new central replay
  policy.
- Do not change API authentication, Gateway trust, upload limits, STT runtime
  model selection, sidecar health semantics, retention TTLs, or CPU fallback
  policy.

## Deliverables

- [ ] Red-first create-job contract test proving the current bug: a matching
  idempotency replay of a terminal `failed` job with `retryable=true`
  returns the old failed `job_id` instead of admitting a new attempt.
- [ ] Service-owned idempotency attempt state with race-safe reattempt
  admission for terminal retryable failures.
- [ ] Public JSON response contract for idempotency replay/reattempt metadata,
  with headers kept accurate but non-authoritative.
- [ ] Focused tests for succeeded, active, non-retryable failed, retryable
  failed, canceled, fingerprint mismatch, missing old job, and concurrent
  replay behavior.
- [ ] Contract docs synchronized:
  `multi_format_conversion_service_api_v2.md`,
  `audio-transcription-service-api-artifact-contract.md`,
  `downstream_integration_contract_v2.md`, and CLI docs only insofar as
  they point to the service-owned policy before Task 369 removes the old
  CLI workaround.
- [ ] Independent retained review before completion.
- [ ] Hemma live proof after deploy showing retryable-failed replay admits a
  new attempt and succeeds without manual idempotency deletion,
  quarantine, filename changes, or caller-side idempotency-key salting.

## Acceptance Criteria

- [ ] Existing strict idempotency behavior remains unchanged for active jobs,
  successful jobs, non-retryable failed jobs, canceled jobs, and
  same-key/different-fingerprint conflicts.
- [ ] A terminal `failed` job whose manifest records `failure_retryable=true`
  is not replayed forever. The next identical create-job call admits a
  fresh attempt, records lineage to the failed attempt, and returns the new
  active `job_id`.
- [ ] The idempotency store records enough state to audit which job is active
  for the logical request and which retryable failed jobs were superseded.
- [ ] Reattempt admission is atomic under the idempotency scope: concurrent
  identical replay requests after a retryable failure create at most one
  fresh job.
- [ ] Callers can determine from the JSON body whether a response is a strict
  replay, a fresh first admission, or a service-owned reattempt after a
  retryable terminal failure.
- [ ] Result and artifact endpoints preserve original failure retryability in
  their error details where that information is service-owned and safe to
  expose.
- [ ] No caller compatibility wrapper is added. If a downstream gap appears,
  stop and record it as a consumer contract alignment task rather than
  moving retry policy out of Sir Convert.
- [ ] Red/green evidence includes the same focused command failing before the
  implementation and passing after it.
- [ ] Close-out includes live Hemma evidence:
  - deployed service revision matches the implementing commit;
  - a retained retryable failed idempotency record exists before the proof;
  - re-submitting the same payload/spec/key through the production Service API
    path returns a different new `job_id` without deleting or quarantining the
    old pointer;
  - the new job reaches `succeeded`;
  - result and `transcript_json` artifact fetch succeed for the new job;
  - bounded logs show no new poisoned replay loop for the proof interval.

## Red-First Test Plan

First failing proof:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py::test_retryable_failed_idempotency_replay_admits_new_attempt -q
```

The test must fail on current code because `POST /v2/convert/jobs` returns the
old terminal failed job with `X-Idempotent-Replay: true`.

Green focused proof should include:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q
```

Broader close-out gates:

```bash
pdm run format-all
pdm run lint-fix
pdm run typecheck-all
pdm run coverage-gate
pdm run docs-sync
pdm run docs-validate
pdm run skills-validate
pdm run handoff-validate
git diff --check
```

## Live Verification Gate

Before this task can be marked completed, run a retained Hemma proof against
the deployed service. The proof must use a content-safe audio fixture and must
not repair state by deleting, editing, or quarantining idempotency files.

Required evidence bundle:

- deployment report with expected, remote, and `/readyz` service revisions;
- pre-proof manifest for the retryable failed attempt and its idempotency
  lineage;
- create-job response for the identical retry showing a new active attempt;
- terminal success manifest for the new job;
- result and named `transcript_json` artifact fetch proof;
- bounded service/gpu_worker/stt_sidecar log scan for the proof interval.

## Stop Conditions

- Stop before changing `canceled` replay semantics without an accepted
  decision distinguishing user-canceled from system-canceled attempts.
- Stop before introducing a database or durable queue migration; propose a new
  architecture task if file-backed atomic state is insufficient.
- Stop before adding caller-side reattempt logic in CLI, Gateway, Skriptoteket,
  or adapter clients. This task exists to keep retry policy centralized.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
