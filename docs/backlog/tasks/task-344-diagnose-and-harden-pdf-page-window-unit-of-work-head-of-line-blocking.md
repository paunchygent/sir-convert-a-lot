---
id: task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking
title: Diagnose and harden PDF page-window unit-of-work head-of-line blocking
type: task
status: in_progress
priority: high
created: '2026-06-04'
last_updated: '2026-06-05'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/tasks/task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-273-run-chunk-size-8-production-baseline-tuning-proof-with-warm-up-and-gpu-sampling.md
  - docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md
  - docs/backlog/tasks/task-343-investigate-pdf-conversion-decision-logic-and-gpu-cpu-performance-attribution.md
  - docs/backlog/tasks/task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs.md
  - docs/runbooks/runbook-hemma-conversion-benchmarks.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpoint_chunk_runner.py
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_chunk_conversion.py
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpoint_models.py
labels:
  - long-pdf
  - docling
  - chunking
  - page-window
  - head-of-line-blocking
  - observability
  - performance
  - gpu
---

PR-sized execution unit; may be linked to a story or standalone.

## User Intent and Goal Alignment

The user intent is to diagnose and remediate a concrete low-level conversion
failure mode, not to avoid it by changing quality expectations or routing around
the current pipeline.

The product constraints for this task are:

- `auto` remains quality-first. Quality is not a lever for solving this issue.
- The current Docling/OCR/checkpoint pipeline is the first object of diagnosis
  and tuning. Do not treat current code or library settings as already
  optimized.
- Do not introduce route bypass, selectable-text bypass, scrape-style
  extraction, or lower-quality profiles as remediation.
- Do not add toy complexity heuristics. Any document feature model, page
  classifier, or adaptive policy must use proven libraries or controlled
  profiler evidence and must be quality/parity gated.
- Always prefer a simpler and faster method only when heavy processing is not
  needed to retain quality and output parity, and only after a proper
  high-quality implementation method proves that decision.
- Do not cancel or abort active conversions as part of this task.

## Objective

Prove and harden the PDF page-window unit of work used by checkpointed Docling
conversion so a single pathological chunk cannot remain opaque for tens of
minutes, hide its internal progress, or make the batch appear stalled.

This task is separate from:

- `T342`, which owns general CLI progress, manifest, idempotent replay, and
  recovery visibility.
- `T343`, which owns broad conversion decision logic and GPU/CPU performance
  attribution.
- `T345`, which owns source-layer formula authority and output-quality
  remediation for born-digital PDFs after this task proved generation-stability
  fixes are necessary but not sufficient.

This task owns the narrower runtime question exposed by the 2026-06-04 incident:
is a fixed 4-page Docling chunk the wrong unit of work for some PDFs, and how do
we prove, instrument, and tune that without reducing quality?

## Current Incident Evidence

The concrete job that exposed this task was:

- job id: `jobv2_63a3d3533e154af1887a61f31d`
- source: `efficient-llm-comparative-assessment-a-product-of-experts-framework-for-pairwise-comparisons--df95b4a730.pdf`
- total pages: `21`
- total wall-clock: about `64` minutes
- visible symptom: about `35` minutes of silence while one chunk was inside
  Docling

Checkpoint timing evidence showed one dominant chunk:

- pages `1-4`: `730998 ms`
- pages `5-8`: `261858 ms`
- pages `9-12`: `746425 ms`
- pages `13-16`: `2113664 ms`
- pages `17-20`: `7244 ms`
- page `21`: `2983 ms`

The apparent `paper_alpha.pdf` stall was queue wait behind this job, not its own
conversion runtime.

Important findings from the first read-only inspection:

- A 4-page chunk is currently submitted to Docling as one opaque conversion
  unit.
- There is no page-level or sub-window timing inside that Docling call, so the
  system cannot tell whether page `13`, `14`, `15`, `16`, or their combination
  caused the pathological runtime.
- Ordered artifact commit creates head-of-line blocking: later chunks can finish
  but cannot be committed into the final artifact before earlier chunks.
- Existing `chunk_elapsed_ms` can exclude GPU-stage semaphore wait, so elapsed
  timing must distinguish queue/semaphore wait from actual Docling conversion.
- Naive page-complexity explanations are disproven by current evidence. Pages
  `17-20` had much larger drawing/XObject volume than pages `13-16` but
  completed in about `7` seconds.
- The v2 job spec requested `execution.document_timeout_seconds=1800`, but the
  current PDF execution path resolved that value without applying it to
  Docling `PdfPipelineOptions.document_timeout`.
- Diagnostic replay must therefore combine Docling's internal
  `document_timeout` with a parent-enforced subprocess timeout and stack dump,
  so a pathological replay can identify the current low-level path without
  waiting for the original full wall-clock duration.

## Initial Diagnosis Evidence

2026-06-04 read-only Hemma inspection found no queued or running jobs before a
bounded container probe was run against the original job input.

The bounded probe replayed pages `13-16` inside the deployed GPU worker
container with:

- Python stack dump after `25` seconds,
- external process timeout after `45` seconds,
- no service queue mutation,
- no cancellation or restart of existing jobs.

The probe exited via the external timeout (`124`) instead of waiting for the
original roughly `35` minute chunk runtime. The dumped stack placed the slow
path inside Docling formula/code VLM enrichment:

- `docling/models/stages/code_formula/code_formula_vlm_model.py:272`
  `self.engine.predict_batch(engine_inputs)`
- `docling/models/inference_engines/vlm/auto_inline_engine.py:232`
  `actual_engine.predict_batch(...)`
- `docling/models/inference_engines/vlm/transformers_engine.py:386`
  `self.vlm_model.generate(**gen_kwargs)`
- Transformers `Idefics3`/`Llama` generation using SDPA attention

This localizes the incident beyond Sir Convert's chunk runner:

- not PyMuPDF page-window extraction,
- not ordered checkpoint commit,
- not GPU semaphore wait as the primary 35-minute compute path,
- not naive PDF object/drawing complexity,
- but Docling's accurate-table formula/code enrichment VLM generation path for
  the formula-heavy page window.

The product conclusion remains quality-preserving: this is not authority to
disable formula handling or route around Docling. It is authority to bound,
profile, and tune the current formula/code enrichment lane and expose its
in-flight progress truthfully.

## Implementation Slice 1

- Propagate `JobSpec.execution.document_timeout_seconds` into the PDF backend
  request and Docling `PdfPipelineOptions.document_timeout`.
- Include `document_timeout_seconds` in the Docling converter cache key so
  different timeout budgets cannot reuse an incompatible converter instance.
- Add `pdm run diagnose:task-344-page-window-replay` as a bounded page-window
  replay command.
- Run each replay window in a child process with:
  - Docling `document_timeout`,
  - parent-enforced timeout,
  - terminate/kill cleanup,
  - Python stack dump before kill,
  - sanitized JSON and Markdown reports.
- Generate full-window, single-page, and adjacent-pair windows from an incident
  range by default.

## Implementation Slice 2

- Add low-level Docling formula/code VLM diagnostics around:
  - `CodeFormulaVlmModel.__call__`,
  - `AutoInlineVlmEngine.predict_batch`,
  - `TransformersVlmEngine.predict_batch`.
- Capture sanitized converter-cache, formula batch, image crop area, selected
  engine, device, model class, dtype, KV-cache, prompt count, token budget,
  generated-token count, and elapsed-time facts.
- Add a JSONL sidecar that writes a `transformers_predict_batch_started` event
  immediately before the Docling Transformers generation call. This preserves
  evidence when a child is terminated or crashes before in-memory diagnostics can
  be serialized.
- Add Docling/Torch/Transformers runtime inventory to replay child payloads.
- Update the Markdown report to show sidecar-started Transformers calls for
  timed-out windows so operator-visible replay output is not blank when the
  child never writes its normal payload.
- Correct the fallback timing attribution boundary so broad Docling attempt time
  is not mislabeled as formula enrichment. Precise formula VLM timings now come
  from the dedicated diagnostics.

## Hemma Sidecar Replay Evidence

2026-06-04 targeted replay ran in the temporary GPU-worker app overlay at
`/tmp/task344-app-codex-20260604T231317`, not in the live service app. The
original production input remained at
`/var/lib/sir-convert-a-lot/prod/jobs_v2/jobv2_63a3d3533e154af1887a61f31d/raw/input.pdf`.

The replay command used:

- `--window 14`
- `--window 15`
- `--window 15-16`
- `--window 13`
- `--window 13-14`
- `--attempt-timeout-seconds 75`
- `--docling-document-timeout-seconds 60`
- `--stack-dump-after-seconds 20`
- `--terminate-grace-seconds 5`
- `--max-total-seconds 390`

Report paths:

- remote:
  `/tmp/task344-app-codex-20260604T231317/build/verification/task-344-page-window-replay/task344-page-window-replay-20260604T213546Z/report.json`
- local extracted copy: `/tmp/task344-report-20260604T213546Z.json`

Common formula/code VLM facts across the pathological windows:

- engine: `TransformersVlmEngine`
- model class: `OptimizedModule`
- model dtype: `torch.float32`
- device: `cuda:0` in Docling/Torch's ROCm-backed CUDA abstraction
- prompt class: `<formula>`
- `use_kv_cache`: `true`
- `max_new_tokens_max`: `2048`

| Window | Result | Child elapsed | Formula VLM sidecar evidence |
| --- | ---: | ---: | --- |
| `14` | timed out, return `-15` | `75284 ms` | four started batches: `5`, `5`, `2`, `5`; three completed batches generated `4405`, `4975`, and `1852` tokens in `13287`, `18371`, and `13604 ms`; timeout occurred after the fourth batch started. |
| `15` | timed out, return `-15` | `75307 ms` | one started batch of `5` formulas; no completed Transformers event before termination. |
| `15-16` | process crash, return `-11` | `34997 ms` | one started batch of `5` formulas; no completed event; stack tail ended in Torch/Transformers generation (`silu`). |
| `13` | timed out, return `-15` | `75308 ms` | one started batch of `5` formulas; no completed Transformers event before termination. |
| `13-14` | timed out, return `-15` | `75281 ms` | one started batch of `5` formulas; no completed Transformers event before termination. |

Interpretation:

- The issue is localized to Docling's formula/code VLM enrichment, specifically
  Transformers generation through Docling's `TransformersVlmEngine`.
- The earlier apparent queue/idempotency stall explanation is ruled out for this
  compute path. Queue wait can make later jobs appear stalled, but this incident
  has a real long-running GPU generation path inside the active job.
- The failures are not merely one 4-page window: single pages `13`, `14`, and
  `15`, plus adjacent windows involving them, can independently enter the same
  pathological generation path.
- The `15-16` return code `-11` shows an unstable crash mode around the same
  ROCm/Torch/Transformers path, not a separate service-routing issue.
- Next remediation must tune the current Docling formula VLM generation path
  itself: batch sizing, Docling code/formula options, Transformers generation
  limits/stopping behavior, model compilation/optimization path, dtype, and ROCm
  attention/kernel behavior must be inspected against upstream-supported
  controls before any implementation change. Disabling formula enrichment,
  lowering quality, or routing around Docling remains out of scope.

## Upstream Evidence

Persist these upstream reports so future work does not re-derive the same
failure class by guesswork:

- Docling issue
  [`#2478`](https://github.com/docling-project/docling/issues/2478) reports
  hangs with `do_formula_enrichment=True` after `document_timeout`, including a
  CLI reproduction using `--document-timeout 60 --enrich-formula`.
- Docling issue
  [`#2472`](https://github.com/docling-project/docling/issues/2472) reports
  Transformers-backed VLM hanging on GPU after document processing starts, with
  GPU activity but no completion. The reporter also states that reducing token
  limits did not resolve that broader VLM-pipeline hang.
- Installed Docling `2.73.1` source for our runtime sets formula VLM inputs in
  `CodeFormulaVlmModel.__call__` with `prompt="<formula>"`,
  `temperature=0.0`, and `max_new_tokens=2048`.
- Installed Docling `CodeFormulaVlmOptions` exposes model spec, engine options,
  scale, max size, and extract-code/formula flags. It does not expose a
  formula-specific `max_new_tokens` option or crop-level diagnostic surface.

## Implementation Slice 3

Keep this as a simple observation pass, not a broad profiler:

- Add one JSONL event, `code_formula_batch_started`, emitted before each Docling
  formula/code VLM batch when the replay sidecar is configured.
- Include only content-safe per-crop metrics:
  - batch position,
  - label,
  - crop width and height,
  - pixel area,
  - image mode/shape when available,
  - SHA-256 identifier of the crop bytes.
- Do not persist crop pixels, recognized text, generated text, source bytes, or
  prompts beyond the existing prompt-count aggregate.
- Use this event to correlate the last-started formula crops with subsequent
  `transformers_predict_batch_started/completed`, timeout, or crash outcomes.
- Do not tune batch size, token budget, dtype, compile path, or engine selection
  until the crop-metrics replay identifies the failing crop/batch pattern.

## Crop Metrics Replay Evidence

2026-06-04/05 replay evidence after adding `code_formula_batch_started`:

- crop-metrics report:
  `/tmp/task344-report-20260604T220954Z-crop-metrics.json`
- page-14 crop-token attempt:
  `/tmp/task344-report-20260604T221501Z-page14-crop-tokens.json`

The crop metrics sidecar records crop dimensions and SHA-256 identifiers only;
it does not store crop pixels, source bytes, recognized text, or generated text.

Key observations:

- Page `14` timed out in the two-window crop-metrics run after starting four
  formula batches. The first three batches completed with the same generated
  token totals as the previous replay: `4405`, `4975`, and `1852`.
- The fourth page-14 batch repeated the first batch's crop hashes and then timed
  out before a completed Transformers event. This indicates a repeated Docling
  attempt/retry can re-enter the same formula crop set and still fail to return.
- A follow-up page-14 run with per-output token counts enabled crashed with
  return `-11` after starting the first formula batch, before any completed
  Transformers event. Therefore that run produced crop hashes but no per-crop
  token counts.
- Window `15-16` timed out after starting one formula batch in the crop-metrics
  run. Earlier replay had reproduced return `-11` for the same window class.

Page-14 first-batch crop identifiers:

| Index | Size | Pixel area | SHA-256 |
| ---: | ---: | ---: | --- |
| `0` | `481x199` | `95719` | `46dabcf37892db71122c17214df0245b9b7c94bd225e1fa6b127d208ee4f9a98` |
| `1` | `435x92` | `40020` | `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4` |
| `2` | `454x32` | `14528` | `950bf921d80c5e1813e4ed06f20ec2ce2ecaeb3d578bd7ac1521d0959defd5a0` |
| `3` | `454x32` | `14528` | `5a7b93099ee4be855c87a168a784dd67ac6c57613f1b8efc9d3a0b049c1643dc` |
| `4` | `480x53` | `25440` | `adc3d509986d8abea8eeb992ffc063572fd38661a34543691c3f371647ce7c25` |

Window `15-16` first-batch crop identifiers:

| Index | Size | Pixel area | SHA-256 |
| ---: | ---: | ---: | --- |
| `0` | `456x59` | `26904` | `ae49b0b15bcfed84a11f20a558dfcb2e6e15e9af18bcba111fff912683b0ba68` |
| `1` | `478x99` | `47322` | `7235209215ad7a69727274f4079f4707e44cdd7d2f62e75a5f58b8d0f6e335e9` |
| `2` | `478x92` | `43976` | `f71e32a99e1f71db2925d55805c4e997e03ef270d2e01521b9337a27f57fe924` |
| `3` | `465x68` | `31620` | `a4db34ca1304d0a2bff88f6b70523e11c73d4b78bd697b5b50d8a06d570692b5` |
| `4` | `462x59` | `27258` | `442501e69e7bc060a9d7e182425ba14c22e3fb2f0a05ad5992be7d35729dd0e4` |

Evidence boundary:

- We still do not have per-crop generated-token counts from a completed
  page-14 run after adding that field, because the follow-up page-14 run crashed
  before completion.
- The next evidence step should be a single controlled replay that changes only
  the unit under observation, for example one crop or one formula item at a time,
  if Docling's internals can be exercised that narrowly without changing model
  quality or prompt semantics.

## Granite Formula Generation Root Cause

2026-06-04/05 live `/app` replay added a generation-boundary JSONL event around
Docling's Hugging Face `generate(...)` call. This event records tensor shapes,
token budgets, stop-criteria counts, elapsed time, and GPU memory counters
without storing source text, crop pixels, or decoded model output.

Direct page-14 Granite replay, without the `codeformulav2` primary pass:

- remote report:
  `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260604T232151Z/report.json`
- result: timed out after `120276 ms`, return `-15`
- first Granite formula batch:
  - crop hashes:
    `46dabcf37892db71122c17214df0245b9b7c94bd225e1fa6b127d208ee4f9a98`,
    `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`,
    `950bf921d80c5e1813e4ed06f20ec2ce2ecaeb3d578bd7ac1521d0959defd5a0`,
    `5a7b93099ee4be855c87a168a784dd67ac6c57613f1b8efc9d3a0b049c1643dc`,
    `adc3d509986d8abea8eeb992ffc063572fd38661a34543691c3f371647ce7c25`
  - `input_ids_shape`: `[5, 606]`
  - `pixel_values_shape`: `[5, 9, 3, 512, 512]`
  - `max_new_tokens`: `2048`
  - `stopping_criteria_count`: `null`
  - `generation_config_eos_token_id`: `100257`
  - `generated_ids_shape`: `[5, 2654]`
  - `generated_new_token_counts`: `[2048, 2048, 2048, 2048, 2048]`
  - `max_new_tokens_exhausted`: `true`
  - generation elapsed: `80930 ms`

This proves the slow Granite behavior is not page-complexity-proportional
formula decoding. The first Granite formula batch ran to the exact
`max_new_tokens=2048` ceiling for every item.

Direct page-14 Granite single-item replay:

- remote report:
  `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260604T232432Z/report.json`
- result: native crash, return `-11`, after `55312 ms`
- crop `#/texts/1`, hash
  `46dabcf37892db71122c17214df0245b9b7c94bd225e1fa6b127d208ee4f9a98`,
  completed in `11820 ms` with `310` new tokens
- crop `#/texts/5`, hash
  `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`,
  entered Granite generation and crashed before a completed event
- stack dump for the crash path was inside
  `transformers.generation.utils.generate/_sample`,
  `transformers.models.idefics3`, `transformers.models.llama`, and
  `torch.nn.modules.linear`

Installed Docling `2.73.1` source explains the missing stop-control path:

- `CodeFormulaVlmModel.__call__` constructs formula `VlmEngineInput` with
  hard-coded `max_new_tokens=2048` and `extra_generation_config`, but does not
  pass `self.options.model_spec.stop_strings`.
- `VlmEngineInput` has a `stop_strings` field.
- `TransformersVlmEngine.predict_batch` only installs `StopStringCriteria`
  when `first_input.stop_strings` is present.
- Granite's Docling model spec declares stop strings
  `["</doctag>", "<|end_of_text|>"]`, but the observed live formula call had
  `stopping_criteria_count: null`.

Root cause:

- Sir Convert exercises Docling's `granite_docling` formula preset through
  Docling's formula/code VLM adapter.
- The adapter did not forward the Granite model spec's stop strings into the
  generic VLM inputs. That was a real implementation gap, but live replay proved
  it is not sufficient by itself.
- With stop strings active, the pathological page-14 crop `#/texts/5` / image
  hash `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`
  still emits no configured stop string and no EOS/pad suffix before the hard
  `2048` generated-token ceiling.
- The retained decoded-output replay proves why: Granite enters a deterministic
  LaTeX repetition loop for this crop. It starts with
  `<loc_0><loc_0><loc_500><loc_500>\begin{array} ...`, emits an incomplete
  formula fragment containing `\mathbb { E } [ s _ { i }`, then repeats the
  fragment pattern `\mathbb { E } [ s _ { i } ] ... = ... \int` until the
  `2048` generated-token ceiling. The output contains no configured terminator
  and never reaches a closed formula/environment state.
- On the Hemma ROCm/Torch/Transformers runtime, that one crop explains the
  apparent random huge-token batch: the other rows stop, but the shared batch
  tensor is padded to the one row that does not stop.
- The native crash is in the same Granite/Idefics3/Llama generation path. The
  ROCm `torch.compile` guard removes the compiled `OptimizedModule` wrapper and
  prevents the direct-batch crash in observed replay, but it does not make
  `#/texts/5` stop correctly.

## Remediation Ladder

The remediation must preserve output quality and fix the current Docling
formula VLM path rather than route around it:

1. Forward model-spec stop strings into formula generation.
   - Carry `CodeFormulaVlmModel.options.model_spec.stop_strings` into each
     `VlmEngineInput` when Docling's formula adapter leaves it empty.
   - Keep Docling's `max_new_tokens=2048` ceiling unchanged; it remains a
     safety cap, not the normal stopping mechanism.
   - Prove live Granite calls enter generation with
     `stopping_criteria_count >= 1`.
   - Prove no completed Granite generation row has
     `max_new_tokens_exhausted: true`.
1. Prove Granite stops by stop criteria, not the token ceiling.
   - Rerun direct page-14 `granite_docling`.
   - Rerun crop-isolated page-14 `granite_docling`.
   - Verify crop `#/texts/5` / hash
     `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`
     completes without return `-11`.
   - Verify the normal fallback path from `codeformulav2` to
     `granite_docling` completes when fallback is legitimately exercised.
1. If a native crash remains after stop strings are active, disable
   `torch.compile` only for the ROCm formula VLM Transformers path and rerun
   the same direct/crop/fallback proof.
   - The crash stack is in the compiled `OptimizedModule` path over
     Idefics3/Llama generation.
   - Disabling compile is a runtime-stability remediation for the observed
     native crash path, not a quality-reduction profile.
   - Accept only if the same crop succeeds and output quality gates do not
     regress.

## Remediation Evidence

Implementation added:

- Formula model-spec stop strings are now carried from
  `CodeFormulaVlmModel.options.model_spec.stop_strings` to each formula
  `VlmEngineInput` when Docling leaves `stop_strings` empty.
- Formula-stage terminators used by Docling's post-processing are added to that
  same stop list: `</formula>`, `</code>`, `<end_of_utterance>`, and
  `<end_of_utterance`.
- The generation sidecar now reports corrected per-row effective token counts,
  because raw generated tensor width is batch-wide and can be padded by one
  unfinished row.
- The ROCm formula VLM path unwraps `torch.compile` from Docling's
  Transformers model before active formula generation.

Local tests:

- `pdm run pytest-root tests/sir_convert_a_lot/test_docling_formula_diagnostics.py tests/sir_convert_a_lot/test_task344_page_window_replay.py`
- Result: `18 passed`.

Live direct Granite page-14 replay after stop forwarding, stage terminators,
compile guard, and corrected effective-token diagnostics:

- report:
  `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T000851Z/report.json`
- result: succeeded, return `0`, child elapsed `142366 ms`
- runtime: Docling `2.73.1`, Transformers `4.57.3`, Torch `2.10.0+rocm7.1`
- active controls:
  - `formula_torch_compile_disabled`
  - model class `Idefics3ForConditionalGeneration`, not `OptimizedModule`
  - `use_cache: true`
  - `stopping_criteria_count: 1`
  - `stop_string_count_max: 6`
- first Granite batch crops:
  - index `0`, `#/texts/1`,
    `46dabcf37892db71122c17214df0245b9b7c94bd225e1fa6b127d208ee4f9a98`
  - index `1`, `#/texts/5`,
    `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`
  - index `2`, `#/texts/6`,
    `950bf921d80c5e1813e4ed06f20ec2ce2ecaeb3d578bd7ac1521d0959defd5a0`
  - index `3`, `#/texts/7`,
    `5a7b93099ee4be855c87a168a784dd67ac6c57613f1b8efc9d3a0b049c1643dc`
  - index `4`, `#/texts/9`,
    `adc3d509986d8abea8eeb992ffc063572fd38661a34543691c3f371647ce7c25`
- first Granite batch generated tensor width:
  - `generated_new_token_counts: [2048, 2048, 2048, 2048, 2048]`
- corrected effective counts:
  - `generated_new_token_counts_effective: [310, 2048, 56, 83, 116]`
- stop-marker probe:
  - `decoded_stop_string_anywhere_count: 4`
  - `decoded_stop_string_terminal_count: 4`
- conclusion:
  - Four rows stop correctly.
  - Crop index `1` / `#/texts/5` emits no configured stop marker and alone
    forces the batch to the `2048` ceiling.

Live crop-isolated Granite page-14 replay after the same controls:

- report:
  `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T001145Z/report.json`
- result: harness timed out at `120290 ms` after later crops; the
  `#/texts/5` crop itself completed before timeout
- `#/texts/1` control crop:
  - completed in `11837 ms`
  - effective tokens `309`
  - `decoded_stop_string_terminal_count: 1`
  - `max_new_tokens_exhausted: false`
- `#/texts/5` pathological crop:
  - completed in `75161 ms`
  - effective tokens `2048`
  - `decoded_stop_string_anywhere_count: 0`
  - `decoded_stop_string_terminal_count: 0`
  - `max_new_tokens_exhausted: true`
- retained decoded-output replay:
  `/app/build/verification/task-344-output-samples-001/formula-output-00-7b7c286c86be5eae.txt`
  - output bytes: `4341`
  - output starts with
    `<loc_0><loc_0><loc_500><loc_500>\begin{array} { r l r l }`
  - repeated lexical counts include `{`: `406`, `}`: `405`, and `81` each for
    `\mathbb`, `E`, `_`, `i`, and `=`, with `\int` repeated `80` times
  - configured terminator matches: `0`
- conclusion:
  - Disabling `torch.compile` prevented the observed native crash for the same
    crop in this run.
  - Granite behavior is still not acceptable: the crop completes only by token
    ceiling, not stop criteria.

Live target-only token-probe replay for `#/texts/5`:

- report:
  `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T005544Z/report.json`
- decoded output sample:
  `/app/build/verification/task-344-output-samples-004/formula-output-00-7b7c286c86be5eae.txt`
- token probe:
  `/app/build/verification/task-344-token-probes-004/token-probe-1780621036820582674.json`
- target isolation:
  - `#/texts/1`, `#/texts/6`, `#/texts/7`, `#/texts/9`,
    `#/texts/12`, `#/texts/14`, `#/texts/16`, `#/texts/19`,
    `#/texts/20`, `#/texts/21`, and `#/texts/23` were skipped by
    `SIR_CONVERT_A_LOT_DOCLING_FORMULA_TARGET_ITEM_REF`.
  - Only `#/texts/5` entered `Transformers.generate`.
- generation result:
  - `elapsed_ms`: `75370`
  - `generated_new_token_counts_effective`: `[2048]`
  - `max_new_tokens_exhausted`: `true`
  - decoded stop-string matches: `0`
  - decoded output size: `4341` bytes
  - repeated `\mathbb { E } [ s _ { i }` fragment count: `81`
- stop-token probability evidence across the 143 recorded probe steps:
  - `</formula>` max probability: `0.00016645138384774327`
  - `<|end_of_text|>` max probability: `0.000007661951713089366`
  - `</code>` max probability: `0.00000010091729052419396`
  - `</doctag>` max probability: `0.00000000037992542445408617`
- repeated-region rank-1 evidence:
  - from steps `96` through `125`, the greedy rank-1 tokens reconstruct the
    repeated fragment `& { \int } & { \mathbb { E } [ s _ { i } ] } & { = }`
    token by token.
  - representative rank-1 probabilities in that region:
    - step `96`: chosen `&`, probability `0.9634665250778198`
    - step `104`: chosen `math`, probability `0.9545466899871826`
    - step `106`: chosen `{`, probability `0.999972939491272`
    - step `112`: chosen `{`, probability `0.9999277591705322`
    - step `120`: chosen `}`, probability `0.9883920550346375`
  - at the same steps, full `</formula>` and EOS probabilities remain orders
    of magnitude below the chosen continuation token.
- root-cause conclusion:
  - This is not a missing stop-criteria configuration in the live replay; the
    replay has `stopping_criteria_count: 1` and `stop_string_count_max: 6`.
  - The operational root cause is a deterministic greedy-decoding attractor in
    Granite-Docling for this formula crop: conditioned on its own unfinished
    `\begin{array}` output, the model assigns the next repeated LaTeX
    continuation token the highest probability and never emits a complete
    configured terminator before the `2048` token ceiling.
  - The crop should not be labeled invalid from current evidence; the proven
    failure is model-generation behavior on that crop/prompt.

Root-cause remediation proof:

- library mechanism:
  - Use Transformers' built-in `NoRepeatNGramLogitsProcessor` through
    `generate(no_repeat_ngram_size=64)`.
  - Set `renormalize_logits=True`, matching Transformers guidance that logits
    should be normalized after logits processors.
  - Keep deterministic extraction: `do_sample=false`, `temperature=0.0`,
    `max_new_tokens=2048`, and active stop strings remain unchanged.
- diagnostic selected-control proof:
  - report:
    `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T064357Z/report.json`
  - active controls:
    - `no_repeat_ngram_size: 64`
    - `renormalize_logits: true`
    - `do_sample: false`
    - `stopping_criteria_count: 1`
    - `use_cache: true`
  - result:
    - generation elapsed `17471 ms`
    - effective generated tokens `[444]`
    - `max_new_tokens_exhausted: false`
    - `decoded_stop_string_terminal_count: 1`
    - decoded output sample:
      `/app/build/verification/task-344-output-samples-006/formula-output-00-a500d6bf66d7511b.txt`
- production-default proof, without setting the no-repeat env override:
  - report:
    `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T064631Z/report.json`
  - active controls recorded by live worker:
    - `no_repeat_ngram_size: 64`
    - `renormalize_logits: true`
    - `do_sample: false`
    - `stopping_criteria_count: 1`
    - `use_cache: true`
  - result:
    - child elapsed `35795 ms`
    - conversion elapsed `28074 ms`
    - generation elapsed `17107 ms`
    - effective generated tokens `[444]`
    - `max_new_tokens_exhausted: false`
    - `decoded_stop_string_anywhere_count: 1`
    - `decoded_stop_string_terminal_count: 1`
    - decoded output sample:
      `/app/build/verification/task-344-output-samples-007/formula-output-00-a500d6bf66d7511b.txt`
- non-pathological control crop proof, also using the production default:
  - target crop: `#/texts/1`
  - report:
    `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T064826Z/report.json`
  - active controls recorded by live worker:
    - `no_repeat_ngram_size: 64`
    - `renormalize_logits: true`
    - `do_sample: false`
    - `stopping_criteria_count: 1`
    - `use_cache: true`
  - result:
    - child elapsed `31429 ms`
    - conversion elapsed `23683 ms`
    - generation elapsed `12552 ms`
    - effective generated tokens `[309]`
    - `max_new_tokens_exhausted: false`
    - `decoded_stop_string_terminal_count: 1`
    - decoded output sample:
      `/app/build/verification/task-344-output-samples-008/formula-output-00-2a6799d3618dd082.txt`
- full page-14 validation replay, no target selector and no no-repeat env
  override:
  - report:
    `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T110626Z/report.json`
  - result:
    - status `succeeded`, child return `0`
    - child elapsed `90713 ms`
    - conversion elapsed `82947 ms`
    - `3` Granite formula generate calls
    - every generate call recorded:
      - `no_repeat_ngram_size: 64`
      - `renormalize_logits: true`
      - `do_sample: false`
      - `stopping_criteria_count: 1`
      - `use_cache: true`
    - effective token counts:
      - `[310, 444, 56, 83, 116]`
      - `[60, 222, 137, 70, 503]`
      - `[160, 254]`
    - every generate call had `max_new_tokens_exhausted: false`
    - terminal stop counts matched decoded row counts: `5/5`, `5/5`, `2/2`
    - formula generation elapsed total: `64206 ms`
    - conversion residual outside recorded formula generation:
      `18741 ms`
    - decoded samples retained under:
      `/app/build/verification/task-344-output-samples-validation-p14/`
- full incident-window `13-16` validation replay, no target selector and no
  no-repeat env override:
  - report:
    `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T110852Z/report.json`
  - result:
    - status `succeeded`, child return `0`
    - child elapsed `250273 ms`
    - conversion elapsed `242456 ms`
    - `8` Granite formula generate calls
    - every generate call recorded:
      - `no_repeat_ngram_size: 64`
      - `renormalize_logits: true`
      - `do_sample: false`
      - `stopping_criteria_count: 1`
      - `use_cache: true`
    - every generate call had `max_new_tokens_exhausted: false`
    - terminal stop counts matched decoded row counts for every batch:
      `5/5`, `5/5`, `5/5`, `5/5`, `5/5`, `5/5`, `5/5`, and `1/1`
    - maximum effective generated tokens in any row: `985`
    - formula generation elapsed total: `200977 ms`
    - conversion residual outside recorded formula generation:
      `41479 ms`
    - the three longest completed formula batches took `55112 ms`,
      `46748 ms`, and `27954 ms`; all terminated by stop string rather than
      the `2048` token ceiling
    - decoded samples retained under:
      `/app/build/verification/task-344-output-samples-validation-p13-16/`
- output-correctness replay with persisted Markdown artifact:
  - report:
    `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T112725Z/report.json`
  - persisted Markdown:
    `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260605T112725Z/p000013-000016.child.md`
  - local review bundle:
    `build/verification/task-344-md-review-20260605T112725Z/`
  - result:
    - status `succeeded`, child return `0`
    - child elapsed `249740 ms`
    - conversion elapsed `241975 ms`
    - Markdown SHA-256 matched the previous full `13-16` replay:
      `8ebb6a207d163701699d7f585ce6b3205c36206d6826318e46349acdeb49ac68`
    - all eight Granite formula generate calls stopped before the `2048` token
      ceiling; formula generation elapsed total: `201647 ms`
  - correctness verdict:
    - The converted Markdown is not correct for pages `13-16`.
    - The persisted Markdown contains `36` leaked `</formula` fragments,
      `304` `\mathbf` repetitions, and `59` `\mathbmath` fragments.
    - Rendered source pages `13-14` show clean equations, while the converted
      Markdown replaces several equations with hallucinated arrays, repeated
      symbols, and stray words such as `license`, `Data`, and `looly`.
    - Therefore, the current low-level no-repeat remediation proves
      non-termination/crash avoidance, but it does not prove formula-output
      correctness for this incident window.
- pre-remediation full-job Markdown comparison:
  - full output:
    `/var/lib/sir-convert-a-lot/prod/jobs_v2/jobv2_63a3d3533e154af1887a61f31d/artifacts/output.md`
  - affected chunk:
    `/var/lib/sir-convert-a-lot/prod/jobs_v2/jobv2_63a3d3533e154af1887a61f31d/checkpoints/chunks/chunk_0003_p000013-000016.md`
  - artifact evidence:
    - `artifacts/output.md` was written pre-remediation on
      `2026-06-04 16:42:22` with SHA-256
      `917f806f2102390c2da2effa89110b161a8be2fe57332db417a98572c63cbd0b`
    - the affected chunk has SHA-256
      `7cba9d296f42ccf57aa5607bac925094e8f9d21dcd183d76db00b71fbd3a03e5`
  - comparison verdict:
    - The exact post-remediation Markdown-review markers were not present in
      the pre-remediation full output: `0` leaked `</formula`, `0`
      `\mathbmath`, and `0` `\mathbf` occurrences in both the full output and
      the affected `13-16` chunk.
    - Formula hallucinations were still present pre-remediation in the affected
      chunk, including generated text such as `A s t h e d i t i o n o v e r
      s o r e s`, `Govc`, `asoucsumd`, `cisic`, `Sumerian-Morphism`, and
      `loly`.
    - Therefore, the no-repeat remediation changed the failure signature and
      avoided token-ceiling/non-return behavior, but formula-output quality was
      already failing before the remediation.
- implementation conclusion:
  - The root-cause fix is not crop routing, fallback, lower quality mode,
    shorter token ceiling, or a hand-written loop heuristic.
  - The fix changes the low-level decoding contract so exact long n-gram
    repetition cannot remain the greedy path. On the proven pathological crop,
    Granite then emits a real terminal stop string and exits before the token
    ceiling.

Current acceptance status:

- Forward model-spec stop strings into formula generation: implemented and
  proved live.
- Prove Granite stops by stop criteria, not token ceiling: implemented and
  proved live for `#/texts/5` with the production default no-repeat control.
- If native crash remains, disable `torch.compile` for ROCm formula VLM path and
  prove the same crop succeeds: implemented; after the no-repeat default, the
  same crop completed without native crash and before the token ceiling.

Performance interpretation:

- The evidence does not support a missing-KV-cache explanation for this run:
  the live Granite calls report `use_cache: true`.
- The no-repeat decoding fix is causally related to the former stopless
  autoregressive loop: the proven pathological page-14 crop now generates `444`
  effective tokens and exits through a terminal stop string instead of running
  to the `2048` token ceiling.
- The no-repeat decoding fix is not sufficient evidence of general conversion
  efficiency. The full `13-16` replay still spent `200977 ms` inside completed
  Granite formula generation calls, and those calls all stopped correctly.
  Remaining throughput work must therefore be treated as a separate
  GPU/runtime/model-efficiency investigation, not as a continuation of the
  stopless-loop root cause.
- The no-repeat decoding fix is also not sufficient evidence of output
  correctness. A persisted Markdown replay for pages `13-16` completed
  reproducibly but failed formula correctness review, so quality remediation
  remains open under `T345` even though the generation loop no longer reaches
  the token ceiling.
- The evidence does show one remaining low-level performance gap:
  the live formula model reports `model_dtype: torch.float32`. If a future
  remediation changes dtype, it must be grounded in the model/provider contract
  and proved by replay, because dtype tuning is orthogonal to the stopless
  crop-root cause.

## PR Scope

- Add or extend a repo-owned diagnostic harness that can replay the same PDF
  through the current Docling pipeline at controlled page-window sizes.
- Replay the incident pages as individual pages and bounded windows:
  - `13`
  - `14`
  - `15`
  - `16`
  - `13-14`
  - `15-16`
  - `13-16`
- Compare current 4-page windows against smaller page windows only as a
  quality-preserving unit-of-work tuning candidate, not as a quality downgrade.
- Capture timing truth for each relevant boundary:
  - job queue wait,
  - chunk worker start,
  - GPU-stage semaphore wait,
  - Docling convert start/end,
  - checkpoint write,
  - ordered commit wait,
  - artifact finalization.
- Add visible in-flight state for long opaque chunks so users/operators can see
  which page window is currently being processed even before it completes.
- Represent head-of-line blocking explicitly in checkpoint/status data:
  completed out-of-order chunks may be visible as metadata, while artifact
  content remains committed in deterministic page order.
- Add tests that prove the progress/checkpoint contract stays truthful when one
  chunk is slow and later chunks complete first.
- Feed benchmarkable conclusions into `T74` and `T273` only after this task
  produces controlled evidence.

## Out of Scope

- Solving this by route bypass, selectable-text bypass, scrape extraction, or
  lower-quality conversion profiles.
- Changing production defaults solely because one file was slow.
- Adding hand-written page-complexity heuristics.
- Treating page count, drawing count, text span count, XObject count, or formula
  presence as sufficient routing authority without measured Docling replay and
  parity evidence.
- Reopening unsafe high-concurrency profiles or canceling active jobs.
- Owning general CLI batch progress/idempotency remediation; that remains
  `T342`.
- Owning broad GPU/CPU attribution and conversion decision policy; that remains
  `T343`.

## Required Diagnosis

The implementation must gather evidence before tuning:

1. Reproduce the incident page-window behavior on Hemma or an explicitly
   declared equivalent runtime.
1. Run controlled page-window replays for the incident pages with the same
   Docling options, OCR mode, table/formula settings, acceleration policy, and
   worker profile unless the experiment declares a single changed variable.
1. Capture CPU/GPU evidence for the replay:
   - CPU wall time and process pressure,
   - ROCm/GPU busy and memory samples where available,
   - model initialization or warm-up state,
   - Docling stage/profiler evidence when supported by the library.
1. Prove whether the pathological behavior is page-specific, window-combination
   specific, first-use/warm-up related, semaphore/queue related, or commit-order
   related.
1. Verify markdown/output parity for any smaller-window candidate before
   recommending it.
1. Record why naive feature heuristics are insufficient for this incident.

## Deliverables

- [ ] A task-owned diagnostic command or script for page-window replay against
  the current Docling pipeline.
- [ ] A sanitized diagnostic report for the incident job and source PDF,
  including page-window timings and resource samples.
- [ ] Runtime/checkpoint fields or events that expose in-flight page-window
  state and head-of-line blocking truthfully.
- [ ] Focused tests for slow earlier chunk plus completed later chunk behavior.
- [ ] A benchmark/parity recommendation for page-window sizing or adaptive
  policy, linked forward to `T74`/`T273` when appropriate.
- [ ] Documentation updates explaining how operators should interpret an active
  long-running page window versus a true stall.

## Acceptance Criteria

- [ ] The incident PDF can be replayed at page/window granularity with recorded
  timings for `13`, `14`, `15`, `16`, `13-14`, `15-16`, and `13-16`.
- [ ] Timing output distinguishes semaphore/queue wait from Docling conversion
  time and checkpoint/artifact commit time.
- [ ] Checkpoint/status data can show an in-flight long page window before the
  Docling call returns.
- [ ] Head-of-line blocking is visible in metadata without committing final
  artifact content out of page order.
- [ ] Smaller page-window candidates are accepted only if markdown/output parity
  and quality gates pass.
- [ ] No production default changes are made without controlled measurement,
  quality parity evidence, and explicit rollback criteria.
- [ ] The implementation does not add toy heuristics or quality-reduction
  routing.
- [ ] The task report states whether the root cause is page-specific,
  combination-specific, warm-up/model-init related, GPU/CPU scheduling
  related, or still unresolved.
- [ ] Focused regression tests cover slow opaque chunk progress and completed
  out-of-order chunk reporting.
- [ ] Docs and generated indexes are synchronized.

## Product Decision Questions

1. Should the default Docling page-window size remain `4`, move smaller, or
   become evidence-adaptive?

   Recommendation: decide only after replay evidence. A smaller unit of work is
   quality-preserving in principle, but it can increase overhead and must prove
   parity.

1. Should the user-facing CLI/API report completed out-of-order chunks while the
   final artifact remains ordered?

   Recommendation: yes, as metadata only, once tested. This directly addresses
   the blindness without risking artifact determinism.

1. Should page-window diagnostics become a normal support command?

   Recommendation: yes, but keep it an operator/developer diagnostic until the
   output is stable enough for ordinary CLI users.

## Validation Plan

- 2026-06-04 unrelated coverage-gate follow-up:
  - The seven non-Task-344 failures from the earlier full gate were traced to
    stale compose/QTI/PDF test contracts governed by `TASK-337`, `TASK-315`,
    `TASK-321`, `TASK-340`, and `TASK-341`.
  - The focused seven-node slice now passes after the test-contract update.
  - The affected test files also pass as a 38-test focused proof.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
- For implementation closeout:
  - `pdm run format`
  - `pdm run lint`
  - `pdm run typecheck`
  - focused `pdm run test` for chunk/checkpoint/progress behavior
  - Hemma page-window replay evidence captured without aborting active jobs

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
