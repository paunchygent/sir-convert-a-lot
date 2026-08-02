---
type: reference
id: REF-SIRCON-PLAN-local-model-answer-key-completion-runtime-and-benchmark-plan
title: Local Model Answer-key Completion Runtime And Benchmark Plan
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: plan
retired_ids:
- REF-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan
summary: Local Model Answer-key Completion Runtime And Benchmark Plan
---

## Outcome And Purpose

## Planning Boundary

## Evidence Basis

## Confirmed Contract

## Backlog Derivation

## Planning Stop Conditions

## Historical Source Content

### Purpose

This reference records the first local `llama.cpp` GGUF model shortlist, the
Granite/vLLM runtime proof, and the current evidence boundary for Sir
Convert-a-Lot's machine-marked answer-key completion route.

Task 301 proved that **vLLM serving `ibm-granite/granite-4.1-8b-fp8`** can run
on Hemma's R9700 ROCm preview lane and satisfy constrained-output protocol
smokes. Task 309 then live-validated Granite/vLLM, Qwen3.6 GGUF, and Devstral
Small GGUF against the production advisory path and a versioned pure DigiExam
DXE corpus. The Task 309 evidence demotes Granite/vLLM and Devstral Small for
answer-key completion quality. Qwen3.6-27B-Q6_K remains the guarded local
rollback model for this route, with `temperature=0.15`, `--reasoning off`, and
the llama.cpp JSON Schema runtime. Task 326 later promoted OpenAI
`gpt-5.4-mini-2026-03-17` as the temporary accepted/default development and
production provider so the Qwen3.6 container can be stopped to save GPU VRAM.
This provider-default decision does not promote automatic answer-key
application; teacher review remains the product contract unless a later
governed task changes it. Task 300 remains the later comparative model bake-off
and must not start until the full app path is working and deployed.

Task 318 owns a metadata correction required before future model comparisons
are interpreted as final evidence. Evaluation artifacts must derive provider
profile, runtime, capabilities, output-mode policy, sampling settings, token
budgets, and vision media path from the selected provider profile/run artifact,
not from hardcoded Granite or Qwen constants in the evaluator.

### Hemma Model Cache Contract

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

### Selection Boundary

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

### Qwen3.6-27B Live Validation Result

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

### Devstral-Small-2-24B Live Validation Result

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
- MTP is available via `--spec-type draft-mtp --spec-draft-n-max 2`.

**MTP speed validation on Task 309 corpus:**

| Metric | Non-MTP | MTP (`draft-mtp`, n-max=2) |
|---|---|---|
| Total latency (44 items) | **103.3 s** | **85.6 s** |
| Avg generation speed | **21.4 tok/s** | **35.0 tok/s** |
| Speedup | 1.0× | **1.63×** |
| Correct / eligible | 41 / 44 (93%) | 39 / 42 (93%) |
| Wrong-but-valid | 3 | 3 |

MTP achieves **1.63× faster generation** with **no accuracy loss** on the
answer-key corpus. The 2 extra `manual_follow_up` items in the MTP run are
model-variance outliers, not a systematic degradation. VRAM usage increases
from ~26 GB to ~30 GB because the MTP draft model loads alongside the main
model.

Launch command used for validation:

```bash
/srv/scratch/sir-convert-a-lot/bin/llama-server \
  -hf unsloth/Qwen3.6-27B-MTP-GGUF \
  -hff Qwen3.6-27B-UD-Q6_K_XL.gguf \
  --no-mmproj --no-webui --alias qwen3.6-27b-q6k-mtp \
  --host 127.0.0.1 --port 8082 \
  --ctx-size 32768 --n-gpu-layers all --fit off --flash-attn on --jinja \
  --reasoning off --temp 0.15 \
  --spec-type draft-mtp --spec-draft-n-max 2
```

### Promotion Status

**Temporary default provider, guarded advisory only.** OpenAI
`gpt-5.4-mini-2026-03-17` is the accepted default provider for development and
Hemma production after Task 326 adjudication: 43 correct, 1 wrong-but-valid, and
0 manual-follow-up out of 44 scored items. Qwen3.6-27B remains the local
rollback profile with a retained baseline of 41 correct, 3 wrong-but-valid, and
0 manual-follow-up. Devstral-Small-2-24B is demoted after 8 wrong-but-valid
answers on the same corpus. Do not route provider suggestions directly into
accepted answer keys without teacher review or a later governed decision that
changes the wrong-but-valid risk posture.

### Verified Source Notes

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

### Ranked Candidate Pool

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

### Benchmark Protocol

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

### Required Metrics

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

### Architecture Requirements

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
