---
type: reference
id: REF-stt-proof-lanes-and-admission-operations
title: STT Proof Lanes and Admission Operations
status: active
created: 2026-06-14
updated: 2026-06-14
owners:
  - platform
tags:
  - stt
  - remote-proof
  - admission
  - hemma
  - operations
links:
  - docs/backlog/tasks/task-365-fence-remote-proof-trust-lane-and-remove-create-job-multipart-replay.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/runbooks/runbook-hemma-service-ops.md
---

## Purpose

Keep the STT proof lanes and create-job admission timing invariants visible for
operators and future agents. This reference exists because production browser
proof can fail at a public edge timeout while the underlying defect is slower
Sir Convert admission, not HuleEdu trust, CORS configuration, or proxy timeout
policy.

## Proof Lane Order

Task 365 STT proof order is fixed:

1. Run local/downstream proof through the fenced Hemma `remote-proof` lane.
1. Diagnose and fix until that proof works.
1. Run native Hemma production proof.
1. Start external/ruthless review only after both live proofs pass.

The local/downstream proof may use a local Skriptoteket browser/dev service,
but it must not require laptop-local Whisper, Pyannote, or other heavy model
workers. Remote hosted model execution stays on Hemma. Production proof must run
natively on Hemma rather than through a local Playwright tunnel to production.

## Runtime Boundaries

`remote-proof` is a non-production Sir Convert lane with separate service names,
profile, data volume, API key surface, and local-auth-integration HuleEdu trust
inputs. It is not public ingress and must not share production trust settings.

Production remains the `hemma-production` trust/runtime lane. Production must
not reference remote-proof trust variables, remote-proof ports, or remote-proof
data volumes.

The hosted STT sidecar is the model-worker lane for both production and
remote-proof proof. Do not add a dedicated remote-proof STT sidecar; that
duplicates heavy model hosting and has already failed under GPU memory pressure.
Remote-proof shares only the sanctioned sidecar input staging volume so the
hosted sidecar can read uploaded media.

## Formatter Replay Recovery Invariant

Remote-proof and production use separate API and worker containers over a shared
job store. The API container may execute deterministic
`transcript_json -> transcript_bundle` formatter replay inline, while the worker
container runs the generic queue supervisor for runtime-dispatched jobs.

The generic worker supervisor must not recover non-dispatching formatter replay
jobs to `queued`. Formatter replay is intentionally marked
`dispatches_runtime_jobs=false`; once such a job is claimed by the API fast
lane, it must terminalize through that fast-lane path as `succeeded` or
fail-closed `failed`. Requeuing it for the generic worker leaves produced
artifacts disconnected from terminal state and downstream products will wait for
downloads that never become available.

Do not explain formatter replay export failures with the retained-job admission
timeout unless the container evidence actually shows slow audio admission. The
formatter recovery symptom has a different concrete signature: persisted
formatter artifacts exist, `/result` and `/artifacts` return `202`, and the job
manifest events show `queued -> running -> running/transcript_replay_fast_lane -> queued` without success or failure fields.

## Admission Timing Invariant

`POST /v2/convert/jobs?wait_seconds=0` for
`audio -> transcript_bundle` is an admission operation. With
`SIR_CONVERT_A_LOT_RUN_JOBS_ON_SUBMIT=0`, it must not perform STT, diarization,
sidecar media probing, or worker execution before returning `202`.

Admission may validate request shape, owner scope, route policy, idempotency,
capacity, and persistence. It must keep retained-job capacity checks bounded.
In particular, capacity checks must not call runtime APIs that run broad
housekeeping for each retained job. Runtime-wide expiry sweeping belongs at
explicit lifecycle boundaries, supervisor loops, startup, or public status reads,
not once per retained job during admission.

The June 14, 2026 production failure had this concrete shape:

- Sir Convert accepted the audio job after about 66 seconds.
- HuleEdu Gateway also completed with `202`.
- `nginx-proxy` returned `504` first while reading Gateway response headers.
- The browser reported a CORS/network failure because the edge-generated timeout
  response did not carry app CORS headers.
- The root cause was slow Sir Convert admission: the audio capacity loop called
  `runtime.get_job()` for retained jobs, and `runtime.get_job()` starts with
  `job_store.sweep_expired()`.

Fixing this class means reducing admission work, not widening the public timeout
budget first.

## Operator Guardrails

- Do not change `proxy_read_timeout`, body-size, trust keys, production ingress,
  or other runtime knobs before proving the upstream root cause and getting
  explicit operator approval.
- Treat browser CORS failures on `/sir-convert/v2/convert/jobs` as symptoms.
  Check edge logs, Gateway logs, and Sir Convert logs for the same UTC window
  before assigning ownership.
- Use bounded logs and state probes. Do not print environment variables broadly;
  query named non-secret settings only.
- When an admission regression is suspected, preserve evidence for:
  - edge response code and timestamp;
  - Gateway downstream status and completion timestamp;
  - Sir Convert request duration and status;
  - retained job count and relevant admission code path;
  - local proof artifact path and native production proof artifact path.
