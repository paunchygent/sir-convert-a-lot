---
id: task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports
title: Define unkeyed manual QTI profile for accepted current state exports
type: task
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - qti
  - examnet
  - target-readiness
  - teacher-review
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the governed unkeyed/manual QTI export profile that lets a teacher
`accept_current_state_for_export` decision enable QTI export when the selected
QTI 2.1 or QTI 3.0 package is otherwise schema-valid and target-valid.

A missing machine-marked key means Sir Convert has no trusted source, manual,
or reviewed effective correct-response data for a machine-markable item. The
question content may still be complete and exportable as manual/unkeyed QTI.

This task exists because QTI schema validity does not universally require a
machine-marked correct response, while Sir Convert's current Exam.net QTI
profile still requires machine-marked keys for machine-marked targets. The new
profile must make that policy exception explicit, validated, and visible in
target readiness before any runtime enables QTI download for missing-key items.

## PR Scope

- Extend `ref-examnet-qti-import-contract-and-validation-strategy.md` with a
  versioned unkeyed/manual profile for QTI 2.1 and a QTI 3.0 compatibility
  decision point.
- Define which item types may be exported without machine-marked keys when the
  teacher has accepted the current state.
- Define the QTI representation for unkeyed/manual items:
  response declarations, response processing policy, outcome declarations,
  manual-marking metadata, and package manifest requirements.
- Preserve visible item content for QTI export whenever a deterministic
  manual/unkeyed representation exists. Missing machine-marked keys must remove
  automatic correct-answer/evaluation claims, not the teacher-visible question.
- Define how the profile distinguishes:
  - bare schema-valid unkeyed QTI;
  - Sir Convert target-valid unkeyed/manual QTI;
  - Exam.net-import-proven unkeyed/manual QTI.
- Distinguish items that are unsupported for automatic evaluation from items
  that are unavailable for manual/unkeyed export.
- Add deterministic sample packages and validation reports for every supported
  unkeyed/manual item type.
- Update target readiness so `accept_current_state_for_export` can set
  `export_enabled=true` for `qti_package` only when this profile validates and
  no other QTI schema/profile violations remain.
- Keep missing machine-marked keys disabled for all QTI profiles not covered by
  this task.
- Proceed with local package/schema/profile proof and record Exam.net import
  proof as vendor-unproven external dependency until the vendor provides an
  import test path. Exam.net has asked for realistic Sir Convert QTI exam files,
  not curated Exam.net-specific simplifications.

## Implementation Roadmap

### 1. Capture QTI schema requirements

- Link the authoritative QTI 2.1 and QTI 3.0 XSD/schema sources from the QTI
  reference.
- Record the schema facts needed by Sir Convert:
  `responseDeclaration`/`qti-response-declaration` optionality,
  `responseProcessing`/`qti-response-processing` optionality, optional
  `correctResponse`/`qti-correct-response`, and interaction binding rules.
- Separate QTI schema-validity from Exam.net import readiness.

Checkpoint:

- docs explain why an unkeyed/manual item can be schema-valid while still not
  being target-ready under the current Exam.net profile.

### 2. Define supported unkeyed/manual item representations

- Start with free text/manual marking and accepted-current-state
  machine-markable items that preserve visible content but omit automatic
  correct-answer/evaluation claims.
- For single-choice and multiple-response items, preserve the prompt, all
  visible alternatives, allowed resources, and interaction cardinality while
  omitting `correctResponse`/`qti-correct-response` and automatic
  `responseProcessing` correct/incorrect evaluation.
- Treat matching, gap-fill, and similar shapes as priority preservation cases:
  define deterministic manual/unkeyed QTI representations that keep the visible
  question content in the package even when Exam.net imports them as free-text
  items or does not render them as automatically evaluated test items.
- Define item-addressable manual-follow-up/reporting semantics for every
  downgraded or unkeyed representation.
- Report unsupported-for-automatic-evaluation items separately from
  unavailable-for-manual/unkeyed-export items:
  unsupported-for-automatic-evaluation preserves visible content in a valid
  manual/unkeyed package, while unavailable-for-manual/unkeyed-export blocks the
  target because valid preservation would drop content or break validation.

Checkpoint:

- every accepted-current-state QTI item has deterministic XML shape and report
  semantics; only shapes that cannot be represented without dropping visible
  content, violating schema/profile rules, or breaking package validation remain
  disabled.

### 3. Add validation and sample proof

- Generate QTI 2.1 samples first.
- Add QTI 3.0 samples only after the QTI 3.0 schema/profile decision is
  explicit.
- Validate package integrity, XML/XSD schema, local semantic smoke where
  available, and Exam.net import proof when a test path exists.
- Treat Exam.net import proof as vendor-unproven and externally pending until
  the vendor provides a test path; do not block local Task 303 implementation on
  live import access.

Checkpoint:

- target readiness uses sample-backed validation evidence, not a local
  teacher flag or bundle status.

### 4. Wire readiness policy

- Update readiness reason handling so teacher `accept_current_state_for_export`
  can enable `qti_package` only under the validated unkeyed/manual profile.
- Preserve validation failures, unsupported resources, unsupported target
  shapes, and malformed package failures as disabled regardless of teacher
  acceptance.

## Deliverables

- [x] QTI reference section for QTI 2.1 and QTI 3.0 schema requirements.
- [x] Versioned unkeyed/manual QTI profile definition.
- [x] Deterministic unkeyed/manual sample packages and validation reports.
- [x] Target-readiness policy updates for `accept_current_state_for_export`.
- [x] Contract tests proving QTI export remains disabled outside the profile.

## Acceptance Criteria

- [x] The reference links the full authoritative QTI 2.1 and QTI 3.0 schemas
  and records the schema requirements Sir Convert depends on.
- [x] The profile states exactly when a missing machine-marked key may still
  produce a QTI package after teacher acceptance.
- [x] Missing keys never drop visible prompt text, alternatives, gap text,
  matching prompts, or allowed resources from QTI/PDF output; they only remove
  automatic correct-answer/evaluation claims unless a reviewed answer key
  exists.
- [x] `accept_current_state_for_export` never bypasses XML/schema validation,
  package validation, unsupported-resource policy, or Exam.net profile gates.
- [x] Target readiness reports distinguish current
  `needs_teacher_answer_key` from future `ready_after_accepted_current_state`
  under the unkeyed/manual QTI profile.
- [x] Target readiness and validation reports distinguish unsupported for
  automatic evaluation from unavailable for manual/unkeyed export.
- [x] Sample packages prove every supported unkeyed/manual shape.
- [x] Matching, gap-fill, and other non-choice shapes are either preserved in a
  deterministic manual/unkeyed QTI representation with item-level follow-up, or
  remain unavailable only with an explicit proof that preservation would break
  schema/profile/package validation or silently lose visible content.
- [x] Exam.net import proof is recorded as vendor-unproven/external dependency
  until an import test path exists, while local package/schema/profile proof is
  sufficient for this implementation slice.

## Implementation Notes

- The runtime QTI item contract now carries `profile_id` through package plans
  and validation reports. `unkeyed_manual_qti_2_1_v1` identifies manual/unkeyed
  preservation output separately from the existing automatic-evaluation
  profile.
- Accepted-current-state single-choice and multiple-response items preserve
  prompts, alternatives, allowed resources, and interaction cardinality while
  omitting `correctResponse` and automatic `responseProcessing`.
- Accepted-current-state gap-fill items are preserved as manual/free-text QTI
  from real tracked DigiExam DXE fixture item `item-007`.
- The code path can preserve matching-like contract samples as manual/free-text
  QTI, but canonical DigiExam `.dxe` sources do not carry matching items. The
  Task 303 matching sample is therefore not a DigiExam capability claim and
  does not claim reviewed matching answer-pair support, automatic evaluation,
  or IR v3 application.
- Additional local DXE mining under `inputs/` found more real choice and
  gap-fill examples, including matching-like gap-fill prompts, but no parsed
  `DigiExamItemType.MATCHING` fixture. Keyed matching QTI export waits for Task
  307's `ExamAuthoringIR v1` and real matching-capable source fixtures from
  Exam.net PDF artifacts or teacher-authored structured DOCX/Markdown.
- Task 298 remains the authority for matching answer-pair fields. Task 305 owns
  the gapped/open-cloze accepted-value contract. Task 306 owns later reviewed
  answer-key application into effective IR.

## Stop Conditions

- Stop if Exam.net import behavior contradicts the profile assumptions.
- Stop if the profile would silently drop visible item content, resources, or
  teacher review decisions.
- Stop if an item is blocked merely because automatic evaluation is unsupported
  while a schema-valid manual/unkeyed representation can preserve the visible
  question for QTI/PDF export.
- Stop if QTI schema validation passes but Sir Convert cannot represent the
  item's manual-marking policy clearly to the consumer.

## Validation Plan

- QTI 2.1 XML/XSD validation for generated samples
- QTI 3.0 XML/XSD validation for generated samples when included
- local QTI semantic smoke where available
- Exam.net import proof when an importer/test path exists
- focused target-readiness tests
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Validation Evidence

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all` (`655 source files`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_examnet_qti_package.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_unavailable_pdf_target_returns_named_artifact_error tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_qti_without_correct_response tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_applies_source_bound_teacher_overlay`
  (`14 passed`)
- `pdm run coverage-gate` (`1188 passed, 5 skipped`, coverage `95.43%`)
- `pdm run examnet-qti-task-303-samples`
- `pdm run openapi-export-v2`
- `pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_examnet_qti_package.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_qti_without_correct_response`
  (`15 passed`)
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
