---
id: story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab
title: Containerized Qwen3-TTS Swedish full-finetune baseline on Hemma and Colab
type: story
status: in_progress
priority: high
created: '2026-03-08'
last_updated: '2026-03-11'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-98-add-qwen-english-reference-clone-lane-to-hemma-benchmark.md
  - docs/backlog/tasks/task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
  - docs/backlog/tasks/task-141-define-frozen-qwen-pilot-dataset-use-for-finetuning.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/tasks/task-143-harden-qwen-pilot-training-eval-and-bundle-preflight-contracts.md
  - docs/backlog/tasks/task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma.md
  - docs/backlog/tasks/task-117-harden-the-qwen-hemma-training-runtime-for-graceful-stop-and-cold-start-safety.md
  - docs/backlog/tasks/task-118-profile-the-qwen-finetuning-dataloader-and-decide-whether-to-precompute-ref-mels.md
  - docs/backlog/tasks/task-119-activate-the-colab-h100-qwen-training-lane-with-a-cuda-dockerfile.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - tts
  - finetuning
  - roc-m
  - hemma
---

Implementation slice with acceptance-driven scope.

## Objective

Establish the reproducible runtime baseline for full fine-tuning
`Qwen/Qwen3-TTS-12Hz-1.7B-Base` on Hemma and Colab, with Triton flash attention
enabled by default in the supported container path and with explicit evidence
that a real Swedish optimizer step fits on the R9700.

## Scope

- Make the existing Task 79 Qwen benchmark use Triton flash attention by
  default again, while keeping one explicit fallback switch for regression
  triage.
- Define the container/runtime policy for Qwen full-finetune work:
  - ROCm container on Hemma,
  - persistent Hugging Face cache roots,
  - no raw host or `systemd` training lane,
  - no dependency sprawl into the main service image.
- Record the current proof-of-fit evidence:
  - clean GPU baseline with no resident models,
  - real model residency on Hemma,
  - real official full-finetune step with `AdamW` on a Swedish sample.
- Define Hemma as the default scaling lane and Colab H100 as an optional
  fallback only when Hemma proves insufficient.
- Keep model training isolated from the current Epic 07 public route work.
- Define the fault-tolerant resume/checkpoint contract required before long
  unattended Hemma training windows.
- Make the frozen pilot root and its deterministic Task 101 training bundle the
  only allowed pilot dataset bridge for the first bounded Hemma fine-tune.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark.md`
1. `docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md`
1. `docs/backlog/tasks/task-141-define-frozen-qwen-pilot-dataset-use-for-finetuning.md`
1. `docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md`
1. `docs/backlog/tasks/task-143-harden-qwen-pilot-training-eval-and-bundle-preflight-contracts.md`
1. `docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md`
1. `docs/backlog/tasks/task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma.md`
1. `docs/backlog/tasks/task-117-harden-the-qwen-hemma-training-runtime-for-graceful-stop-and-cold-start-safety.md`
1. `docs/backlog/tasks/task-118-profile-the-qwen-finetuning-dataloader-and-decide-whether-to-precompute-ref-mels.md`
1. `docs/backlog/tasks/task-119-activate-the-colab-h100-qwen-training-lane-with-a-cuda-dockerfile.md`

## Acceptance Criteria

- [ ] Task 99 records the benchmark/runtime change that makes Triton flash
  attention the default Qwen Hemma lane again.
- [ ] Task 100 defines one containerized Qwen `1.7B` runtime path on Hemma that
  aligns with the repo's existing ROCm/HF-cache discipline.
- [ ] Task 101 records a real containerized Swedish full-finetune pilot result
  on Hemma with `AdamW`.
- [x] The story now states that the first Task 101 pilot must consume a
  deterministic training bundle projected from the frozen pilot root rather
  than the generic promoted preprocessing root.
- [x] A dedicated implementation task exists to materialize that deterministic
  pilot bundle before the Task 101 launch, and `T142` now provides the
  committed bundle-materialization surface.
- [x] A dedicated hardening task exists to make the pilot bundle relocation-safe,
  fail closed on broken bundle-local paths, propagate held-out eval manifest
  metadata through the detached runtime contract, and `T143` now provides that
  committed surface.
- [ ] A dedicated task defines and proves robust resumable checkpointing before
  the first long unattended Hemma training window.
- [ ] A follow-on hardening task covers graceful stop behavior, resumable cache
  sync, and cold-build operator visibility for the Hemma training lane.
- [ ] A profiling follow-up task exists for the dataloader/mel-precompute
  question before any architecture claim is treated as settled.
- [ ] A separate Colab activation task exists for the CUDA runtime rather than
  overloading the Hemma ROCm image.
- [ ] The story documents the already-proven Hemma memory reality:
  - `32.06 GB` total VRAM,
  - clean idle baseline around `0.06 GB`,
  - real official Waxholm full-finetune step around `20.19 GB`.
- [ ] The story keeps the training objective focused on future general Swedish
  support rather than narrowing into a single custom voice lane.

## Test Requirements

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task79_hemma_tts_sidecar_benchmark.py`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Real Hemma benchmark or pilot evidence is written under
  `build/verification/` before the story can close.

## Done Definition

The repo has one documented, containerized, reproducible Qwen `1.7B`
fine-tuning baseline on Hemma as the default lane, a documented optional Colab
fallback path, and an explicit resumable-checkpoint plan for longer Hemma
training windows, plus explicit follow-on tasks for runtime hardening,
dataloader profiling, Colab CUDA activation, and deterministic pilot-bundle
materialization from the frozen pilot root.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
