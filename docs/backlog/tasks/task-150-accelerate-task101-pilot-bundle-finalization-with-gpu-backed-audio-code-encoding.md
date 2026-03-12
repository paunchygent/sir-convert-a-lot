---
id: task-150-accelerate-task101-pilot-bundle-finalization-with-gpu-backed-audio-code-encoding
title: Accelerate Task101 pilot bundle finalization with GPU-backed audio-code encoding
type: task
status: active
priority: high
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma.md
  - docs/backlog/tasks/task-149-containerize-task101-pilot-bundle-batch-finalization-runtime.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - hemma
  - gpu
  - rocm
  - pilot
  - training-bundle
  - audio-codes
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make Task 101 pilot-bundle batch finalization use the governed ROCm GPU path
for `audio_codes` generation instead of the current CPU-bound tokenizer
default, while preserving the resumable batched bundle contract introduced by
`T148-T149`.

## PR Scope

- Keep the existing Task 101 `build` / `finalize-batch` / `assemble` command
  surfaces stable for operators.
- Keep the governed Task 100/101 runtime image and the fixed in-container HF
  cache contract from `T149`.
- Upgrade the tokenizer/audio-code runtime so the canonical Task 101 batch
  finalization path loads and runs on ROCm with the same governed dependency
  posture as the training image.
- Fail closed when the governed Task 101 batch finalization runtime cannot
  obtain the expected GPU-backed tokenizer posture.
- Preserve resumability for already-copied bundle inputs and completed batch
  shards.
- Preserve the runtime provenance contract added by `T149`.
- Minimize duplicated runtime logic between Task 101 bundle finalization and
  the shared Task 103 finalization helpers.

## Non-Goals

- Do not redesign the Task 101 batch-plan or bundle-report contracts.
- Do not reintroduce host-venv finalization as a fallback.
- Do not silently continue on CPU when the governed runtime cannot initialize
  the tokenizer on GPU.
- Do not broaden this slice into multi-worker finalization orchestration unless
  the current single-process GPU path proves insufficient after evidence is
  captured.

## Why This Slice Exists

The live Hemma `2026-03-12` Task 101 pilot-bundle build showed that `T148`
and `T149` fixed scratch-space governance and runtime drift, but it also
exposed a serious throughput flaw in the remaining audio-code path:

- the active `finalize-batch` process drove host CPU hard while `rocm-smi`
  reported `GPU% 0`
- the shared `encode_audio_codes()` path constructs `Qwen3TTSTokenizer` with
  `from_pretrained(tokenizer_model)` only
- the installed `qwen_tts` tokenizer forwards `**kwargs` to
  `AutoModel.from_pretrained(...)`, but no device, dtype, or attention
  settings are passed today
- the result is a CPU-loaded tokenizer model even inside the governed
  container runtime

That means the current Task 101 lane is governed and reproducible, but still
not using the hardware we intentionally prepared for this workload.

## Required Implementation Shape

1. Upgrade the shared audio-code tokenizer loader so it can construct one
   governed GPU-backed tokenizer runtime.
   - Use the official `qwen_tts` tokenizer surface rather than bypassing it
     with an unrelated ad hoc model loader.
   - Thread explicit runtime options required to place the tokenizer model on
     ROCm and use the governed attention posture where supported.
1. Keep one warm tokenizer instance per finalization process.
   - Do not regress back to recreating the tokenizer per chunk.
1. Make the canonical Task 101 batch-finalization path fail closed when the
   tokenizer model is not on GPU.
   - No silent CPU fallback for the governed Hemma batch runtime.
1. Preserve resumability for interrupted bundle builds.
   - If a batch is interrupted after `batch_started` but before
     `batch_completed`, the next governed rerun must still validate existing
     shards and rerun only the incomplete batch.
1. Add operator-visible runtime evidence that the tokenizer posture is GPU
   backed.
   - At minimum record the tokenizer device plus the relevant dtype / attention
     posture in the governed runtime fingerprint or an adjacent deterministic
     report surface.
1. Keep the implementation compatible with the existing governed Task 100/101
   image.
   - Reuse the shared Qwen dependency set and fixed `/cache/huggingface`
     contract from `T149`.
1. Review whether the shared Task 103 finalization surface should inherit the
   same GPU-backed tokenizer initialization.
   - If yes, update the shared helper and the affected tests/docs together.
   - If no, document the reason clearly in code and task notes.

## Deliverables

- [ ] Committed GPU-backed tokenizer/runtime helper for governed Qwen
  audio-code finalization.
- [ ] Task 101 batch finalization updated to require GPU-backed tokenizer
  initialization in the governed runtime.
- [ ] Runtime evidence updated so operators can verify the tokenizer used ROCm
  rather than CPU.
- [ ] Tests covering tokenizer runtime selection, fail-closed behavior, and
  resumable bundle reuse after interrupted partial batches.
- [ ] Docs updates describing the new Task 101 GPU-backed finalization
  contract and the live-Hemma stop/resume rationale for the interrupted
  `2026-03-12` bundle run.

## Acceptance Criteria

- [ ] Task 101 governed batch finalization no longer runs the tokenizer model
  on CPU by default.
- [ ] The canonical governed Task 101 runtime fails closed when GPU-backed
  tokenizer initialization is unavailable.
- [ ] Runtime evidence proves the tokenizer model device is GPU-backed for the
  accepted path.
- [ ] An interrupted governed bundle build remains resumable from the last
  completed batch without redoing already validated shards.
- [ ] The task doc, runbook, and current-session log all describe the same
  GPU-first finalization posture.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] focused pytest for Task 101 bundle runtime plus shared finalization
  helpers
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Implementation Notes

- Live Hemma bundle run intentionally stopped at:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h`
  - last completed batch:
    `swedish_pilot_train:batch-00012`
  - next incomplete batch:
    `swedish_pilot_train:batch-00013`
- That run was stopped so the repo checkout on Hemma can be updated and the
  next rerun can use the GPU-backed governed runtime instead of finishing the
  slower CPU-bound path.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
