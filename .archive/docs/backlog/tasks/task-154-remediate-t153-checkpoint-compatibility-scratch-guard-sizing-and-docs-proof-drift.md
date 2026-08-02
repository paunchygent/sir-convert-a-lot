---
id: task-154-remediate-t153-checkpoint-compatibility-scratch-guard-sizing-and-docs-proof-drift
title: Remediate T153 checkpoint compatibility, scratch guard sizing, and docs-proof drift
type: task
status: completed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma.md
  - docs/backlog/tasks/task-153-retain-only-bounded-durable-qwen-training-checkpoints-and-guard-scratch-capacity-on-hemma.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - checkpoints
  - docs-as-code
  - validation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Bring the `T153` follow-on surfaces back into contract by restoring exact-resume
compatibility for existing Task 101 launches, making the scratch-capacity guard
conservative on the first durable save, preventing failed durable saves from
wedging later retries, and reconciling docs/tests with the real pilot state.

## Why This Exists

The post-`T153` review found a bounded but concrete remediation slice:

- `status` / `resume` now reject pre-`T153` `launch.json` payloads that do not
  yet carry the new durable-checkpoint fields
- the first durable-checkpoint free-space guard still uses an optimistic
  fallback compared with the measured Hemma checkpoint size
- failed or invalid `state-step-*` directories can poison later retries at the
  same optimizer step
- the new tests do not yet prove validation-before-prune ordering, exported
  checkpoint preservation, or the Task 101 artifact contract for the new
  retention/free-space fields
- docs-as-code surfaces now disagree about the active lane and the completion
  state of the bounded Task 101 pilot

## PR Scope

- Add backward-compatible Task 101 launch metadata loading so `status` and
  `resume` preserve the exact-resume contract from `T115` for pre-`T153`
  launches while defaulting missing fields to the canonical bounded policy.
- Replace the optimistic first-checkpoint scratch-capacity fallback with a
  conservative requirement grounded in live Hemma evidence or an explicitly
  persisted size estimate.
- Make durable checkpoint writes atomic or clean up invalid partial
  `state-step-*` directories so one failed save does not block a later retry at
  the same optimizer step.
- Strengthen test coverage for:
  - resume compatibility with pre-`T153` launch metadata
  - validation-before-pointer/prune ordering
  - exported checkpoint preservation under durable retention
  - non-tautological scratch-capacity thresholds
  - Task 101 launch/status/report artifact exposure of the new checkpoint
    policy fields
- Reconcile docs governance drift across `.codex/handoff.md`, Story 25,
  Task 101, and related handoff context so the canonical planning surface
  matches the real Qwen pilot state.
- Update task/runbook language if the operator-facing checkpoint policy or
  compatibility semantics change during remediation.

## Non-Goals

- Do not redesign the Task 101 training objective, pilot dataset bridge, or the
  bounded `N=2` checkpoint policy itself.
- Do not use this slice to launch the uncapped Hemma run.
- Do not broaden this task into dataloader/performance work owned by `T118`.

## Deliverables

- [x] Task 101 resume/status compatibility fix plus durable-checkpoint retry
  hardening in code.
- [x] Conservative first-checkpoint scratch guard with focused regression
  coverage.
- [x] Test updates that prove the new checkpoint policy rather than only happy
  path flag plumbing.
- [x] Docs-as-code reconciliation for Task 101 / `T153` / Story 25 / current
  context state.

## Acceptance Criteria

- [x] `task-101-pilot status` and `task-101-pilot resume` can load pre-`T153`
  launch metadata without manual JSON edits and still apply canonical durable
  checkpoint defaults.
- [x] A first durable checkpoint save fails closed when free space is below the
  proven safe threshold for one new trainer-state checkpoint plus the minimum
  free-space floor.
- [x] A failed or invalid durable checkpoint save does not leave a
  `state-step-*` directory that blocks a later retry at the same optimizer
  step.
- [x] Tests prove validation happens before latest-pointer updates and pruning,
  and that epoch/final exported checkpoints remain untouched by durable
  retention.
- [x] Task 101 launch/status/report artifact tests assert the configured durable
  checkpoint retention and minimum-free-space fields.
- [x] `.codex/handoff.md`, Story 25, Task 101, and related handoff
  context no longer disagree about the active lane or bounded-pilot completion
  state.
- [x] `pdm run validate-tasks`, `pdm run validate-docs`, and task indexing pass
  after the reconciliation.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
