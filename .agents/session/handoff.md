# Session Handoff

## Current State

- Active epic: Epic 08 Qwen Swedish language expansion on Hemma.
- Active story: Story 26 remains in progress for Task 101 throughput and
  numerical-stability closure.
- Completed remediation task: `T186`
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
- Docs were synchronized so Story 28 is marked completed and `T186` is now
  closed out with the finished Hemma proof.

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
- The guarded detached proof now exists at:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T180643Z`
- The completed proof showed:
  - `trigger_reason=pre_step_non_finite_grad_norm`
  - `optimizer_step=1405`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
  - `text_embedding.weight` and optimizer state were still finite pre-step
  - `text_embedding.weight.grad` was already non-finite pre-step
- Acceptance conclusion:
  - the guarded lane stopped before the corrupt optimizer update was applied
  - `T186` is complete as the prerequisite proof slice for the next `T179`
    decision

## Immediate Next Step

Decide the next bounded `T179` stability retry from the completed `T186`
proof artifacts. Do not restart broad training first.

## Open Risks

- Do not ignore the stale legacy-source diagnostic lesson: future detached
  proofs must reuse a truthful source launch root rather than inheriting stale
  `2/100/2` checkpoint cadence settings.
- `T179` should proceed only as a bounded next slice that explicitly uses the
  completed `T186` fail-closed evidence.
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
