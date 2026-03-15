---
id: task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics
title: Restore the upstream Qwen fine-tune graph and add clip-boundary forensics
type: task
status: in_progress
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-194-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405.md
  - docs/backlog/current.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - rca
  - numerical-stability
  - diagnostics
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Restore the patched Qwen fine-tuning lane to the upstream no-projection
training contract, add stage-resolved clipping forensics, and reframe the
preserved Task 101 run as the canonical no-projection RCA lane rather than as
discarded progress.

## PR Scope

- Remove active `text_projection` application from the patched train and eval
  forward paths while preserving `talker_runtime` fingerprinting.
- Split optimizer-boundary gradient probes into:
  - `pre_clip_gradient_probes`
  - `post_clip_gradient_probes`
  - explicit `clip_grad_norm_value`
  - explicit `first_non_finite_stage`
- Keep pre-step parameter and optimizer-state probes so the same artifact still
  answers whether weights or optimizer state were already poisoned.
- Add focused regression coverage proving the canonical fine-tune graph no
  longer injects projection while still fingerprinting it when present.
- Quietly rewrite operator docs so:
  - the projection-enabled replay/restart is recorded as a diagnostic
    experiment,
  - `state-step-00001238` remains meaningful no-projection evidence,
  - and the next live proof targets a fresh diagnostic checkpoint near the
    failure boundary rather than another projection-enabled restart.

## Deliverables

- [x] The patched train and eval paths match the upstream no-projection
  fine-tuning contract.
- [x] Optimizer-boundary artifacts distinguish `pre_clip`, `clip_grad_norm`,
  `post_clip`, and `post_step` failure stages.
- [x] Focused train/eval/guard tests lock the restored contract and the new
  stage-separated failure payload.
- [x] Operator docs and handoff memory no longer demote the preserved Task 101
  lane as "wrong graph" merely because it omitted `text_projection`.
- [ ] One bounded Hemma proof mints a fresh diagnostic checkpoint near the
  failure boundary and replays the `1401 -> 1406` window with the new probes.
  - March 15 operator note: the first attempt failed operationally because the
    resumed lane was monitored manually with coarse sleep-based polling and was
    allowed to run into the `1405` boundary before the planned stop near
    `1401`; a retry must use an automated stop threshold keyed to
    `current_optimizer_step`.

## Acceptance Criteria

- [x] A focused train-step test proves talker-level projection may be present
  for fingerprinting but is not injected into the fine-tune forward graph.
- [x] A focused eval-runtime test proves held-out eval uses the same
  no-projection contract.
- [x] Focused guard tests prove distinct failure reasons for:
  - `pre_clip_non_finite_gradients`
  - `clip_grad_norm_non_finite`
  - `post_clip_non_finite_gradients`
  - `post_step_non_finite_parameters` / `post_step_non_finite_optimizer_state`
- [x] Operator docs identify `state-step-00001238` as the canonical
  no-projection RCA checkpoint and record the projection-enabled restart as a
  diagnostic experiment rather than the new mainline.
- [ ] One bounded Hemma proof from a fresh diagnostic checkpoint near optimizer
  step `1401` writes machine-readable stage truth for the first non-finite
  event.
  - Current partial truth: the resumed no-projection lane already proved the
    first bad stage at optimizer step `1405` is `pre_clip`, with
    `text_embedding.weight.grad` as the first non-finite surface, but it did
    not mint the intended fresh near-`1401` checkpoint.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-ml`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_optimizer_guard.py tests/sir_convert_a_lot/ml/qwen/training/test_train_step_runtime.py tests/sir_convert_a_lot/ml/qwen/training/test_eval_runtime.py tests/sir_convert_a_lot/ml/qwen/training/test_talker_runtime.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting_failure_projection.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting_status_payloads.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py tests/sir_convert_a_lot/ml/qwen/training/test_diagnostic_replay.py -q`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [ ] Validation complete
- [x] Docs updated
