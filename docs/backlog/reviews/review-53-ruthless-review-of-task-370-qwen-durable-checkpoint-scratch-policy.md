---
id: review-53-ruthless-review-of-task-370-qwen-durable-checkpoint-scratch-policy
title: Ruthless review of Task 370 Qwen durable checkpoint scratch policy
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-370-harden-qwen-durable-checkpoint-scratch-policy-and-deterministic-local-tests.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - review
  - approved
  - task-370
  - qwen
  - checkpoints
  - scratch
  - testing
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Independent ruthless review for Task 370. This reviewer did not author the
implementation or tests and did not modify production or test files. The only
intentional mutation from this pass is this retained review artifact plus any
generated docs index refresh required by docs-as-code validation.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `.codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md`
- `.codex/skills/speech-model-finetuning-on-hemma/SKILL.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/095-qwen-training-architecture-boundaries.md`
- `.codex/rules/096-qwen-experiment-governance.md`
- `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
- `docs/backlog/tasks/task-370-harden-qwen-durable-checkpoint-scratch-policy-and-deterministic-local-tests.md`
- `docs/_meta/docs-contract.yaml`
- `docs/backlog/README.md`
- Existing retained review format in `docs/backlog/reviews/`.

Task 370 files reviewed:

- `scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/paths.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/command_builder.py`
- `tests/sir_convert_a_lot/ml/qwen/training/test_detached_runtime_command_builder.py`
- `tests/sir_convert_a_lot/ml/qwen/training/test_checkpoint_persistence.py`
- `tests/sir_convert_a_lot/ml/qwen/training/checkpoint_space_test_support.py`
- `tests/sir_convert_a_lot/ml/qwen/training/conftest.py`
- `docs/backlog/tasks/task-370-harden-qwen-durable-checkpoint-scratch-policy-and-deterministic-local-tests.md`
- `docs/backlog/INDEX.md` only for the Task 370 generated row.

Supporting runtime files inspected to verify boundary behavior:

- `scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/launch_service.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/control_plane/launch_use_case.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/control_plane/resume_use_case.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/control_plane/capture_diagnostic_state_use_case.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/control_plane/diagnose_use_case.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/diagnostics.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/schedule_runner.py`
- `scripts/devops/qwen_finetuning_patches/sft_12hz_checkpointing.py`

Unrelated worktree changes were excluded from this Task 370 decision, including
Task 368/369/idempotency/STT contract edits and the existing untracked
`docs/backlog/reviews/review-52-ruthless-review-of-task-368-centralize-retryable-failed-idempotency-reattempts.md`.

Public/operator surfaces affected:

- Qwen detached training Docker command construction for launch, resume,
  schedule resume, diagnostic replay, and diagnostic-state capture.
- Host-to-container path projection for run roots, launch metadata, manifests,
  tracker/profiler roots, pilot bundle roots, and resume checkpoints.
- Qwen durable checkpoint unit tests and local free-space test determinism.

Compatibility posture:

- This is a fail-closed hardening of the Qwen training operator surface, not a
  public HTTP/API compatibility change.
- No legacy wrapper, compatibility shim, CPU fallback, alternate storage tier,
  checkpoint-cadence change, or experiment-conclusion change was found in the
  Task 370 scope.

## Findings

No findings.

The detached runtime now centralizes the scratch-root check in
`require_scratch_path()` and raises a labeled, fail-closed error with both the
resolved offending path and the configured scratch root
(`scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/paths.py:21`).
`build_detached_training_command()` applies that guard to the effective run
root, train/eval manifests, launch metadata path, pilot bundle root, MLflow and
TensorBoard roots, profiler roots, and optional resume checkpoint before the
launch service calls Docker (`scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/command_builder.py:57`,
`scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/command_builder.py:102`,
`scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/launch_service.py:51`).
That is the right boundary for Task 370: the public CLI remains a composition
root, while detached runtime command construction refuses escaped paths before
`docker run`.

The new escaped-path test is behavioral enough for the risk under review. It
drives the detached command builder with escaped `launch_root`, `run_root`, and
`resume_from_checkpoint` inputs, and asserts that diagnostics name the concrete
field, offending path, and scratch root
(`tests/sir_convert_a_lot/ml/qwen/training/test_detached_runtime_command_builder.py:116`).
The adjacent capture and diagnostic control-plane tests still pass, and their
launch paths delegate through the same detached launch service.

The deterministic free-space fixture is test-only and scoped to the Qwen
checkpoint module's `shutil.disk_usage` boundary
(`tests/sir_convert_a_lot/ml/qwen/training/conftest.py:25`). It prevents local
positive checkpoint lifecycle tests from depending on macOS temporary
filesystem free space, as Task 370 requires. The production guard itself still
uses the runtime module's required-free calculation and `shutil.disk_usage`
(`scripts/devops/qwen_finetuning_patches/sft_12hz_checkpointing.py:141`), and
the low-space negative test overrides the autouse fixture to prove the
conservative first-save floor still fails closed
(`tests/sir_convert_a_lot/ml/qwen/training/test_checkpoint_persistence.py:316`).

Static review found no `typing.Any`, `typing.cast`, `# type: ignore`, `noqa`,
lint-ignore escape hatches, compatibility wrappers, false fallbacks, or broad
Qwen orchestrator/reporting modules in the Task 370 files. Reviewed hot-path
detached runtime modules remain inside Rule 095 limits: `paths.py` is 99 lines
and `command_builder.py` is 251 lines. The new/materially changed Python files
carry Google-style module docstrings describing domain purpose and
relationships.

The retained task doc accurately keeps Task 370 `in_progress`, records the
review as the remaining deliverable/acceptance item, keeps validation truthful
by leaving `format-all`, `lint-fix`, and `docs-validate` unchecked, and does not
claim Hemma runtime capacity evidence or real training execution.

## Decision

approved

## Response

Task 370 is approved for overseer closeout. The implementation fails closed for
escaped detached Qwen checkpoint/run/metadata paths before container execution,
keeps checkpoint-capacity policy in the production checkpoint runtime, and makes
local positive checkpoint tests deterministic without accepting local temp
space as Qwen runtime evidence.

This approval does not mark the Task 370 backlog item completed. The overseer
should close the task after recording this retained review.

## Follow-up Actions

1. Overseer should mark Task 370 reviewed/complete after syncing generated
   docs indexes and retaining this review artifact.
1. If the unrelated review-52/docs-validation blocker recurs in another
   worktree state, handle it separately; it is not a Task 370 implementation
   blocker.

## Validation

Reviewer-run evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_checkpoint_persistence.py tests/sir_convert_a_lot/ml/qwen/training/test_detached_runtime_command_builder.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py -q`
  passed: `34 passed in 27.72s`.
- `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_capture_diagnostic_state_use_case.py tests/sir_convert_a_lot/ml/qwen/training/test_diagnostic_replay.py -q`
  passed: `6 passed in 46.60s`.
- Static scan for `Any`, `typing.Any`, `cast(`, `type: ignore`, `noqa`,
  `pyright`, and `mypy` escape hatches in the Task 370 files returned no
  matches.
- `wc -l` confirmed reviewed Task 370 modules stay inside the Rule 095 and repo
  size budgets.
- `pdm run docs-sync` refreshed generated docs indexes.
- `pdm run docs-validate` passed: `Validated 494 backlog files` and
  `Validated docs=570 rules=11`.
- `pdm run skills-validate` passed: `skills-validate: ok`.
- `pdm run handoff-validate` passed: `handoff-validate: ok`.
- `git diff --check` passed.

Not run by this reviewer:

- `pdm run format-all` and `pdm run lint-fix`; skipped to avoid repo-wide
  mutations in the known dirty unrelated worktree.
- `pdm run typecheck-all`; implementer reported success, and this review
  focused on the Task 370 behavioral proof.

## Completion

Review completed on 2026-06-29. Decision is `approved`.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
