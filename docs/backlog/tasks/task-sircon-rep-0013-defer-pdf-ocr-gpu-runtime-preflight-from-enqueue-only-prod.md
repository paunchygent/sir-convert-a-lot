---
type: task
id: TASK-SIRCON-REP-0013
title: Defer PDF OCR GPU runtime preflight from enqueue-only prod API to GPU worker
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- '`gpu_required` PDF/OCR create-job admission succeeds on an enqueue-only runtime
  with `gpu_available=false`, `run_jobs_on_submit=false`, and `enable_supervisor=false`.'
- '`gpu_required` PDF/OCR create-job admission still fails on a runtime that will
  execute locally when `gpu_available=false` and CPU fallback is not allowed.'
- Hemma prod conversion through the tunnel succeeds with `acceleration_policy=gpu_required`,
  processed by the private GPU worker.
- No CPU fallback is introduced.
retired_ids:
- task-339-defer-pdf-ocr-gpu-runtime-preflight-from-enqueue-only-prod-api-to-gpu-worker
---
## Context

Source record: docs/backlog/tasks/task-339-defer-pdf-ocr-gpu-runtime-preflight-from-enqueue-only-prod-api-to-gpu-worker.md

### Objective

> Fix the Hemma production PDF/OCR submission path where the public prod API
> container is intentionally enqueue-only and has `SIR_CONVERT_A_LOT_GPU_AVAILABLE=0`,
> but create-job OCR preflight rejects `gpu_required` before the private
> `sir_convert_a_lot_gpu_worker` can claim and execute the job.

## Impact And Escalation

## Decision And Assumption Ledger

## Plan

## Implementation Steps

## Proof

### Deliverables

> - [ ] OCR preflight can distinguish local execution/runtime-probe enforcement
>   from enqueue-only admission.
> - [ ] `ServiceRuntimeV2.create_job` passes the correct enforcement mode from
>   runtime config.
> - [ ] Regression tests prove enqueue-only prod API admission does not reject
>   `gpu_required`, while executing runtimes still fail when GPU is missing.

## Validation

## Stop Conditions

## Lessons Learned

## Notes

### PR Scope

> - Keep the front-door prod API as a CPU/no-device enqueue lane:
>   `RUN_JOBS_ON_SUBMIT=0`, `ENABLE_SUPERVISOR=0`, no ROCm devices.
> - Keep the private GPU worker as the execution lane:
>   `ENABLE_SUPERVISOR=1`, shared prod data volume, ROCm devices, GPU runtime
>   validation at execution time.
> - Change create-job OCR preflight so enqueue-only runtimes still validate
>   static OCR engine/language/model configuration but defer local GPU runtime
>   probing to the worker.
> - Preserve fail-closed GPU behavior when the same runtime will execute jobs
>   directly or through its own supervisor.

## Readiness

## Closeout
