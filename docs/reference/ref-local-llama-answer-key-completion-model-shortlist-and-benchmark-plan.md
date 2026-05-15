---
type: reference
id: REF-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan
title: Local Model Answer-key Completion Runtime And Benchmark Plan
status: active
created: 2026-05-14
updated: 2026-05-14
owners:
  - platform
tags:
  - llama-cpp
  - vllm
  - gguf
  - fp8
  - benchmark
  - answer-key-completion
  - structured-output
  - local-models
links:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
---

## Purpose

This reference records the first local `llama.cpp` GGUF model shortlist and
the current vLLM FP8 working model for Sir Convert-a-Lot's machine-marked
answer-key completion route.

The current implementation default is **vLLM serving
`ibm-granite/granite-4.1-8b-fp8`** on Hemma's R9700 ROCm preview lane. That
choice is an interim engineering default so the feature can be implemented
against a concrete local structured provider. Final model selection still
requires live structured experiments on real teacher/DigiExam items with
grammar/schema-constrained decoding and backend validation.

## Current Working Runtime

Use this runtime for the first Sir Convert implementation of the local
answer-key completion provider until Task 300 runs the deeper comparative
benchmark:

```text
provider_runtime: vllm
model: ibm-granite/granite-4.1-8b-fp8
container_image: rocm/vllm:rocm7.12.0_gfx120X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0
container_image_digest: rocm/vllm@sha256:6c30a80030864070f44d1b2ab44ad95fe0fda3ef07079e12c7ea4a6fa4c18f2d
host_device: AMD Radeon AI PRO R9700
endpoint_kind: chat_completions
structured_output_mode: vllm_structured_outputs
first_proven_constraint: choice
host_bind: 127.0.0.1
default_candidate_port: 8017
max_model_len: 4096
gpu_memory_utilization: 0.70
prefix_caching: enabled
request_log_capture: disabled
```

Task 301 proved:

- the ROCm vLLM image imports vLLM and PyTorch HIP correctly on R9700;
- Granite 4.1 8B FP8 loads with compressed-tensors FP8 and Triton attention;
- the OpenAI-compatible `/v1/models` and `/v1/chat/completions` surfaces start;
- `structured_outputs.choice` returned the constrained MCQ answer `B`.

The original `0.75` memory setting was too tight while Sir Convert and HuleEdu
GPU services were live. Keep `0.70` as the shared-host default unless a task
runs in an isolated GPU window and records a higher safe setting.

## Hemma Model Cache Contract

Granite FP8 vLLM runs use the same scratch-backed Hugging Face cache method as
the existing HF-backed llama.cpp/Qwen/TTS lanes:

```text
canonical_host_cache: /srv/scratch/sir-convert-a-lot/cache/huggingface
docker_visible_cache: /home/paunchygent/.data/sir-convert-a-lot/cache/huggingface
container_mount: /cache/huggingface
HF_HOME: /cache/huggingface
HF_HUB_CACHE: /cache/huggingface/hub
TRANSFORMERS_CACHE: /cache/huggingface
```

The Task 301 smoke initially downloaded the model to
`/home/paunchygent/.cache/huggingface`. On 2026-05-14, that snapshot was copied
to the canonical cache and verified as visible inside the ROCm vLLM image at:

```text
/cache/huggingface/hub/models--ibm-granite--granite-4.1-8b-fp8
```

Do not introduce a second long-lived vLLM cache tree. If Docker bind-root
preflight fails, stop and record the failure rather than falling back to
redownloading into container-local or home-only cache paths.

## Selection Boundary

The first pass evaluates local text models for answer-key completion only:

- classic single-choice and multiple-choice decisions;
- matching pair decisions;
- real open cloze / gap-fill accepted-value decisions.

Excluded from the first pass:

- visual/OCR-dependent item interpretation;
- free-text rubric reconstruction;
- reasoning traces or rationale generation;
- normal prompting or "use JSON" fallback behavior outside constrained
  grammar/schema decoding.

Structured-output support is treated as a runtime property enforced by the
provider adapter, followed by Sir Convert backend validation. For llama.cpp
candidates this means GBNF or JSON Schema constrained decoding. For the interim
vLLM runtime this means `structured_outputs` constraints, starting with
`choice` for MCQ/MCW decisions and expanding to JSON Schema only behind
provider-harness tests. Do not trust a model card's tool-calling claim as
sufficient proof for this route.

## Verified Source Notes

Checked on 2026-05-14 against Hugging Face model cards and `llama.cpp`
documentation:

- Qwen3.5 4B and 9B cards list 262,144-token native context and explicit
  OpenAI-compatible serving/tool-call parser guidance. The Qwen card states
  Qwen3.5 thinks by default and shows `enable_thinking: false` through
  `chat_template_kwargs` for direct responses.
- llama.cpp supports `/v1/chat/completions` `response_format` with
  `type: "json_schema"` and supports grammar / JSON Schema constrained output.
- The benchmark must run non-thinking/direct-output mode for Qwen-style
  candidates. Thinking traces are incompatible with the route's strict bounded
  decision objects.
- Nemotron 3 Nano 4B is an edge/agentic candidate, but the card lists English as
  its supported language; it must be treated as a comparison candidate for this
  Swedish/English school-item route, not as the default.

## Ranked Candidate Pool

The current working runtime above is the implementation default. All rows below
remain mandatory first-pass benchmark entries once Task 300 compares the settled
vLLM Granite FP8 route against the GGUF local candidates.

| Rank | Model | First quant | Role | Reason to test |
|---:|---|---|---|---|
| 1 | `unsloth/Qwen3.5-4B-GGUF` | `UD-Q6_K_XL` | Default local primary candidate | 4B size, long context, multilingual/tool-call card evidence, manageable memory. |
| 2 | `unsloth/gemma-4-E4B-it-GGUF` | `Q6_K` | Alternate primary candidate | Strong practical 4B-8B band candidate with multilingual/on-device positioning. |
| 3 | `unsloth/granite-4.1-8b-GGUF` | `Q6_K` | Tool-call compliance comparator | Explicit tool/function-calling model-card evidence, heavier runtime footprint. |
| 4 | `unsloth/Qwen3.5-9B-GGUF` | `Q6_K` | Quality fallback candidate | Higher-capacity Qwen candidate if 4B fails on real gap-fill or matching items. |
| 5 | `unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF` | `UD-Q6_K_XL` | Edge/agentic comparison candidate | Small agentic model; language caveat makes it non-default for this route. |

Watchlist only:

- `unsloth/Qwen3.5-0.8B-GGUF`: harness smoke-test candidate, not production
  answer-key candidate.
- `unsloth/gemma-4-E2B-it-GGUF`: tiny-machine fallback only.
- `unsloth/Qwen3-VL-4B-Instruct-GGUF`: separate future visual/OCR candidate,
  not this text-only 2026-filtered pass.
- `unsloth/Falcon-H1R-7B-GGUF`: watchlist until stronger first-party
  function-calling evidence is available.

## Benchmark Protocol

Run the matrix against a real-data corpus with item-level expected answers and
source bindings:

- classic multiple choice;
- multiple response;
- matching;
- real open cloze / gap-fill.

Each run must use only constrained decoding:

- `llama.cpp` JSON Schema or GBNF constraints;
- no normal prompting fallback;
- no relaxed "return JSON" fallback;
- no parser repair of malformed semantic answers;
- no model-generated confidence, rationale, provenance, or explanations.

The prompt may describe the bounded decision task and schema semantics, because
schema constraints do not inject task meaning by themselves. It must still be
single-turn and item-local, with no full exam, raw `.dxe`, result PDF content,
student data, owner metadata, or artifact paths.

## Required Metrics

The primary metric is **wrong-but-valid answer rate**. A model that emits
manual follow-up more often is safer than a model that fills plausible but wrong
keys.

Record at minimum:

- structured call success rate;
- valid JSON / grammar-conformant rate;
- backend-valid decision rate;
- correctness rate by item type;
- wrong-but-valid answer rate;
- `manual_follow_up_required` rate;
- unknown-ID hallucination rate;
- gap-ID correctness;
- matching pair completeness;
- duplicate/invalid selection rate;
- latency per item;
- tokens per second;
- RAM/VRAM footprint;
- backend failure-code distribution.

Promotion requires per-item evidence, not only aggregate benchmark scores.

## Architecture Requirements

The benchmark harness must follow the same boundaries as the production route:

- domain models for model profile, quant profile, item fixture, structured
  decision, backend validation result, and benchmark report;
- application services for matrix planning, item execution, result evaluation,
  and report aggregation;
- infrastructure adapters for `llama.cpp` process/server lifecycle and
  structured provider calls;
- Dishka DI for provider profiles, clock/ID generation, report sinks, corpus
  loaders, and runtime adapters where it clarifies composition;
- no parser, renderer, or HTTP artifact-route dependency on benchmark internals.

The benchmark result should be a deterministic JSON report plus a concise
Markdown summary. The summary may recommend a candidate for the next runtime
slice only when wrong-but-valid risk, manual-follow-up burden, and latency are
all visible.
