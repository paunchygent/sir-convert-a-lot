---
id: 'task-118-profile-the-qwen-finetuning-dataloader-and-decide-whether-to-precompute-ref-mels'
title: 'Profile the Qwen finetuning dataloader and decide whether to precompute ref mels'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-117-harden-the-qwen-hemma-training-runtime-for-graceful-stop-and-cold-start-safety.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - dataloader
  - profiling
  - preprocessing
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Measure whether the patched Qwen fine-tuning dataloader is actually starving
the GPU on Hemma and make an evidence-backed decision about whether
`ref_mel` extraction should remain in `dataset.py` or move into the Task 103
preprocessing lane.

## Why This Exists

`review-02` correctly identified a plausible hotspot in `dataset.py`: each
item currently loads audio and computes `ref_mel` on demand inside
`__getitem__`. That is a real performance risk, but it is still a hypothesis,
not a proven architecture defect.

This task exists to replace guesswork with evidence before the repo commits to
expanding Task 103 artifact scope or storage cost.

## PR Scope

- Add explicit profiling and timing surfaces around the patched Qwen training
  dataloader path.
- Produce evidence that distinguishes:
  - data loading time,
  - mel extraction time,
  - GPU busy/idle behavior during bounded training steps.
- Evaluate at least two implementation options:
  - keep runtime mel extraction in `dataset.py`,
  - precompute and persist `ref_mel` in Task 103 artifacts.
- Record the storage/runtime trade-off clearly enough to support a later
  implementation PR if the optimization is justified.

## Chosen Planning Shape

This task should land as an evidence PR, not an architecture-change PR.

The planned execution order is:

1. add lightweight timing/profiling hooks around the current dataloader path
1. collect one bounded Hemma training trace on the current runtime
1. decide whether the current lane is actually GPU-starved
1. only then decide whether a follow-up implementation task is justified

The expected result is one of:

- `keep-runtime-mels`
  - no Task 103 artifact change
  - close the concern with evidence
- `precompute-ref-mels`
  - open one follow-up implementation PR that changes Task 103 artifacts,
    manifests, and training-row loading in one coherent slice

## Expected Evidence

- dataloader wait time or per-batch data-prep time
- model step time
- bounded host CPU and GPU utilization for the same run window
- sample storage-cost estimate for adding persisted `ref_mel`
- explicit note on whether the current bottleneck is:
  - CPU decode / mel extraction
  - disk I/O
  - or not meaningfully on the dataloader side at all

## Follow-on Rule

No one should change the Task 103 artifact contract for `ref_mel` persistence
until this task records evidence that the current runtime path is a real
bottleneck on Hemma.

## Non-Goals

- Do not move mel extraction into Task 103 in this task.
- Do not change manifest contracts or preprocessing artifacts yet.
- Do not bundle this investigation into the T117 Hemma runtime hardening PR.

## Deliverables

- [ ] Bounded Hemma or reproducible local profiling evidence for the current
      dataloader path.
- [ ] A written recommendation on whether precomputing `ref_mel` is justified.
- [ ] If precompute is justified, a concrete follow-up implementation plan that
      names the affected Task 103 artifacts and contracts.

## Acceptance Criteria

- [ ] The task records real timing/profiling evidence rather than intuition.
- [ ] The decision explicitly covers GPU starvation risk, CPU cost, and storage
      impact.
- [ ] The result clearly says one of:
  - keep current runtime mel extraction,
  - implement Task 103 precompute in a later PR.
- [ ] The runbook/reference docs are updated if the recommendation changes the
      planned architecture.

## Validation

- [ ] bounded profiling evidence is written under `build/verification/`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
