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
- **Implement the critical multi-speaker language expansion patches to `sft_12hz.py`**:
  - Remove the single-speaker collapse logic (the `spk_id=3000` rewrite).
  - Preserve the `speaker_encoder` in the state dict.
  - Maintain `tts_model_type="base"`.
  - Include the known community text-projection fix.
  - Make checkpoint export work for both:
    - local model directories,
    - and Hugging Face Hub ids such as
      `Qwen/Qwen3-TTS-12Hz-1.7B-Base`.
- Define the **training-image dependency baseline** for the runtime image:
  - `qwen_tts`
  - `torch` ROCm-compatible build
  - `accelerate`
  - `transformers`
  - `safetensors`
  - `huggingface_hub`
  - `librosa`
  - `soundfile`
  - `sentencepiece`
  - `tensorboard`
- Keep cache/model storage under the canonical Sir Convert-a-Lot cache roots.
- Keep command execution wrapper-driven:
  - local PDM wrapper,
  - remote Hemma wrapper,
  - no ad hoc raw SSH training loops.

## Deliverables

- [ ] One committed runtime/image definition for Qwen `1.7B` fine-tuning on
  Hemma.
- [ ] Canonical image definition:
  - `containers/qwen-finetune-hemma/Dockerfile`
- [ ] Canonical pinned dependency baseline:
  - `containers/qwen-finetune-hemma/requirements.txt`
- [ ] Patched versions of the official Qwen training scripts (`sft_12hz.py`).
- [ ] One explicit dependency matrix for the Task 100 training image.
- [ ] One deterministic command surface for smoke/pilot runs.
- [ ] Canonical wrapper-driven smoke command:
  - `pdm run run-hemma -- pdm run task-100-smoke`
- [ ] Runbook instructions for build, launch, cache roots, and GPU validation.
- [ ] Explicit note that this runtime is separate from the current production
  sidecar candidate images.

## Acceptance Criteria

- [ ] The runtime is containerized and GPU-first.
- [ ] The runtime reuses canonical persistent caches instead of container-local
  model downloads as the steady-state path.
- [ ] The runtime does not modify the main Sir Convert-a-Lot service image.
- [ ] The training script successfully exports a valid multi-speaker checkpoint
  (with speaker encoder intact) without collapsing to a single voice.
- [ ] The training script exports cleanly when `--init_model_path` is either a
  local directory or a Hugging Face Hub id.
- [ ] The Task 100 runtime image includes the training-only dependency set and
  does not silently rely on host-python installs.
- [ ] The runtime documentation names the exact Hemma host paths and wrapper
  commands that are allowed.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
