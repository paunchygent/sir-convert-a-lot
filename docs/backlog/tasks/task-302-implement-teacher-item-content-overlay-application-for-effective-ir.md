---
id: task-302-implement-teacher-item-content-overlay-application-for-effective-ir
title: Implement teacher item-content overlay application for effective IR
type: task
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
labels:
  - digiexam
  - overlay
  - effective-ir
  - teacher-review
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement teacher item-content overlay application for
`effective_item_patch` so Skriptoteket teacher edits can repair parsed item
content in the effective renderer input without mutating the parser-owned
source IR.

Task 295 deliberately shipped only answer-key overlays and review decisions as
runtime-applied behavior. This task closes the remaining contract/runtime gap
for item text, option text, prompt/body, gap labels, and matching prompt/option
repair.

## PR Scope

- Apply `effective_item_patch` to `digiexam_effective_exam_v1` only. The
  parser-owned `digiexam_intermediate_exam_v2` artifact, source manifest, and
  parser provenance must remain byte-for-byte source owned.
- Validate patch payloads by item type before application:
  - choice/multiple-choice option text and visible item body fields;
  - gap-fill visible prompt/body and gap-level visible repair fields;
  - matching visible prompt/body, left/right text labels, and source-bound
    option identifiers.
- Reject patches that try to create new source item IDs, source asset IDs,
  answer-key provenance, raw/base64 assets, arbitrary HTML resources, scoring
  policy, or unbounded free-form context.
- Preserve separation from `manual_answer_key` overlays and
  `review_decision`. Item-content repair must not create or imply answer-key
  evidence.
- Recompute target readiness from the effective item content after patch
  application and target generation/validation.
- Prove Exam.net PDF and QTI renderers consume effective item content when
  `effective_ir_json` changes renderer input.
- Keep QTI export disabled for missing machine-marked keys until Task 303 or a
  later governed QTI profile validates unkeyed/manual representation for the
  selected QTI version.

## Implementation Roadmap

### 1. Normalize patch DTOs around current source IDs

- Extend the overlay contract DTOs only where the existing
  `effective_item_patch` shape is too vague for runtime validation.
- Keep `extra=forbid` on every patch object.
- Require source-bound identifiers for every patched nested field.
- Make unsupported patch fields reject before rendering, not downgrade into
  warnings.

Checkpoint:

- malformed, stale, duplicate, unknown-field, and wrong-type patches fail
  before any target renderer runs.

### 2. Apply patches into effective IR only

- Add a focused item-content patch application service under the overlay
  domain boundary.
- Return explicit accepted/rejected fields in `ingestion_overlay_report_v1`.
- Emit `effective_ir_json` only when item content actually changes.
- Preserve effective answer-key and review-decision behavior from Task 295
  without sharing procedural branches.

Checkpoint:

- tests prove source IR bytes and source item fingerprints remain unchanged
  after item-content repair.

### 3. Recompute readiness and renderer inputs

- Feed patched effective items into the Exam.net PDF renderer.
- Feed patched effective items into the QTI adapter only when the item type is
  inside the governed QTI profile.
- Recompute `target_readiness_report_v1` after patch application, target
  generation, and target validation.

Checkpoint:

- target readiness can move from unsupported/malformed content to ready only
  when the patched effective item has a governed target shape and validation
  passes.

### 4. Add contract and consumer-facing tests

- Add domain tests for each supported patch type.
- Add bundle/API tests proving patched text/options/prompts appear in
  effective artifacts and rendered targets.
- Add negative tests proving item-content patches do not create answer keys or
  satisfy missing-key readiness.
- Add report tests proving accepted/rejected patch fields are item-addressable
  for Skriptoteket.

## Deliverables

- [x] Strict runtime DTOs for supported `effective_item_patch` payloads.
- [x] Effective item-content patch application service.
- [x] Ingestion overlay report entries for applied and rejected patch fields.
- [x] Effective IR artifact output for item-content repair.
- [x] PDF renderer integration tests for patched item text/options/prompts.
- [x] QTI adapter/generator tests for patched effective item content inside the
  current governed QTI profile.
- [x] Target-readiness tests after item-content patch application.

## Acceptance Criteria

- [x] Source IR, source manifest, source item fingerprints, and parser
  provenance remain unchanged by item-content overlays.
- [x] Item-content patches apply only to `digiexam_effective_exam_v1` and
  renderer input.
- [x] Patch validation is source-bound by item ID, sequence, item type, source
  item fingerprint, and nested source IDs where applicable.
- [x] Patch payloads cannot carry raw/base64 assets, arbitrary source files,
  result-PDF text, student data, answer-key provenance, or scoring policy.
- [x] Manual answer-key overlays and review decisions remain separate paths and
  are not required for pure item-content repair.
- [x] Missing machine-marked keys remain `needs_teacher_answer_key` unless a
  manual key or a governed unkeyed/manual target profile applies.
- [x] PDF and QTI outputs consume effective item content only after effective
  patch validation succeeds.
- [x] Contract tests cover text, option, prompt/body, gap, and matching visible
  field repair plus negative cases.

## Implementation Evidence

- Added `domain.digiexam_effective_item_patch` as the focused visible-content
  patch application service.
- Extended strict overlay DTOs for choice, gap-fill, and matching visible patch
  shapes while keeping raw/base64 resources, arbitrary external resource
  references, scoring policy, and answer-key provenance out of patch payloads.
- `domain.digiexam_ingestion_overlay` now applies valid
  `effective_item_patch` values into effective renderer input, reports
  `effective_item_patch` in `ingestion_overlay_report_v1`, and preserves the
  source item fingerprint in `digiexam_effective_exam_v1`.
- Manual answer-key overlays and review decisions remain separate application
  paths. Patch-only overlays do not remove missing-answer-key follow-up.

## Validation Evidence

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_ingestion_overlay.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`

## Stop Conditions

- Stop if the implementation needs to mutate parser output or source
  provenance to make a target render.
- Stop if a patch needs raw assets or source files embedded in overlay JSON.
- Stop if renderer behavior diverges from target readiness.
- Stop before enabling unkeyed/manual QTI export; Task 303 owns that profile.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- focused overlay/effective IR domain tests
- focused DigiExam migration bundle API tests
- focused Exam.net PDF/QTI renderer tests
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
