---
type: runbook
id: RUN-SIRCON-hemma-gpu-runtime-runbook-for-sir-convert-a-lot
title: Hemma GPU Runtime Runbook for Sir Convert-a-Lot
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-02'
status: active
summary: Hemma GPU Runtime Runbook for Sir Convert-a-Lot
system: hemma.hule.education
retired_ids:
  - RUN-hemma-gpu-runtime
---

## Trigger

State the observable condition that starts this procedure and who may run it.

## Preconditions

- Required authority, system state, access, inputs, and safety checks.

## Steps

1. Give each action, command, expected intermediate result, and decision point in
   execution order.

## Expected Results

- Observable success state and the evidence that distinguishes it from partial
  or failed execution.

## Stop Conditions

- Exact condition that requires stopping, escalating, or returning to diagnosis.

## Rollback

State the safe recovery procedure and its boundary. If rollback is impossible,
state that explicitly and name the required escalation.

## Historical Source Content

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
- `/srv/scratch/sir-convert-a-lot/bin`
- `/srv/scratch/sir-convert-a-lot/cache`
- `/srv/scratch/sir-convert-a-lot/cache/huggingface`

Canonical llama.cpp server binary:

```text
/srv/scratch/sir-convert-a-lot/bin/llama-server
```

This symlink must point to the current HIP-enabled llama.cpp build for GGUF
answer-key model probes. Do not use older home-directory builds for Qwen3.5 or
Gemma 4 validation; they may lack current architecture support.

## llama.cpp HIP Build Stability

`llama.cpp` HIP builds are heavyweight host operations.

- Serialize: build first, verify the binary, then launch model providers and
  run probes.
- Do not overlap with local model serving, full advisory-corpus evaluation,
  large model downloads, Docker image rebuilds, or other GPU/offload work.
- Do not raise parallelism during an operator session just because the host has
  idle cores. Prior `-j16` HIP builds made SSH/Tailscale access unreliable;
  `nice -n 10` with `-j8` kept the recovered host responsive.

Preflight:

```bash
pdm run run-hemma -- uptime
pdm run run-hemma -- ps -eo pid,stat,ni,pcpu,pmem,comm,args
pdm run run-hemma -- rocm-smi --showmeminfo vram --showpids
```

Build:

```bash
pdm run qwen-llama-provider-build
```

The helper is the preferred command surface for Task 320 and enforces the
`nice -n 10` / `-j8` contract. Its expanded command is:

```bash
cd /srv/scratch/sir-convert-a-lot/build/llama.cpp-qwen35
cmake -S . -B build-hip -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON \
  -DAMDGPU_TARGETS=gfx1201 \
  -DGGML_HIP_GRAPHS=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON
nohup nice -n 10 ninja -C build-hip -j8 llama-server \
  > build-hip/build-log.txt 2>&1 &
```

Recovery:

- After a host reset or interrupted configure, zero-byte `build.ninja` or
  `CMakeCache.txt` means corrupt generator state. Recreate `build-hip` and
  reconfigure; do not resume from object files alone.
- For `relocation R_X86_64_32 ... can not be used when making a PIE object`,
  reconfigure with `-DCMAKE_POSITION_INDEPENDENT_CODE=ON` and rerun the bounded
  detached build. Do not disable PIE unless a governed task records that
  exception.

## GPU Verification

Use these probes before GPU workload changes:

```bash
pdm run run-hemma -- rocminfo
pdm run run-hemma -- rocm-smi
```

If GPU readiness is missing, fail the lane and record the degraded state in the
governing task. Do not silently switch to CPU execution.

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

## Docling GPU Validation

Docling and OCR GPU validation belongs in the governing parser/converter task.
Keep the runbook to runtime invariants and link detailed evidence from the task
or reference document.
