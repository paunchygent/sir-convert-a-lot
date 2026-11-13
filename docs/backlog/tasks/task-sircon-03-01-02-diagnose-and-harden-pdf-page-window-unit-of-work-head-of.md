---
type: task
id: TASK-SIRCON-03-01-02
title: Diagnose and harden PDF page-window unit-of-work head-of-line blocking
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-03-01
task_kind: story
acceptance_criteria:
- The incident PDF can be replayed at page/window granularity with recorded timings
  for `13`, `14`, `15`, `16`, `13-14`, `15-16`, and `13-16`.
- Timing output distinguishes semaphore/queue wait from Docling conversion time and
  checkpoint/artifact commit time.
- Checkpoint/status data can show an in-flight long page window before the Docling
  call returns.
- Head-of-line blocking is visible in metadata without committing final artifact content
  out of page order.
- Smaller page-window candidates are accepted only if markdown/output parity and quality
  gates pass.
- No production default changes are made without controlled measurement, quality parity
  evidence, and explicit rollback criteria.
- The implementation does not add toy heuristics or quality-reduction routing.
- The task report states whether the root cause is page-specific, combination-specific,
  warm-up/model-init related, GPU/CPU scheduling related, or still unresolved.
- Focused regression tests cover slow opaque chunk progress and completed out-of-order
  chunk reporting.
- Docs and generated indexes are synchronized.
retired_ids:
- task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking
---
## Context

Source record: docs/backlog/tasks/task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking.md

### User Intent and Goal Alignment

> The user intent is to diagnose and remediate a concrete low-level conversion
> failure mode, not to avoid it by changing quality expectations or routing around
> the current pipeline.
>
> The product constraints for this task are:
>
> - `auto` remains quality-first. Quality is not a lever for solving this issue.
> - The current Docling/OCR/checkpoint pipeline is the first object of diagnosis
>   and tuning. Do not treat current code or library settings as already
>   optimized.
> - Do not introduce route bypass, selectable-text bypass, scrape-style
>   extraction, or lower-quality profiles as remediation.
> - Do not add toy complexity heuristics. Any document feature model, page
>   classifier, or adaptive policy must use proven libraries or controlled
>   profiler evidence and must be quality/parity gated.
> - Always prefer a simpler and faster method only when heavy processing is not
>   needed to retain quality and output parity, and only after a proper
>   high-quality implementation method proves that decision.
> - Do not cancel or abort active conversions as part of this task.

### Objective

> Prove and harden the PDF page-window unit of work used by checkpointed Docling
> conversion so a single pathological chunk cannot remain opaque for tens of
> minutes, hide its internal progress, or make the batch appear stalled.
>
> This task is separate from:
>
> - `T342`, which owns general CLI progress, manifest, idempotent replay, and
>   recovery visibility.
> - `T343`, which owns broad conversion decision logic and GPU/CPU performance
>   attribution.
> - `T345`, which owns source-layer formula authority and output-quality
>   remediation for born-digital PDFs after this task proved generation-stability
>   fixes are necessary but not sufficient.
>
> This task owns the narrower runtime question exposed by the 2026-06-04 incident:
> is a fixed 4-page Docling chunk the wrong unit of work for some PDFs, and how do
> we prove, instrument, and tune that without reducing quality?

## Decision And Assumption Ledger

### Product Decision Questions

> 1. Should the default Docling page-window size remain `4`, move smaller, or
>    become evidence-adaptive?
>
>    Recommendation: decide only after replay evidence. A smaller unit of work is
>    quality-preserving in principle, but it can increase overhead and must prove
>    parity.
>
> 1. Should the user-facing CLI/API report completed out-of-order chunks while the
>    final artifact remains ordered?
>
>    Recommendation: yes, as metadata only, once tested. This directly addresses
>    the blindness without risking artifact determinism.
>
> 1. Should page-window diagnostics become a normal support command?
>
>    Recommendation: yes, but keep it an operator/developer diagnostic until the
>    output is stable enough for ordinary CLI users.

## Story Contract Slice

### PR Scope

> - Add or extend a repo-owned diagnostic harness that can replay the same PDF
>   through the current Docling pipeline at controlled page-window sizes.
> - Replay the incident pages as individual pages and bounded windows:
>   - `13`
>   - `14`
>   - `15`
>   - `16`
>   - `13-14`
>   - `15-16`
>   - `13-16`
> - Compare current 4-page windows against smaller page windows only as a
>   quality-preserving unit-of-work tuning candidate, not as a quality downgrade.
> - Capture timing truth for each relevant boundary:
>   - job queue wait,
>   - chunk worker start,
>   - GPU-stage semaphore wait,
>   - Docling convert start/end,
>   - checkpoint write,
>   - ordered commit wait,
>   - artifact finalization.
> - Add visible in-flight state for long opaque chunks so users/operators can see
>   which page window is currently being processed even before it completes.
> - Represent head-of-line blocking explicitly in checkpoint/status data:
>   completed out-of-order chunks may be visible as metadata, while artifact
>   content remains committed in deterministic page order.
> - Add tests that prove the progress/checkpoint contract stays truthful when one
>   chunk is slow and later chunks complete first.
> - Feed benchmarkable conclusions into `T74` and `T273` only after this task
>   produces controlled evidence.

### Out of Scope

> - Solving this by route bypass, selectable-text bypass, scrape extraction, or
>   lower-quality conversion profiles.
> - Changing production defaults solely because one file was slow.
> - Adding hand-written page-complexity heuristics.
> - Treating page count, drawing count, text span count, XObject count, or formula
>   presence as sufficient routing authority without measured Docling replay and
>   parity evidence.
> - Reopening unsafe high-concurrency profiles or canceling active jobs.
> - Owning general CLI batch progress/idempotency remediation; that remains
>   `T342`.
> - Owning broad GPU/CPU attribution and conversion decision policy; that remains
>   `T343`.

## Contract Inputs

## Plan

### Implementation Slice 1

> - Propagate `JobSpec.execution.document_timeout_seconds` into the PDF backend
>   request and Docling `PdfPipelineOptions.document_timeout`.
> - Include `document_timeout_seconds` in the Docling converter cache key so
>   different timeout budgets cannot reuse an incompatible converter instance.
> - Add `pdm run diagnose:docling-page-window-replay` as a bounded page-window
>   replay command.
> - Run each replay window in a child process with:
>   - Docling `document_timeout`,
>   - parent-enforced timeout,
>   - terminate/kill cleanup,
>   - Python stack dump before kill,
>   - sanitized JSON and Markdown reports.
> - Generate full-window, single-page, and adjacent-pair windows from an incident
>   range by default.

### Implementation Slice 2

> - Add low-level Docling formula/code VLM diagnostics around:
>   - `CodeFormulaVlmModel.__call__`,
>   - `AutoInlineVlmEngine.predict_batch`,
>   - `TransformersVlmEngine.predict_batch`.
> - Capture sanitized converter-cache, formula batch, image crop area, selected
>   engine, device, model class, dtype, KV-cache, prompt count, token budget,
>   generated-token count, and elapsed-time facts.
> - Add a JSONL sidecar that writes a `transformers_predict_batch_started` event
>   immediately before the Docling Transformers generation call. This preserves
>   evidence when a child is terminated or crashes before in-memory diagnostics can
>   be serialized.
> - Add Docling/Torch/Transformers runtime inventory to replay child payloads.
> - Update the Markdown report to show sidecar-started Transformers calls for
>   timed-out windows so operator-visible replay output is not blank when the
>   child never writes its normal payload.
> - Correct the fallback timing attribution boundary so broad Docling attempt time
>   is not mislabeled as formula enrichment. Precise formula VLM timings now come
>   from the dedicated diagnostics.

### Implementation Slice 3

> Keep this as a simple observation pass, not a broad profiler:
>
> - Add one JSONL event, `code_formula_batch_started`, emitted before each Docling
>   formula/code VLM batch when the replay sidecar is configured.
> - Include only content-safe per-crop metrics:
>   - batch position,
>   - label,
>   - crop width and height,
>   - pixel area,
>   - image mode/shape when available,
>   - SHA-256 identifier of the crop bytes.
> - Do not persist crop pixels, recognized text, generated text, source bytes, or
>   prompts beyond the existing prompt-count aggregate.
> - Use this event to correlate the last-started formula crops with subsequent
>   `transformers_predict_batch_started/completed`, timeout, or crash outcomes.
> - Do not tune batch size, token budget, dtype, compile path, or engine selection
>   until the crop-metrics replay identifies the failing crop/batch pattern.

### Validation Plan

> - 2026-06-04 unrelated coverage-gate follow-up:
>   - The seven non-Task-344 failures from the earlier full gate were traced to
>     stale compose/QTI/PDF test contracts governed by `TASK-337`, `TASK-315`,
>     `TASK-321`, `TASK-340`, and `TASK-341`.
>   - The focused seven-node slice now passes after the test-contract update.
>   - The affected test files also pass as a 38-test focused proof.
> - `pdm run docs-sync`
> - `pdm run docs-validate`
> - `pdm run skills-validate`
> - `pdm run handoff-validate`
> - `git diff --check`
> - For implementation closeout:
>   - `pdm run format`
>   - `pdm run lint`
>   - `pdm run typecheck`
>   - focused `pdm run test` for chunk/checkpoint/progress behavior
>   - Hemma page-window replay evidence captured without aborting active jobs

## Implementation Steps

## Proof

### Deliverables

> - [ ] A task-owned diagnostic command or script for page-window replay against
>   the current Docling pipeline.
> - [ ] A sanitized diagnostic report for the incident job and source PDF,
>   including page-window timings and resource samples.
> - [ ] Runtime/checkpoint fields or events that expose in-flight page-window
>   state and head-of-line blocking truthfully.
> - [ ] Focused tests for slow earlier chunk plus completed later chunk behavior.
> - [ ] A benchmark/parity recommendation for page-window sizing or adaptive
>   policy, linked forward to `T74`/`T273` when appropriate.
> - [ ] Documentation updates explaining how operators should interpret an active
>   long-running page window versus a true stall.

## Validation

## Stop Conditions

### Remediation Ladder

> The remediation must preserve output quality and fix the current Docling
> formula VLM path rather than route around it:
>
> 1. Forward model-spec stop strings into formula generation.
>    - Carry `CodeFormulaVlmModel.options.model_spec.stop_strings` into each
>      `VlmEngineInput` when Docling's formula adapter leaves it empty.
>    - Keep Docling's `max_new_tokens=2048` ceiling unchanged; it remains a
>      safety cap, not the normal stopping mechanism.
>    - Prove live Granite calls enter generation with
>      `stopping_criteria_count >= 1`.
>    - Prove no completed Granite generation row has
>      `max_new_tokens_exhausted: true`.
> 1. Prove Granite stops by stop criteria, not the token ceiling.
>    - Rerun direct page-14 `granite_docling`.
>    - Rerun crop-isolated page-14 `granite_docling`.
>    - Verify crop `#/texts/5` / hash
>      `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`
>      completes without return `-11`.
>    - Verify the normal fallback path from `codeformulav2` to
>      `granite_docling` completes when fallback is legitimately exercised.
> 1. If a native crash remains after stop strings are active, disable
>    `torch.compile` only for the ROCm formula VLM Transformers path and rerun
>    the same direct/crop/fallback proof.
>    - The crash stack is in the compiled `OptimizedModule` path over
>      Idefics3/Llama generation.
>    - Disabling compile is a runtime-stability remediation for the observed
>      native crash path, not a quality-reduction profile.
>    - Accept only if the same crop succeeds and output quality gates do not
>      regress.

## Lessons Learned

### Granite Formula Generation Root Cause

> 2026-06-04/05 live `/app` replay added a generation-boundary JSONL event around
> Docling's Hugging Face `generate(...)` call. This event records tensor shapes,
> token budgets, stop-criteria counts, elapsed time, and GPU memory counters
> without storing source text, crop pixels, or decoded model output.
>
> Direct page-14 Granite replay, without the `codeformulav2` primary pass:
>
> - remote report:
>   `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260604T232151Z/report.json`
> - result: timed out after `120276 ms`, return `-15`
> - first Granite formula batch:
>   - crop hashes:
>     `46dabcf37892db71122c17214df0245b9b7c94bd225e1fa6b127d208ee4f9a98`,
>     `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`,
>     `950bf921d80c5e1813e4ed06f20ec2ce2ecaeb3d578bd7ac1521d0959defd5a0`,
>     `5a7b93099ee4be855c87a168a784dd67ac6c57613f1b8efc9d3a0b049c1643dc`,
>     `adc3d509986d8abea8eeb992ffc063572fd38661a34543691c3f371647ce7c25`
>   - `input_ids_shape`: `[5, 606]`
>   - `pixel_values_shape`: `[5, 9, 3, 512, 512]`
>   - `max_new_tokens`: `2048`
>   - `stopping_criteria_count`: `null`
>   - `generation_config_eos_token_id`: `100257`
>   - `generated_ids_shape`: `[5, 2654]`
>   - `generated_new_token_counts`: `[2048, 2048, 2048, 2048, 2048]`
>   - `max_new_tokens_exhausted`: `true`
>   - generation elapsed: `80930 ms`
>
> This proves the slow Granite behavior is not page-complexity-proportional
> formula decoding. The first Granite formula batch ran to the exact
> `max_new_tokens=2048` ceiling for every item.
>
> Direct page-14 Granite single-item replay:
>
> - remote report:
>   `/app/build/verification/task-344-page-window-replay/task344-page-window-replay-20260604T232432Z/report.json`
> - result: native crash, return `-11`, after `55312 ms`
> - crop `#/texts/1`, hash
>   `46dabcf37892db71122c17214df0245b9b7c94bd225e1fa6b127d208ee4f9a98`,
>   completed in `11820 ms` with `310` new tokens
> - crop `#/texts/5`, hash
>   `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`,
>   entered Granite generation and crashed before a completed event
> - stack dump for the crash path was inside
>   `transformers.generation.utils.generate/_sample`,
>   `transformers.models.idefics3`, `transformers.models.llama`, and
>   `torch.nn.modules.linear`
>
> Installed Docling `2.73.1` source explains the missing stop-control path:
>
> - `CodeFormulaVlmModel.__call__` constructs formula `VlmEngineInput` with
>   hard-coded `max_new_tokens=2048` and `extra_generation_config`, but does not
>   pass `self.options.model_spec.stop_strings`.
> - `VlmEngineInput` has a `stop_strings` field.
> - `TransformersVlmEngine.predict_batch` only installs `StopStringCriteria`
>   when `first_input.stop_strings` is present.
> - Granite's Docling model spec declares stop strings
>   `["</doctag>", "<|end_of_text|>"]`, but the observed live formula call had
>   `stopping_criteria_count: null`.
>
> Root cause:
>
> - Sir Convert exercises Docling's `granite_docling` formula preset through
>   Docling's formula/code VLM adapter.
> - The adapter did not forward the Granite model spec's stop strings into the
>   generic VLM inputs. That was a real implementation gap, but live replay proved
>   it is not sufficient by itself.
> - With stop strings active, the pathological page-14 crop `#/texts/5` / image
>   hash `ba7f9866ffe1ad8d822f73e78f1d329f7ad51f1762629b64791e0013e094cec4`
>   still emits no configured stop string and no EOS/pad suffix before the hard
>   `2048` generated-token ceiling.
> - The retained decoded-output replay proves why: Granite enters a deterministic
>   LaTeX repetition loop for this crop. It starts with
>   `<loc_0><loc_0><loc_500><loc_500>\begin{array} ...`, emits an incomplete
>   formula fragment containing `\mathbb { E } [ s _ { i }`, then repeats the
>   fragment pattern `\mathbb { E } [ s _ { i } ] ... = ... \int` until the
>   `2048` generated-token ceiling. The output contains no configured terminator
>   and never reaches a closed formula/environment state.
> - On the Hemma ROCm/Torch/Transformers runtime, that one crop explains the
>   apparent random huge-token batch: the other rows stop, but the shared batch
>   tensor is padded to the one row that does not stop.
> - The native crash is in the same Granite/Idefics3/Llama generation path. The
>   ROCm `torch.compile` guard removes the compiled `OptimizedModule` wrapper and
>   prevents the direct-batch crash in observed replay, but it does not make
>   `#/texts/5` stop correctly.

### Required Diagnosis

> The implementation must gather evidence before tuning:
>
> 1. Reproduce the incident page-window behavior on Hemma or an explicitly
>    declared equivalent runtime.
> 1. Run controlled page-window replays for the incident pages with the same
>    Docling options, OCR mode, table/formula settings, acceleration policy, and
>    worker profile unless the experiment declares a single changed variable.
> 1. Capture CPU/GPU evidence for the replay:
>    - CPU wall time and process pressure,
>    - ROCm/GPU busy and memory samples where available,
>    - model initialization or warm-up state,
>    - Docling stage/profiler evidence when supported by the library.
> 1. Prove whether the pathological behavior is page-specific, window-combination
>    specific, first-use/warm-up related, semaphore/queue related, or commit-order
>    related.
> 1. Verify markdown/output parity for any smaller-window candidate before
>    recommending it.
> 1. Record why naive feature heuristics are insufficient for this incident.

## Notes

## Plan Document Review

## Implementation Review
