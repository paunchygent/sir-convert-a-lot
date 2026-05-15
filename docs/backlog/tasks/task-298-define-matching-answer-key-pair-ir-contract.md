---
id: task-298-define-matching-answer-key-pair-ir-contract
title: Define matching answer-key pair IR contract
type: task
status: done
priority: high
created: '2026-05-14'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/backlog/tasks/task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
labels:
  - effective-ir
  - answer-key-completion
  - matching
  - ir-contract
  - source-adapter
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and implement the matching answer-key pair contract in the Sir
Convert-owned source-neutral `ExamAuthoringIR v1` shape before any teacher
overlay, LLM advisory output, reviewed application, QTI export, or PDF renderer
claims matching can be machine-evaluated.

This task closes the parser-to-IR contract shape for matching items. It does
not implement LLM provider calls, advisory completion, reviewed application, or
model selection.

The intermediary contract must be broader than the current Exam.net PDF import
profile. It must preserve QTI-style match interactions with two ordered match
sets, directed pairs, per-choice association constraints, and target/right-side
distractors. Exam.net-specific limits belong in target-readiness/export
validators, not in source/effective IR.

`DigiExamIntermediateExam` must not become the universal exam authoring IR for
future Exam.net PDF, teacher-authored DOCX, or teacher-authored Markdown source
parsers. Task 307 is the hard-blocking follow-up that defines
the first `ExamAuthoringIR v1` matching contract slice by extracting the
source-neutral matching definitions from the current `DigiExamIntermediateExam`
adapter-shaped contracts. The full source-neutral extraction for choices,
gaps/open-cloze, provenance, evidence spans, validators, and exporters waits
for later tasks, with Task 305 as the next prerequisite for gapped/open-cloze.

Canonical DigiExam `.dxe` sources do not carry matching items. Task 298 must
not add keyed DigiExam matching QTI export or a
`DigiExamIntermediateExam -> ExamNetQtiMatchPair` bridge. Matching source
fixtures belong to source families that actually support matching, such as
Exam.net PDF artifacts and teacher-authored structured DOCX/Markdown formats,
and those sources must map through `ExamAuthoringIR v1` once Task 307 lands.

## PR Scope

- Add first-class matching answer-key pair fields to `ExamAuthoringIR v1`
  through an explicit schema-version authority. Do not add aliases,
  compatibility layers, dual-version response modes, or silent reinterpretation
  of older matching fields.
- Preserve the matching interaction structure needed by real matching-capable
  source families: ordered source prompts, ordered target options, item IDs,
  source spans, and absent answer-key provenance when no trusted pairs exist.
- Do not implement a DigiExam keyed matching QTI bridge. The DigiExam-to-QTI
  adapter must keep matching absent/unsupported and must not construct
  `ExamNetQtiMatchPair` for DigiExam.
- Add stable `source_id` and `target_id` bindings for matching prompts/options.
  Do not expose `left_id`/`right_id` as compatibility aliases in the new public
  matching answer-key schema.
- Represent matching answer keys as exact directed pairs of known source and
  target IDs.
- Preserve per-choice `match_min`/`match_max` or equivalent association
  constraints so the IR can represent QTI 2.1/3.0-style many-to-one,
  one-to-many, one-to-one, and distractor-target shapes.
- Validate that every referenced source/target ID exists, duplicate identical
  pairs are rejected, pair counts obey the intermediary association
  constraints, and required pairs are complete for the selected target profile.
- Preserve source-bound parser provenance separately from teacher/manual or
  reviewed effective answer-key provenance.
- Reject aggregate `mixed` matching provenance until matching pairs carry
  first-class per-pair provenance and evidence. Current matching provenance is
  a whole-key trust state only.
- Update manifest, parity, manual-follow-up, target-readiness, PDF, and QTI
  contract docs where they depend on matching answer-key shape.
- Keep applied matching completion disabled until this contract and its
  validators are implemented.
- Surface and resolve any consumer contract changes for HuleEdu Gateway and
  Skriptoteket before changing OpenAPI snapshots or response JSON.
- Update all known consumers in the Sir Convert and Skriptoteket repos in the
  same schema-bump slice; Task 298 must not close with stale consumer code
  expecting the previous bundle or overlay schema.

## Deliverables

- [x] Matching answer-key pair `ExamAuthoringIR v1` contract.
- [x] Matching pair validation rules and target-profile issue semantics.
- [x] Target-profile validator contract separating QTI-permissive IR from
  Exam.net PDF and future Exam.net QTI constraints.
- [x] Documentation proving DigiExam migration manifests/reports do not claim
  keyed matching support, while neutral matching provenance is available for
  future matching-capable source adapters.
- [x] Renderer/QTI gate documentation proving matching remains unavailable for
  DigiExam and unavailable elsewhere unless trusted pairs exist.
- [x] Documentation proving DigiExam `.dxe` does not claim keyed matching QTI
  export and that keyed matching QTI bridging waits for `ExamAuthoringIR v1`
  plus a source adapter with real matching fixtures.
- [x] OpenAPI/Skriptoteket consumer-impact inventory for any effective-IR,
  overlay, readiness, or manifest field changes.
- [x] Sir Convert and Skriptoteket consumer updates for the versioned schema
  bump, with focused tests in both repos or an explicit blocked handoff if the
  second repo cannot be changed in the same branch.
- [x] Shared or generated schema-version constants replace hard-coded version
  strings in both repos where consumers branch on bundle, IR, overlay,
  effective-exam, or readiness schema versions.
- [x] Focused tests for exact pair binding, missing IDs, duplicate identical
  pairs, malformed association bounds, association-limit violations,
  distractor targets, source/effective provenance, and target readiness.

## Acceptance Criteria

- [x] Matching answer-key pairs are first-class structured IR data, not prompt
  text, renderer labels, or provider-specific output.
- [x] Source IR remains source-owned: missing pairs stay absent unless the
  source adapter or trusted evidence supplies them.
- [x] `ExamAuthoringIR v1` can carry teacher/manual or later reviewed matching
  pairs without rewriting source-adapter provenance.
- [x] The intermediary validator allows duplicate target/right IDs when the
  target choice association limit permits many-source-to-one-target matching.
- [x] The intermediary validator allows unmatched target/right IDs as
  distractors and does not require every target option to appear in the answer
  key.
- [x] Matching PDF/QTI output can distinguish source-proven, teacher/manual,
  reviewed effective, and absent answer-key provenance.
- [x] Matching validation rejects opaque aggregate `mixed` provenance while
  the pair contract has no per-pair provenance fields.
- [x] Matching remains unavailable for automatic evaluation when exact pairs
  are missing, while Task 303 manual/unkeyed preservation remains available
  where schema/profile validation allows it.
- [x] DigiExam-to-QTI adapter behavior remains unsupported for keyed matching;
  it does not construct `ExamNetQtiMatchPair`.
- [x] Exam.net PDF target readiness accepts only the current Exam.net-supported
  keyed shape: each source/left ID has at most one matched target/right ID,
  each matched target/right ID has at most one source/left ID, and unmatched
  target/right IDs may remain as distractors.
- [x] Exam.net QTI readiness remains vendor-unproven until Exam.net ships or
  exposes a QTI import test path; no implementation may require
  Exam.net-accepted QTI fixture proof before that surface exists.
- [x] Skriptoteket can consume the updated API shape through generated OpenAPI
  types and versioned contract updates; it must not infer matching readiness
  locally from pair counts or duplicate IDs.
- [x] Old `left_id`/`right_id` matching-pair payloads are rejected by the new
  overlay schema rather than accepted through aliases or compatibility layers.
- [x] Reviewed application and LLM advisory tasks can consume the contract but
  are not implemented here.

## Implementation Evidence

- `ExamAuthoringIR v1` owns matching interactions in
  `domain.exam_authoring_ir_contracts`, with centralized schema version and
  validation issue-code constants.
- Neutral validation covers exact ID-bound pairs, unknown IDs, duplicate
  identical pairs, distractors, malformed association bounds,
  association-limit violations, opaque `mixed` provenance rejection, and
  QTI-permissive many-to-one shapes.
- The Exam.net PDF profile validator rejects repeated source IDs and repeated
  target IDs while allowing unmatched target distractors.
- DigiExam parser/IR/overlay/effective/OpenAPI contracts no longer expose
  matching structures or `correct_matching_pairs`.
- Skriptoteket review consumers no longer parse or fixture DigiExam
  `matching` fields and use centralized schema-version constants.

## Target-Profile Planning Decision

Task 298 implements a layered contract:

1. The IR/effective-IR layer is QTI-permissive. It stores two ordered match
   sets, stable IDs, association constraints, and directed correct pairs. It
   can represent many-left-to-one, one-left-to-many, one-to-one, and unmatched
   right-side distractors.
1. Target validators decide what can be exported. The current Exam.net PDF
   profile allows one-to-one matched pairs plus unmatched right-side
   distractors. It rejects left-to-many and right-to-many keyed matching for
   Exam.net PDF readiness.
1. Exam.net QTI is a planned target profile only. Because Exam.net does not yet
   expose QTI import, Sir Convert may produce general QTI-valid samples and
   reports, but it must not claim live Exam.net QTI import support.

Keyed matching QTI export is a neutral-authoring concern, not a DigiExam
adapter concern. The bridge from matching answer pairs to QTI
`ExamNetQtiMatchPair` must wait for Task 307 and a source adapter with real
matching fixtures, such as Exam.net PDF artifacts or teacher-authored
structured DOCX/Markdown.

## Public Schema Strategy

Task 298 must use a versioned public-contract cutover:

- `digiexam_intermediate_exam_v3`;
- `digiexam_ir_manifest_v3`;
- `digiexam_ingestion_overlay_v2`;
- `digiexam_effective_exam_v2`;
- `digiexam_migration_bundle_v3`.

`target_readiness_report_v1` may remain unchanged only if the JSON shape stays
the same and new matching outcomes are represented as string reason codes. If
readiness row structure changes, version that report too.

The new matching pair names are `source_id` and `target_id`. `left_id` and
`right_id` belong to the retired pre-Task-298 overlay DTO and must not be
accepted by the new schema. This is an intentional breaking contract change, not
a compatibility extension.

Schema-version handling must be robust across repo boundaries. Do not scatter
literal strings such as `digiexam_migration_bundle_v3` or
`digiexam_ingestion_overlay_v2` through adapters and tests. Sir Convert should
publish the authoritative constants through contract modules and generated
OpenAPI/schema artifacts; Skriptoteket should consume generated types or a
single local contract-constants module derived from that authority.

Chosen shape:

1. Sir Convert owns one narrow contract-version module for DigiExam migration
   schemas. Domain contracts, OpenAPI DTOs, artifact builders, and tests import
   constants or literal type aliases from that module instead of copying schema
   strings.
1. Sir Convert publishes those versions in the generated OpenAPI snapshot,
   preferably as a small `x-sir-convert-digiexam-schema-versions` extension in
   addition to the normal schema `const` values.
1. Skriptoteket generates or refreshes one local Sir Convert contract constants
   module from the OpenAPI snapshot. Public Exam Converter handlers,
   projection models, saved-artifact metadata, and API metadata import from
   that module.
1. Tests in both repos assert against imported constants. A static guard should
   fail when retired schema literals or scattered current schema literals are
   introduced outside the contract-version modules, generated snapshots, or
   explicit migration-test fixtures.

This preserves SOLID boundaries: Sir Convert remains the contract producer;
Skriptoteket remains a consumer; version knowledge has one reason to change;
and UI/business logic depends on a generated contract surface rather than
duplicated literals.

## Consumer/API Planning Checkpoints

Implementation must inspect and update these consumer-facing surfaces before
changing runtime behavior:

- `scripts/sir_convert_a_lot/application/openapi_contracts_v2.py`, because its
  DTOs are exported as the generated v2 OpenAPI snapshot consumed by
  Skriptoteket type generation.
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`, through the
  governed OpenAPI export command, if effective answer-key, overlay, readiness,
  or manifest schemas change.
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`,
  especially `effective_ir_json`, `target_readiness_report_v1`, and the
  Skriptoteket adapter contract.
- Known Skriptoteket consumers from Task 294's breaking-consumer inventory,
  because UI code may currently assume matching answer keys are unsupported or
  one-to-one.

Minimum Sir Convert update surface:

- `scripts/sir_convert_a_lot/domain/digiexam_contracts.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_ir_contracts.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay_contracts.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay.py`;
- `scripts/sir_convert_a_lot/application/openapi_contracts_v2.py`;
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py`;
- generated OpenAPI under `docs/_generated/openapi/`;
- focused IR, overlay, bundle API, target-readiness, and OpenAPI tests.

Minimum Skriptoteket update surface:

- `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/public_exam_converter.py`;
- `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/public_exam_converter_artifacts.py`;
- `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/conversion_hub_saved_artifacts.py`;
- `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/handlers/public_exam_converter_jobs.py`;
- `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/web/api/v1/public_apps.py`;
- matching public Exam Converter/conversion-hub tests and any generated
  consumer types.

If implementation cannot update both repos in the same working slice, stop and
create a governed cross-repo handoff before merging either side.

Consumer updates must remove brittle hard-coded schema version strings where
they currently exist and replace them with generated or centralized constants.
Tests should assert against those constants, not copy the literal into each
callsite.

## Stop Conditions

- Stop if matching pairs cannot be represented as exact ID-bound data.
- Stop if the implementation would infer correct pairs from visible prompt text
  without trusted source, teacher/manual, or reviewed evidence.
- Stop if QTI/PDF rendering would need target-specific labels inside the
  intermediary contract.
- Stop if target-profile constraints leak into parser-owned source IR or
  effective IR instead of readiness/export validators.
- Stop if OpenAPI or Skriptoteket consumer compatibility would change without a
  real schema-version bump and same-slice consumer updates.
- Stop if the implementation tries to accept old `left_id`/`right_id` payloads
  through aliases, compatibility layers, or dual-schema parsing.
- Stop if either repo needs scattered hard-coded schema strings to pass tests
  after the version bump.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
