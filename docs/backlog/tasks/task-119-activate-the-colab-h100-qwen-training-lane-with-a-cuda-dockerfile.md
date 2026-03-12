---
id: task-119-activate-the-colab-h100-qwen-training-lane-with-a-cuda-dockerfile
title: Activate the Colab H100 Qwen training lane with a CUDA Dockerfile
type: task
status: proposed
priority: high
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - colab
  - cuda
  - docker
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Activate the optional Colab H100 training lane with a dedicated CUDA training
image that mirrors the committed Hemma Qwen runtime contract without trying to
blend ROCm and CUDA concerns into one Dockerfile.

## Why This Exists

The Hemma ROCm runtime is the canonical default lane, but Story 25 still keeps
Colab H100 as a fallback or comparison environment when Hemma hits real
stability or wall-clock limits.

The current training Dockerfile is intentionally ROCm-only. This task exists to
create the missing CUDA counterpart cleanly instead of pretending the existing
image is portable.

## PR Scope

- Add a dedicated CUDA/H100 Qwen training Dockerfile for the Colab lane.
- Preserve the same patched Qwen training entrypoints and detached/operator
  contracts where they still apply.
- Document the Colab-specific differences clearly:
  - base image,
  - PyTorch/torchaudio install source,
  - flash-attention build/runtime path,
  - expected launcher commands and cache roots.
- Keep the Hemma ROCm image untouched except for shared refactors that reduce
  duplication cleanly.

## Chosen Planning Shape

This task should be implemented as a parallel runtime lane, not as a
cross-platform unification exercise.

Planned structure:

- keep `containers/qwen-finetune-hemma/Dockerfile` ROCm-only
- add one dedicated CUDA Dockerfile for Colab H100 activation
- share only clearly runtime-neutral assets:
  - patched Qwen training scripts
  - detached launch/report contracts when applicable
  - common manifest expectations

Expected implementation order:

1. define the CUDA image contract and dependency baseline
1. add a bounded smoke or pilot surface for the Colab lane
1. update the runbook with exact lane-selection guidance
1. record one reproducible validation result before calling the lane active

## Expected Colab-Specific Decisions

- CUDA base image choice
- PyTorch/torchaudio CUDA wheel source
- flash-attention install/build path for Nvidia
- cache and output-root policy in Colab storage constraints
- whether detached Task 101 semantics are mirrored exactly or need one
  Colab-specific wrapper

## Follow-on Rule

Do not weaken or generalize the Hemma ROCm runtime to make Colab easier. If
code sharing is useful, it must happen through small neutral helpers, not by
compromising the existing ROCm lane.

## Non-Goals

- Do not switch the default training lane away from Hemma.
- Do not merge ROCm and CUDA into one compromised Dockerfile.
- Do not treat Colab notebook drift as acceptable; the repo still needs a
  committed reproducible runtime surface.

## Deliverables

- [ ] Dedicated Colab CUDA Dockerfile for Qwen training.
- [ ] Updated runbook instructions for activating the Colab lane.
- [ ] One bounded validation surface that proves the CUDA image boots the
  patched Qwen training stack successfully.

## Acceptance Criteria

- [ ] The Colab lane uses a dedicated CUDA image rather than the ROCm image.
- [ ] The repo docs explain when to choose Hemma versus Colab.
- [ ] The CUDA image keeps the same patched Qwen training code path unless a
  documented CUDA-specific divergence is required.
- [ ] The task records at least one reproducible bounded validation result.

## Validation

- [ ] bounded CUDA-lane validation evidence is written under `build/verification/`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
