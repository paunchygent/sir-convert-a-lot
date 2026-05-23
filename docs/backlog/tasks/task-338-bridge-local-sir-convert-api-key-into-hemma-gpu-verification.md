---
id: 'task-338-bridge-local-sir-convert-api-key-into-hemma-gpu-verification'
title: 'Bridge local Sir Convert API key into Hemma GPU verification'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-05-23'
last_updated: '2026-05-23'
related:
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - scripts/devops/run-hemma.sh
  - scripts/devops/verify-hemma-gpu-runtime.sh
  - tests/sir_convert_a_lot/test_run_hemma_wrapper.py
  - tests/sir_convert_a_lot/test_verify_hemma_gpu_runtime_wrapper.py
labels:
  - hemma
  - devops
  - gpu
  - verification
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the repeated operator/session discovery that `hemma-verify-gpu-runtime`
needs a locally available `SIR_CONVERT_A_LOT_V2_API_KEY` passed manually as
`--api-key` when launched from a client machine. The verifier should reuse the
local key loaded by `run-local-pdm` while preserving the Task 76 key-resolution
contract and avoiding accidental key forwarding to unrelated Hemma commands.

## PR Scope

- Add an explicit `run-hemma` opt-in that forwards only
  `SIR_CONVERT_A_LOT_V2_API_KEY` into the remote script stream when
  `SIR_CONVERT_A_LOT_RUN_HEMMA_FORWARD_API_KEY=1`.
- Update `verify-hemma-gpu-runtime.sh` local mode to enable that opt-in when a
  local `SIR_CONVERT_A_LOT_V2_API_KEY` exists and the caller did not already
  pass `--api-key`.
- Keep explicit `--api-key` precedence untouched.
- Do not write API keys to docs, artifacts, logs, or routine command output.

## Deliverables

- [x] `run-hemma` supports whitelisted, opt-in API-key forwarding for verifier
      workflows.
- [x] `hemma-verify-gpu-runtime` works from a local session without rediscovering
      or manually passing `--api-key` when `.env` provides
      `SIR_CONVERT_A_LOT_V2_API_KEY`.
- [x] Regression tests cover default non-forwarding, opt-in forwarding, and the
      verifier wrapper's no-secret-in-argument behavior.

## Acceptance Criteria

- [x] Ordinary `run-hemma` calls do not forward `SIR_CONVERT_A_LOT_V2_API_KEY`
      unless the new opt-in flag is set.
- [x] The verifier wrapper enables the opt-in only when a local key is present
      and no explicit `--api-key` argument was supplied.
- [x] Focused tests pass for `test_run_hemma_wrapper.py` and
      `test_verify_hemma_gpu_runtime_wrapper.py`.
- [x] Host-lane GPU verification passes on Hemma prod using the default local
      launcher form.

## Evidence

- `pdm run ruff format tests/sir_convert_a_lot/test_run_hemma_wrapper.py
  tests/sir_convert_a_lot/test_verify_hemma_gpu_runtime_wrapper.py`
- `pdm run ruff check tests/sir_convert_a_lot/test_run_hemma_wrapper.py
  tests/sir_convert_a_lot/test_verify_hemma_gpu_runtime_wrapper.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_run_hemma_wrapper.py
  tests/sir_convert_a_lot/test_verify_hemma_gpu_runtime_wrapper.py -q`
  passed with 15 tests.
- `pdm run run-local-pdm hemma-verify-gpu-runtime` passed from the client
  checkout without `--api-key`. Remote report:
  `build/verification/task-76-hemma-deploy-verify/gpu-runtime/gpu_runtime_report.json`.
  The report recorded host lane `28085`, service profile `prod`,
  `runtime_kind=rocm`, `torch_version=2.10.0+rocm7.1`,
  `acceleration_used=cuda`, `gpu_busy_peak=17`, and succeeded status.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
