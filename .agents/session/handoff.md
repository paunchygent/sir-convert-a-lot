# Session Handoff

## Current State

- Active epic: Epic 08 Qwen Swedish language expansion on Hemma.
- Active story: Story 26 remains in progress for Task 101 throughput and
  numerical-stability closure.
- Active remediation task: `T186`
  (`docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md`).
- Delivered architecture lane: Story 28 / `T187-T191` is complete and now
  governs all future Qwen control-plane/runtime changes.

## What Landed

- `qwen-train diagnose-non-finite` now exists as the canonical detached
  diagnostic surface.
- Fast ML quality gates now exist for the Qwen lane:
  - `pdm run test-ml`
  - `pdm run typecheck-ml`
  - `test-ml` uses `pytest --import-mode=importlib` so duplicate test
    basenames under `tests/sir_convert_a_lot/ml/qwen/` collect safely from the
    repo root
- Optimizer-boundary diagnostics now probe:
  - pre-step and post-step finiteness for text-embedding / text-projection
    params
  - targeted optimizer-state tensors
  - whether `optimizer.step()` was attempted, skipped, or completed
- Story 28 refactor is delivered:
  - `scripts/sir_convert_a_lot/cli/ml/qwen_train.py` is now a composition root
  - host control-plane logic lives under
    `scripts/sir_convert_a_lot/ml/qwen/training/control_plane/`
  - detached runtime logic lives under
    `scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/`
  - reporting lives under
    `scripts/sir_convert_a_lot/ml/qwen/training/reporting/`
  - patched runtime logic is split across focused `sft_12hz_*` modules
  - `orchestrator.py` and `reporting.py` are deleted and must not return
- Docs were synchronized so Story 28 is marked completed while `T186` remains
  honestly in progress pending the Hemma proof.

## Latest Task 101 Truth

- Baseline held-out eval exists for `state-step-00001236`:
  - `eval_loss=6.440637648105621`
- Canonical strict-resume checkpoint is:
  - `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001238`
- The later instrumented replay proved:
  - step `1405` still had finite forward losses but non-finite `grad_norm`
  - the loop then applied `optimizer.step()`
  - step `1406` entered with `input_text_embedding` already poisoned
  - this is an optimizer-boundary corruption bug, not just a reporting bug

## Immediate Next Step

Run one detached Hemma `qwen-train diagnose-non-finite` proof from
`state-step-00001238` and confirm the guarded lane now stops before applying
the corrupt optimizer update. Do not restart broad training first.

## Open Risks

- `T186` is not complete until the detached Hemma proof exists under
  `build/verification/`.
- `T179` must stay blocked until that proof shows fail-closed behavior before
  weight corruption.
- Do not add new Qwen feature logic to central files; use the Story 28 package
  owners enforced by `RULE-095`.

## Validation

- `PASS` `pdm run typecheck-ml`
- `PASS` `pdm run test-ml -q` (`225 passed`)
- `PASS` `pdm run format-all`
- `PASS` `pdm run lint-fix`
- `PASS` `pdm run typecheck-all`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_control_plane_launch_use_case.py tests/sir_convert_a_lot/ml/qwen/training/test_control_plane_diagnose_use_case.py tests/sir_convert_a_lot/ml/qwen/training/test_detached_runtime_command_builder.py tests/sir_convert_a_lot/ml/qwen/training/test_detached_runtime_inspect_service.py tests/sir_convert_a_lot/ml/qwen/training/test_diagnostic_replay.py tests/sir_convert_a_lot/ml/qwen/training/test_optimizer_guard.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting_status_payloads.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting_failure_projection.py tests/sir_convert_a_lot/ml/qwen/training/test_train_step_runtime.py tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py tests/sir_convert_a_lot/ml/qwen/training/test_eval_runner.py tests/sir_convert_a_lot/ml/qwen/training/test_schedule_runner.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py -q`
- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`

## Key References

- `docs/backlog/current.md`
- `docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md`
- `docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md`
- `docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md`
- `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`
- `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
