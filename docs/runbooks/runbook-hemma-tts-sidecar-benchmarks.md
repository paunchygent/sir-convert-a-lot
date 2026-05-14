---
type: runbook
id: RUN-hemma-tts-sidecar-benchmarks
title: Hemma TTS Sidecar Benchmark Runbook for Sir Convert-a-Lot
status: active
created: '2026-05-14'
updated: '2026-05-14'
owners:
  - platform
system: hemma.hule.education
tags:
  - tts
  - qwen
  - openvoice
  - f5-tts
  - chatterbox
links:
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
---

## Purpose

Route Swedish TTS sidecar benchmark work without mixing it into conversion,
deploy, or local answer-key LLM operations.

## Route

- Qwen3 Swedish fine-tuning: `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
- Chatterbox multilingual tuning:
  `docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md`
- Generic GPU/cache invariants: `docs/runbooks/runbook-hemma-gpu-runtime.md`
- Service/tunnel/deploy invariants: `docs/runbooks/runbook-hemma-service-ops.md`

## Shared Rules

- Keep active TTS proof, training, and evaluation roots on `/srv/scratch`.
- Demote only cold completed artifact trees to `/srv/storage`.
- Keep canonical Hugging Face caches under
  `/srv/scratch/sir-convert-a-lot/cache/huggingface`.
- Do not prune scratch while active TTS containers or explicit maintenance block
  files are present.
- Use detached execution for training, long evaluation, and batch generation.
- Store full audio outputs and benchmark artifacts outside governed docs.

## Evidence Checklist

- [ ] Model and checkpoint source recorded.
- [ ] Training/evaluation corpus manifest recorded.
- [ ] GPU/runtime image and revision recorded.
- [ ] Scratch/cache roots recorded.
- [ ] Sample-selection method recorded.
- [ ] Human listening result or acceptance rubric linked from the governing task.
- [ ] Promotion decision recorded as task/reference text, not as runbook prose.

## Maintenance Boundary

This runbook is an operator router. If a model-specific lane needs more than
these shared rules, put the detail in its model-specific runbook or governing
task.
