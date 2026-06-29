---
id: 'task-374-preserve-advisory-candidates-during-correction-apply-replay'
title: 'Preserve advisory candidates during correction apply replay'
type: 'task'
status: 'in_progress'
priority: 'high'
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md
  - docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md
  - docs/backlog/reviews/review-58-ruthless-review-of-task-373-compact-answer-key-review-state.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0408-st-21-04-exam-converter-frontend-design-implementation-alignment.md
labels:
  - exam-migration
  - answer-key-review
  - correction-apply
  - production-regression
  - skriptoteket
---

PR-sized producer-contract remediation for the production post-accept replay
failure found after the Task 373 / PR-0406 closeout.

## Objective

Preserve valid first-pass advisory answer-key candidates for untouched keyed
items when a teacher applies one correction through the source-neutral
exam-authoring correction apply route.

Production evidence on 2026-06-29 showed the first accepted advisory key
replayed successfully, but sibling choice and gap/open-cloze items lost their
pending advisory state and rendered as generic missing-facit validation rows in
Skriptoteket. Transport was healthy: source-state issue, correction-session
intent persistence, and correction apply all returned HTTP 200. The failing
boundary is producer projection: correction apply rebuilds
`answer_key_review_state` from effective source items and correction outcomes,
but does not carry the untouched advisory candidate set used by the first-pass
`answer_key_review_state_report`.

The corrected contract is:

- an accepted advisory correction becomes `review_complete` with
  `current_key_origin = reviewed_advisory` and
  `reasons = [reviewed_advisory_accepted]`;
- untouched valid advisory candidates remain `review_required` with
  `current_key_origin = none` and
  `reasons = [advisory_candidate_pending]`;
- untouched items with no valid advisory remain validation/missing-key rows;
- free-text/open-writing items are not converted into keyed review gates, while
  gap/open-cloze items remain in the keyed correction/review set.

## PR Scope

- Extend the producer-owned correction source-state/apply context so valid
  advisory candidates from the first pass survive a later correction apply
  replay for untouched items.
- Keep the advisory context bounded to the existing safe fields already used by
  `DigiExamAnswerKeyReviewAdvisoryCandidateInput`; do not carry raw provider
  prompts, raw responses, source file text, identity data, private paths, or
  browser-local UI state.
- Feed the preserved candidate context into
  `build_digiexam_answer_key_review_state` inside correction apply result
  projection, including replay artifact attachment paths.
- Preserve existing digest validation for accepted advisory corrections. An
  accepted unchanged advisory candidate must still fail closed when the
  submitted keyed payload digest does not match its lineage digest.
- Update contract docs and OpenAPI/schema tests if the source-state or apply
  DTO shape changes.
- Add focused route/domain tests for multi-item replay with choice and
  gap/open-cloze siblings.

## Out of Scope

- No Skriptoteket-only fallback that turns a producer
  `validation_required` / missing-key row back into a pending suggestion from
  local browser state.
- No change to final export authority. `target_readiness_report_v1` remains
  the only source of PDF/QTI readiness.
- No broad advisory recomputation during correction apply. This task preserves
  first-pass bounded advisory context; it does not rerun an LLM provider.
- No expansion of advisory support to free-text/open-writing items.
- No legacy `review_decision`, accepted-current-state, generic `history`, or
  compatibility field.

## Deliverables

- [x] Source-state/apply DTOs carry bounded advisory candidate context with
  strict validation and content-safe serialization.
- [x] Source-state issuance populates the advisory context from producer-owned
  first-pass artifacts/state for authenticated jobs where advisory completion
  ran.
- [x] Correction apply review-state projection passes preserved candidates to
  the shared compact projection builder so untouched candidates remain
  `advisory_candidate_pending`.
- [x] Route/domain tests cover accepting one advisory candidate while sibling
  choice and gap/open-cloze advisory candidates remain pending.
- [x] Tests cover no-advisory siblings staying as missing-key validation rows,
  invalid/stale candidate context failing closed or being ignored according to
  the existing projection contract, and public/content-safety exclusions.
- [x] Contract docs/OpenAPI schema are synchronized when the DTO surface
  changes.

## Acceptance Criteria

- [x] A correction apply request containing multiple source items and multiple
  first-pass valid advisory candidates returns `answer_key_review_state` where
  only the submitted item changes to reviewed/teacher-owned state; untouched
  valid advisory siblings stay `review_required` with
  `advisory_candidate_pending` and bounded `provenance_detail` when that detail
  is authorized.
- [x] Choice, gap-fill, and open-cloze keyed rows are covered. Free-text/open-
  writing rows remain outside keyed answer-key review and do not acquire
  generated keys.
- [x] Existing accepted-advisory digest-match and digest-mismatch behavior is
  unchanged.
- [x] The correction replay artifact writer preserves the same review-state
  semantics after replay-scoped PDF/QTI references are attached.
- [x] The HTTP route test proves the full source-state issue -> correction
  apply flow, not only an in-memory builder call.
- [x] The projection remains content-safe: no raw source text beyond existing
  sanitized source-state fields, provider prompts/responses, credentials,
  identity markers, private paths, browser-local state, or student data leak
  into the advisory context or review-state projection.
- [x] Skriptoteket can consume the returned producer state without local
  review-state inference; if the producer returns `validation_required`, the
  consumer must display it as a real current producer validation state.

## Red-First Test Plan

- Add a failing correction apply route test with at least three keyed items:
  accept one choice advisory candidate, leave one choice and one gap/open-
  cloze advisory candidate untouched, and assert the siblings remain
  `review_required` / `advisory_candidate_pending`.
- Add a failing replay-artifact test for the same state after
  `write_exam_authoring_correction_replay_artifacts` attaches replay artifact
  references.
- Add/update a source-state issue test proving bounded advisory context is
  issued from the original producer job and remains content-safe.
- Add a negative test where an item has no valid advisory candidate and still
  returns the appropriate missing-key reason after a sibling accept.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

2026-06-29 implementation adds signed, bounded
`advisory_answer_key_candidates` to `exam_authoring_correction_source_state_v1`.
The source-state content digest now includes that context, first-pass DigiExam
bundle generation persists it from the advisory completion report, and
correction apply adapts it back into the shared
`digiexam_answer_key_review_state_v1` builder. Accepted advisory rows no longer
retain pending-candidate `provenance_detail`; untouched valid siblings keep
`review_required` / `current_key_origin = none` /
`advisory_candidate_pending` with bounded detail when authorized.
Review-state projection now also gates preserved advisory candidates to keyed
choice and gap/open-cloze rows; free-text/open-writing rows project as
`review_complete` / `current_key_origin = none` /
`answer_key_not_applicable` and ignore advisory candidate context.

Red evidence captured:

- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py::test_apply_preserves_untouched_advisory_candidates_after_sibling_accept -q`
  failed because `ExamAuthoringCorrectionSourceStateV1` rejected
  `advisory_answer_key_candidates` as an extra field.

Focused green evidence:

- Same focused node passed after the DTO/projection fix.
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py -q`
  passed: `4 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_choice_advisory_candidate_digest_mismatch_rejected tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_choice_advisory_candidate_digest_match_is_reviewed tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_gap_advisory_candidate_digest_mismatch_rejected tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_gap_advisory_candidate_digest_match_is_reviewed tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py::test_digiexam_migration_job_emits_correction_source_state_for_issuer tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py::test_digiexam_migration_job_emits_gap_correction_source_state_for_issuer tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py::test_digiexam_correction_apply_returns_downloadable_replay_artifacts tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_public_exam_converter_grant_runtime_v2.py::test_public_exam_converter_grant_review_state_omits_advisory_provenance_detail tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed: `16 passed`.
- `pdm run openapi-export-v2` refreshed
  `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`.

Cross-repo dev proof:

- `/opt/homebrew/bin/pdm run python -m scripts.playwright_pr_0337_correction_session_live --source-dxe /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1776888013-ak7-lag-och-ratt.dxe --base-url http://127.0.0.1:5173 --timeout-seconds 600`
  passed in Skriptoteket at
  `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/playwright-pr-0337-correction-session-live/20260629T193503Z/manifest.redacted.json`.
  The manifest records `post_accept_untouched_advisory_sibling` with accepted
  `item-001`, sibling `item-002`, sibling status `Granska`, and
  `sibling_advisory_panel_visible: true`.
