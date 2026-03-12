---
id: task-141-define-frozen-qwen-pilot-dataset-use-for-finetuning
title: Define frozen qwen pilot dataset use for finetuning
type: task
status: completed
priority: high
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-guide.md
  - docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - pilot
  - finetuning
  - dataset
  - governance
---

## Objective

Define the canonical rule for how the frozen Qwen pilot dataset is used by the
Task 101 fine-tuning lane so the repo has one unambiguous bridge between:

1. frozen pilot ownership,
1. Qwen-ready pilot manifests and references, and
1. the bounded Hemma pilot full-finetune run.

## PR Scope

- Define the frozen pilot dataset as the only allowed pilot-owned source for the
  next Task 101 launch.
- Define the required projection from the frozen canonical root into the
  Qwen-ready pilot/train/dev/test manifest families already governed by Task
  103 finalization.
- Update Task 101 and Story 25 so they reference the frozen pilot dataset
  rather than an ambiguous promoted corpus view.
- Record the explicit next implementation slice needed to materialize a
  deterministic pilot training bundle from the frozen root.

## Deliverables

- [x] Task 101 updated with the frozen pilot dataset contract.
- [x] Story 25 updated with the frozen pilot dataset bridge.
- [x] Runbook and reference docs updated with the pilot-use rule.
- [x] Explicit follow-on implementation target named for pilot-bundle
  materialization.

## Acceptance Criteria

- [x] The repo states one canonical pilot-owned source root for the next Task
  101 run.
- [x] The repo states that pilot fine-tuning must consume Task 103-finalized
  Qwen manifest families projected from the frozen pilot root, not ad hoc
  row subsets.
- [x] The next implementation gap is explicit: materialize the frozen pilot
  root into a deterministic Task 101 training bundle.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Outcome

The next bounded Qwen fine-tuning run is now governed by one simple rule:

- freeze ownership first,
- project the frozen pilot root into the canonical finalized Qwen manifest
  families second,
- launch Task 101 only from that deterministic pilot training bundle.

The current frozen pilot ownership source is:

- `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`

The next implementation slice is to materialize that frozen root into one
deterministic Task 101 pilot training bundle that includes:

- `swedish_pilot_train.prepared.jsonl`
- `swedish_checkpoint_dev.prepared.jsonl`
- stable per-speaker `refs/`
- any required Task 101 metadata needed for the detached Hemma pilot launcher

That implementation target is now tracked explicitly in:

- `docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md`
