---
id: task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma
title: Create the containerized Qwen3-TTS 1.7B Swedish full-finetune runtime on Hemma
type: task
status: proposed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - runtime
  - hemma
  - rocm
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Create the canonical containerized runtime for full fine-tuning
`Qwen/Qwen3-TTS-12Hz-1.7B-Base` on Hemma, using the repo's normal ROCm cache,
wrapper, and GPU-governance discipline.

## PR Scope

- Add one committed runtime surface for Qwen `1.7B` full fine-tune work on
  Hemma.
- Base the image/runtime on a ROCm training container instead of the main
  service image.
- Keep cache/model storage under the canonical Sir Convert-a-Lot cache roots.
- Keep command execution wrapper-driven:
  - local PDM wrapper,
  - remote Hemma wrapper,
  - no ad hoc raw SSH training loops.

## Deliverables

- [ ] One committed runtime/image definition for Qwen `1.7B` fine-tuning on
  Hemma.
- [ ] One deterministic command surface for smoke/pilot runs.
- [ ] Runbook instructions for build, launch, cache roots, and GPU validation.
- [ ] Explicit note that this runtime is separate from the current production
  sidecar candidate images.

## Acceptance Criteria

- [ ] The runtime is containerized and GPU-first.
- [ ] The runtime reuses canonical persistent caches instead of container-local
  model downloads as the steady-state path.
- [ ] The runtime does not modify the main Sir Convert-a-Lot service image.
- [ ] The runtime documentation names the exact Hemma host paths and wrapper
  commands that are allowed.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
