---
type: reference
id: REF-machine-marked-answer-key-completion-implementation-roadmap
title: Machine-marked Answer-key Completion Implementation Roadmap
status: active
created: 2026-05-14
updated: 2026-05-15
owners:
  - platform
tags:
  - roadmap
  - answer-key-completion
  - llm
  - llama-cpp
  - digiexam
  - skriptoteket
links:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-304-publish-generated-sir-convert-v2-openapi-contract-for-digiexam-migration-bundles.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/backlog/tasks/task-299-publish-cross-repo-skriptoteket-and-huleedu-answer-key-completion-handoff.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
---

## Purpose

This roadmap sequences the implementation of Sir Convert-a-Lot's
machine-marked answer-key completion route from governed contracts to local
model benchmarking, advisory completion, reviewed application, and downstream
Skriptoteket/HuleEdu integration.

The roadmap is intentionally checkpoint-heavy. A later tranche may not start
until the previous checkpoint has produced durable evidence in the governed
task, reference, report, or retained review surface.

## Delivery Order

1. Contract foundation: Task 294.
1. Overlay runtime foundation: Task 295.
1. Teacher item-content overlay application: Task 302.
1. Generated OpenAPI consumer contract publication: Task 304.
1. Unkeyed/manual QTI profile for accepted-current-state export: Task 303.
1. Matching answer-key pair IR contract: Task 298.
1. Gapped/open-cloze accepted-value IR contract: Task 305.
1. Structured provider harness: Task 296.
1. Experimental Granite FP8/vLLM Hemma smoke and interim local provider
   settlement: Task 301.
1. Advisory completion reports: Task 297.
1. Reviewed application into effective IR: Task 306.
1. Local model benchmark harness and live matrix: Task 300.
1. Cross-repo Skriptoteket/HuleEdu handoff: Task 299.

Do not collapse these tranches. The sequence protects source-bound parser
provenance, prevents provider code from leaking into parser/rendering concerns,
and keeps model choice evidence-driven.

Task 301 is allowed to run before the full benchmark harness because it is a
bounded operator smoke test of a runtime candidate, not a provider integration
or final model-selection gate. Its evidence settles Granite 4.1 8B FP8 on vLLM
as the interim local provider while the feature is implemented. Task 300 remains
the real-data benchmark authority for later comparison against the GGUF
shortlist before longer-term promotion.

Tasks 302 and 303 close the overlay/export contract gaps discovered after Task
295: Task 302 now applies supported item-content patches to effective IR, while
accepted-current-state still cannot enable QTI until Task 303 or a later
governed unkeyed/manual profile proves schema/profile validity for the selected
QTI version.

Task 304 is the consumer-contract checkpoint before more Skriptoteket live
integration. It makes the FastAPI-generated v2 OpenAPI snapshot deterministic
and includes the multipart overlay, effective exam, bundle manifest, overlay
report, and target-readiness schemas needed for consumer type generation.

## Tranche 0: Readiness Baseline

Goal: confirm the lane is ready to implement without mixing in unrelated
runtime or public-grant work.

Checklist:

- [ ] Confirm `EPIC-11` is the governing epic.
- [ ] Confirm `REF-digiexam-machine-marked-answer-key-completion-architecture`
  is the architecture authority.
- [ ] Confirm `REF-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan`
  is the benchmark/model candidate authority.
- [ ] Confirm Story 46 cleanup tasks that block unrelated Exam.net runtime are
  not being reopened by this lane.
- [ ] Confirm no code implementation starts before Task 294 updates the route
  and IR contracts.

Checkpoint:

- [ ] `pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`
  pass with the roadmap linked from Epic 11.

Stop conditions:

- Stop if the implementation would treat LLM output as parser evidence.
- Stop if it needs Skriptoteket UI behavior before the Sir Convert overlay
  contract exists.

## Tranche 1: Contract Foundation

Governing task: `task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md`.

Goal: make every public and internal contract shape explicit before runtime code
accepts overlays or emits completion reports.

Checklist:

- [x] Add `digiexam_ingestion_overlay` to the service API/artifact contract as
  an optional multipart part.
- [x] Add job-spec options for overlay policy, completion mode, eligible item
  types, and remote provider policy.
- [x] Define `digiexam_ingestion_overlay_v2`.
- [x] Define teacher review-decision entries, including accepting the current
  missing answer-key state without adding answer data.
- [x] Define source item fingerprint inputs and exclusion rules.
- [x] Define `effective_ir_json` artifact semantics as
  `digiexam_effective_exam_v2`.
- [x] Define `ingestion_overlay_report_v1`.
- [x] Define `answer_key_completion_report_v1`.
- [x] Define `target_readiness_report_v1` with per-target and per-item
  consumer readiness after overlay application.
- [x] Define idempotency inputs including overlay digest.
- [x] Decide that effective IR must not reuse the parser-owned source IR
  schema.
- [x] Keep matching application blocked unless exact matching pairs exist in IR.

Checkpoint:

- [x] Contract examples cover source binding, source-derived item context,
  choice patch, gap-fill patch, matching patch, manual answer key, accepted
  current state, and target readiness.
- [x] The docs explicitly say source-derived item context is not answer
  evidence.
- [x] The docs explicitly say local Skriptoteket acceptance is not file
  readiness; only Sir Convert target readiness can enable PDF or QTI.
- [x] The current `digiexam_migration_bundle_v3` contract is documented as a
  hard bundle cutover with no compatibility shim or source-only fallback lane.
- [x] Contract text confirms no privacy-policy regression for product-visible
  outputs, overlays, reports, and target readiness.

Stop conditions:

- Stop if the overlay contract needs raw files, caller-supplied raw asset
  payloads, result PDF text, student data, owner metadata, or artifact paths.
- Stop if a breaking API change is introduced without locating the Sir Convert,
  Skriptoteket, and HuleEdu consumers that must migrate.

## Tranche 2: Overlay Runtime Foundation

Governing task: `task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md`.

Goal: accept and apply teacher overlays while keeping source IR immutable.

Checklist:

- [ ] Add typed overlay DTOs with `extra=forbid`.
- [ ] Add source binding validation for source file hash, source IR hash/schema,
  item ID, sequence, item fingerprint, and item type.
- [ ] Add source item fingerprint generation to the source IR manifest path.
- [ ] Persist overlay bytes beside uploads.
- [ ] Include overlay digest in idempotency.
- [ ] Add an overlay application service that returns source exam, effective
  exam, and ingestion overlay report.
- [ ] Apply review-decision entries without mutating parser evidence or source
  IR answer-key provenance.
- [ ] Emit `effective_ir_json` only when renderer input changes.
- [ ] Emit `ingestion_overlay_report` as a named artifact when overlays are
  present.
- [ ] Emit target readiness after overlay application and before named target
  artifacts become downloadable.
- [ ] Prove no-overlay requests emit v2 bundles and target readiness without
  applying overlay behavior.

Checkpoint:

- [ ] Unit tests cover stale overlay, wrong item, wrong type, unknown fields,
  oversized overlay, forbidden payload content, accepted current state, and
  valid manual overlay.
- [ ] Bundle tests prove source IR remains unchanged and effective IR changes
  only when expected.
- [ ] Bundle tests prove accepted current state clears only the teacher-review
  gate and keeps unsupported target shapes or failed QTI validation unavailable.
- [ ] Focused route tests prove overlay persistence and idempotency.

Stop conditions:

- Stop if parser output must be mutated to make overlay application work.
- Stop if renderers need provider or overlay validation details.

## Tranche 2.5: Teacher Item-content Overlay Application

Governing task: `task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md`.

Goal: apply teacher item-content repairs from `effective_item_patch` to the
effective renderer input while preserving source IR and answer-key provenance.

Checklist:

- [x] Validate patch payloads by item type with `extra=forbid`.
- [x] Bind every patch to source item ID, sequence, item type, source item
  fingerprint, and nested source IDs where applicable.
- [x] Reject raw/base64 assets, arbitrary files, scoring policy changes, and
  answer-key provenance in item-content patches.
- [x] Apply choice/MCQ visible option and prompt/body repairs to effective IR.
- [x] Apply gap-fill visible prompt/body and source-bound gap repair fields to
  effective IR.
- [x] Keep matching visible prompt/body and pair editing out of the DigiExam
  effective IR path; matching is owned by the neutral authoring slice.
- [x] Prove PDF and QTI renderers consume effective item content when the
  target shape is governed and validation passes.
- [x] Recompute target readiness after patch application and target
  validation.

Checkpoint:

- [x] Source IR bytes, source manifest, parser provenance, and source item
  fingerprints remain unchanged after item-content overlays.
- [x] `ingestion_overlay_report_v1` names accepted and rejected patch fields.
- [x] Missing answer keys remain missing unless a manual answer key or
  governed unkeyed/manual target profile applies.

Stop conditions:

- Stop if item-content repair requires mutating parser output.
- Stop if target readiness and renderer output disagree.
- Stop before enabling unkeyed/manual QTI export.

## Tranche 2.55: Generated OpenAPI Consumer Contract

Governing task: `task-304-publish-generated-sir-convert-v2-openapi-contract-for-digiexam-migration-bundles.md`.

Goal: publish a deterministic Sir Convert v2 OpenAPI snapshot so Skriptoteket
can generate or validate consumer types before live Docker/service tests.

Checklist:

- [x] Add `pdm run openapi-export-v2`.
- [x] Commit `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`.
- [x] Mark `job_spec` and `digiexam_ingestion_overlay` as multipart JSON
  parts.
- [x] Publish schemas for the DigiExam overlay, bundle manifest, effective
  exam, overlay report, and target-readiness report.
- [x] Add tests that fail when the committed OpenAPI snapshot is stale.

Checkpoint:

- [x] Skriptoteket no longer has to infer the changed overlay/effective-IR
  service contract from Markdown alone before live integration tests.

Stop conditions:

- Stop if consumer contracts require compatibility shims for
  `digiexam_migration_bundle_v1`.
- Stop if route docs and generated OpenAPI disagree.

## Tranche 2.6: Unkeyed/manual QTI Profile For Accepted-current-state

Governing task: `task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md`.

Goal: define and validate the QTI profile that lets teacher
`accept_current_state_for_export` enable QTI export for missing-key items only
when the selected QTI 2.1 or QTI 3.0 package is otherwise schema-valid and
target-valid.

Missing-key means Sir Convert lacks trusted source, manual, or reviewed
effective correct-response data for automatic evaluation; it does not mean the
visible question content is missing.

Checklist:

- [x] Link authoritative QTI 2.1 and QTI 3.0 schema sources from the QTI
  reference.
- [x] Record the schema requirements Sir Convert depends on, including
  optional response declarations, optional response processing, optional
  correct responses, and interaction binding requirements.
- [x] Define preservation-first unkeyed/manual item representations and report
  semantics. Missing keys remove automatic correct-answer/evaluation claims, not
  visible question content.
- [x] Preserve matching, gap-fill, and similar shapes through deterministic
  manual/unkeyed QTI representations whenever schema/profile validation allows
  it, even when Exam.net imports them as free-text/manual items or requires
  teacher cleanup.
- [x] Keep unsupported for automatic evaluation distinct from unavailable for
  manual/unkeyed export in target readiness and validation reports.
- [x] Generate deterministic sample packages and validation reports for every
  supported shape.
- [x] Update target readiness so accepted-current-state can enable QTI only
  inside the validated unkeyed/manual profile.
- [x] Record Exam.net import proof as vendor-unproven/external dependency until
  the vendor provides an import test path; use realistic Sir Convert QTI exam
  files for local proof and later vendor support.

Checkpoint:

- [x] QTI schema-validity, Sir Convert target-validity, and Exam.net import
  proof are distinct in docs and reports.
- [x] Unsupported for automatic evaluation is distinct from unavailable for
  manual/unkeyed export; only shapes that would drop visible content or break
  validation remain unavailable.

Stop conditions:

- Stop if Exam.net import proof contradicts the profile.
- Stop if teacher acceptance would hide XML/schema/profile validation failures.

## Tranche 2.7: Matching Answer-key Pair IR Contract

Governing task: `task-298-define-matching-answer-key-pair-ir-contract.md`.

Goal: define the first-class source-neutral matching answer-key pair shape
before teacher overlays, LLM advisory output, reviewed application, PDF
rendering, or QTI export may claim matching can be automatically evaluated.

Checklist:

- [x] Add stable source and target bindings for matching prompts and options in
  `ExamAuthoringIR v1`.
- [x] Add directed answer pairs as ordered pairs of known source/target IDs in
  `ExamAuthoringIR v1`.
- [ ] Preserve QTI-style `match_min`/`match_max` or equivalent association
  constraints so the IR can represent many-left-to-one, one-left-to-many,
  one-to-one, and right-side distractors.
- [ ] Define target-profile completeness validation separately from
  intermediary IR validation.
- [ ] Preserve source-bound parser provenance separately from effective
  teacher/manual or reviewed answer-key provenance.
- [ ] Update manifest/report, target-readiness, PDF, and QTI contract surfaces
  that depend on matching answer-key shape.
- [ ] Surface OpenAPI/Skriptoteket consumer impacts before changing generated
  schemas or runtime response JSON.
- [ ] Replace cross-repo hard-coded schema version strings with generated or
  centralized contract constants before closing the version bump.

Checkpoint:

- [ ] Matching answer-key pairs are first-class IR/effective-IR data.
- [ ] Matching remains manual/unkeyed or unavailable for automatic evaluation
  until exact trusted pairs exist.
- [ ] Exam.net PDF readiness enforces one-to-one matched pairs with optional
  unmatched right-side distractors, while general IR remains QTI-permissive.
- [ ] Exam.net QTI readiness remains vendor-unproven until Exam.net provides an
  import test path.
- [ ] Sir Convert and Skriptoteket consumers reference schema-version constants
  or generated types rather than duplicating version literals at callsites.
- [ ] Later provider/advisory/application tasks can consume the contract
  without changing it.

Stop conditions:

- Stop if correct pairs would be inferred from visible prompt text.
- Stop if matching pairs cannot be represented as exact ID-bound data.
- Stop if target-specific Exam.net PDF limits would be encoded into
  parser-owned source IR or effective IR.
- Stop if OpenAPI/Skriptoteket compatibility would change without a real schema
  version bump and same-slice consumer updates.
- Stop if the version bump depends on scattered hard-coded schema strings in
  either repo.

## Tranche 2.8: Gapped/open-cloze Accepted-value IR Contract

Governing task: `task-305-define-gapped-open-cloze-accepted-value-ir-contract.md`.

Goal: define the first-class, source-neutral gap/open-cloze accepted-value
shape in `ExamAuthoringIR v1` before teacher overlays, LLM advisory output,
reviewed application, PDF rendering, or QTI export may claim gapped/open-cloze
items can be automatically evaluated.

Checklist:

- [ ] Define stable gap IDs, display order, prompt binding, source evidence,
  and source spans.
- [ ] Add accepted values per gap as structured authoring answer-key data.
- [ ] Define normalization policy and whether it is validation-only or
  target-specific.
- [ ] Define multi-gap completeness rules.
- [ ] Preserve source-bound parser provenance separately from effective
  teacher/manual or reviewed answer-key provenance.
- [ ] Update manifest/report, target-readiness, PDF, and QTI contract surfaces
  that depend on gap accepted-value shape.
- [ ] Keep unsupported target export as target-readiness/degradation, not an IR
  restriction.
- [ ] Preserve teacher choices for degraded/manual/free-text inclusion,
  omission, or manual recreation guidance.

Checkpoint:

- [ ] Gap accepted values are first-class `ExamAuthoringIR v1` data.
- [ ] Gapped/open-cloze items remain manual/unkeyed or unavailable for
  automatic evaluation until trusted accepted values exist.
- [ ] Matching-styled gap/open-cloze workaround evidence is not promoted to
  DigiExam matching; target remapping decisions stay in validators/exporters.
- [ ] Later provider/advisory/application tasks can consume the contract
  without changing it.

Stop conditions:

- Stop if accepted values would be inferred from visible prompt text.
- Stop if accepted values cannot be represented as exact gap-ID-bound data.
- Stop if target limitations are encoded as source-parser or neutral-IR
  restrictions.
- Stop if the implementation deepens `DigiExamIntermediateExam` into a
  universal model instead of mapping source-neutral concepts into
  `ExamAuthoringIR v1`.

## Tranche 3: Structured Provider Harness

Governing task: `task-296-extract-structured-chat-provider-harness-for-local-first-completion.md`.

Goal: build the generic local-first structured provider boundary without tying
it to DigiExam parser or renderer internals.

Checklist:

- [ ] Add `StructuredChatProviderProtocol`.
- [ ] Add `StructuredOutputSpec` with Chat Completions, Responses, and
  llama.cpp grammar/schema payload fields.
- [ ] Add provider profile/config models with explicit capabilities.
- [ ] Add provider set and failover policy.
- [ ] Add token budget resolver and item-local preflight.
- [ ] Add metadata-only capture and telemetry decisions.
- [ ] Add Dishka providers where composition and test injection benefit.
- [ ] Add module-level Google-style docstrings to new Python modules.

Checkpoint:

- [ ] Payload-builder tests cover Chat Completions `response_format`, Responses
  `text.format`, and llama.cpp schema/GBNF modes.
- [ ] Routing tests cover local success, local unavailable, remote forbidden,
  explicit false, missing consent, and allowed signed consent.
- [ ] Capture tests prove raw prompts, raw responses, item text, and student data
  are not persisted in normal mode.

Stop conditions:

- Stop if implementation relies on edit-ops-specific Skriptoteket types.
- Stop if remote fallback can happen without explicit signed/authenticated
  policy.

## Tranche 3.5: Granite FP8 vLLM Runtime Smoke And Interim Settlement

Governing task: `task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md`.

Goal: prove whether Granite 4.1 8B FP8 can start on Hemma's AMD R9700/RDNA4
ROCm vLLM preview lane, satisfy one structured-output MCQ smoke, and serve as
the interim local provider while the feature is implemented.

Checklist:

- [x] Verify Hemma repo root, Docker, GPU, ROCm device nodes, scratch/cache, and
  current port usage.
- [x] Select a non-conflicting localhost port for the vLLM OpenAI-compatible
  server.
- [x] Pull or reuse the AMD ROCm 7.12 `gfx120X-all` vLLM preview image.
- [x] Start a named detached vLLM container for
  `ibm-granite/granite-4.1-8b-fp8`.
- [x] Run vLLM/PyTorch/HIP sanity checks in the container image.
- [x] Run a structured `choice` Chat Completions MCQ request that must answer
  `B`.
- [x] Record port, container name, image, model, startup state, log summary,
  response, and cleanup state in the governed task.
- [x] Copy the downloaded Granite FP8 snapshot into the canonical
  scratch-backed Hugging Face cache used by the existing local model lanes.
- [x] Document vLLM Granite FP8 as the interim local provider until Task 300
  benchmarks it against the remaining candidates.

Checkpoint:

- [x] Task 301 states whether the FP8/vLLM candidate is viable, blocked, or
  needs a specific runtime follow-up.
- [x] The result is not treated as model selection until Task 300's real-data
  benchmark matrix proves correctness and wrong-but-valid behavior.
- [x] Provider implementation may proceed against this runtime without waiting
  for the comparative benchmark.

Stop conditions:

- Stop if the smoke would require changing production service ports, compose
  files, or public routing.
- Stop if Docker/ROCm devices are unavailable.
- Stop if image/model acquisition would require destructive cache or Docker
  pruning.

## Tranche 4: Local Model Benchmark Harness

Governing task: `task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md`.

Goal: benchmark the settled vLLM Granite FP8 route against the mandatory local
model matrix on real data after the first feature implementation path exists.

Mandatory first-pass matrix:

| Model | Quant |
|---|---|
| `ibm-granite/granite-4.1-8b-fp8` on vLLM | FP8 |
| `unsloth/Qwen3.5-4B-GGUF` | `UD-Q6_K_XL` |
| `unsloth/gemma-4-E4B-it-GGUF` | `Q6_K` |
| `unsloth/granite-4.1-8b-GGUF` | `Q6_K` |
| `unsloth/Qwen3.5-9B-GGUF` | `Q6_K` |
| `unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF` | `UD-Q6_K_XL` |

Checklist:

- [ ] Add domain models for candidate, quant, item fixture, expected answer,
  structured decision, validation result, and benchmark report.
- [ ] Add application services for matrix planning, execution, evaluation, and
  aggregation.
- [ ] Add infrastructure adapters for `llama.cpp` server/process lifecycle.
- [ ] Add corpus loader for real multiple choice, multiple response, matching,
  and open cloze/gap-fill items.
- [ ] Enforce grammar/schema-constrained output only.
- [ ] Disable thinking/direct-output traces where needed.
- [ ] Emit deterministic JSON report and Markdown summary.

Checkpoint:

- [ ] Every candidate has structured call success rate, backend-valid decision
  rate, correctness by item type, wrong-but-valid rate,
  `manual_follow_up_required` rate, unknown-ID rate, latency, tokens/sec, and
  memory footprint.
- [ ] Report can recommend no model if wrong-but-valid risk is too high.
- [ ] The selected model is justified by real data, not model-card benchmark
  scores.

Stop conditions:

- Stop if any run uses relaxed JSON prompting fallback.
- Stop if wrong-but-valid answers cannot be separated from schema failures.
- Stop if expected answers for the real corpus are not source-bound or
  teacher-verified.

## Tranche 5: Advisory Completion Reports

Governing task: `task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md`.

Goal: produce safe advisory completion reports without changing renderer input.

Checklist:

- [ ] Build choice candidate inputs.
- [ ] Build gap-fill/open cloze candidate inputs.
- [ ] Skip source-bound answer keys, unreliable structures, unsupported assets,
  unsupported item types, and over-budget items.
- [ ] Add item-type output specs and backend validators.
- [ ] Emit `answer_key_completion_report`.
- [ ] Keep source IR, effective IR, PDF, QTI, and manifest output unchanged by
  advisory suggestions.

Checkpoint:

- [ ] Tests prove advisory mode makes no renderer-input changes.
- [ ] Reports include per-item status and backend failure code, but no raw
  prompts/responses or item text capture.
- [ ] Manual follow-up remains safer than wrong-but-valid completion.

Stop conditions:

- Stop if advisory output is needed by renderers.
- Stop if a provider error can become an answer key.

## Tranche 6: Reviewed Application Into Effective IR

Governing task: `task-306-apply-reviewed-answer-key-completion-into-effective-ir.md`.

Goal: apply validated completion only after explicit review semantics and IR
support exist. Matching and gapped/open-cloze answer-key shapes are contract
preconditions owned by Tasks 298 and 305.

Checklist:

- [ ] Add effective answer-key provenance distinct from parser provenance.
- [ ] Add apply mode for reviewed completion.
- [ ] Preserve source-bound evidence precedence.
- [ ] Consume Task 298 matching answer-pair fields without widening them.
- [ ] Consume Task 305 gap/open-cloze accepted-value fields without widening
  them.
- [ ] Emit effective IR and completion report when completion is applied.
- [ ] Prove teacher-accepted suggestions can be resubmitted as manual overlay.

Checkpoint:

- [ ] Source IR remains unchanged after applied completion.
- [ ] Effective IR identifies LLM-inferred answer keys explicitly.
- [ ] Matching remains blocked unless Task 298 validators prove exact pairs.
- [ ] Gapped/open-cloze application remains blocked unless Task 305 validators
  prove accepted values and completeness.
- [ ] Public/grant jobs remain remote-provider-forbidden unless a later signed
  policy authorizes them.

Stop conditions:

- Stop if applying a completion would overwrite source-bound evidence.
- Stop if matching pairs or gap accepted values are not first-class IR data.

## Tranche 7: Cross-Repo Integration

Governing task: `task-299-publish-cross-repo-skriptoteket-and-huleedu-answer-key-completion-handoff.md`.

Goal: hand off the Sir Convert-owned contract to Skriptoteket and HuleEdu
without duplicating conversion policy.

Checklist:

- [ ] Create Skriptoteket handoff for teacher overlay/review UI and adapter
  changes.
- [ ] Create HuleEdu handoff for a possible generic structured-completion API
  decision.
- [ ] Keep Sir Convert as conversion producer and Skriptoteket as UI/consumer.
- [ ] Keep HuleEdu LLM Provider reuse optional until it exposes a compatible
  structured-completion surface.
- [ ] Preserve public/authenticated access and remote fallback boundaries.

Checkpoint:

- [ ] Skriptoteket docs/task references Sir Convert overlay and report
  contracts instead of duplicating parser/provider rules.
- [ ] HuleEdu docs/task describes a new generic structured-completion shape, not
  reuse of comparison-only callback envelopes.
- [ ] Cross-repo proof plan includes authenticated and public/grant cases where
  applicable.

Stop conditions:

- Stop if Skriptoteket begins inferring answer keys outside manual overlay.
- Stop if HuleEdu comparison-provider callbacks are treated as drop-in
  structured completion.

## Final Promotion Gate

The route can move from experimental/advisory to production candidate only when:

- [ ] Contract, overlay runtime, provider harness, benchmark, advisory report,
  and reviewed-application gates are all complete or explicitly scoped out.
- [ ] Wrong-but-valid rate is below the accepted threshold on real data.
- [ ] Manual follow-up burden is visible and acceptable.
- [ ] Remote fallback policy is fail-closed by default and tested.
- [ ] Product-visible reports are privacy-safe.
- [ ] A retained review approves source provenance, effective provenance,
  benchmark methodology, and downstream integration boundaries.

Required close-out commands for docs-only roadmap updates:

```bash
pdm run docs-sync
pdm run docs-validate
pdm run skills-validate
pdm run handoff-validate
git diff --check
```
