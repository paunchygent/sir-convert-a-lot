---
type: reference
id: REF-SIRCON-PLAN-machine-marked-answer-key-completion-implementation-roadmap
title: Machine-marked Answer-key Completion Implementation Roadmap
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: plan
retired_ids:
- REF-machine-marked-answer-key-completion-implementation-roadmap
summary: Machine-marked Answer-key Completion Implementation Roadmap
---
## Outcome And Purpose

Source record: docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md

## Planning Boundary

### Delivery Order

> 1. Contract foundation: Task 294.
> 1. Overlay runtime foundation: Task 295.
> 1. Teacher item-content overlay application: Task 302.
> 1. Generated OpenAPI consumer contract publication: Task 304.
> 1. Historical unkeyed/manual QTI profile exploration: Task 303, superseded by
>
> [Detailed field lists and examples remain in the frozen source record.]

### Tranche 0: Readiness Baseline

> Goal: confirm the lane is ready to implement without mixing in unrelated
> runtime or public-grant work.
>
> Checklist:
>
>
> [Detailed field lists and examples remain in the frozen source record.]

### Tranche 2: Overlay Runtime Foundation

> Governing task: `task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md`.
>
> Goal: accept and apply teacher overlays while keeping source IR immutable.
>
> Checklist:
>
> [Detailed field lists and examples remain in the frozen source record.]

### Tranche 2.5: Teacher Item-content Overlay Application

> Governing task: `task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md`.
>
> Goal: apply teacher item-content repairs from `effective_item_patch` to the
> effective renderer input while preserving source IR and answer-key provenance.
>
>
> [Detailed field lists and examples remain in the frozen source record.]

### Tranche 2.6: Unkeyed/manual QTI Profile For Accepted-current-state

> Governing task: `task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md`.
>
> Goal: historical/superseded by Task 337 for current runtime. This tranche
> defined and validated a QTI profile for teacher-accepted missing-key exports,
> but that profile is no longer an active authoring/correction or
>
> [Detailed field lists and examples remain in the frozen source record.]

### Tranche 2.9: Exam.net PDF Manual/unkeyed Accepted-current-state Profile

> Governing task:
> `task-308-define-examnet-pdf-manual-unkeyed-accepted-current-state-profile-and-multigap-readiness.md`.
>
> Goal: historical/superseded by Task 337 for current runtime. This tranche
> defined the Exam.net PDF counterpart to Task 303's manual/unkeyed QTI profile,
> but teacher-accepted missing-key PDF export is no longer an active
> authoring/correction or target-readiness unlock. Missing-key single-choice,
> missing-key multiple-response, and item-013-style multi-gap gap/open-cloze items
> remain blocked until real source, manual, or reviewed effective key state
> exists.
> Task 321 adds the reviewed-key correction: when accepted gap/open-cloze values
> exist, the PDF artifact must include those values, and this missing-key
> fallback must not be used to drop reviewed keys.
>
> Task 303 is QTI-only. It proves that missing keys can become
> manual/unkeyed QTI when XML/package/profile validation allows it. It does not
> prove that the Exam.net PDF-to-exam renderer can do the same. The PDF route
> must define its own profile, renderer behavior, and target-readiness proof.
>
> Checklist:
>
> - [ ] Define supported and unsupported PDF manual/unkeyed shapes for accepted
>   current-state.
> - [ ] Superseded by Task 337: do not thread accepted-current-state target
>   policy into the active Exam.net PDF renderer.
> - [ ] Superseded by Task 337: do not report a removed accepted-current-state
>   readiness unlock for `examnet_pdf`; missing-key PDF remains unavailable until
>   real effective key state exists.
> - [ ] Completed by Task 373 / Story 57 / PR-0406: downstream review-state
>   display consumes the compact Sir Convert projection while target readiness
>   remains the export authority.
> - [ ] Use item-013 as the regression case for a five-blank `Lucktext` item
>   with an embedded image and no accepted blank values.
> - [ ] Promote native multi-gap `Lucktext` PDF rendering if fixture proof
>   validates the shape; otherwise block the current profile until a governed
>   provenance-preserving degraded target shape is approved.
> - [ ] Fix warning/readiness precedence so item-specific multi-gap limitations
>   are not masked by the first `manual_answer_key_required` warning or confused
>   with fatal target unavailability when degraded rendering succeeds.
>
> Stop conditions:
>
> - Stop if PDF output would drop visible prompt text, alternatives, gaps,
>   embedded images, or manual follow-up semantics.
> - Stop if no governed provenance-preserving rendering can preserve the item
>   content requested for PDF export.
> - Stop if the profile would invent answers or source provenance.
>
> ### PR-0331 reviewed-key target fallback purge
>
> Governing task:
> `task-321-purge-reviewed-answer-key-export-fallbacks-for-pr-0331.md`.
>
> Goal: prevent target-specific QTI/PDF fallbacks from removing reviewed,
> teacher-provided, or source-provided keys after those keys reach effective
> renderer input. QTI package availability must fail closed when items are
> omitted or still missing required accepted values; reviewed gap/open-cloze
> values must be emitted in keyed QTI text-entry responses and in PDF artifacts.
>
> - Stop if public JSON shape changes without OpenAPI snapshot and same-slice
>   consumer impact planning.

### Tranche 3: Structured Provider Harness

> Governing task: `task-296-extract-structured-chat-provider-harness-for-local-first-completion.md`.
>
> Goal: build the generic local-first structured provider boundary without tying
> it to DigiExam parser or renderer internals.
>
> Checklist:
>
> - [x] Add `StructuredChatProviderProtocol`.
> - [x] Add `StructuredOutputSpec` with Chat Completions, Responses, and
>   llama.cpp grammar/schema payload fields.
> - [x] Add provider profile/config models with explicit capabilities.
> - [x] Add provider set and failover policy.
> - [x] Add token budget resolver and item-local preflight.
> - [x] Add metadata-only capture and telemetry decisions.
> - [x] Add Dishka providers where composition and test injection benefit.
> - [x] Add module-level Google-style docstrings to new Python modules.
>
> Tranche 3.1 evidence:
>
> - `domain.structured_llm_contracts` owns pure source-neutral provider
>   contracts, route policy, budget preflight, and metadata-only capture.
> - `infrastructure.structured_llm_payloads` builds Chat Completions, Responses,
>   llama.cpp JSON Schema, llama.cpp GBNF, and vLLM structured-choice payloads
>   without provider network calls.
>
> Tranche 3.2 evidence:
>
> - `infrastructure.structured_llm_provider` now executes configured
>   OpenAI-compatible structured-provider calls with endpoint selection for Chat
>   Completions, Responses, llama.cpp-compatible chat completions, and
>   vLLM-compatible chat completions.
> - `infrastructure.structured_llm_responses` now parses provider responses into
>   `StructuredLLMResponse` and maps missing config, request errors, HTTP status
>   errors, invalid JSON, empty content, non-JSON content, non-object content,
>   and conservative schema mismatches into typed backend failure codes.
> - This left service settings/config loading, Dishka composition, and
>   route/runtime default proof for the final Task 296 slice.
>
> Tranche 3.3 evidence:
>
> - `infrastructure.structured_llm_config` now loads disabled-by-default
>   service settings with centralized constants for provider env vars and JSON
>   provider keys.
> - `ServiceConfig` carries the structured LLM runtime config without making
>   parser, renderer, or HTTP artifact routes provider-aware.
> - `infrastructure.structured_llm_di` provides the opt-in Dishka async container
>   for `HttpStructuredChatProvider` and HTTP client lifecycle/test injection.
> - `dishka<2,>=1.7` is now a direct runtime dependency and the generated service
>   dependency manifests include it for CPU and ROCm images.
> - DigiExam migration default route proof shows the
>   `answer_key_completion_report` remains `not_requested` and provider execution
>   is not called during default artifact creation or download.
> - Task 296 is complete. Task 297 is complete; advisory candidate builders and
>   answer-key completion reports are implemented for missing choice and gap-fill
>   answer keys.
>
> Checkpoint:
>
> - [x] Payload-builder tests cover Chat Completions `response_format`, Responses
>   `text.format`, and llama.cpp schema/GBNF modes.
> - [x] Routing tests cover local success, local unavailable, remote forbidden,
>   explicit false, missing consent, and allowed signed consent.
> - [x] Capture tests prove raw prompts, raw responses, item text, and student data
>   are not persisted in normal mode.
> - [x] Composition tests cover disabled defaults, constant-backed env loading,
>   local-primary enforcement, API-key env indirection, Dishka provider
>   injection, and default DigiExam artifact routes making no structured LLM
>   calls.
>
> Stop conditions:
>
> - Stop if implementation relies on edit-ops-specific Skriptoteket types.
> - Stop if remote fallback can happen without explicit signed/authenticated
>   policy.

### Tranche 3.5: Granite FP8 vLLM Runtime Smoke And Interim Settlement

> Governing task: `task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md`.
>
> Goal: prove whether Granite 4.1 8B FP8 can start on Hemma's AMD R9700/RDNA4
> ROCm vLLM preview lane, satisfy one structured-output MCQ smoke, and serve as a
> temporary local provider while the feature is implemented.
>
> Checklist:
>
> - [x] Verify Hemma repo root, Docker, GPU, ROCm device nodes, scratch/cache, and
>   current port usage.
> - [x] Select a non-conflicting localhost port for the vLLM OpenAI-compatible
>   server.
> - [x] Pull or reuse the AMD ROCm 7.12 `gfx120X-all` vLLM preview image.
> - [x] Start a named detached vLLM container for
>   `ibm-granite/granite-4.1-8b-fp8`.
> - [x] Run vLLM/PyTorch/HIP sanity checks in the container image.
> - [x] Run a structured `choice` Chat Completions MCQ request that must answer
>   `B`.
> - [x] Record port, container name, image, model, startup state, log summary,
>   response, and cleanup state in the governed task.
> - [x] Copy the downloaded Granite FP8 snapshot into the canonical
>   scratch-backed Hugging Face cache used by the existing local model lanes.
> - [x] Document vLLM Granite FP8 as the temporary local provider pending
>   production-path validation and later Task 300 benchmarking.
>
> Checkpoint:
>
> - [x] Task 301 states whether the FP8/vLLM candidate is viable, blocked, or
>   needs a specific runtime follow-up.
> - [x] The result is not treated as model selection until Task 300's real-data
>   benchmark matrix proves correctness and wrong-but-valid behavior.
> - [x] Provider implementation may proceed against this runtime without waiting
>   for the comparative benchmark.
> - [x] Task 309 later demoted this runtime for answer-key completion after live
>   corpus and direct-probe evidence showed unacceptable wrong-but-valid answer
>   quality despite successful structured-output protocol behavior.
>
> Stop conditions:
>
> - Stop if the smoke would require changing production service ports, compose
>   files, or public routing.
> - Stop if Docker/ROCm devices are unavailable.
> - Stop if image/model acquisition would require destructive cache or Docker
>   pruning.

### Tranche 4: Deferred Local Model Benchmark Harness

> Governing task: `task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md`.
>
> Goal: benchmark the mandatory local model matrix on real data after the full
> app path is working and deployed. Granite/vLLM remains only as a demoted
> baseline unless a later governed result overturns the Task 309 evidence. Task
> 309 owns the first Granite/vLLM-only live validation and failure-path inventory;
> do not use this tranche for that precursor run.
>
> Mandatory first-pass matrix:
>
> | Model | Quant |
> |---|---|
> | `ibm-granite/granite-4.1-8b-fp8` on vLLM | FP8 demoted baseline |
> | `unsloth/Qwen3.6-27B-GGUF` | `Qwen3.6-27B-Q6_K.gguf` current guarded baseline |
> | `unsloth/Devstral-Small-2-24B-Instruct-2512-GGUF` | `UD-Q6_K_XL` demoted comparison |
> | `unsloth/Qwen3.5-4B-GGUF` | `UD-Q6_K_XL` |
> | `unsloth/gemma-4-E4B-it-GGUF` | `Q6_K` |
> | `unsloth/granite-4.1-8b-GGUF` | `Q6_K` |
> | `unsloth/Qwen3.5-9B-GGUF` | `Q6_K` |
> | `unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF` | `UD-Q6_K_XL` |
> | Mistral Small on `llama.cpp` | exact GGUF/quant resolved by the next governed runtime slice |
>
> Checklist:
>
> - [ ] Add domain models for candidate, quant, item fixture, expected answer,
>   structured decision, validation result, and benchmark report.
> - [ ] Add application services for matrix planning, execution, evaluation, and
>   aggregation.
> - [ ] Add infrastructure adapters for `llama.cpp` server/process lifecycle.
> - [ ] Add corpus loader for real multiple choice, multiple response, matching,
>   and open cloze/gap-fill items.
> - [ ] Enforce grammar/schema-constrained output only.
> - [ ] Prefer vLLM `choice` values for MCQ/MCW items with clear bounded
>   candidate selection; use JSON Schema/grammar only where the provider harness
>   proves support or the item type requires structured objects.
> - [ ] Disable thinking/direct-output traces where needed.
> - [ ] Emit deterministic JSON report and Markdown summary.
>
> Checkpoint:
>
> - [ ] Every candidate has structured call success rate, backend-valid decision
>   rate, correctness by item type, wrong-but-valid rate,
>   `manual_follow_up_required` rate, unknown-ID rate, latency, tokens/sec, and
>   memory footprint.
> - [ ] Report can recommend no model if wrong-but-valid risk is too high.
> - [ ] The selected model is justified by real data, not model-card benchmark
>   scores.
> - [ ] The bake-off starts only after Task 309 has completed and the full app
>   path is working and deployed.
> - [ ] Granite/vLLM is compared only as a demoted baseline unless a later
>   governed result overturns the Task 309 evidence.
>
> Stop conditions:
>
> - Stop if any run uses relaxed JSON prompting fallback.
> - Stop if wrong-but-valid answers cannot be separated from schema failures.
> - Stop if expected answers for the real corpus are not source-bound or
>   teacher-verified.

## Evidence Basis

## Confirmed Contract

### Tranche 1: Contract Foundation

> Governing task: `task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md`.
>
> Goal: make every public and internal contract shape explicit before runtime code
> accepts overlays or emits completion reports.
>
>
> [Detailed field lists and examples remain in the frozen source record.]

### Tranche 2.55: Generated OpenAPI Consumer Contract

> Governing task: `task-304-publish-generated-sir-convert-v2-openapi-contract-for-digiexam-migration-bundles.md`.
>
> Goal: publish a deterministic Sir Convert v2 OpenAPI snapshot so Skriptoteket
> can generate or validate consumer types before live Docker/service tests.
>
>
> [Detailed field lists and examples remain in the frozen source record.]

### Tranche 2.7: Matching Answer-key Pair IR Contract

> Governing task: `task-298-define-matching-answer-key-pair-ir-contract.md`.
>
> Goal: define the first-class source-neutral matching answer-key pair shape
> before teacher overlays, LLM advisory output, reviewed application, PDF
> rendering, or QTI export may claim matching can be automatically evaluated.
>
> [Detailed field lists and examples remain in the frozen source record.]

### Tranche 2.8: Gapped/open-cloze Accepted-value IR Contract

> Governing task: `task-305-define-gapped-open-cloze-accepted-value-ir-contract.md`.
>
> Goal: define the first-class, source-neutral gap/open-cloze accepted-value
> shape in `ExamAuthoringIR v1` before teacher overlays, LLM advisory output,
> reviewed application, PDF rendering, or QTI export may claim gapped/open-cloze
> items can be automatically evaluated.
>
> Checklist:
>
> - [x] Define stable gap IDs, display order, prompt binding, source evidence,
>   and source spans.
> - [x] Add accepted values per gap as structured authoring answer-key data.
> - [x] Define normalization policy and whether it is validation-only or
>   target-specific.
> - [x] Define multi-gap completeness rules.
> - [x] Preserve source-bound parser provenance separately from effective
>   teacher/manual or reviewed answer-key provenance.
> - [x] Update manifest/report, target-readiness, PDF, and QTI contract surfaces
>   that depend on gap accepted-value shape.
> - [x] Keep unsupported target export as target-readiness/degradation, not an IR
>   restriction.
> - [x] Preserve teacher choices for degraded/manual/free-text inclusion,
>   omission, or manual recreation guidance.
>
> Checkpoint:
>
> - [x] Gap accepted values are first-class `ExamAuthoringIR v1` data.
> - [x] Gapped/open-cloze items remain manual/unkeyed or unavailable for
>   automatic evaluation until trusted accepted values exist.
> - [x] Matching-styled gap/open-cloze workaround evidence is not promoted to
>   DigiExam matching; target remapping decisions stay in validators/exporters.
> - [x] Later provider/advisory/application tasks can consume the contract
>   without changing it.
>
> Task 305 completed this tranche with
> `ExamAuthoringGapOpenClozeInteraction`, gap accepted-value validators,
> normalization profiles, DigiExam source-adapter mapping, and target-readiness
> degradation rows for unsupported multi-gap Exam.net PDF export.
>
> Stop conditions:
>
> - Stop if accepted values would be inferred from visible prompt text.
> - Stop if accepted values cannot be represented as exact gap-ID-bound data.
> - Stop if target limitations are encoded as source-parser or neutral-IR
>   restrictions.
> - Stop if the implementation deepens `DigiExamIntermediateExam` into a
>   universal model instead of mapping source-neutral concepts into
>   `ExamAuthoringIR v1`.

## Backlog Derivation

## Planning Stop Conditions

### Purpose

> This roadmap sequences the implementation of Sir Convert-a-Lot's
> machine-marked answer-key completion route from governed contracts to local
> model benchmarking, advisory completion, reviewed application, and downstream
> Skriptoteket/HuleEdu integration.
>
> The roadmap is intentionally checkpoint-heavy. A later tranche may not start
> until the previous checkpoint has produced durable evidence in the governed
> task, reference, report, or retained review surface.
