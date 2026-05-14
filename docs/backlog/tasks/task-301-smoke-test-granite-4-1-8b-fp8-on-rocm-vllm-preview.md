---
id: 'task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview'
title: 'Smoke test Granite 4.1 8B FP8 on ROCm vLLM preview'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
labels:
  - hemma
  - rocm
  - vllm
  - fp8
  - granite
  - structured-output
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run a bounded Hemma smoke test proving whether
`ibm-granite/granite-4.1-8b-fp8` can start on the AMD R9700/RDNA4 ROCm vLLM
preview runtime and answer a minimal structured-output MCQ request.

This task is a runtime viability checkpoint for the answer-key completion lane.
It does not select the production model, replace the `llama.cpp` GGUF benchmark
matrix, or authorize provider integration before Task 296.

## PR Scope

- Verify current Hemma path, GPU, Docker, scratch/cache, and port state before
  starting the container.
- Pull the AMD ROCm vLLM preview image for `gfx120X-all` if it is not already
  present:
  `rocm/vllm:rocm7.12.0_gfx120X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0`.
- Start a named, detachable vLLM OpenAI-compatible server container with:
  - `/dev/kfd` and `/dev/dri` exposed;
  - host networking on a non-conflicting local port;
  - `/home/paunchygent/.cache/huggingface` mounted as `/app/models`;
  - `HF_HOME=/app/models`;
  - ROCm SDK library path workaround;
  - `FLASH_ATTENTION_TRITON_AMD_ENABLE=TRUE`;
  - `ibm-granite/granite-4.1-8b-fp8`;
  - `--max-model-len 4096`;
  - first attempt with `--gpu-memory-utilization 0.75`;
  - lower utilization only if co-resident Hemma GPU services leave too little
    free VRAM, with the deviation recorded in this task;
  - `--enable-prefix-caching`;
  - `--disable-log-requests`.
- Run a sanity check for vLLM/PyTorch/HIP device visibility inside the same
  image.
- Run a minimal Chat Completions structured `choice` request that must emit only
  the answer ID for a known MCQ.
- Capture operational evidence in this task: port, container name, image ID,
  model, selected endpoint, log summary, structured-output result, and cleanup
  state.

## Deliverables

- [x] Hemma preflight report: repo path, GPU identity, Docker readiness,
  selected port, and conflicting-port avoidance.
- [x] Container launch evidence for the named vLLM smoke container.
- [x] Runtime sanity evidence for `vllm.__version__`, HIP availability, device
  name, and HIP version.
- [x] Structured `choice` smoke response for the known MCQ.
- [x] Failure classification if startup or structured output fails.
- [x] Cleanup/status note documenting whether the smoke container is stopped or
  intentionally left running for follow-up probing.

## Acceptance Criteria

- [x] The smoke uses the ROCm 7.12 `gfx120X-all` preview image, not a host pip
  install or unrelated CUDA image.
- [x] The selected port is proven free before launch.
- [x] The server reaches the OpenAI-compatible model-list or chat-completion
  surface on Hemma localhost.
- [x] The MCQ structured-output request returns the constrained choice `B`
  without wrapper JSON, rationale, or fallback parsing.
- [x] Logs are checked for startup failures, FP8/quantization rejection, HIP
  device visibility failures, or obvious fallback-kernel warnings.
- [x] The final evidence explicitly says whether Granite 4.1 8B FP8 is a viable
  candidate for deeper structured-output experiments.

## Stop Conditions

- Stop before changing production Sir Convert deployment, compose files,
  service ports, or public routes.
- Stop if the required Docker/ROCm device path is unavailable.
- Stop if all reasonable non-conflicting local ports are occupied.
- Stop if the image pull or model download would require destructive cache or
  Docker pruning.
- Stop before treating a successful smoke as model selection; Task 300 still
  owns the benchmark matrix and real-data correctness comparison.

## Execution Evidence

Run date: 2026-05-14.

Hemma preflight:

- Canonical repo root verified at `/home/paunchygent/apps/sir-convert-a-lot`.
- Port scan showed `8000`, `8017`, `18017`, and `28017` free; the smoke used
  `127.0.0.1:8017`.
- Running containers already used the service/observability ports including
  `28085`, `8085`, `9000-9002`, `9090-9094`, `9187`, `9308`, `3000`, `3100`,
  `4317-4318`, `16686`, `80`, and `443`.
- Scratch and cache headroom was sufficient: `/srv/scratch` had about `250G`
  free and the OS/cache filesystem had about `282G` free.
- Existing ROCm processes were present before the smoke:
  `sir_convert_a_lot_prod`, HuleEdu RST parser, and HuleEdu essay offload.
  `rocm-smi` reported the R9700 at `25%` VRAM before vLLM launch.

Image/runtime:

- Image:
  `rocm/vllm:rocm7.12.0_gfx120X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0`.
- Repo digest:
  `rocm/vllm@sha256:6c30a80030864070f44d1b2ab44ad95fe0fda3ef07079e12c7ea4a6fa4c18f2d`.
- Image ID:
  `sha256:914354c09c17be02d1418836db2cd11efa89dc202237292e81c17e69bf5d2f15`.
- Container sanity check passed:
  `vLLM: 0.16.1.dev10+g11515110f.d20260323`,
  `HIP available: True`, `Device: AMD Radeon AI PRO R9700`,
  `HIP: 7.12.60610-2bd1678d3d`.

Serve attempts:

- The first serve attempt used `--gpu-memory-utilization 0.75` and failed before
  model load because existing GPU services left `22.26 GiB` free while vLLM
  requested `22.39 GiB`.
- The successful retry used `--gpu-memory-utilization 0.70` on the same port,
  model, image, and runtime settings.
- Startup logs resolved `GraniteForCausalLM`, used `max_model_len 4096`,
  configured `quantization=compressed-tensors`, selected
  `ChannelWiseTorchFP8ScaledMMLinearKernel` for `CompressedTensorsW8A8Fp8`, and
  used the Triton attention backend.
- Startup warning observed:
  `AITER is not found or QuarkOCP_MX is not supported on the current platform.
  QuarkOCP_MX quantization will not be available.`
- Weight download took about `150.6s`; safetensors loading took about `24.0s`;
  model loading used `9.05 GiB`; torch compile took about `76.9s`; graph
  capture took about `13s` and `2.83 GiB`.
- vLLM reported available KV cache memory of `10.2 GiB`, GPU KV cache size of
  `66,816` tokens, and maximum concurrency of `16.31x` at `4096` tokens per
  request.
- `/v1/models` returned
  `ibm-granite/granite-4.1-8b-fp8` with `max_model_len: 4096`.

Structured-output smoke:

- Request path: OpenAI-compatible `/v1/chat/completions`.
- Constraint: `extra_body={"structured_outputs": {"choice": ["A", "B", "C", "D"]}}`.
- Prompt asked for the correct answer ID only for the chemical symbol `Al`.
- Response content: `B`.
- Usage: `prompt_tokens=104`, `completion_tokens=2`, `total_tokens=106`.

Cleanup:

- Smoke container name: `scalo-task301-granite-vllm`.
- The container was stopped after the smoke and is left exited for short-term
  log/evidence inspection: `Exited (0)`.
- The downloaded Docker image and Hugging Face model cache were retained; no
  Docker pruning, production service change, or cache deletion was performed.

Verdict:

Granite 4.1 8B FP8 is viable for deeper structured-output experiments on
Hemma's R9700 ROCm vLLM preview lane when co-resident GPU services are accounted
for. The default `0.75` GPU memory reservation is too tight while current
Hemma services are live, so follow-up experiments should start at `0.70` or run
in an isolated GPU window before making throughput claims.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Follow-up Runtime Decision

Post-smoke runtime adoption keeps the successful Granite FP8/vLLM settings, but
normalizes cache layout to the existing Sir Convert Hemma model-cache contract
used by HF-backed llama.cpp/Qwen/TTS lanes:

- canonical host cache:
  `/srv/scratch/sir-convert-a-lot/cache/huggingface`;
- Docker-visible home mirror:
  `/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface`;
- container mount:
  `/cache/huggingface`;
- container environment:
  `HF_HOME=/cache/huggingface`,
  `HF_HUB_CACHE=/cache/huggingface/hub`,
  `TRANSFORMERS_CACHE=/cache/huggingface`.

The smoke used `/home/paunchygent/.cache/huggingface:/app/models` as an
operator shortcut. Follow-up vLLM runs must use the canonical scratch-backed
cache path above unless the bind-root probe fails and the task explicitly
records the exception.
