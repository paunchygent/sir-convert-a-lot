---
type: reference
id: REF-exam-converter-solid-domain-coupling-audit
title: Exam Converter SOLID Domain Coupling Audit
status: active
created: 2026-05-15
updated: 2026-05-20
owners:
  - platform
tags:
  - solid
  - ddd
  - exam-converter
  - target-policy
  - refactor
links:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries.md
  - docs/backlog/tasks/task-313-audit-solid-domain-coupling-and-implementation-branch-hotspots-across-exam-converter-surfaces.md
  - docs/backlog/tasks/task-315-extract-exam-net-pdf-item-rendering-policy-strategies-from-item-type-branch-ladder.md
  - docs/backlog/tasks/task-316-extract-target-readiness-policy-decisions-from-artifact-availability-and-target-string-branches.md
  - docs/backlog/tasks/task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters.md
---

## Purpose

This reference records the 2026-05-15 audit of SOLID refactoring opportunities
where exam-converter business policy is entangled with implementation-specific
branching.

The audit was created after Task 312 extracted answer-key candidate planning
behind a provider protocol. Task 312 is complete and remains scoped to provider
planning. The broader audit belongs to Story 50 because the coupling pattern is
not limited to model/provider checks.

## Audit Lens

A branch is a SOLID/DDD coupling finding when it combines business decisions
with implementation mechanics so that adding a new item type, target, source
family, provenance state, or provider output policy requires edits across
unrelated functions.

The core separation rule for the exam converter is:

```text
source parser/source IR/effective IR -> target policy/validator -> exporter
```

Exporters and target policies consume IR state, but they must not own or mutate
IR state. Source IR owns source structure and provenance. Effective IR owns
accepted authoring corrections such as manual answer keys, reviewed completion,
item text changes, point corrections, and gap/choice corrections. Target/export
policy owns layout, target support, warning semantics, artifact availability,
and target-readiness interpretation.

Incomplete export is not exam state. Historical runtime behavior encoded
best-effort export as an authoring/correction-shaped decision. Task 337 removes
that coupling. If incomplete export is approved again later, it must enter as
export-only request context consumed by the relevant target policy, not as
parser IR, effective IR, ingestion overlay, or correction replay state.

The smell is stronger when one function decides several of these at once:

- item-type support;
- target/export capability;
- answer-key trust or missing-key policy;
- incomplete-export request policy;
- teacher action or target-readiness reason codes;
- source-evidence family or provenance mapping;
- provider/request output mode; and
- renderer or artifact assembly.

Not every `if` statement is a refactor target. Local validation guards,
dataclass invariants, parser extraction checks, and infrastructure adapter
mechanics can stay conditional when they are isolated at the right boundary and
do not duplicate exam business policy.

## High-Priority Findings

### 1. Exam.net PDF Item Rendering Policy

Surface:

- `scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf_items.py:68`
- `scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf_items.py:157`
- `scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf_items.py:201`
- `scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf_items.py:248`
- `scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf_items.py:292`

Evidence:

- `_render_item` dispatches on `DigiExamItemType` and also decides unsupported
  target-shape warnings.
- Choice, multiple-response, and gap-fill helpers historically mixed
  answer-key provenance checks, target support, warning construction, and HTML
  assembly. Task 337 removes the historical export-unlock branch from current
  runtime, but the remaining target policy and formatting concerns still need
  strategy extraction.
- Adding a new PDF target item profile would currently widen the same branch
  ladder and likely duplicate trust/manual-follow-up policy.

Refactor direction:

- Introduce an Exam.net PDF item rendering strategy/protocol selected by item
  semantics and target profile.
- Keep HTML escaping/shell helpers local and pure.
- Move support, answer-key trust, target-profile support, and warning semantics
  into strategy objects.
- Keep the core PDF item protocol target-agnostic. Exam.net-specific target
  shaping, including gap/open-cloze free-text-style presentation, must live in
  the Exam.net PDF profile/extension and preserve source/effective provenance
  through labels, warnings, and manual-follow-up state.
- Keep renderer strategies read-only with respect to source IR and effective IR;
  their output is target sections, target warnings, and PDF-ready layout state,
  not parser/source/effective-IR state.

Governed follow-up: Task 315.

### 2. Target Readiness Policy Builder

Surface:

- `scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py:140`
- `scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py:224`
- `scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py:281`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py:209`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py:227`

Evidence:

- `_rows_for_target` branches over artifact availability, raw
  `unavailable_code` strings, target name, missing answer-key item IDs,
  teacher action, retryability, and localized message keys.
- `_unsupported_gap_open_cloze_rows` special-cases the Exam.net PDF target in
  the readiness builder rather than in a target profile. This keeps PDF
  gap/open-cloze support policy in the generic readiness assembler.
- Missing-key rows are assembled from source IR manual-follow-up reasons plus
  artifact unavailability state. That is the right semantic layer after Task
  337, but it is still encoded as a target-string branch instead of a typed
  target-readiness policy.
- The bundle builder has target-specific assembly branches. That is acceptable
  orchestration today, but readiness policy must not keep growing around target
  strings when more targets, missing-key policies, or future export-only
  incomplete-output requests are added.

Refactor direction:

- Add a typed target-readiness policy/protocol that returns
  `DigiExamTargetReadinessRow` decisions from artifact state and item context.
- Replace raw unavailable-code string checks with typed unavailable reasons or
  a method on artifact entries.
- Move missing-key, unsupported target-shape, and future export-only incomplete
  output decisions into target profiles.

Governed follow-up: Task 316.

### 3. Answer-Key Eligibility And Output-Mode Drift

Surface:

- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_live_validation_manifest.py:273`
- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_live_validation_manifest.py:306`
- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_live_validation_manifest.py:318`
- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion_candidates.py`

Evidence:

- Task 312 made live answer-key candidate planning provider-protocol driven.
- The Task 309 manifest still classifies eligibility, output mode, and
  candidate counts with its own item-type and answer-key-provenance checks.
- This duplicates policy that should now be derived from the candidate
  planning/eligibility decision surface, otherwise the manifest can drift from
  live execution when planner policy changes.

Refactor direction:

- Expose a shared answer-key candidate eligibility/output-mode classifier.
- Make the Task 309 manifest consume that classifier instead of repeating
  planner policy.
- Keep manifest schema and counts compatible while removing duplicated
  business decisions.

Governed follow-up: Task 317.

### 4. Source-Evidence Provenance Mapping Strings

Surface:

- `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py:418`
- `scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py:131`
- `scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py:144`

Evidence:

- Gap validation maps `source_family` strings such as `digiexam_dxe`,
  `digiexam_result_pdf_correct_labels`, `teacher_overlay`, and
  `reviewed_completion` to provenance values.
- The DigiExam authoring adapter separately maps `DigiExamAnswerKeyProvenance`
  to ExamAuthoring provenance and source-family strings.
- This is tolerable for the current source set, but it becomes a coupling
  problem when teacher-authored source adapters, reviewed completions, or new
  evidence families expand.

Refactor direction:

- Introduce a typed source-evidence family/provenance mapper.
- Keep parser/source provenance distinct from teacher overlay and reviewed
  completion lineage.
- Require new source-family additions to update one mapping surface.

Governed follow-up: Task 317.

## Medium-Priority Tracking

### QTI Item Dispatch

Surface:

- `scripts/sir_convert_a_lot/domain/digiexam_examnet_qti_adapter.py:69`
- `scripts/sir_convert_a_lot/domain/digiexam_examnet_qti_adapter.py:89`

Current classification:

- Monitor, not immediate refactor.

Rationale:

- QTI item-type dispatch is currently small and target-specific.
- It should become a strategy boundary if QTI expands to more item types,
  incomplete-export profiles, matching, gaps, or alternate Exam.net
  import profiles.

### Bundle Target Assembly

Surface:

- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py:209`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py:227`

Current classification:

- Monitor through Task 316.

Rationale:

- Target-specific artifact calls can remain in bundle orchestration while the
  target set is small.
- If target policy, readiness, or incomplete-export semantics remain in
  the builder, split target artifact builders behind a registry.

## Non-Findings

These surfaces contain conditionals but are not current SOLID findings under
this audit:

- `scripts/sir_convert_a_lot/infrastructure/structured_llm_payloads.py`
- `scripts/sir_convert_a_lot/infrastructure/structured_llm_responses.py`
- `scripts/sir_convert_a_lot/infrastructure/structured_llm_provider.py`

Reason: endpoint/output-mode branching is at the provider-adapter boundary and
does not decide exam item eligibility, target support, or source provenance.
If new endpoint families multiply, split those builders into provider-mode
strategies, but do not treat them as exam-domain coupling today.

- `scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py`

Reason: Docling formula presets are isolated infrastructure fallback behavior,
not exam converter business policy.

- `scripts/sir_convert_a_lot/domain/service_routes_v2.py`

Reason: route-policy checks are part of the Story 46 route-policy boundary.
They are not a new coupling finding unless route handlers begin duplicating
renderer, readiness, or source-evidence decisions outside that boundary.

## Priority Order

1. Task 315: PDF item rendering policy extraction. Highest near-term risk
   because answer-key trust, target support, and warning construction are still
   mixed into renderer assembly.
1. Task 316: target-readiness policy extraction. High consumer-contract risk
   because Skriptoteket enables actions from these rows.
1. Task 317: answer-key eligibility/output-mode and source-evidence mapping
   reuse. High drift risk for Task 309 and future source-family expansion, but
   lower renderer/runtime blast radius than the first two tasks.

## Stop Conditions

- Do not broaden implementation tasks into new target support.
- Do not relax unsupported-target-shape failures.
- Do not synthesize answer keys or reclassify LLM output as parser/source
  evidence.
- Do not move infrastructure endpoint mechanics into the exam domain.
- Do not refactor parser-local validation guards just because they are
  conditionals.
