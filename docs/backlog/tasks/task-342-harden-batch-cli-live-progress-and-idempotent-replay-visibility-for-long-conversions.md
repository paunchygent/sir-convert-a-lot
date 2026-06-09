---
id: task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions
title: Harden batch CLI live progress and idempotent replay visibility for long conversions
type: task
status: in_progress
priority: high
created: '2026-06-04'
last_updated: '2026-06-05'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/tasks/fix-01-harden-cli-timeout-handling-for-long-running-background-jobs.md
  - docs/backlog/tasks/task-67-detect-stalled-conversions-separately-from-active-long-running-jobs.md
  - docs/backlog/tasks/task-69-add-page-level-progress-fields-to-v2-jobs-api.md
  - docs/backlog/tasks/task-343-investigate-pdf-conversion-decision-logic-and-gpu-cpu-performance-attribution.md
  - docs/backlog/tasks/task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking.md
  - docs/backlog/tasks/task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs.md
  - docs/converters/sir_convert_a_lot.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - scripts/sir_convert_a_lot/interfaces/cli_app.py
  - scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py
  - scripts/sir_convert_a_lot/interfaces/cli_manifest_writer_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py
labels:
  - cli
  - batch
  - progress
  - idempotency
  - observability
  - long-pdf
---

PR-sized execution unit; may be linked to a story or standalone.

## User Intent and Goal Alignment

The user intent is operational trust during real conversion work, not cosmetic
console output.

The implementation must serve these goals:

- Keep conversions alive unless the operator explicitly cancels them. A local
  client that stops, times out, or is interrupted must not imply the service job
  has been aborted.
- Make progress visible while it matters: after submit, during queue/running
  phases, while partial artifacts/checkpoints exist, and when a job appears
  stalled.
- Let the user answer "what is happening right now?" from the normal CLI/output
  artifacts without SSHing into Hemma or inspecting container internals.
- Make duplicates and idempotent replays explainable. If the service reuses an
  existing job, the user should see that. If a new job is created for the same
  file, the persisted evidence should explain which request identity differed.
- Preserve batch continuity. One slow file should not make the whole batch look
  silent, lost, or unsubmitted.
- Preserve deterministic auditability. The manifest must be useful during the
  run, after an interrupt, and after completion.
- Keep user-facing signals actionable but safe: no secrets, upload contents,
  generated artifact contents, prompts, model responses, or unbounded metric
  labels.

This task is successful only if a user running a long PDF batch can tell, from
the CLI and manifest/status artifacts alone, whether the system is queued,
actively progressing, replaying an existing job, stalled, failed, canceled, or
ready for artifact download.

## Current CLI Gaps

1. Batch progress is hidden behind a blocking per-file call.

   - Current behavior: `submit_service_route_batch_v2` loops sequentially and
     waits inside `convert_upload_to_artifact` for one file at a time.
   - User impact: one long or replayed job makes the batch look frozen, even
     when the worker is progressing normally.
   - Recommendation: split submit, progress observation, terminal wait, and
     artifact download into explicit client operations that the CLI can surface.

1. The manifest is written too late.

   - Current behavior: `write_cli_manifest_v2` runs after the batch submission
     function returns.
   - User impact: during a long wait or local interruption, there is no durable
     job id trail in the output directory.
   - Recommendation: write an incremental manifest or manifest state file as
     soon as each job id is known, then atomically refresh it on meaningful
     status transitions.

1. Submission and replay are not visible as first-class user events.

   - Current behavior: the CLI prints conversion success or timeout/running
     outcomes, but not a submitted/replayed state immediately after the service
     accepts or reuses a job.
   - User impact: duplicate/idempotent behavior is hard to interpret; a reused
     running job can look like a stall.
   - Recommendation: emit submitted/replayed lines with source label, job id,
     target path, replay flag, and retry mode.

1. Polling progress is not streamed to the operator.

   - Current behavior: API progress exists, but the high-level CLI path does not
     periodically show page counters, heartbeat freshness, ETA, or partial
     availability.
   - User impact: healthy slow work and stalled work feel similar.
   - Recommendation: add bounded periodic progress output using existing v2
     `job.progress` fields and existing partial/checkpoint endpoints.

1. Formula-heavy decisions are not visible to the operator.

   - Current behavior: after Task 344, the service can distinguish formula VLM
     generation calls, stop criteria, and source Markdown quality failures, but
     the normal CLI/manifest path does not explain whether formula VLM was
     skipped, advisory, accepted, rejected, or still running.
   - User impact: a formula-heavy born-digital PDF can still look like an
     unexplained stall or an unexplained quality failure.
   - Recommendation: consume Task 345 formula-authority metadata and render it
     as safe progress/result reasons without exposing raw backend flags,
     prompts, crops, or generated formula contents. Task 342 must not parse
     PDFs, inspect formula crops, classify source-layer evidence, or duplicate
     formula-authority policy; those are Task 345 responsibilities.

1. Interrupts and local client termination lose context.

   - Current behavior: known running jobs are only represented after a handled
     client error such as poll-window expiry.
   - User impact: a local stop can leave the user unsure whether Hemma is still
     converting.
   - Recommendation: handle `KeyboardInterrupt` and local exceptions by writing
     known submitted/running entries before exiting.

1. There is no normal post-run status/recovery workflow.

   - Current behavior: docs tell users to call status/result/artifact endpoints,
     but the CLI does not provide a convenient manifest/job-id status surface.
   - User impact: users resort to ad hoc curl, SSH, or container inspection.
   - Recommendation: add `convert-a-lot status` or equivalent to inspect a job
     id or manifest, refresh entries, and download completed artifacts.

1. Duplicate-looking jobs are not explainable from persisted job evidence.

   - Current behavior: service idempotency is enforced, but persisted job
     manifests do not expose safe idempotency key/fingerprint/replay metadata.
   - User impact: two jobs for the same filename cannot be explained without
     reconstructing request details externally.
   - Recommendation: persist safe request identity diagnostics and replay
     metadata, without secrets or payload contents.

1. Batch continuity semantics are underdefined.

   - Current behavior: sequential processing is simple but creates a perception
     that later files are unsubmitted while a slow earlier file runs.
   - User impact: the user cannot distinguish "next files not submitted yet" from
     "batch stalled."
   - Recommendation: make the CLI explicitly report batch position and decide
     whether to keep sequential execution with strong visibility or move to a
     bounded submit-ahead queue.

## Recommendations

1. Implement the progress-visible sequential path first.

   - This is the safest remediation because it preserves current service load,
     idempotency behavior, and GPU concurrency assumptions while closing the
     immediate blindness.

1. Make incremental manifesting non-optional by default.

   - The manifest is the audit surface; it should be trustworthy during the run,
     not only after normal completion.

1. Add a CLI status/recover command as the second slice.

   - Once the manifest carries running jobs, users need a first-class way to
     refresh and fetch results without resubmitting source files.

1. Treat submit-ahead batch queuing as a product decision, not an implicit fix.

   - Submitting every file up front improves visibility and allows queue
     position reporting, but it changes service queue behavior and operator
     expectations. It should follow only after the visible sequential path is
     proven.

1. Keep idempotency conservative.

   - Do not auto-rerun non-terminal jobs. Show replay state, progress, and stale
     classification; require `--new-job` or another explicit operator action for
     duplicate fresh submissions.

## Product Decision Questions

1. Should folder batches remain sequential by default after visibility is fixed,
   or should the CLI submit all files up front with bounded queueing?

   - Recommendation: keep sequential as default for the first remediation slice;
     add submit-ahead later behind an explicit option if desired.

1. What is the desired default progress cadence for long jobs?

   - Recommendation: print immediately on submit/replay, then every 30 seconds
     or when page progress changes, whichever comes first.

1. Should interrupted local CLI runs exit non-zero even when the service job is
   safely running and recorded?

   - Recommendation: exit non-zero for interruption, but write a manifest entry
     with `status: running` and an explicit `error_code` such as
     `client_interrupted`.

1. Should successful idempotent replays be visually distinct in the final
   manifest?

   - Recommendation: preserve the existing required fields and add optional safe
     metadata if the manifest contract allows it; otherwise record replay state
     in a companion state file to avoid breaking consumers.

1. Should the CLI download partial artifacts automatically during long waits?

   - Recommendation: show partial availability by default, but only download
     partial artifacts when requested or when a job exits running/stalled.

## Objective

Remove the remaining operator blind spot for long-running service-backed CLI
batches. A batch conversion must persist and display enough progress to make a
slow, queued, idempotent replay, or stalled job distinguishable without ad hoc
container inspection.

This task is a corrective extension to the completed long-job timeout/progress
work. The API already exposes progress fields and the CLI already records
running jobs after the max poll window is exceeded, but the current batch flow
blocks inside one source file and only writes the batch manifest after the
entire sequential loop returns.

## Current Incident Evidence

- A 2026-06-04 HuleEduOS research conversion batch appeared stalled after the
  first file because the second file stayed inside the per-file submit/poll
  path for a long time.
- The worker-side job was still healthy:
  - `job_id`: `jobv2_63a3d3533e154af1887a61f31d`
  - `status`: `running`
  - `source_filename`:
    `efficient-llm-comparative-assessment-a-product-of-experts-framework-for-pairwise-comparisons--df95b4a730.pdf`
  - `progress`: 8 of 21 pages, 38.095%, stage `converting`
  - `artifacts/partial.md` and chunk checkpoints existed.
- The CLI did not surface the job id, progress counters, partial artifact
  presence, heartbeat age, or idempotent replay state while waiting.
- A prior successful job for the same filename existed, but persisted job
  manifests did not include idempotency key, request fingerprint, or replay
  metadata, making duplicate-looking jobs hard to explain from durable evidence.

## 2026-06-04 Runtime Diagnosis and Slice

Read-only Hemma inspection showed that lifecycle-log grep was misleading: the
candidate "running" matches were historical event entries, while the top-level
job manifests had already reached `succeeded`.

Important findings:

- `jobv2_9daddbc98ee8457ba7e0034dd5` was a 1-page job that appeared to take
  47 minutes, but the events showed it waited queued behind a slow job and then
  converted in about 6 seconds.
- `jobv2_63a3d3533e154af1887a61f31d` was the real slow job: 21 pages, about
  64 minutes wall-clock, with page progress advancing only at chunk commits.
- The service heartbeat existed, but the CLI did not stream progress while
  blocking in the per-file `convert_upload_to_artifact` call.
- The CLI therefore could distinguish fresh vs stale only after the poll window
  elapsed; it could not answer "what is happening now?" during the wait.

Implemented first remediation slice:

- Extracted v2 upload-to-artifact orchestration from the main HTTP client into
  `interfaces.http_client_v2_conversion`.
- Added a progress callback to v2 polling without increasing request volume
  beyond the existing status polling.
- Added throttled CLI progress messages that emit on progress changes and
  periodically while the same long-running state remains active.
- Preserved retry/idempotent replay behavior and existing timeout
  classification.

Still open:

- Incremental manifest/state-file writing immediately after job id acquisition.
- First-class CLI status/recover command for manifest/job ids.
- Safe idempotency/replay diagnostics in persisted evidence.
- Product decision on submit-ahead queueing vs visible sequential execution.

## PR Scope

- Add a progress-aware per-file submission path for the service-backed CLI that
  emits structured operator messages when a job is submitted, replayed, running,
  progressing, queued, stalled, succeeded, failed, or canceled.
- Persist a deterministic incremental batch manifest or companion state file
  immediately after each job id becomes known and after each meaningful status
  transition.
- Ensure `KeyboardInterrupt`, local client termination, and poll-window expiry
  preserve known job ids and running status entries before exit.
- Expose idempotent replay state and safe request identity diagnostics in
  client-visible outcomes and/or persisted job metadata without logging secrets,
  API keys, upload bytes, file contents, or dynamic identifiers as metric
  labels.
- Keep service idempotency semantics intact:
  - terminal `failed`/`canceled` replay may auto-rerun in `auto` mode,
  - terminal `succeeded` replay downloads the existing artifact and proceeds,
  - non-terminal replay keeps polling the existing job unless the operator
    explicitly requests `--new-job`.
- Add a CLI status/resume-friendly surface for existing batch manifests or job
  ids so a user can inspect completion later without resubmitting the folder.
- Update converter docs/runbook guidance for long-running batch observation.

## Out of Scope

- Canceling, pruning, or force-rerunning the active Hemma job from the current
  incident.
- Changing GPU-first policy or adding silent CPU fallback.
- Changing the core conversion algorithm, OCR backend, or chunking strategy.
- Adding high-cardinality metric labels such as job id, filename, or
  correlation id.

## Deliverables

- [ ] CLI emits an immediate submitted/replayed line per file with `job_id`,
  source label, target path, and idempotent replay flag when applicable.
- [ ] CLI emits bounded periodic progress lines while waiting, including status,
  stage, pages processed/total, percent, pages per minute, ETA, heartbeat age,
  and partial artifact/checkpoint availability when present.
- [ ] Batch manifest persistence is incremental and atomic enough that a killed
  local client leaves a valid manifest/state artifact with known jobs.
- [ ] Interrupt handling writes known running entries before propagating the
  interrupt outcome.
- [ ] Client/service persisted evidence can explain duplicate-looking jobs by
  exposing safe idempotency/replay diagnostics.
- [ ] A status command or equivalent documented workflow can poll a previous
  manifest/job id and download completed artifacts without submitting a new
  conversion request.
- [ ] Converter docs describe active-running, stalled, idempotent replay, and
  existing-artifact behaviors using the current v2 taxonomy.

## Acceptance Criteria

- [ ] A long-running second file in a multi-file batch produces visible progress
  and a persisted job id before the file reaches terminal state.
- [ ] A batch interrupted after job submission preserves a manifest entry with
  `status: running`, `job_id`, and the current non-terminal error/status code.
- [ ] A non-terminal idempotent replay is displayed as an existing running job,
  not as an unexplained hang or a duplicate fresh submission.
- [ ] A terminal successful idempotent replay downloads the existing artifact,
  writes a succeeded manifest entry, and proceeds to the next file.
- [ ] A stale non-terminal job is classified with the existing `job_timeout`
  semantics and visible stale/heartbeat details.
- [ ] Manifest schema remains deterministic and backward compatible for existing
  required fields:
  - `source_file_path`
  - `job_id`
  - `status`
  - `output_path`
  - `error_code`
- [ ] Observability additions preserve the redaction policy and bounded-cardinality
  metrics contract.
- [ ] Focused CLI/client/API tests prove behavior through public boundaries, not
  private helper-call assertions.

## Red-First Test Plan

1. Add a CLI route-submission test with a fake client that returns a submitted
   non-terminal job and progress snapshots before success. The test should fail
   until the CLI emits submitted/progress messages and persists a valid
   incremental manifest before the final artifact is available.
1. Add a CLI interrupt test that raises `KeyboardInterrupt` after submission and
   proves the output directory contains a manifest/state file with the known
   running job id.
1. Add an HTTP client test for non-terminal idempotent replay that proves replay
   metadata is preserved and status/progress can be reported without auto-rerun.
1. Add an API/job-store contract test that safe idempotency diagnostics are
   persisted or exposed without leaking API keys or payload contents.
1. Add a CLI status/resume test that starts from an existing manifest/job id,
   polls status, downloads a succeeded artifact, and updates the manifest
   without resubmitting the source upload.

## Implementation Plan

1. Split `convert_upload_to_artifact` into lower-level typed operations:
   submit, classify replay, observe progress, wait, and download. Keep the
   current high-level method as a thin compatibility wrapper.
1. Introduce a small progress event model in the CLI boundary so submission,
   replay, polling, partial availability, terminal success, and error states
   are represented consistently.
1. Move manifest persistence behind an incremental writer with atomic replace
   semantics and deterministic sorting. Preserve the final
   `sir_convert_a_lot_manifest.json` contract.
1. Refactor `submit_service_route_batch_v2` so the per-file loop records state
   immediately and can recover known entries on interrupt or poll-window exit.
1. Add replay diagnostics to safe client outcome models and persisted job
   records, using non-secret request fingerprint/idempotency metadata.
1. Add `convert-a-lot status` or equivalent command coverage for manifest/job-id
   observation and completed artifact download.
1. Update `docs/converters/sir_convert_a_lot.md` and the v2 API contract if new
   fields or CLI commands are added.

## Validation Commands

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_convert_a_lot_cli.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop before changing service idempotency semantics in a way that would create
  duplicate jobs for ordinary retries.
- Stop before logging API keys, signed grants, uploaded file contents, generated
  artifact contents, prompts, model responses, or student data.
- Stop before adding job id, filename, correlation id, or request fingerprint as
  Prometheus metric labels.
- Stop before canceling or force-rerunning active Hemma conversions without an
  explicit operator command.

## Checklist

- [ ] Implementation complete
- [x] Validation complete for first progress-callback slice
- [x] Docs updated for first progress-callback slice
