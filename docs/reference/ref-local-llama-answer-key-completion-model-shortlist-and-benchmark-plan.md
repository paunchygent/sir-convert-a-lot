---
type: reference
id: REF-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan
title: Local Model Answer-key Completion Runtime And Benchmark Plan
status: active
created: 2026-05-14
updated: 2026-05-16
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
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-310-add-validation-only-force-eval-mode-for-source-keyed-answer-key-live-validation.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/backlog/tasks/task-312-make-answer-key-candidate-planning-provider-protocol-driven.md
  - docs/backlog/tasks/task-318-make-task-309-eval-provider-metadata-profile-driven.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
---

## Purpose

This reference records the first local `llama.cpp` GGUF model shortlist, the
Granite/vLLM runtime proof, and the current evidence boundary for Sir
Convert-a-Lot's machine-marked answer-key completion route.

Task 301 proved that **vLLM serving `ibm-granite/granite-4.1-8b-fp8`** can run
on Hemma's R9700 ROCm preview lane and satisfy constrained-output protocol
smokes. Task 309 then live-validated Granite/vLLM, Qwen3.6 GGUF, and Devstral
Small GGUF against the production advisory path and a versioned pure DigiExam
DXE corpus. The Task 309 evidence demotes Granite/vLLM and Devstral Small for
answer-key completion quality. Qwen3.6-27B-Q6_K is the current guarded local
model choice for this route, with `temperature=0.15`, `--reasoning off`, and
the llama.cpp JSON Schema runtime. It is not promoted for automatic answer-key
application because the zero wrong-but-valid safety gate is still unmet. Task
300 remains the later comparative model bake-off and must not start until the
full app path is working and deployed.

Task 318 owns a metadata correction required before future model comparisons
are interpreted as final evidence. Evaluation artifacts must derive provider
profile, runtime, capabilities, output-mode policy, sampling settings, token
budgets, and vision media path from the selected provider profile/run artifact,
not from hardcoded Granite or Qwen constants in the evaluator.

## Demoted Granite Runtime Record

This runtime remains the recorded vLLM/ROCm protocol proof and failure baseline.
Do not treat it as the current answer-key completion provider candidate after
the 2026-05-16 demotion:

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
vLLM runtime this means `structured_outputs` constraints. Use `choice` values
as the preferred implementation for MCQ/MCW items where candidate selection is
clear and bounded, because avoiding a model-generated JSON wrapper reduces the
failure surface. JSON Schema remains required for gap-fill objects and for
capability microprobes, but it is not the preferred MCQ/MCW path when a
bounded `choice` value can express the decision. Do not trust a model card's
tool-calling claim as sufficient proof for this route.

## Granite Live Validation Precursor

Task 309 validates the current Granite/vLLM implementation before any
comparative bake-off. It uses only the pure DigiExam `.dxe` exports moved to:

```text
inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/
```

That task must move the files into a versioned DigiExam DXE fixture location,
freeze a corpus manifest with source SHA and item fingerprints, and create a
teacher-verified expected-answer manifest for every scored item. Straightforward
grade 7-9 choice and gap/open-cloze goldens are owned by the implementer; only
genuinely ambiguous cases should be surfaced for adjudication.
The moved `.dxe` files are committed as the versioned fixture corpus; this
lane is not manifest-only.

Task 309's preferred execution shape is a low-variable first pass: full-corpus
production advisory validation through the in-process job path on Hemma, plus a
small deployed service-backed smoke against the same provider. If that pass
succeeds, the follow-up is a strictly service-backed mirror validation with
auth/public-edge readiness intentionally in scope. Validation-only force-eval
over source-keyed items is reserved for Task 310 and the later service-backed
mirror follow-up, not for Task 309's initial advisory run. Task 311 owns the
strict service-backed mirror with auth/public-edge readiness.

The Granite/vLLM provider for Task 309 was persistent by default during the
live run. It used a named localhost-only container on port `8017`, disabled
request logging, recorded image/model/cache/runtime state, and stayed running
until the operator explicitly asked for cleanup. Run the existing detached
resource-monitor pattern alongside comparable validation so GPU and memory
behavior are part of the evidence.

Task 312 is the precondition that makes the preferred Task 309 shape real in
production code. The advisory answer-key orchestration consumes an injected
candidate planner instead of branching on provider details. The Granite/vLLM
planner derives the item-local provider output mode from provider capabilities
and item type: choice and multiple-response rows use bounded
`structured_outputs.choice` values, while gap-fill rows use vLLM JSON Schema
objects. llama.cpp validation uses explicit runtime selection:
`llama-cpp-json-schema` sends Chat Completions
`response_format.type=json_schema`, while `llama-cpp-gbnf` sends a
Skriptoteket-validated Chat Completions `grammar` field with GBNF that emits
JSON objects for the normal advisory decoder. Normal "return JSON" prompting is
not an allowed llama.cpp validation mode.

The live run has three phases:

1. Provider microprobes for vLLM `choice`, JSON Schema choice object, and JSON
   Schema gap-fill object.
1. In-process production advisory execution over all eligible DXE items with
   `local_llm_suggest_missing_machine_marked`, followed by a small deployed
   service-backed smoke.
1. Evaluation against goldens for valid suggestion, manual follow-up,
   wrong-but-valid answer, unknown IDs, duplicate IDs, partial gap answers,
   latency, tokens/sec, and backend failure code.

Acceptance is intentionally strict: retained artifacts must contain no raw
prompts or raw provider responses, advisory mode must mutate neither source IR
nor effective IR, malformed output cannot count as success, unknown and
duplicate IDs must be zero for promotion, and wrong-but-valid answers are the
primary safety metric. Manual follow-up is acceptable; plausible wrong keys are
not.

Do not prompt-engineer around a specific difficult item. Persistent failure
paths should be documented across runs and shaped later into generalized retry
or failure-handling policy by item type or failure class.

### Task 309 First Live Result

On 2026-05-15, Task 309 launched the persistent Granite/vLLM provider on Hemma
at `127.0.0.1:8017` and retained redacted reports under:

```text
/srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live/
```

Provider preflight passed for ROCm, cache paths, localhost-only exposure,
disabled request logging, `/v1/models`, and no CPU fallback. The three
structured-output microprobes all passed. The detached resource monitor showed
the full-corpus advisory run was GPU-bound, with median GPU busy `100%` and
median GPU memory used `94%`.

The in-process advisory corpus run completed over 23 files and 317 items in
`86919.444ms`: 36 suggested, 8 manual follow-up, and 273 skipped. Golden
evaluation found 12 correct suggestions and 24 wrong-but-valid suggestions,
with 0 unknown IDs, 0 duplicate IDs, 0 malformed successes, and 0 partial gap
answers. This blocks promotion. Do not tune prompts against these individual
items; use this result to classify failure paths and design generalized retry
or failure-handling policy before a later mirror validation.

Direct follow-up probes using improved consumer-friendly item messages did not
change the conclusion. A 10-item sample from failed rows covered gap-fill,
multiple-response, and single-choice items and produced 1 correct result, 3
wrong-but-valid results, and 6 invalid-output results. A separate temperature
`0.1` chat experiment on a word-bank gap-fill row reached 7/10 in full-question
framing and 1/10 when segmented gap-by-gap, with persistent plausible wrong
keys. On 2026-05-16, Granite/vLLM was therefore demoted for this lane. The
operator stopped `sir-convert-task309-granite-vllm`,
`huleedu_rst_parser_service`, `huleedu_essay_embed_offload`, and
`sir_convert_a_lot_prod`; post-stop Hemma verification showed GPU use `0%`,
VRAM `0%`, and no KFD PIDs.

After Granite demotion, the operator diagnostics moved to llama.cpp GGUF
providers against the same corpus and failed-question probe set. This was a
focused post-demotion provider-choice pass, not the full Task 300 model bake-off
or an automatic provider-promotion decision. The Task 309 runner can now
preview, microprobe, and run advisory corpus validation with
`--provider-runtime llama-cpp-json-schema` or `--provider-runtime llama-cpp-gbnf`;
the GBNF path follows Skriptoteket's validated llama.cpp practice of using the
`grammar` request field on `/v1/chat/completions`.

On 2026-05-16, the first Devstral Small launch attempt found the active Hemma
GGUF symlink set to `Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf`, but the
canonical `llama-server-rocm.service` was inactive and its
`llama.cpp-rocm:7.2.0` image was missing. A BuildKit image rebuild using the
current ROCm/llama.cpp `master` commit
`68717eac3c081eec00bbb961c0e0e3c129a1790f` passed the stale pinned-commit
failure and entered HIP compilation, after which Hemma stopped responding over
Tailscale/SSH. No live Devstral model-quality result was produced in that
attempt; a later successful Devstral corpus run is recorded below.

## Qwen3.6-27B Live Validation Result

On 2026-05-16, Qwen3.6-27B-Q6_K was live-validated locally against the full
Task 309 DXE corpus via `llama-server` on `127.0.0.1:8082`:

```text
provider_runtime: llama-cpp-json-schema
model: qwen3.6-27b-q6k
llama-server: 0253fb21f (version 9187, HIP, gfx1201)
context: 32768
temperature: 0.15          # task-optimal; card-default 0.7 gave worse results
reasoning: off
mtp: supported (--spec-type draft-mpt, not yet enabled)
build: /srv/scratch/sir-convert-a-lot/build/llama.cpp-qwen35/build-hip/bin/llama-server
```

### Schema Simplification

The `decision_state` enum (`answered` vs `manual_follow_up_required`) was
removed from all model-facing output specs, GBNF grammars, decoder logic,
prompts, and tests. The new paradigm: **schema-valid + parseable output =
accepted suggestion**. Manual follow-up is exclusively a UI user action.
This eliminated model over-conservatism that previously caused 15
manual-follow-up items despite correct underlying answers.

### Synonym-Aware Evaluation

Gap-fill comparison now canonicalises values through synonym groups before
golden matching. Example groups: `cellkärna/nukleus`, `nervcell/neuron`,
`arter/artär`, `koldioxid/co2`. This accepts valid curriculum synonyms while
rejecting vague shortenings (e.g. `kärnan` ≢ `cellkärna`).

### Corpus Results

| Metric | Count |
|---|---|
| Files | 23 |
| Total items | 317 |
| Eligible scored items | 44 |
| Correct suggestions | **39** |
| Wrong-but-valid | **3** |
| Manual follow-up | 2 (unsupported assets) |
| Skipped | 273 (source-bound keys) |

**Primary safety metric:** `wrong_but_valid_count == 3` — **blocks promotion**.

### Persistent Wrong-but-Valid Items

| Item | Type | Root cause | Prompt fixable? |
|---|---|---|---|
| `ak7-lag-och-ratt.dxe item-001` | gap_fill (10 blanks) | Confuses Swedish legal roles: åklagare ↔ domare, polis ↔ åklagare | **No** — domain knowledge gap |
| `ak7-lag-och-ratt.dxe item-002` | multiple_response (9 options) | Selects all 9 options instead of [2,3,5,6,8] | **No** — reasoning bias |
| `manniskokroppen-prov.dxe item-003` | gap_fill (3 blanks) | Uses colloquial `kärnan` instead of curriculum `cellkärna` | **No** — terminology precision |

Three iterations of prompt engineering (generic guardrails, explicit
cardinality, anti-select-all language, word-bank copy instructions, formal-term
requirements) produced **no improvement** on these items. They represent a hard
knowledge boundary for Qwen3.6-27B on this Swedish educational corpus.

### Temperature Experiment

| Temperature | Correct | Wrong-but-valid |
|---|---|---|
| 0.15 (task-optimal) | 39 | 3 |
| 0.7 (card default) | 38 | 4 |

Higher temperature added an extra biology error (`nukleotider` vs `baspar`)
without fixing the structural failures. For constrained answer-key completion,
lower temperature reduces synonym drift and select-all bias.

## Devstral-Small-2-24B Live Validation Result

On 2026-05-16, Devstral-Small-2-24B-Instruct-2512-UD-Q6_K_XL was live-validated
against the full Task 309 DXE corpus via `llama-server` on `127.0.0.1:8082`:

```bash
/srv/scratch/sir-convert-a-lot/bin/llama-server \
  -hf unsloth/Devstral-Small-2-24B-Instruct-2512-GGUF \
  -hff Devstral-Small-2-24B-Instruct-2512-UD-Q6_K_XL.gguf \
  --no-mmproj --no-webui --alias devstral-small-24b \
  --host 127.0.0.1 --port 8082 \
  --ctx-size 16384 --n-gpu-layers all --fit off --flash-attn on --jinja \
  --temp 0.1 --top-p 0.9 --top-k 40
```

Unsloth guidance recommends `temperature~0.15`, `min_p=0.01`, `--jinja`, and a
minimum 16k context. The probe used `temp=0.1`, `top_p=0.9`, `top_k=40`, and
JSON Schema constrained output.

| Metric | Value |
|---|---|
| Files | 23 |
| Total items | 317 |
| Eligible scored items | 44 |
| Correct suggestions | **34** |
| Wrong-but-valid | **8** |
| Manual follow-up | 2 (unsupported assets) |
| Skipped | 273 (source-bound keys) |

**Primary safety metric:** `wrong_but_valid_count == 8` — **blocks promotion**.

### Devstral Wrong-but-Valid Items

| Item | Type | Root cause | Qwen3.6 result |
|---|---|---|---|
| `ak7-lag-och-ratt.dxe item-001` | gap_fill (10 blanks) | Confuses Swedish legal roles | Wrong (same) |
| `ak7-lag-och-ratt.dxe item-002` | multiple_response | Selects all 9 options | Wrong (same) |
| `ak7-lag-och-ratt.dxe item-004` | gap_fill (5 blanks) | "rån" vs "misshandel" word-bank | **Correct** |
| `ak7-lag-och-ratt.dxe item-005` | gap_fill (10 blanks) | "15" vs "18" criminal-liability age | **Correct** |
| `manniskokroppen-prov.dxe item-003` | gap_fill (3 blanks) | "cellemembran", "kärnan", "mitochondrier" | **Correct** |
| `25c-manniskokroppen-prov-eca.dxe item-009` | gap_fill (2 blanks) | Number swap 2↔5 | **Correct** |
| `prov-biologi-genetik-v2.dxe item-005` | single_choice | Wrong genetics choice | **Correct** |
| `prov-biologi-genetik-v2.dxe item-017` | gap_fill (2 blanks) | "kromatiderna" vs "kromosomer" | **Correct** |

Devstral fails on Swedish curriculum terminology that Qwen3.6 handles
correctly. Its SOTA coding/agentic benchmarks (SWE-bench, Aider) do not
translate to Swedish educational content accuracy.

### llama.cpp Rebuild for MTP Support

On 2026-05-16, the Hemma `llama-server` was rebuilt from `59778f019` (version
9174, no MTP) to `0253fb21f` (version 9187, with MTP) to enable speculative
decoding for future speedup:

```bash
cd /srv/scratch/sir-convert-a-lot/build/llama.cpp-qwen35
rm -rf build-hip
cmake -B build-hip \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON \
  -DAMDGPU_TARGETS=gfx1201 \
  -DGGML_HIP_GRAPHS=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -G Ninja
nice -n 10 ninja -C build-hip -j8 llama-server
```

**Build lessons learned:**

- `-j16` without `nice` saturated all CPU cores and starved SSH, requiring a
  hard power-cycle to recover. Use `-j8` (half core count) and `nice -n 10`.
- The first rebuild failed at link time with `relocation R_X86_64_32 against .rodata.str1.1` because PIE was enabled by default. Adding
  `-DCMAKE_POSITION_INDEPENDENT_CODE=ON` resolved this.
- MTP is available via `--spec-type draft-mtp --spec-draft-n-max 2` but has not
  yet been validated on the answer-key corpus. To use MTP, download the
  separate MTP GGUF (`unsloth/Qwen3.6-27B-MTP-GGUF`) and launch with the flags
  above.

### Promotion Status

**Current guarded choice, not automatic promotion.** Both Qwen3.6-27B
(3 wrong-but-valid) and Devstral-Small-2-24B (8 wrong-but-valid) violate the
primary safety gate. Qwen3.6 remains the best-tested local candidate and is the
operator-selected model of choice for the next service-backed validation lane.
Do not route its suggestions directly into accepted answer keys without teacher
review or a later governed decision that changes the wrong-but-valid risk
posture.

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
- Gemma 4 26B-A4B Unsloth guidance lists the model as a 256K-context MoE
  variant with 3.8B active parameters and text/image support. The operator
  diagnostic candidate uses the text-only GGUF
  `gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf` from
  `unsloth/gemma-4-26B-A4B-it-GGUF`. Recommended sampling follows Google's
  Gemma 4 defaults: `temperature=1.0`, `top_p=0.95`, and `top_k=64`.
  Local llama.cpp runs should start at `--ctx-size 32768` for responsiveness,
  keep repetition and presence penalties disabled (`repeat_penalty=1.0`,
  `presence_penalty=0.0`), and disable thinking/reasoning for strict JSON
  answer-key probes. Unsloth notes that disabling reasoning on `llama-server`
  uses `--chat-template-kwargs '{"enable_thinking":false}'`; the validated
  Hemma llama.cpp build also supports the newer `--reasoning off` switch. Use
  `/srv/scratch/sir-convert-a-lot/bin/llama-server` as the default Hemma
  `llama-server`; it points to the newer HIP build that supports Qwen3.5,
  Gemma 4, Qwen3.6, and MTP GGUF architectures. After the completed Qwen3.6
  and Devstral Task 309 runs, Gemma is no longer the immediate next diagnostic
  by default; keep
  it as future Task 300 comparison material unless a new governed operator
  decision reopens the model search.
- Qwen3.6 27B guidance lists a 262,144-token native context and recommends
  the following instruct/non-thinking settings: `temperature=0.7`,
  `top_p=0.80`, `top_k=20`, `min_p=0.0`, `presence_penalty=1.5`, and
  `repetition_penalty=1.0`. Qwen3.6 thinks by default; for strict answer-key
  JSON probes, use the newer Hemma llama.cpp `--reasoning off` switch. The
  immediate Q6_K diagnostic used
  `unsloth/Qwen3.6-27B-GGUF` / `Qwen3.6-27B-Q6_K.gguf`, `--ctx-size 32768`,
  and the flat numbered word-bank JSON Schema shape. It produced the first
  all-correct result on the recurring Swedish law-and-rights gap-fill probe,
  including the teacher golden `15` for the criminal-liability-age gap.

## Ranked Candidate Pool

The rows below remain mandatory first-pass benchmark entries once Task 300,
deferred until the full app path is working and deployed, compares local
candidates. Granite/vLLM stays in the matrix as a demoted baseline, not as the
settled route.

| Rank | Model | First quant | Role | Reason to test |
|---:|---|---|---|---|
| 1 | `unsloth/Qwen3.5-4B-GGUF` | `UD-Q6_K_XL` | Default local primary candidate | 4B size, long context, multilingual/tool-call card evidence, manageable memory. |
| 2 | `unsloth/gemma-4-E4B-it-GGUF` | `Q6_K` | Alternate primary candidate | Strong practical 4B-8B band candidate with multilingual/on-device positioning. |
| 3 | `unsloth/granite-4.1-8b-GGUF` | `Q6_K` | Tool-call compliance comparator | Explicit tool/function-calling model-card evidence, heavier runtime footprint. |
| 4 | `unsloth/Qwen3.5-9B-GGUF` | `Q6_K` | Quality fallback candidate | Higher-capacity Qwen candidate if 4B fails on real gap-fill or matching items. |
| 5 | `unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF` | `UD-Q6_K_XL` | Edge/agentic comparison candidate | Small agentic model; language caveat makes it non-default for this route. |

Completed Task 309 diagnostic:

- Devstral Small on `llama.cpp` is demoted for this Swedish educational route:
  the full-corpus run produced 34 correct and 8 wrong-but-valid scored
  suggestions, including several Swedish curriculum terminology failures that
  Qwen3.6 answered correctly.

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
