---
id: task-333-implement-non-matching-unified-correction-apply-runtime-for-digiexam-pr-0332
title: Implement non-matching unified correction apply runtime for DigiExam PR-0332
type: task
status: completed
priority: critical
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-330-implement-unified-source-neutral-exam-authoring-correction-apply-route-hard-cut.md
  - docs/backlog/tasks/task-331-remediate-review-24-task-330-correction-apply-contract-blockers.md
  - docs/backlog/tasks/task-332-implement-matching-capable-source-state-producer-for-unified-corrections.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
labels:
  - correction-contract
  - service-api-v2
  - pr-0332
  - digiexam
  - teacher-corrections
---

PR-sized runtime slice that lets downstream PR-0332 continue on the unified
correction route for non-matching DigiExam-backed correction families.

## Objective

Implement Sir Convert-owned apply semantics for the non-matching correction
entries whose producer state is now available from Task 331's signed DigiExam
source-state sidecar. The runtime slice has landed for point, choice,
gap/open-cloze, and item-text correction families; downstream matching use
remains blocked on Task 332.

## PR Scope

- Implement `/v2/exam-authoring/corrections/apply` runtime support for
  `point_correction` against producer-owned `max_score`.
- Implement `manual_choice_answer_key` against producer-owned choice
  interaction IDs and choice IDs.
- Implement `manual_gap_open_cloze_answer_key` against producer-owned
  gap/open-cloze interaction IDs and gap IDs.
- Implement `item_text_patch` for DigiExam-backed item title, prompt HTML,
  prompt lines, and visible option text when those fields are present in
  producer source state.
- Preserve Task 331 binding rules: canonical source-state digest, signed
  producer authority, stale item binding rejection, advisory-candidate digest
  validation where applicable, privacy-safe errors, and fail-closed mixed-batch
  readiness/artifact semantics.
- Recompute effective state, target readiness, and artifact availability only
  from Sir Convert-applied state, never from browser-local edits.
- Update OpenAPI, converter contract support matrix, Story 49, Task 331/333
  evidence, and handoff after validation.

## Deliverables

- [x] Supported non-matching entries produce accepted report rows and effective
  state changes.
- [x] Unsupported or stale non-matching entries fail closed before readiness or
  artifact availability unlocks.
- [x] Advisory-origin choice/gap submissions validate bounded candidate lineage
  and accepted-candidate payload digests before reviewed provenance is applied.
- [x] Focused runtime tests cover point, choice, gap/open-cloze, item text
  patch, stale binding, unknown nested IDs, mixed-batch fail-closed behavior,
  and privacy-safe validation errors.
- [x] Real DigiExam source-state regression proves `manual_matching_answer_key`
  attempts fail closed without readiness or artifact unlock until Task 332.
- [x] Generated OpenAPI publishes the unified source-state and non-matching
  correction contract used by HuleEdu/Skriptoteket.
- [x] Docs state says downstream PR-0332 may continue only for implemented
  non-matching families; `manual_matching_answer_key` remains blocked on Task
  332\.

## Out of Scope

- `manual_matching_answer_key` downstream use. Task 332 owns real
  matching-capable producer state and apply proof.
- Reintroducing, proxying, or preserving
  `/v2/exam-authoring/matching/manual-answer-key/apply`.
- DigiExam matching synthesis from unknown item types, prompt text, or
  browser-local drafts.
- HuleEdu Gateway implementation and Skriptoteket consumer UI work. Those are
  separate repo-owned slices after this task lands.
- General teacher-authored Exam.net-origin API work beyond the DigiExam-backed
  non-matching correction families listed above.

## Acceptance Criteria

- [x] A signed source-state bundle from a real DigiExam producer job can be
  issued and used to accept point, choice, gap/open-cloze, and item-text
  correction entries.
- [x] Accepted corrections change effective state and recompute readiness from
  producer-applied state only.
- [x] Rejected entries do not partially unlock artifacts or target readiness in
  the same batch.
- [x] Candidate-lineage and payload-digest semantics remain at least as strict
  as the existing reviewed-completion overlay contract.
- [x] OpenAPI omits the abandoned Task 324 route and exposes only unified
  correction routes.
- [x] Handoff identifies HuleEdu unified auth-edge widening as the next
  cross-repo slice after this task is reviewed.

## Validation Plan

- `pdm run openapi-export-v2`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Focused correction apply route tests for the newly supported entries.
- Focused DigiExam producer/issuer/apply tests for real source-state bundles.
- Focused OpenAPI route contract tests.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Added Task 333 non-matching apply semantics to
  `POST /v2/exam-authoring/corrections/apply` for:
  `item_text_patch`, `point_correction`, `manual_choice_answer_key`, and
  `manual_gap_open_cloze_answer_key`.
- Kept the existing signed source-state binding, canonical source-state digest,
  stale item binding rejection, validation-error privacy, and mixed-batch
  fail-closed semantics.
- Added candidate payload digest validation for accepted advisory choice and
  gap/open-cloze corrections while preserving teacher-edited advisory drift as
  teacher-provided provenance.
- Split hard-cut/privacy, matching-route, and non-matching runtime tests so the
  route module remains within the repo module-size boundary.

## Validation Evidence

- `pdm run openapi-export-v2`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_hard_cut.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_job_emits_correction_source_state_for_issuer tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_job_emits_gap_correction_source_state_for_issuer`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_correction_matching_blocked.py`
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
