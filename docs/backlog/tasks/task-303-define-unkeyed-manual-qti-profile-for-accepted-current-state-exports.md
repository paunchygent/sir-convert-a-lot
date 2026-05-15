---
id: task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports
title: Define unkeyed manual QTI profile for accepted current state exports
type: task
status: proposed
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
- Define how the profile distinguishes:
  - bare schema-valid unkeyed QTI;
  - Sir Convert target-valid unkeyed/manual QTI;
  - Exam.net-import-proven unkeyed/manual QTI.
- Add deterministic sample packages and validation reports for every supported
  unkeyed/manual item type.
- Update target readiness so `accept_current_state_for_export` can set
  `export_enabled=true` for `qti_package` only when this profile validates and
  no other QTI schema/profile violations remain.
- Keep missing machine-marked keys disabled for all QTI profiles not covered by
  this task.

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
  machine-marked items that preserve visible content but omit machine scoring.
- Decide whether choice/matching/gap items become manual-response items,
  unscored interactions, or blocked shapes for the first profile.
- Define item-addressable manual-follow-up/reporting semantics for every
  downgraded or unkeyed representation.

Checkpoint:

- every accepted-current-state QTI item has deterministic XML shape and report
  semantics; unsupported shapes remain disabled.

### 3. Add validation and sample proof

- Generate QTI 2.1 samples first.
- Add QTI 3.0 samples only after the QTI 3.0 schema/profile decision is
  explicit.
- Validate package integrity, XML/XSD schema, local semantic smoke where
  available, and Exam.net import proof when a test path exists.

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

- [ ] QTI reference section for QTI 2.1 and QTI 3.0 schema requirements.
- [ ] Versioned unkeyed/manual QTI profile definition.
- [ ] Deterministic unkeyed/manual sample packages and validation reports.
- [ ] Target-readiness policy updates for `accept_current_state_for_export`.
- [ ] Contract tests proving QTI export remains disabled outside the profile.

## Acceptance Criteria

- [ ] The reference links the full authoritative QTI 2.1 and QTI 3.0 schemas
  and records the schema requirements Sir Convert depends on.
- [ ] The profile states exactly when a missing machine-marked key may still
  produce a QTI package after teacher acceptance.
- [ ] `accept_current_state_for_export` never bypasses XML/schema validation,
  package validation, unsupported-resource policy, or Exam.net profile gates.
- [ ] Target readiness reports distinguish current
  `needs_teacher_answer_key` from future `ready_after_accepted_current_state`
  under the unkeyed/manual QTI profile.
- [ ] Sample packages prove every supported unkeyed/manual shape.
- [ ] Unsupported or unproven QTI 2.1/3.0 shapes remain unavailable.

## Stop Conditions

- Stop if Exam.net import behavior contradicts the profile assumptions.
- Stop if the profile would silently drop visible item content, resources, or
  teacher review decisions.
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

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
