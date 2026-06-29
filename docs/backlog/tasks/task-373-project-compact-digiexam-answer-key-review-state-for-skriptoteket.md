---
id: 'task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket'
title: 'Project compact DigiExam answer-key review state for Skriptoteket'
type: 'task'
status: 'ready'
priority: 'high'
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md
  - docs/backlog/tasks/task-337-remove-accepted-current-state-from-authoring-correction-contracts.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md
labels:
  - exam-migration
  - answer-key-review
  - correction-apply
  - skriptoteket
  - service-contract
---
PR-sized service-contract planning and implementation slice.

## Objective

Define and implement a Sir Convert-owned compact answer-key review-state
projection for DigiExam exam migration jobs and source-neutral correction apply
results. The projection must give Skriptoteket a stable item-addressable state
surface for teacher review without forcing the frontend to re-derive review
semantics from `ir_json`, `answer_key_completion_report`,
`effective_ir_json`, correction reports, local correction sessions, and
`target_readiness_report_v1`.

The projection must preserve the accepted boundary:

- Sir Convert owns source/effective exam truth, answer-key provenance,
  candidate lineage, validation reasons, target readiness, and replay artifact
  references.
- Skriptoteket owns teacher interaction, authenticated correction-session
  persistence, and presentation, but must project saved/reviewed/exportable
  claims only from Sir Convert-returned state.
- `target_readiness_report_v1` remains the export-action authority. The new
  projection is an item review-state contract, not an export-readiness
  replacement.

## PR Scope

- Add a versioned compact projection,
  `digiexam_answer_key_review_state_v1`, derived from Sir Convert-owned state.
- Emit the projection for first-pass DigiExam migration bundle jobs as a named
  artifact, `answer_key_review_state_report`.
- Add the same projection to `exam_authoring_corrections_apply_result_v1` as
  the top-level `answer_key_review_state` field so corrected/replayed state can
  be rendered without consumer-side inference.
- Derive item states from source/effective state, answer-key completion report,
  correction report, manual follow-up rows, target readiness, artifact
  availability, and replay artifact references where available.
- Expose stable item binding fields needed by Skriptoteket:
  `item_id`, `sequence`, `item_type`, `source_item_fingerprint`, supported
  interaction IDs, choice IDs, gap IDs, and correction affordance metadata.
- Expose semantic state and reason codes, not Swedish UI labels. Skriptoteket
  localizes and chooses compact labels such as `Granska`, `Klart`, `Ändrat`,
  and `Kontrollera`.
- Preserve advisory provenance only as a bounded `provenance_detail` object
  for detail/audit display. Do not introduce a generic `history` field or
  event-log compatibility surface; list state must stay independent of AI
  provenance after a key is reviewed or teacher-edited.
- Keep missing answer keys blocked until real answer-key corrections exist.
  Do not reintroduce `review_decision` /
  `accept_current_state_for_export` or any accepted-current-state substitute.

## Out of Scope

- No Skriptoteket UI implementation in this task.
- No HuleEdu Gateway changes unless generated OpenAPI changes later require a
  separate consumer/proxy slice.
- No best-effort incomplete export mode.
- No source IR mutation, parser-provenance rewrite, or consumer-side answer-key
  inference.
- No legacy compatibility layer for `review_decision`, reviewed-current-state,
  or historical-lineage fields. Old names may remain only in tests that prove
  rejected legacy payloads still fail.
- No raw `.dxe`, result PDF text, raw provider prompt/response, raw overlay
  JSON, student-result data, credentials, identity markers, or private artifact
  paths in the projection.

## Deliverables

- [ ] Contract docs update for the compact projection in
  `docs/converters/digiexam-migration-service-api-artifact-contract.md`.
- [ ] Contract docs update for correction apply result semantics in
  `docs/converters/exam-authoring-corrections-apply-contract.md`.
- [ ] Pydantic/domain DTOs for the projection with strict literal states and
  reason codes.
- [ ] Projection builder used by both first-pass migration bundle generation
  and correction apply/replay result generation.
- [ ] Named artifact manifest support for first-pass bundle jobs.
- [ ] OpenAPI/schema export updates where the correction apply response changes.
- [ ] Focused red-first behavioral tests for initial bundle and correction
  apply/replay projection.

## Acceptance Criteria

- [ ] Sir Convert emits an item-addressable projection that lets Skriptoteket
  render compact review states without joining multiple artifact families.
- [ ] Pending usable advisory candidates are represented as review-needed with
  advisory provenance available for detail display.
- [ ] Accepted unchanged advisory keys are represented as complete/reviewed
  current keys without requiring the consumer to show an AI marker in list
  state.
- [ ] Teacher-edited advisory keys and teacher-authored keys are represented as
  teacher-owned current keys; AI provenance is not represented as current key
  provenance after keyed content changes.
- [ ] Choice items with no selected correct answer produce a validation/review
  reason equivalent to `no_correct_choice_selected`; gap/open-cloze items with
  no accepted values produce an equivalent missing-value reason.
- [ ] Missing-key states remain export-blocking through
  `target_readiness_report_v1`; the compact projection does not unlock target
  downloads.
- [ ] Rejected correction entries and stale source-state failures are surfaced
  as current review/correction problems without leaking raw submitted payloads.
- [ ] Replay result projection carries replay artifact references only when
  Sir Convert produced replay-scoped target artifacts.
- [ ] The projection is content-safe and excludes raw source/provider/student
  data listed in the scope.
- [ ] Tests prove the states for source-provided key, missing key,
  pending advisory candidate, accepted unchanged advisory candidate,
  teacher-edited advisory candidate, teacher-authored key, rejected correction,
  target-specific blocker, and replay artifact reference.

## Closed Implementation Decisions

1. Exact state vocabulary.
   - Decision: the producer `review_state` vocabulary is
     `review_required`, `review_complete`, `teacher_modified`, and
     `validation_required`.
   - Decision: the producer `current_key_origin` vocabulary is `none`,
     `source_provided`, `reviewed_advisory`, `teacher_authored`,
     `teacher_edited_advisory`, and `mixed`.
   - Decision: initial reason codes include
     `source_answer_key_present`, `advisory_candidate_pending`,
     `reviewed_advisory_accepted`, `teacher_answer_key_present`,
     `teacher_edited_advisory_candidate`, `manual_answer_key_required`,
     `no_correct_choice_selected`, `required_gap_accepted_values_missing`,
     `unsupported_item_type`, `unsupported_target_shape`,
     `target_validation_failed`, `provider_unavailable`,
     `correction_rejected`, `stale_source_state`,
     `replay_artifact_unavailable`, and `matching_source_state_unavailable`.
   - Rationale: these are source-neutral semantic codes. Skriptoteket owns
     Swedish labels such as `Granska`, `Klart`, `Ändrat`, and `Kontrollera`.
1. Detail versus list provenance.
   - Decision: use a bounded `provenance_detail` object, not a generic
     `history` field.
   - Rationale: `provenance_detail` names the narrow audit/detail purpose and
     avoids implying event-log replay, old overlay compatibility, or a second
     user-facing state machine. It may support a detail disclosure such as
     `Tidigare förslag`, but it must not affect list state or export readiness.
1. Teacher-edited advisory display.
   - Decision: expose both compact review state and origin. A teacher edit to
     an advisory key or keyed content is represented as
     `review_state = teacher_modified` and
     `current_key_origin = teacher_edited_advisory`.
   - Decision: the current key is teacher-owned after keyed content changes.
     AI/advisory provenance may appear only in bounded `provenance_detail` and
     must not be represented as current-key provenance.
1. Correction apply placement.
   - Decision: first-pass bundle jobs emit named artifact
     `answer_key_review_state_report`; correction apply returns top-level
     `answer_key_review_state`.
   - Decision: Task 373 does not require a separate named replay review-state
     artifact. Replay-scoped target artifact references remain governed by
     target readiness rows.
1. Public lane exposure.
   - Decision: public Exam Converter jobs may receive the compact report when
     it can be derived from public-safe producer state.
   - Decision: public rows must omit privileged correction-session state,
     source-state signatures, identity/grant data, private paths, raw
     source/provider/student data, provider diagnostics, and advisory
     `provenance_detail` unless a later signed public grant contract explicitly
     authorizes it.
1. Localization contract.
   - Decision: Sir Convert emits reason codes plus `message_key` values.
   - Decision: `message_key` is copy lookup metadata only; Sir Convert must not
     ship final Swedish UI strings for this projection.
1. Matching items.
   - Decision: represent matching/unsupported rows only from producer-backed
     source state. Do not emit inferred `left_id` / `right_id` structures,
     browser-draft pair slots, or consumer-fillable matching skeletons.
   - Decision: when matching structure is unavailable or unsupported, emit a
     validation/unsupported reason such as `unsupported_item_type` or
     `matching_source_state_unavailable`.

These decisions make Task 373 implementation-ready. An implementation agent may
refine field grouping only when tests preserve the exact state/origin/reason
vocabulary, the `provenance_detail` boundary, and the no-legacy-compatibility
rules above.

## Red-First Test Plan

- Add a first failing projection test for a migration bundle with one pending
  advisory candidate and one missing machine-marked key. Expected failure:
  no compact projection artifact/DTO exists.
- Add a first failing correction-apply test for accepted unchanged advisory
  versus teacher-edited advisory. Expected failure: both currently require
  consumers to inspect effective provenance/correction report directly.
- Add a failing missing-key validation projection test for choice and
  gap/open-cloze items. Expected failure: no dedicated review-state reason is
  emitted.

Focused commands to decide during implementation after exact test nodes are
written:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py ...`
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py ...`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_answer_key_completion_api_v2.py ...`

## Validation Plan

- `pdm run openapi-export-v2`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Focused `pdm run pytest-root ...`
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if the implementation needs Skriptoteket to infer answer-key state from
  multiple artifacts after the new projection exists.
- Stop if a proposed state would reintroduce accepted-current-state export as
  authoring/correction state.
- Stop if target readiness and item review state become conflated.
- Stop if raw provider/source/student data would be exposed in the projection.
- Stop if the projection cannot distinguish current key truth from historical
  advisory lineage.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
