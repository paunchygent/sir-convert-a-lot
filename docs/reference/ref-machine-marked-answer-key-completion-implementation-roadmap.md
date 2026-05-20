---
type: reference
id: REF-machine-marked-answer-key-completion-implementation-roadmap
title: Machine-marked Answer-key Completion Implementation Roadmap
status: active
created: 2026-05-14
updated: 2026-05-16
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
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/backlog/tasks/task-310-add-validation-only-force-eval-mode-for-source-keyed-answer-key-live-validation.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/backlog/tasks/task-312-make-answer-key-candidate-planning-provider-protocol-driven.md
  - docs/backlog/tasks/task-325-add-openai-responses-provider-and-hot-swappable-operator-routing-for-answer-key-completion.md
  - docs/backlog/tasks/task-326-run-openai-mini-nano-answer-key-evaluation-gate-before-provider-promotion.md
  - docs/backlog/tasks/task-299-publish-cross-repo-skriptoteket-and-huleedu-answer-key-completion-handoff.md
  - docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md
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
1. Experimental Granite FP8/vLLM Hemma smoke and temporary local provider
   settlement: Task 301.
1. Advisory completion reports: Task 297.
1. Reviewed application into effective IR: Task 306.
1. Provider live validation on the versioned DigiExam DXE corpus: Task 309.
1. Validation-only force-eval over source-keyed live-validation items: Task
   310\.
1. Strict service-backed auth/public-edge mirror validation: Task 311.
1. Cross-repo Skriptoteket/HuleEdu handoff: Task 299.
1. Hot-swappable direct API provider routing: the next governed task after
   ADR-0010 should add OpenAI first and prove running-service settings can
   switch new advisory requests between local and API provider profiles. The
   production local route depends on Task 320 service-backed Docker DNS and
   authenticated service-report proof; Task 320 is done with 2026-05-18 proof,
   while full authenticated/public-edge mirror claims remain gated by Task 311.
   Provider route selection stays operator-internal unless the same slice adds a
   governed public contract field, OpenAPI snapshot update, request-validation
   tests, and Skriptoteket consumer-impact proof. Task 325 is this OpenAI-first
   slice: direct OpenAI Responses provider, hot running-service settings,
   operator/internal-identity mutation, admission-time lineage, no public
   `provider_route_class`, and no HuleEdu LLM Provider Service broker work. Its
   first OpenAI model manifest entries are pinned to
   `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`.
1. OpenAI model-quality eval gate: Task 326 owns the existing local-model
   answer-key evaluation harness/corpus run for both pinned OpenAI snapshots and
   compares them to the current Qwen3.6 baseline. Task 325 cannot be marked done
   and no OpenAI profile can be promoted as an operator-selectable production
   default until Task 326 is complete.
1. Deferred local model benchmark harness and live matrix: Task 300, after the
   full app path is working and deployed.

Do not collapse these tranches. The sequence protects source-bound parser
provenance, prevents provider code from leaking into parser/rendering concerns,
and keeps model choice evidence-driven.

Task 301 was allowed to run before the full benchmark harness because it was a
bounded operator smoke test of a runtime candidate, not a provider integration
or final model-selection gate. Its evidence temporarily settled Granite 4.1 8B
FP8 on vLLM as the local provider while the feature was implemented. Task 309 is
the first production-path live validation of that temporary provider, plus the
follow-on GGUF diagnostics needed to select the next guarded local lane, using
the versioned pure DigiExam DXE corpus and strict golden-backed correctness
metrics. The 2026-05-16 Task 309 evidence demotes Granite/vLLM and Devstral
Small for answer-key completion because wrong-but-valid answer quality is
unacceptable. Qwen3.6-27B-Q6_K is the current guarded model choice, but not an
automatic answer-key promotion because it still produced 3 wrong-but-valid
suggestions. Task 300 remains the later comparative benchmark authority for a
GGUF/vLLM bake-off and must not start until the full app path is working and
deployed.

Task 310 and Task 311 are follow-up gates after Task 309: Task 310 isolates
validation-only force-eval so it cannot leak into production advisory behavior,
and Task 311 intentionally includes deployed service, auth, and public-edge
readiness for the production mirror.

Tasks 302 and 303 originally closed overlay/export contract gaps discovered
after Task 295. Task 337 now supersedes the accepted-current-state export
portion of that work: Task 302 remains active for supported item-content
patches to effective IR, while missing-key QTI/PDF exports remain blocked until
real source, manual, or reviewed effective key state exists.

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

Goal: historical/superseded by Task 337 for current runtime. This tranche
defined and validated a QTI profile for teacher-accepted missing-key exports,
but that profile is no longer an active authoring/correction or
target-readiness unlock.

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
- [x] Historical: target readiness previously allowed accepted-current-state
  QTI only inside the validated unkeyed/manual profile. Task 337 removes this
  runtime unlock.
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
- [ ] Exam.net PDF readiness follows the source-neutral matching bounds, so
  one-to-one, many-left-to-one, one-left-to-many, and unmatched right-side
  distractors remain supported when the item allows them.
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

- [x] Define stable gap IDs, display order, prompt binding, source evidence,
  and source spans.
- [x] Add accepted values per gap as structured authoring answer-key data.
- [x] Define normalization policy and whether it is validation-only or
  target-specific.
- [x] Define multi-gap completeness rules.
- [x] Preserve source-bound parser provenance separately from effective
  teacher/manual or reviewed answer-key provenance.
- [x] Update manifest/report, target-readiness, PDF, and QTI contract surfaces
  that depend on gap accepted-value shape.
- [x] Keep unsupported target export as target-readiness/degradation, not an IR
  restriction.
- [x] Preserve teacher choices for degraded/manual/free-text inclusion,
  omission, or manual recreation guidance.

Checkpoint:

- [x] Gap accepted values are first-class `ExamAuthoringIR v1` data.
- [x] Gapped/open-cloze items remain manual/unkeyed or unavailable for
  automatic evaluation until trusted accepted values exist.
- [x] Matching-styled gap/open-cloze workaround evidence is not promoted to
  DigiExam matching; target remapping decisions stay in validators/exporters.
- [x] Later provider/advisory/application tasks can consume the contract
  without changing it.

Task 305 completed this tranche with
`ExamAuthoringGapOpenClozeInteraction`, gap accepted-value validators,
normalization profiles, DigiExam source-adapter mapping, and target-readiness
degradation rows for unsupported multi-gap Exam.net PDF export.

Stop conditions:

- Stop if accepted values would be inferred from visible prompt text.
- Stop if accepted values cannot be represented as exact gap-ID-bound data.
- Stop if target limitations are encoded as source-parser or neutral-IR
  restrictions.
- Stop if the implementation deepens `DigiExamIntermediateExam` into a
  universal model instead of mapping source-neutral concepts into
  `ExamAuthoringIR v1`.

## Tranche 2.9: Exam.net PDF Manual/unkeyed Accepted-current-state Profile

Governing task:
`task-308-define-examnet-pdf-manual-unkeyed-accepted-current-state-profile-and-multigap-readiness.md`.

Goal: historical/superseded by Task 337 for current runtime. This tranche
defined the Exam.net PDF counterpart to Task 303's manual/unkeyed QTI profile,
but teacher-accepted missing-key PDF export is no longer an active
authoring/correction or target-readiness unlock. Missing-key single-choice,
missing-key multiple-response, and item-013-style multi-gap gap/open-cloze items
remain blocked until real source, manual, or reviewed effective key state
exists.
Task 321 adds the reviewed-key correction: when accepted gap/open-cloze values
exist, the PDF artifact must include those values, and this missing-key
fallback must not be used to drop reviewed keys.

Task 303 is QTI-only. It proves that missing keys can become
manual/unkeyed QTI when XML/package/profile validation allows it. It does not
prove that the Exam.net PDF-to-exam renderer can do the same. The PDF route
must define its own profile, renderer behavior, and target-readiness proof.

Checklist:

- [ ] Define supported and unsupported PDF manual/unkeyed shapes for accepted
  current-state.
- [ ] Superseded by Task 337: do not thread accepted-current-state target
  policy into the active Exam.net PDF renderer.
- [ ] Superseded by Task 337: do not report a removed accepted-current-state
  readiness unlock for `examnet_pdf`; missing-key PDF remains unavailable until
  real effective key state exists.
- [ ] Use item-013 as the regression case for a five-blank `Lucktext` item
  with an embedded image and no accepted blank values.
- [ ] Promote native multi-gap `Lucktext` PDF rendering if fixture proof
  validates the shape; otherwise block the current profile until a governed
  provenance-preserving degraded target shape is approved.
- [ ] Fix warning/readiness precedence so item-specific multi-gap limitations
  are not masked by the first `manual_answer_key_required` warning or confused
  with fatal target unavailability when degraded rendering succeeds.

Stop conditions:

- Stop if PDF output would drop visible prompt text, alternatives, gaps,
  embedded images, or manual follow-up semantics.
- Stop if no governed provenance-preserving rendering can preserve the item
  content requested for PDF export.
- Stop if the profile would invent answers or source provenance.

### PR-0331 reviewed-key target fallback purge

Governing task:
`task-321-purge-reviewed-answer-key-export-fallbacks-for-pr-0331.md`.

Goal: prevent target-specific QTI/PDF fallbacks from removing reviewed,
teacher-provided, or source-provided keys after those keys reach effective
renderer input. QTI package availability must fail closed when items are
omitted or still missing required accepted values; reviewed gap/open-cloze
values must be emitted in keyed QTI text-entry responses and in PDF artifacts.

- Stop if public JSON shape changes without OpenAPI snapshot and same-slice
  consumer impact planning.

## Tranche 3: Structured Provider Harness

Governing task: `task-296-extract-structured-chat-provider-harness-for-local-first-completion.md`.

Goal: build the generic local-first structured provider boundary without tying
it to DigiExam parser or renderer internals.

Checklist:

- [x] Add `StructuredChatProviderProtocol`.
- [x] Add `StructuredOutputSpec` with Chat Completions, Responses, and
  llama.cpp grammar/schema payload fields.
- [x] Add provider profile/config models with explicit capabilities.
- [x] Add provider set and failover policy.
- [x] Add token budget resolver and item-local preflight.
- [x] Add metadata-only capture and telemetry decisions.
- [x] Add Dishka providers where composition and test injection benefit.
- [x] Add module-level Google-style docstrings to new Python modules.

Tranche 3.1 evidence:

- `domain.structured_llm_contracts` owns pure source-neutral provider
  contracts, route policy, budget preflight, and metadata-only capture.
- `infrastructure.structured_llm_payloads` builds Chat Completions, Responses,
  llama.cpp JSON Schema, llama.cpp GBNF, and vLLM structured-choice payloads
  without provider network calls.

Tranche 3.2 evidence:

- `infrastructure.structured_llm_provider` now executes configured
  OpenAI-compatible structured-provider calls with endpoint selection for Chat
  Completions, Responses, llama.cpp-compatible chat completions, and
  vLLM-compatible chat completions.
- `infrastructure.structured_llm_responses` now parses provider responses into
  `StructuredLLMResponse` and maps missing config, request errors, HTTP status
  errors, invalid JSON, empty content, non-JSON content, non-object content,
  and conservative schema mismatches into typed backend failure codes.
- This left service settings/config loading, Dishka composition, and
  route/runtime default proof for the final Task 296 slice.

Tranche 3.3 evidence:

- `infrastructure.structured_llm_config` now loads disabled-by-default
  service settings with centralized constants for provider env vars and JSON
  provider keys.
- `ServiceConfig` carries the structured LLM runtime config without making
  parser, renderer, or HTTP artifact routes provider-aware.
- `infrastructure.structured_llm_di` provides the opt-in Dishka async container
  for `HttpStructuredChatProvider` and HTTP client lifecycle/test injection.
- `dishka<2,>=1.7` is now a direct runtime dependency and the generated service
  dependency manifests include it for CPU and ROCm images.
- DigiExam migration default route proof shows the
  `answer_key_completion_report` remains `not_requested` and provider execution
  is not called during default artifact creation or download.
- Task 296 is complete. Task 297 is complete; advisory candidate builders and
  answer-key completion reports are implemented for missing choice and gap-fill
  answer keys.

Checkpoint:

- [x] Payload-builder tests cover Chat Completions `response_format`, Responses
  `text.format`, and llama.cpp schema/GBNF modes.
- [x] Routing tests cover local success, local unavailable, remote forbidden,
  explicit false, missing consent, and allowed signed consent.
- [x] Capture tests prove raw prompts, raw responses, item text, and student data
  are not persisted in normal mode.
- [x] Composition tests cover disabled defaults, constant-backed env loading,
  local-primary enforcement, API-key env indirection, Dishka provider
  injection, and default DigiExam artifact routes making no structured LLM
  calls.

Stop conditions:

- Stop if implementation relies on edit-ops-specific Skriptoteket types.
- Stop if remote fallback can happen without explicit signed/authenticated
  policy.

## Tranche 3.5: Granite FP8 vLLM Runtime Smoke And Interim Settlement

Governing task: `task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md`.

Goal: prove whether Granite 4.1 8B FP8 can start on Hemma's AMD R9700/RDNA4
ROCm vLLM preview lane, satisfy one structured-output MCQ smoke, and serve as a
temporary local provider while the feature is implemented.

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
- [x] Document vLLM Granite FP8 as the temporary local provider pending
  production-path validation and later Task 300 benchmarking.

Checkpoint:

- [x] Task 301 states whether the FP8/vLLM candidate is viable, blocked, or
  needs a specific runtime follow-up.
- [x] The result is not treated as model selection until Task 300's real-data
  benchmark matrix proves correctness and wrong-but-valid behavior.
- [x] Provider implementation may proceed against this runtime without waiting
  for the comparative benchmark.
- [x] Task 309 later demoted this runtime for answer-key completion after live
  corpus and direct-probe evidence showed unacceptable wrong-but-valid answer
  quality despite successful structured-output protocol behavior.

Stop conditions:

- Stop if the smoke would require changing production service ports, compose
  files, or public routing.
- Stop if Docker/ROCm devices are unavailable.
- Stop if image/model acquisition would require destructive cache or Docker
  pruning.

## Tranche 4: Deferred Local Model Benchmark Harness

Governing task: `task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md`.

Goal: benchmark the mandatory local model matrix on real data after the full
app path is working and deployed. Granite/vLLM remains only as a demoted
baseline unless a later governed result overturns the Task 309 evidence. Task
309 owns the first Granite/vLLM-only live validation and failure-path inventory;
do not use this tranche for that precursor run.

Mandatory first-pass matrix:

| Model | Quant |
|---|---|
| `ibm-granite/granite-4.1-8b-fp8` on vLLM | FP8 demoted baseline |
| `unsloth/Qwen3.6-27B-GGUF` | `Qwen3.6-27B-Q6_K.gguf` current guarded baseline |
| `unsloth/Devstral-Small-2-24B-Instruct-2512-GGUF` | `UD-Q6_K_XL` demoted comparison |
| `unsloth/Qwen3.5-4B-GGUF` | `UD-Q6_K_XL` |
| `unsloth/gemma-4-E4B-it-GGUF` | `Q6_K` |
| `unsloth/granite-4.1-8b-GGUF` | `Q6_K` |
| `unsloth/Qwen3.5-9B-GGUF` | `Q6_K` |
| `unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF` | `UD-Q6_K_XL` |
| Mistral Small on `llama.cpp` | exact GGUF/quant resolved by the next governed runtime slice |

Checklist:

- [ ] Add domain models for candidate, quant, item fixture, expected answer,
  structured decision, validation result, and benchmark report.
- [ ] Add application services for matrix planning, execution, evaluation, and
  aggregation.
- [ ] Add infrastructure adapters for `llama.cpp` server/process lifecycle.
- [ ] Add corpus loader for real multiple choice, multiple response, matching,
  and open cloze/gap-fill items.
- [ ] Enforce grammar/schema-constrained output only.
- [ ] Prefer vLLM `choice` values for MCQ/MCW items with clear bounded
  candidate selection; use JSON Schema/grammar only where the provider harness
  proves support or the item type requires structured objects.
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
- [ ] The bake-off starts only after Task 309 has completed and the full app
  path is working and deployed.
- [ ] Granite/vLLM is compared only as a demoted baseline unless a later
  governed result overturns the Task 309 evidence.

Stop conditions:

- Stop if any run uses relaxed JSON prompting fallback.
- Stop if wrong-but-valid answers cannot be separated from schema failures.
- Stop if expected answers for the real corpus are not source-bound or
  teacher-verified.

## Tranche 5: Advisory Completion Reports

Governing task: `task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md`.

Goal: produce safe advisory completion reports without changing renderer input.

Checklist:

- [x] Build choice candidate inputs.
- [x] Build gap-fill/open cloze candidate inputs.
- [x] Skip source-bound answer keys, unreliable structures, unsupported assets,
  unsupported item types, and over-budget items.
- [x] Add item-type output specs and backend validators.
- [x] Emit `answer_key_completion_report`.
- [x] Keep source IR, effective IR, PDF, QTI, and manifest output unchanged by
  advisory suggestions.

Checkpoint:

- [x] Tests prove advisory mode makes no renderer-input changes.
- [x] Reports include per-item status and backend failure code, but no raw
  prompts/responses or item text capture.
- [x] Manual follow-up remains safer than wrong-but-valid completion.

Evidence:

- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion.py`
  orchestrates advisory report generation and converts provider failures,
  over-budget prompts, duplicate/unknown IDs, and invalid payloads to manual
  follow-up without candidate digests.
- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion_candidates.py`
  builds item-local structured requests for choice and gap-fill/open-cloze
  items using the Task 305 gap contract.
- `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py`
  writes `answer-key-completion-report.json` only for the requested advisory
  mode, consumes the provider route snapshot admitted with the job, and leaves
  default routes as `not_requested`.
- `DigiExamAnswerKeyCompletionReportV1` is published in the generated v2
  OpenAPI snapshot for consumer type generation. The report includes
  report-level provider lineage for provider family, profile ID, model snapshot,
  output mode, reasoning effort, text verbosity, settings version, route class,
  and route decision without exposing prompts, raw responses, API keys, or
  artifact paths.

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

## Tranche 6.4: Provider-Protocol Candidate Planning

Governing task:
`task-312-make-answer-key-candidate-planning-provider-protocol-driven.md`.

Goal: make the advisory answer-key candidate planner provider-protocol driven
before Task 309 live validation, so Granite/vLLM can use per-item constrained
output modes without embedding provider-specific branches in the orchestration
service.

Checkpoint:

- [ ] Answer-key orchestration consumes an injected/default candidate planner.
- [ ] Granite/vLLM choice and multiple-response rows use bounded
  `structured_outputs.choice` values.
- [ ] Granite/vLLM gap-fill rows use vLLM JSON Schema object mode.
- [ ] Generic providers continue to use JSON Schema decision objects.
- [ ] Provider-native choice responses decode into the stable advisory answer
  payload before report construction.
- [ ] Invalid bounded choices become manual follow-up, not valid suggestions.

Stop conditions:

- Stop if the implementation requires model-name conditionals inside the
  orchestration service.
- Stop if per-item output mode selection requires changing the persistent
  provider connection or service identity.

## Tranche 6.5: Granite/VLLM Live Validation

Governing task: `task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md`.

Goal: validate the completed structured-provider, advisory report, and reviewed
apply paths against the real Hemma provider lane before any model bake-off or
wider corpus expansion, then record whether that stack remains a candidate or
is demoted by live correctness evidence. Granite/vLLM was the initial provider;
Qwen3.6 and Devstral GGUF diagnostics now provide the current model-choice
evidence.

Corpus boundary:

- Use only the pure DigiExam `.dxe` exports moved to
  `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/`.
- Freeze source SHA, item fingerprint, item type, eligibility, skip reason, and
  source binding in a validation manifest.
- Commit the moved `.dxe` files as the governed versioned fixture corpus; do
  not fall back to manifest-only validation for this lane.
- Create teacher-verified expected answers for every scored eligible item.
  Straightforward grade 7-9 multiple-choice, multiple-response, and gap/open
  cloze cases are implementer-owned; only genuinely ambiguous cases should be
  escalated for adjudication.

Runtime checklist:

- [ ] Run Hemma preflight for remote revision, `rocminfo`, `rocm-smi`,
  scratch/cache path, port `8017`, vLLM `/v1/models`, request logging disabled,
  localhost-only exposure, and no CPU fallback.
- [ ] Add committed detached launch/status wrappers before the long run.
- [ ] Start or reuse a named persistent Granite/vLLM localhost-only container
  on port `8017`, with request logging disabled and image/model/cache/runtime
  state recorded.
- [ ] Leave the Granite/vLLM provider running after validation until the
  operator explicitly asks for stop or cleanup.
- [ ] Run the existing detached resource-monitor pattern beside the validation.
- [ ] Retain JSON/Markdown reports outside git with runtime lane, revision,
  manifest, and GPU state.
- [ ] Run provider microprobes for vLLM `choice`, JSON Schema choice object,
  and JSON Schema gap-fill object.
- [ ] Prefer vLLM `choice` values for MCQ/MCW items with clear bounded
  candidate selection.
- [ ] Run the full-corpus production advisory path in-process on Hemma with
  `local_llm_suggest_missing_machine_marked`.
- [ ] Run a small deployed service-backed smoke against the same persistent
  provider after the in-process pass.
- [ ] Evaluate valid suggestion, manual follow-up, wrong-but-valid answer,
  unknown IDs, duplicate IDs, partial gap answers, latency, tokens/sec, and
  backend failure code.
- [ ] Run a small reviewed-apply probe from known valid overlay candidates and
  prove apply mode makes no provider call.
- [ ] If the first pass succeeds, record the next governed follow-up as a
  strict service-backed mirror validation with auth/public-edge readiness in
  scope and validation-only force-eval policy for source-keyed items through
  Tasks 310 and 311.

Checkpoint:

- [ ] Advisory mode has zero source IR mutation and zero effective IR mutation.
- [ ] Retained artifacts have zero raw prompts and zero raw provider responses.
- [ ] Malformed outputs are never counted as success.
- [ ] Unknown IDs and duplicate IDs are zero for any promotion claim.
- [ ] Wrong-but-valid answers are the primary safety metric; manual follow-up
  remains acceptable, plausible wrong keys do not.
- [ ] Persistent failure paths are documented without item-specific prompt
  engineering and are reserved for later generalized retry/failure-policy work.
- [ ] The initial Task 309 run does not use force-eval over source-keyed items.
- [ ] The next service-backed mirror gate may use explicit validation-only
  force-eval before production/auth-edge mirror execution.
- [ ] If Granite/vLLM is demoted, record the stopped-provider state and next
  governed diagnostic provider lane instead of carrying it forward as the
  interim provider by default.
- [ ] If a GGUF diagnostic supersedes Granite/vLLM, record whether it is a
  guarded validation choice or an automatic-promotion candidate. Qwen3.6 is
  currently the guarded validation choice only.

Stop conditions:

- Stop if the run would expand beyond the versioned pure DXE corpus.
- Stop if goldens are missing for scored items.
- Stop if Hemma cannot prove GPU execution without CPU fallback.
- Stop if request logging or exposure controls cannot be proven.
- Stop if the implementation would stop the persistent Granite/vLLM provider as
  ordinary Task 309 closeout before the operator has explicitly requested it.
- Stop if force-eval is enabled in the initial Task 309 advisory run.
- Stop if the strict auth/public-edge service-backed mirror starts before the
  in-process plus service-smoke validation succeeds.
- Stop before starting a model bake-off.

## Tranche 6.6: Validation-only Force-eval

Governing task:
`task-310-add-validation-only-force-eval-mode-for-source-keyed-answer-key-live-validation.md`.

Goal: add an explicit validation-only path for source-keyed items before the
strict service-backed mirror, without changing production advisory semantics.

Checklist:

- [ ] Require an explicit validation command or validation-only flag.
- [ ] Keep default production advisory behavior skipping source-keyed items.
- [ ] Withhold trusted source answer keys from provider payloads and use them
  only in evaluator/golden comparison.
- [ ] Report force-eval metrics separately from missing-key advisory metrics.
- [ ] Preserve zero source IR mutation, zero effective IR mutation, and zero raw
  prompt/response retention.

Stop conditions:

- Stop if force-eval can be enabled by normal production conversion requests.
- Stop if provider payloads include trusted source answer keys.
- Stop if force-eval output can be applied as an answer key.

## Tranche 6.7: Strict Service-backed Mirror

Governing task:
`task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md`.

Goal: mirror the successful Task 309 validation through the deployed service
path, intentionally including auth/public-edge readiness and alpha-readiness
evidence.

Checklist:

- [ ] Use the governed provider lane established after Task 309. Granite/vLLM
  must not be reused by default after the 2026-05-16 demotion unless a later
  governed operator decision overturns that evidence.
- [ ] Run through the deployed service path, not the in-process executor.
- [ ] Prove authenticated access, public-edge readiness, provider reachability,
  and request logging posture.
- [ ] Optionally run Task 310 validation-only force-eval before the
  production/auth-edge mirror execution.
- [ ] Compare service-backed outputs against Task 309's in-process baseline.

Stop conditions:

- Stop if the service mirror silently falls back to in-process execution.
- Stop if auth/public-edge readiness is unproven.
- Stop if the provider becomes publicly exposed.
- Stop before running any model bake-off.

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
