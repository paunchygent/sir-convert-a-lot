---
id: task-153-retain-only-bounded-durable-qwen-training-checkpoints-and-guard-scratch-capacity-on-hemma
title: Retain only bounded durable Qwen training checkpoints and guard scratch capacity on Hemma
type: task
status: completed
priority: critical
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - checkpoints
  - scratch
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make long unattended Hemma Qwen runs operationally safe by bounding durable
trainer-state checkpoint retention, preserving a truthful latest-checkpoint
pointer, and failing closed before a new checkpoint save when `/srv/scratch`
does not have enough headroom.

## Why This Exists

`T115` proved exact durable resume, but it intentionally kept every durable
checkpoint forever. The bounded pilot now gives us real scratch truth:

- retained trainer-state checkpoints reach about `11G` each on Hemma
- the bounded pilot run root reached about `45G`
- the real long-run lane would create hundreds of checkpoints at
  `checkpoint_interval_steps=100`

That means the current implementation can exhaust `/srv/scratch` long before a
real multi-epoch Hemma run completes.

## PR Scope

- Keep the existing exact-resume contract from `T115`.
- Add bounded durable checkpoint retention with `N=2` as the canonical default.
- Validate a newly written durable checkpoint before treating it as the latest
  pointer target or pruning older durable checkpoints.
- Keep `latest_checkpoint.json` pointed at the newest retained durable
  checkpoint.
- Keep epoch/final exported model checkpoints; only durable trainer-state
  checkpoints are pruned.
- Add a fail-closed free-space guard before each durable checkpoint save.
- Surface the retention and free-space settings through the detached Task 101
  launch metadata and in-container status/report artifacts.

## Non-Goals

- Do not weaken resumability into export-only restart.
- Do not delete epoch/final exported model checkpoints in this slice.
- Do not move training off Hemma; this is a Hemma hardening slice.

## Deliverables

- [x] Patched Qwen trainer retention/defaults committed in code.
- [x] Detached Qwen pilot runtime surfaces record the new checkpoint policy.
- [x] Focused tests for retention, pointer updates, and free-space refusal.
- [x] Runbook/task docs updated with the canonical `N=2` policy and scratch
  guard posture.

## Acceptance Criteria

- [x] The training lane retains only the newest `2` durable trainer-state
  checkpoints by default.
- [x] The implementation validates the new checkpoint before pruning older
  durable checkpoints.
- [x] `latest_checkpoint.json` still points at the newest retained durable
  checkpoint after pruning.
- [x] Epoch/final exported checkpoints remain untouched by durable retention.
- [x] A new durable checkpoint save fails closed when the target filesystem
  lacks enough safe free space.
- [x] Detached Task 101 launch/status/report artifacts expose the configured
  retention and free-space settings.

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
