---
type: runbook
id: RUN-SIRCON-answer-key-local-model-operator-guide
title: Answer-Key Local Model Operator Guide
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
summary: Answer-Key Local Model Operator Guide
system: hemma.hule.education
retired_ids:
- RUN-answer-key-local-model-operator-guide
---
## Trigger

Source record: docs/runbooks/runbook-answer-key-local-model-operator-guide.md

### Purpose

> Use this guide when setting up, switching, or probing local answer-key
> completion models on Hemma. It captures operator practices learned during Task
> 309 live validation so model quality experiments compare model behavior rather
> than cache placement, runtime drift, prompt-wrapper noise, or silent CPU
> fallback.

## Preconditions

### Authority

> - Use `pdm run run-hemma -- ...` from the local repo root for Hemma commands.
> - Keep active model caches under `/srv/scratch/sir-convert-a-lot/cache`.
> - Keep active run evidence under `/srv/scratch/sir-convert-a-lot/build/verification`.
> - Bind local model services to `127.0.0.1` only.
> - Do not expose raw prompts, raw provider responses, or model artifacts in git
>   unless a governing task explicitly promotes a sanitized artifact.
> - Do not accept CPU fallback for GPU validation. If full GPU load is required,
>   launch with settings that fail loudly instead of partially offloading.

### Scratch Layout

> Recommended paths:
>
> ```text
> /srv/scratch/sir-convert-a-lot/cache/llama.cpp
> /srv/scratch/sir-convert-a-lot/cache/huggingface
> /srv/scratch/sir-convert-a-lot/bin/llama-server
> /srv/scratch/sir-convert-a-lot/build/llama.cpp-qwen35
> /srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id>
> ```
>
> Use `LLAMA_CACHE=/srv/scratch/sir-convert-a-lot/cache/llama.cpp` for
> `llama.cpp` model downloads. `XDG_CACHE_HOME` alone is not enough for every
> llama.cpp Hugging Face path.
>
> Before switching models, verify and stop active providers:
>
> ```bash
> pdm run run-hemma -- ps -eo pid,stat,comm,args | grep -E 'llama-server|vllm|granite|qwen|gemma'
> pdm run run-hemma -- rocm-smi --showmeminfo vram --showpids
> ```
>
> After stopping, verify there are no KFD PIDs and no live local model endpoint
> left on the chosen port.

### Runtime Choice

> Use vLLM when the model is a supported transformer serving target and the test
> needs vLLM structured-output behavior such as bounded choices. Use llama.cpp
> for GGUF shortlist models and JSON Schema or GBNF constrained-output probes.
>
> The `llama.cpp` build matters. The older Hemma binary at
> `/home/paunchygent/llama.cpp/build/bin/llama-server` could run some GGUFs, but
> failed Qwen3.5 with:
>
> ```text
> unknown model architecture: 'qwen35'
> ```
>
> For the current Qwen3.6 answer-key lane and future GGUF diagnostics, use the
> Scratch default symlink:
>
> ```text
> /srv/scratch/sir-convert-a-lot/bin/llama-server
> ```
>
> The symlink points at the newer HIP build under:
>
> ```text
> /srv/scratch/sir-convert-a-lot/build/llama.cpp-qwen35/build-hip/bin/llama-server
> ```
>
> That build was configured from `llama.cpp` `0253fb21f` (version 9187) with HIP
> enabled for `gfx1201`. This build includes **MTP (Multi Token Prediction)**
> support via `--spec-type draft-mtp`. Use
> `docs/runbooks/run-sircon-hemma-gpu-runtime-runbook-for-sir-convert-a-lot-hemma-gpu-runtime-runbook-for-sir-convert-a-lot.md` for current `llama.cpp` HIP build
> stability, throttling, and recovery guidance.

### Model Settings

> Record the source of model settings before launching. Do not carry sampling
> settings from one family into another.
>
> | Model family | Recommended answer-key probe settings |
> |---|---|
> | Granite 4.1 on vLLM | IBM Granite 4 guidance favors deterministic inference for most tasks. Use `temperature=0`, disabled request logging, localhost-only bind, and the governed vLLM structured-output path. |
> | Devstral Small on llama.cpp | Unsloth guidance recommends `temperature~0.15` (probes used `0.1`), `min_p=0.01`, `--jinja`, `--ctx-size 16384`. Use JSON Schema or GBNF constraints. |
> | Qwen3.5 GGUF on llama.cpp | Use non-thinking direct-output mode. Recommended card settings are `temperature=0.7`, `top_p=0.8`, `top_k=20`, `min_p=0.0`. Disable thinking with `--reasoning off` on current llama.cpp. |
> | Qwen3.6 MTP Q6_K GGUF on llama.cpp | **Current guarded model choice for answer-key completion.** Use `unsloth/Qwen3.6-27B-MTP-GGUF`, `Qwen3.6-27B-Q6_K.gguf`, alias `qwen3.6-27b-q6k-mtp`, instruct/non-thinking mode with `--reasoning off`, `--ctx-size 16384`, `--parallel 1`, `--spec-type draft-mtp`, `--spec-draft-n-max 2`, and provider requests at `temperature=0.15`. The Qwen3.6 card recommends `temperature=0.7`, `top_p=0.80`, `top_k=20`, `min_p=0.0`, `presence_penalty=1.5`, and `repetition_penalty=1.0`; Task 309 evidence shows `temperature=0.15` produces fewer wrong-but-valid answers than the card-default `0.7`. |
> | Gemma 4 GGUF on llama.cpp | Unsloth/Google guidance recommends `temperature=1.0`, `top_p=0.95`, `top_k=64`. Start at `--ctx-size 32768` for responsiveness. Keep repetition and presence penalties disabled unless looping appears. Disable thinking for strict JSON probes. Future comparison candidate only; Qwen3.6 is the settled local choice unless a new governed task reopens model selection. |
>
> For strict answer-key probes, use the provider API request settings as the
> source of truth, not only server defaults.
>
> Task 318 tracks the corresponding artifact contract: provider-run metadata in
> Task 309 reports and evaluations must come from the selected profile/runtime
> settings rather than evaluator-local provider defaults. When switching models,
> the profile/default object must inject the model-specific settings that affect
> comparison evidence, including output mode, capabilities, temperature, max
> output tokens, context window, and vision media path.

### Launch Pattern

> For llama.cpp GGUF probes:
>
> ```bash
> pdm run run-hemma --shell '
>   cd /srv/scratch/sir-convert-a-lot/build/verification/task-309-<model-id> &&
>   LLAMA_CACHE=/srv/scratch/sir-convert-a-lot/cache/llama.cpp \
>   XDG_CACHE_HOME=/srv/scratch/sir-convert-a-lot/cache \
>   setsid /srv/scratch/sir-convert-a-lot/bin/llama-server \
>     -hf <repo> \
>     -hff <file.gguf> \
>     --no-webui \
>     --alias <alias> \
>     --host 127.0.0.1 \
>     --port 8082 \
>     --ctx-size <ctx> \
>     --n-gpu-layers all \
>     --fit off \
>     --flash-attn on \
>     --jinja \
>     --reasoning off \
>     --media-path <output-root>/vision-assets \
>     <sampling-settings> \
>     > <model>.log 2>&1 < /dev/null &
>   echo $! > <model>.pid
> '
> ```
>
> Use `--fit off` when full GPU load is part of the validation contract. If the
> model cannot fit, fix the model choice or context instead of accepting a
> CPU/RAM fallback result as comparable evidence.

### Request Shape

> For answer-key gap-fill probes, expose a consumer-friendly item shape:
>
> - Number gaps as `[1]`, `[2]`, ... in the model-visible cloze text.
> - Keep internal DigiExam gap GUIDs out of the model-facing message.
> - Use a flat JSON object with string keys `"1"` through `"N"`.
> - When a word bank exists, constrain each answer value to the visible word-bank
>   entries with JSON Schema `enum`.
> - Include `manual_follow_up_code` as `null` when all gaps can be answered.
>
> Do not treat schema-valid output as correct. Compare every answer to the
> teacher golden and separate:
>
> - correct;
> - wrong-but-valid;
> - invalid or malformed;
> - manual follow-up;
> - unknown or duplicate IDs.
>
> For choice rows on vLLM, bounded `choice` values are preferred because they
> avoid asking the model to generate a JSON wrapper when the answer is a clear
> candidate selection.

### Lessons Learned

> - Long internal gap IDs made the first gap-fill protocol harder to reason about
>   and created avoidable failure surface. Numbered, item-local gaps are the
>   correct model-facing contract.
> - Raw model outputs are essential diagnostic data during live validation.
>   Sanitized reports can omit raw content, but non-git local artifacts must keep
>   enough exchange detail to explain wrong-but-valid and invalid-output cases.
> - JSON Schema prevents malformed or out-of-bank answers, but it does not fix
>   wrong reasoning. Granite and Qwen3.5 both selected `18` instead of the
>   teacher golden `15` for the same Swedish criminal-liability-age gap.
> - Word-bank enum constraints are still valuable: they prevented invented values
>   such as `körundertid` from being counted as usable output.
> - Model settings are model-family-specific. Granite's deterministic guidance,
>   Qwen's non-thinking sampling defaults, and Gemma 4's Google sampling defaults
>   should not be mixed.
> - Current llama.cpp support is not interchangeable across model generations.
>   Qwen3.5 required a newer build that recognizes `qwen35`.
> - Qwen3.6 27B Q6_K is the current local model of choice right now. It was the
>   first tested local model to answer the Swedish
>   criminal-liability-age word-bank gap correctly as `15` with the flat JSON
>   schema and word-bank enum shape. Full-corpus validation on 2026-05-16
>   produced **39 correct, 3 wrong-but-valid, 2 manual-follow-up** out of 44
>   eligible scored items. The 3 wrong-but-valid items are persistent reasoning
>   failures (Swedish legal-actor confusion, multiple-response select-all bias,
>   biology term abbreviation) that prompt engineering did not resolve. It is the
>   current model of choice for guarded advisory validation, not automatic
>   answer-key application.
> - Devstral-Small-2-24B-Q6_K_XL (`temp=0.1`, `top_p=0.9`, `top_k=40`, `--jinja`,
>   16k context) on 2026-05-16 produced **34 correct, 8 wrong-but-valid, 2
>   manual-follow-up** out of 44 eligible scored items. It fails items Qwen3.6
>   answers correctly (Swedish law word-bank gaps, biology terminology, genetics
>   single-choice), suggesting weaker Swedish curriculum knowledge despite strong
>   coding/agentic benchmarks. Devstral is not a promotion candidate for this
>   Swedish educational route.
> - Schema simplification removed the `decision_state` enum from model-facing
>   output specs. The new rule: schema-valid + parseable output = accepted
>   suggestion. Manual follow-up is exclusively a UI user action, not a
>   model-declared state. This eliminated model over-conservatism that was
>   causing 15 manual-follow-up items despite correct answers.
> - A synonym-aware evaluator canonicalises gap values through synonym groups
>   before golden comparison. Valid equivalents such as `nukleus` for
>   `cellkärna` are accepted; vague shortenings such as `kärnan` for
>   `cellkärna` remain rejected.
> - Cache hygiene matters. Downloads must land on Scratch, and root-owned Docker
>   or Hugging Face cache entries may require `sudo -n rm -rf` when the operator
>   explicitly asks to clear promoted local model caches.
> - Remove superseded local model caches promptly after the operator has
>   preserved the validation result and selected the active local runtime lane.
>   On 2026-05-16 the non-MTP Qwen3.6 cache
>   (`models--unsloth--Qwen3.6-27B-GGUF`, 22 GB) and the Devstral cache
>   (`models--unsloth--Devstral-Small-2-24B-Instruct-2512-GGUF`, 21 GB) were
>   removed after Qwen3.6 remained the current local model choice and Devstral was
>   demoted. Scratch usage dropped from 74 % to 65 %.
> - Keep service exposure narrow. All probe servers in this lane bind to
>   `127.0.0.1`; public-edge mirror validation belongs to the governed service
>   validation task, not ad hoc model probing.

### Evaluation Command Surface

> The committed CLI is `pdm run answer-key-live-validation`. When Codex is already
> running directly on Hemma, run that command locally from the Hemma checkout; do
> not wrap it in an SSH tunnel. From a non-Hemma workstation, use
> `pdm run run-hemma -- pdm run answer-key-live-validation ...`.
>
> | Subcommand | Purpose | Where |
> |---|---|---|
> | `prepare-manifests` | Build corpus manifest + expected-answer worklist from `.dxe` fixtures. | Local |
> | `validate-goldens` | Validate teacher-verified `expected-answer-manifest.json`. | Local |
> | `preview-request-shape` | Build eligible model requests **without calling the provider**. Default text-only profiles keep 42 items; `qwen36-llama-cpp-mtp` vision eval attempts 44 and emits two multimodal request shapes. | Local |
> | `launch-llama-provider` | Start or dry-run the persistent Hemma-local llama.cpp provider for the Qwen3.6 profile. Writes pid/log launch artifacts and leaves the provider running. | Hemma |
> | `provider-status` | Probe Docker or llama.cpp provider readiness, `/v1/models`, localhost-only exposure, and required runtime flags. | Hemma |
> | `microprobes` | Run redacted structured-output probes against the live provider. The Qwen3.6 vision profile also writes a tiny media-path image and sends one `image_url` probe. | Hemma |
> | `run-advisory-corpus` | Execute the full production in-process advisory path over all 23 `.dxe` files / 317 items. Writes per-file reports. | Hemma |
> | `evaluate-advisory-corpus` | Adjudicate reports against teacher goldens and prove manifest-vs-report coverage. Emits `correct`, `wrong-but-valid`, `malformed`, `manual-follow-up`, `unknown-id`, `duplicate-id`, missing-item, and unexpected-report counts. | Hemma or local (reads artifacts) |
>
> ### OpenAI Provider Failure Triage
>
> For OpenAI Responses provider failures, inspect the redacted
> `provider_error_diagnostic` fields from the advisory report or focused
> microprobe. Use the status code to choose the next action:
>
> - `400`: fix request shape. Check strict JSON Schema compatibility,
>   `text.format`, image/data URL shape, unsupported field combinations, and
>   payload or token limits.
>   - If `error.param` points at `input[0].content[*].image_url`, verify the
>     OpenAI/Responses path sends a fully qualified URL or
>     `data:image/<type>;base64,...`, not a media-root-local `file://...` URL.
> - `401` / `403`: fix Hemma credential, project, or model-access configuration.
> - `404`: the configured model/profile is unavailable for the active
>   key/project.
> - `429`: add or tune retry/backoff and check quota/rate limits.
> - `500` / `503`: retry with bounded backoff; mark manual follow-up only after
>   bounded retries fail.
>
> Do not retain raw prompts, item text, raw images or data URLs, raw request
> payloads, raw provider responses, API keys, owner metadata, student data, or
> artifact paths in committed evidence.
>
> Focused item-13 OpenAI repro:
>
> ```bash
> pdm run run-local-pdm answer-key-live-validation digiexam run-openai-advisory-corpus \
>   --openai-provider-profile openai-gpt-5.4-mini-2026-03-17 \
>   --api-key-env OPENAI_API_KEY \
>   --source-file inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1811577114-ekologiprov-v-49-25d-e.dxe \
>   --item-id item-013
> ```
>
> Default args target the **demoted Granite/vLLM** provider on `127.0.0.1:8017`.
> For the current guarded Qwen3.6 MTP llama.cpp run, use
> `--provider-profile qwen36-llama-cpp-mtp`. That profile sets:
>
> - `--provider-url http://127.0.0.1:8082`
> - `--port 8082`
> - `--provider-runtime llama-cpp-json-schema`
> - `--model qwen3.6-27b-q6k-mtp`
> - `--output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local`
> - `--hf-repo unsloth/Qwen3.6-27B-MTP-GGUF`
> - `--hf-file Qwen3.6-27B-Q6_K.gguf`
> - launch settings include `--ctx-size 16384 --spec-type draft-mtp --spec-draft-n-max 2`
>
> For the eval-only vision slice, the same profile launches llama.cpp with
> `--media-path <output-root>/vision-assets`. Supported embedded PNG/JPEG assets
> are exported below that root, provider requests use `file://` URLs relative to
> the media path, and the normal text-only Granite/non-vision eligibility remains
> unchanged.
>
> For production service jobs, the structured-provider config must use the same
> provider-readable media root through
> `SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_PATH`. When the primary provider
> declares `supports_multimodal_vision=true`, service startup rejects missing or
> relative media paths. Runtime exports each job below that media root and sends
> job-scoped `file://<job-id>/...` image URLs, so the URL resolves under the same
> path that llama.cpp receives through `--media-path`.

### Hemma Production Provider Service

> Task 320 moves the current Qwen3.6 MTP Q6_K provider behind Docker service DNS for
> production. The production service is `sir_convert_qwen_answer_key` on
> `hule-network`, exposes container port `8082` only to the Docker network, and
> uses `http://sir_convert_qwen_answer_key:8082` in Sir Convert provider config.
> Production structured-provider URLs must not use `127.0.0.1`, `localhost`, or
> `host.docker.internal`.
>
> Build the HIP `llama-server` binary separately with the GPU runtime runbook
> helper before recreating the provider service:
>
> ```bash
> pdm run qwen-llama-provider-build
> ```
>
> The provider container mounts the runbook-built binary and Task 242
> Docker-visible Scratch-backed build/cache roots. It must not compile
> `llama.cpp` during Compose startup.
>
> The provider container must not bind host `/opt/rocm*` or `/opt/amdgpu` paths.
> Hemma's snap Docker runtime cannot reliably bind those host paths even when
> they exist on the host. Use the ROCm SDK libraries already present in the
> pinned provider image, plus `/dev/kfd`, `/dev/dri`, the runbook-built
> `llama-server`, Docker-visible build/cache roots, and the vision media path.
>
> Compose must add GPU device groups by numeric Hemma GID. Do not use image-local
> `video` or `render` names for the provider: the AMD image does not define
> `render`, and other images can define it with a different GID than the host
> device node. The prod env mirror renders `SIR_CONVERT_A_LOT_GPU_VIDEO_GROUP_ID`
> and `SIR_CONVERT_A_LOT_GPU_RENDER_GROUP_ID` from Hemma's `getent group` output.

### 1. Goldens and request shape, no provider calls

> pdm run answer-key-live-validation digiexam validate-goldens \
>   --provider-profile qwen36-llama-cpp-mtp \
>   --fail-on-blocked
>
> pdm run answer-key-live-validation digiexam preview-request-shape \
>   --provider-profile qwen36-llama-cpp-mtp \
>   --fail-on-blocked

### 2. Start persistent localhost-only llama.cpp provider

> pdm run answer-key-live-validation digiexam launch-llama-provider \
>   --provider-profile qwen36-llama-cpp-mtp \
>   --execute \
>   --fail-on-blocked
>
> pdm run answer-key-live-validation digiexam provider-status \
>   --provider-profile qwen36-llama-cpp-mtp \
>   --timeout-seconds 20 \
>   --fail-on-blocked

### 3. Live probes and full advisory corpus

> pdm run answer-key-live-validation digiexam microprobes \
>   --provider-profile qwen36-llama-cpp-mtp \
>   --timeout-seconds 60 \
>   --fail-on-blocked
>
> pdm run answer-key-live-validation digiexam run-advisory-corpus \
>   --provider-profile qwen36-llama-cpp-mtp \
>   --reports-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local/advisory-corpus-reports \
>   --timeout-seconds 90 \
>   --fail-on-blocked

## Steps

### Evaluation Pipeline

> Run in this order from the Hemma checkout for the Qwen3.6 lane. Artifacts go to
> `/srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local/`.
>
> ```bash

## Expected Results

## Stop Conditions

## Rollback
