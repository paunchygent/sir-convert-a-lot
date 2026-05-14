---
type: runbook
id: RUN-hemma-gpu-runtime
title: Hemma GPU Runtime Runbook for Sir Convert-a-Lot
status: active
created: '2026-05-14'
updated: '2026-05-14'
owners:
  - platform
system: hemma.hule.education
tags:
  - gpu
  - rocm
  - vllm
  - llama-cpp
  - model-cache
links:
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/backlog/tasks/task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md
---

## Purpose

Keep Sir Convert-a-Lot GPU, model-cache, vLLM, and llama.cpp operations on the
same Hemma storage and evidence contract.

## Storage Contract

- `/srv/scratch`: active Docker root, BuildKit cache, Hugging Face/model caches,
  active generated artifacts, and benchmark working roots.
- `/srv/storage`: raw corpora and cold retained datasets or completed artifacts.
- `/`: no long-lived Docker state, model cache, or generated artifact trees.

Canonical Sir Convert scratch roots:

- `/srv/scratch/sir-convert-a-lot/build`
- `/srv/scratch/sir-convert-a-lot/cache`
- `/srv/scratch/sir-convert-a-lot/cache/huggingface`

## GPU Verification

Use these probes before GPU workload changes:

```bash
pdm run run-hemma -- rocminfo
pdm run run-hemma -- rocm-smi
```

If GPU readiness is missing, fail the lane and record the degraded state in the
governing task. Do not silently switch to CPU execution.

## Local Structured LLM Provider

Current interim provider for answer-key completion:

- Runtime: ROCm vLLM preview image
- Image: `rocm/vllm:rocm7.12.0_gfx120X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0`
- Model: `ibm-granite/granite-4.1-8b-fp8`
- Host bind: `127.0.0.1`
- Candidate port: `8017` after proving the port is free
- Max model length: `4096`
- GPU memory utilization: `0.70`
- Request log capture: disabled
- Structured output route: vLLM Chat Completions `structured_outputs`

Use the Task 301 smoke result as viability evidence. Use the local-model
reference for model-selection and benchmark authority.

## Model Cache Contract

Granite FP8 vLLM runs reuse the same scratch-backed Hugging Face cache method as
the HF-backed llama.cpp/Qwen/TTS lanes:

```text
canonical_host_cache: /srv/scratch/sir-convert-a-lot/cache/huggingface
docker_visible_cache: /home/paunchygent/.data/sir-convert-a-lot/cache/huggingface
container_mount: /cache/huggingface
HF_HOME: /cache/huggingface
HF_HUB_CACHE: /cache/huggingface/hub
TRANSFORMERS_CACHE: /cache/huggingface
```

The retained Granite FP8 cache must be visible inside the container at:

```text
/cache/huggingface/hub/models--ibm-granite--granite-4.1-8b-fp8
```

Do not create a second long-lived vLLM cache tree. If the Docker bind-root
preflight fails, stop and record the exception instead of redownloading into
container-local or home-only paths.

## Benchmark Candidates

The settled runtime is Granite FP8 on vLLM until Task 300 compares it with the
GGUF shortlist. Keep these GGUF candidates in the first-pass matrix:

- `unsloth/Qwen3.5-4B-GGUF`, `UD-Q6_K_XL`
- `unsloth/gemma-4-E4B-it-GGUF`, `Q6_K`
- `unsloth/granite-4.1-8b-GGUF`, `Q6_K`
- `unsloth/Qwen3.5-9B-GGUF`, `Q6_K`
- `unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF`, `UD-Q6_K_XL`

The primary promotion metric is wrong-but-valid answer rate on real items, not
generic benchmark score.

## Docling GPU Validation

Docling and OCR GPU validation belongs in the governing parser/converter task.
Keep the runbook to runtime invariants and link detailed evidence from the task
or reference document.
