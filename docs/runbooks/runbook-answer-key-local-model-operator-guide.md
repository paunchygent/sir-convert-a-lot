---
type: runbook
id: RUN-answer-key-local-model-operator-guide
title: Answer-Key Local Model Operator Guide
status: active
created: '2026-05-16'
updated: '2026-05-16'
owners:
  - platform
system: hemma.hule.education
tags:
  - answer-key-completion
  - gpu
  - llama-cpp
  - model-cache
  - structured-output
links:
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
---

## Purpose

Use this guide when setting up, switching, or probing local answer-key
completion models on Hemma. It captures operator practices learned during Task
309 live validation so model quality experiments compare model behavior rather
than cache placement, runtime drift, prompt-wrapper noise, or silent CPU
fallback.

## Authority

- Use `pdm run run-hemma -- ...` from the local repo root for Hemma commands.
- Keep active model caches under `/srv/scratch/sir-convert-a-lot/cache`.
- Keep active run evidence under `/srv/scratch/sir-convert-a-lot/build/verification`.
- Bind local model services to `127.0.0.1` only.
- Do not expose raw prompts, raw provider responses, or model artifacts in git
  unless a governing task explicitly promotes a sanitized artifact.
- Do not accept CPU fallback for GPU validation. If full GPU load is required,
  launch with settings that fail loudly instead of partially offloading.

## Scratch Layout

Recommended paths:

```text
/srv/scratch/sir-convert-a-lot/cache/llama.cpp
/srv/scratch/sir-convert-a-lot/cache/huggingface
/srv/scratch/sir-convert-a-lot/bin/llama-server
/srv/scratch/sir-convert-a-lot/build/llama.cpp-qwen35
/srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id>
```

Use `LLAMA_CACHE=/srv/scratch/sir-convert-a-lot/cache/llama.cpp` for
`llama.cpp` model downloads. `XDG_CACHE_HOME` alone is not enough for every
llama.cpp Hugging Face path.

Before switching models, verify and stop active providers:

```bash
pdm run run-hemma -- ps -eo pid,stat,comm,args | grep -E 'llama-server|vllm|granite|qwen|gemma'
pdm run run-hemma -- rocm-smi --showmeminfo vram --showpids
```

After stopping, verify there are no KFD PIDs and no live local model endpoint
left on the chosen port.

## Runtime Choice

Use vLLM when the model is a supported transformer serving target and the test
needs vLLM structured-output behavior such as bounded choices. Use llama.cpp
for GGUF shortlist models and JSON Schema or GBNF constrained-output probes.

The `llama.cpp` build matters. The older Hemma binary at
`/home/paunchygent/llama.cpp/build/bin/llama-server` could run some GGUFs, but
failed Qwen3.5 with:

```text
unknown model architecture: 'qwen35'
```

For Qwen3.5 and later Gemma 4 runs, use the Scratch default symlink:

```text
/srv/scratch/sir-convert-a-lot/bin/llama-server
```

The symlink points at the newer HIP build under:

```text
/srv/scratch/sir-convert-a-lot/build/llama.cpp-qwen35/build-hip/bin/llama-server
```

That build was configured from `llama.cpp` `59778f019` with HIP enabled for
`gfx1201`.

## Model Settings

Record the source of model settings before launching. Do not carry sampling
settings from one family into another.

| Model family | Recommended answer-key probe settings |
|---|---|
| Granite 4.1 on vLLM | IBM Granite 4 guidance favors deterministic inference for most tasks. Use `temperature=0`, disabled request logging, localhost-only bind, and the governed vLLM structured-output path. |
| Devstral Small on llama.cpp | Use the model-card defaults for deterministic-ish local inference. Prior probes used `temperature=0.15`, `min_p=0.01`, `--jinja`, and JSON Schema or GBNF constraints. |
| Qwen3.5 GGUF on llama.cpp | Use non-thinking direct-output mode. Recommended card settings are `temperature=0.7`, `top_p=0.8`, `top_k=20`, `min_p=0.0`. Disable thinking with `--reasoning off` on current llama.cpp. |
| Qwen3.6 GGUF on llama.cpp | Use instruct/non-thinking mode. The Qwen3.6 card recommends `temperature=0.7`, `top_p=0.80`, `top_k=20`, `min_p=0.0`, `presence_penalty=1.5`, and `repetition_penalty=1.0`. Qwen3.6 thinks by default, so launch with `--reasoning off` for strict JSON answer-key probes. |
| Gemma 4 GGUF on llama.cpp | Unsloth/Google guidance recommends `temperature=1.0`, `top_p=0.95`, `top_k=64`. Start at `--ctx-size 32768` for responsiveness. Keep repetition and presence penalties disabled unless looping appears. Disable thinking for strict JSON probes. |

For strict answer-key probes, use the provider API request settings as the
source of truth, not only server defaults.

## Launch Pattern

For llama.cpp GGUF probes:

```bash
pdm run run-hemma --shell '
  cd /srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id> &&
  LLAMA_CACHE=/srv/scratch/sir-convert-a-lot/cache/llama.cpp \
  XDG_CACHE_HOME=/srv/scratch/sir-convert-a-lot/cache \
  setsid /srv/scratch/sir-convert-a-lot/bin/llama-server \
    -hf <repo> \
    -hff <file.gguf> \
    --no-mmproj \
    --no-webui \
    --alias <alias> \
    --host 127.0.0.1 \
    --port 8082 \
    --ctx-size <ctx> \
    --n-gpu-layers all \
    --fit off \
    --flash-attn on \
    --jinja \
    --reasoning off \
    <sampling-settings> \
    > <model>.log 2>&1 < /dev/null &
  echo $! > <model>.pid
'
```

Use `--fit off` when full GPU load is part of the validation contract. If the
model cannot fit, fix the model choice or context instead of accepting a
CPU/RAM fallback result as comparable evidence.

## Request Shape

For answer-key gap-fill probes, expose a consumer-friendly item shape:

- Number gaps as `[1]`, `[2]`, ... in the model-visible cloze text.
- Keep internal DigiExam gap GUIDs out of the model-facing message.
- Use a flat JSON object with string keys `"1"` through `"N"`.
- When a word bank exists, constrain each answer value to the visible word-bank
  entries with JSON Schema `enum`.
- Include `manual_follow_up_code` as `null` when all gaps can be answered.

Do not treat schema-valid output as correct. Compare every answer to the
teacher golden and separate:

- correct;
- wrong-but-valid;
- invalid or malformed;
- manual follow-up;
- unknown or duplicate IDs.

For choice rows on vLLM, bounded `choice` values are preferred because they
avoid asking the model to generate a JSON wrapper when the answer is a clear
candidate selection.

## Lessons Learned

- Long internal gap IDs made the first gap-fill protocol harder to reason about
  and created avoidable failure surface. Numbered, item-local gaps are the
  correct model-facing contract.
- Raw model outputs are essential diagnostic data during live validation.
  Sanitized reports can omit raw content, but non-git local artifacts must keep
  enough exchange detail to explain wrong-but-valid and invalid-output cases.
- JSON Schema prevents malformed or out-of-bank answers, but it does not fix
  wrong reasoning. Granite and Qwen3.5 both selected `18` instead of the
  teacher golden `15` for the same Swedish criminal-liability-age gap.
- Word-bank enum constraints are still valuable: they prevented invented values
  such as `körundertid` from being counted as usable output.
- Model settings are model-family-specific. Granite's deterministic guidance,
  Qwen's non-thinking sampling defaults, and Gemma 4's Google sampling defaults
  should not be mixed.
- Current llama.cpp support is not interchangeable across model generations.
  Qwen3.5 required a newer build that recognizes `qwen35`.
- Qwen3.6 27B Q6_K was the first tested local model to answer the Swedish
  criminal-liability-age word-bank gap correctly as `15` with the flat JSON
  schema and word-bank enum shape. Keep this as a lead candidate for broader
  corpus validation rather than overfitting prompts to the single item.
- Cache hygiene matters. Downloads must land on Scratch, and root-owned Docker
  or Hugging Face cache entries may require `sudo -n rm -rf` when the operator
  explicitly asks to clear promoted local model caches.
- Keep service exposure narrow. All probe servers in this lane bind to
  `127.0.0.1`; public-edge mirror validation belongs to the governed service
  validation task, not ad hoc model probing.

## Evaluation Command Surface

The committed CLI is `pdm run task-309-answer-key-live` (local) or `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation` (Hemma).

| Subcommand | Purpose | Where |
|---|---|---|
| `prepare-manifests` | Build corpus manifest + expected-answer worklist from `.dxe` fixtures. | Local |
| `validate-goldens` | Validate teacher-verified `expected-answer-manifest.json`. | Local |
| `preview-request-shape` | Build all 42 eligible model requests **without calling the provider**. Proves prompt shape, schema/GBNF contract, and item formatting. | Local |
| `microprobes` | Run redacted structured-output probes (choice object + gap-fill object) against the live provider. | Hemma |
| `run-advisory-corpus` | Execute the full production in-process advisory path over all 23 `.dxe` files / 317 items. Writes per-file reports. | Hemma |
| `evaluate-advisory-corpus` | Adjudicate reports against teacher goldens. Emits `correct`, `wrong-but-valid`, `malformed`, `manual-follow-up`, `unknown-id`, `duplicate-id` counts. | Hemma or local (reads artifacts) |

Default args target the **demoted Granite/vLLM** provider on `127.0.0.1:8017`. For llama.cpp GGUF runs you **must** override:

- `--provider-url http://127.0.0.1:8082` (or active llama-server port)
- `--provider-runtime llama-cpp-json-schema` or `llama-cpp-gbnf`
- `--model <alias>` (e.g. `qwen3.6-27b-q6k`)

## Evaluation Pipeline

Run in this order. Artifacts go to `build/verification/task-309-<model-id>/` locally and `/srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id>/` on Hemma.

```bash
## 1. Local: corpus manifest + golden validation
pdm run task-309-answer-key-live prepare-manifests \
  --corpus-root inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe \
  --output-root build/verification/task-309-<model-id>

pdm run task-309-answer-key-live validate-goldens \
  --output-root build/verification/task-309-<model-id> \
  --fail-on-blocked

## 2. Local: request-shape smoke (zero provider calls)
pdm run task-309-answer-key-live preview-request-shape \
  --provider-url http://127.0.0.1:8082 \
  --model <alias> \
  --provider-runtime llama-cpp-json-schema \
  --corpus-root inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe \
  --output-root build/verification/task-309-<model-id>-shape-smoke

## 3. Hemma: microprobes against live llama-server
pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation microprobes \
  --provider-url http://127.0.0.1:8082 \
  --model <alias> \
  --provider-runtime llama-cpp-json-schema \
  --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id> \
  --timeout-seconds 60

## 4. Hemma: full corpus advisory run
pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation run-advisory-corpus \
  --provider-url http://127.0.0.1:8082 \
  --model <alias> \
  --provider-runtime llama-cpp-json-schema \
  --corpus-root inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe \
  --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id> \
  --reports-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id>/advisory-corpus-reports \
  --timeout-seconds 90

## 5. Hemma: golden evaluation
pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation evaluate-advisory-corpus \
  --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id> \
  --reports-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id>/advisory-corpus-reports
```

Key paths:

- Corpus: `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/` (23 `.dxe` files, 317 items, 42 eligible)
- Goldens: `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/expected-answer-manifest.json`
- Per-file reports: `<reports-root>/*.answer-key-completion-report.json`
- Evaluation output: `advisory-golden-evaluation.json` + `.md`

## Promotion Gates

A model run blocks promotion unless **all** of the following are true:

- `unknown_id_count == 0`
- `duplicate_id_count == 0`
- `malformed_success_count == 0`
- `wrong_but_valid_count == 0` (primary safety metric; manual follow-up is safer than a plausible wrong key)

Acceptable: `manual_follow_up_required` items, `skipped` items, and `partial_gap_answer` entries that are scored correctly.

## Closeout Checklist

Before interpreting model quality:

- model endpoint answers `/v1/models`;
- `rocm-smi --showpids` shows the expected model process and VRAM use;
- launch log confirms the expected model file, context, and reasoning mode;
- request payload records model, settings, output schema, and item shape;
- probe result compares parsed output to teacher goldens;
- provider process state is intentionally left running or intentionally stopped;
- cache additions and removals are recorded in the task or reference evidence.
