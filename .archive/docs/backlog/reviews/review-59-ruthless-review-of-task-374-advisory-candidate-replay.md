---
id: review-59-ruthless-review-of-task-374-advisory-candidate-replay
title: Ruthless review of Task 374 advisory candidate replay preservation
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-374-preserve-advisory-candidates-during-correction-apply-replay.md
  - docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md
  - docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0408-st-21-04-exam-converter-frontend-design-implementation-alignment.md
labels:
  - review
  - approved
  - task-374
  - exam-migration
  - answer-key-review
  - correction-apply
  - skriptoteket
---

Retained independent review for Task 374. This reviewer did not author the
implementation or tests, did not deploy, did not commit, and did not modify
production or test implementation files. The only intentional mutations from
this review pass are retained review artifacts.

## Review Scope

Authorities and instructions read:

- `AGENTS.md`
- `.codex/handoff.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/index.md`
- `docs/backlog/tasks/task-374-preserve-advisory-candidates-during-correction-apply-replay.md`
- `docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md`
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- `docs/converters/exam-authoring-corrections-apply-contract.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`

Reviewed Task 374 surfaces:

- `.codex/handoff.md`
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
- `docs/backlog/INDEX.md`
- `docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md`
- `docs/backlog/tasks/task-374-preserve-advisory-candidates-during-correction-apply-replay.md`
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- `docs/converters/exam-authoring-corrections-apply-contract.md`
- `scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state.py`
- `scripts/sir_convert_a_lot/application/exam_authoring_answer_key_review_projection.py`
- `scripts/sir_convert_a_lot/application/exam_authoring_correction_source_state_models.py`
- `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_integrity.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py`
- `tests/sir_convert_a_lot/exam_authoring_advisory_replay_fixtures.py`
- `tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py`
- `tests/sir_convert_a_lot/test_openapi_contract_v2.py`

Public/runtime surfaces affected:

- Signed correction source-state issue and apply request DTO shape.
- Source-state canonical digest/signature contents.
- `POST /v2/exam-authoring/corrections/apply` top-level
  `answer_key_review_state`.
- First-pass DigiExam bundle correction source-state sidecar.
- Generated Service API v2 OpenAPI schema and converter contract docs.

Compatibility posture:

- Additive current-v2 contract extension for signed source-state context.
- No local Skriptoteket fallback is allowed for producer
  `validation_required`.
- `target_readiness_report_v1` remains export readiness authority.

## Checklist

- [x] Governing Task 374 and Story 57 authority read.
- [x] Exact production, DTO, projection, OpenAPI, docs, and test surfaces
  inspected.
- [x] Public contracts, data/runtime boundaries, typing risks, forbidden
  fallback risks, and verification evidence audited.
- [x] Focused Sir Convert and Skriptoteket tests rerun.
- [x] Decision recorded in retained review artifacts.

## Findings

No blocking findings remain after the Task 374 rereview.

### Resolved high: producer created answer-key review warnings for non-keyed free-text rows

`scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state.py:172`
applies any valid advisory candidate before checking whether the item is a
choice or gap/open-cloze keyed row. The same projection then falls through to
`unsupported_item_type` at
`scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state.py:184`
and returns `validation_required` at
`scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state.py:253`
for items without keyed interactions. The new regression fixture locks that
behavior in for a free-text item at
`tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py:99`.

Why this matters: Task 374 and the cross-repo review brief require only
MCQ/choice and gap-fill/open-cloze keyed rows to preserve advisory candidates;
free-text/open-writing rows must not get answer-key suggestions, missing-facit
warnings, or answer-key review gates. As written, a signed source-state row can
still make a non-keyed item either `review_required` via
`advisory_candidate_pending` or `validation_required` via
`unsupported_item_type`. That forces consumers either to render a false current
producer warning or to add a local override for producer truth.

Fix shape: gate advisory-candidate preservation and answer-key validation
reasons behind a producer-owned keyed-review predicate for choice and
gap/open-cloze items. Non-keyed open-ended/free-text/open-writing rows should
project as non-actionable review state, or the contract must add a governed
non-applicable state/reason and update both producer and consumer tests. Do not
ask Skriptoteket to repair this by reviving local inference.

Proof required:

- Add a Sir Convert regression where a signed source state contains a
  free-text/open-ended item and a valid advisory candidate, and prove the item
  does not become `review_required`, `advisory_candidate_pending`, or
  `validation_required`.
- Update the existing Task 374 apply test so the free-text row is asserted as
  non-gated rather than `unsupported_item_type`.
- Re-run:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_openapi_contract_v2.py::test_service_api_v2_consumer_components_are_published -q`

Resolved in rereview: `answer_key_not_applicable` now short-circuits
non-keyed rows before advisory preservation, pending advisory state is gated to
choice/gap/open-cloze rows, and the Task 374 fixture includes a bogus valid
free-writing advisory candidate that remains non-actionable.

## Non-Blocking Observations

The signed advisory context itself is on the right boundary: the new
`advisory_answer_key_candidates` field is part of the source-state canonical
digest, and correction apply consumes it through the shared compact projection
builder instead of rebuilding from consumer-local browser state.

The preserved sibling behavior for keyed choice and gap/open-cloze rows is
covered at the apply route boundary and replay-reference helper boundary. The
accepted-advisory digest match/mismatch tests were included in focused review
evidence and stayed green.

The large `pdm.lock` delta was not treated as part of this review because the
review request explicitly scoped pre-existing lockfile changes out unless the
patch touched them.

## Follow-up Actions

Completed before approval:

- Fix the producer non-keyed/free-text answer-key warning behavior or amend the
  governed contract with an explicit non-actionable state/reason.
- Add the requested producer regression proof for signed advisory candidates on
  non-keyed rows.
- Re-run the focused Task 374 tests and docs gates.

## Decision

approved

## Response

Task 374 is approved after rereview. The keyed sibling replay preservation path
is implemented and green under focused tests, and non-keyed free-text/open-
writing rows now remain non-actionable even when malformed advisory candidate
context references them.

## Evidence

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_choice_advisory_candidate_digest_mismatch_rejected tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_choice_advisory_candidate_digest_match_is_reviewed tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_gap_advisory_candidate_digest_mismatch_rejected tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_gap_advisory_candidate_digest_match_is_reviewed tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_openapi_contract_v2.py::test_service_api_v2_consumer_components_are_published -q`
  passed: `10 passed, 1 warning`.

Skipped:

- Full `format-all`, `lint-fix`, and `coverage-gate` were not rerun by this
  reviewer. Parent evidence reports the focused remediation gates and docs
  validators are green; `typecheck-all` still has unrelated existing
  `tests/* no-any-return` failures.

## Rereview Evidence

Reviewer-run evidence after the remediation:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_openapi_contract_v2.py::test_service_api_v2_consumer_components_are_published -q`
  passed: `14 passed, 1 warning`.
- `git diff --check` passed.

Parent-reported evidence accepted for closeout context:

- `/opt/homebrew/bin/pdm run docs-validate` passed.
- `/opt/homebrew/bin/pdm run handoff-validate` passed.
- `/opt/homebrew/bin/pdm run typecheck-all` still fails only unrelated existing
  `tests/* no-any-return` errors; no Task 374 errors.
- Skriptoteket dev end-to-end proof passed at
  `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/playwright-pr-0337-correction-session-live/20260629T193503Z/manifest.redacted.json`;
  after accepting `item-001`, untouched sibling `item-002` remained `Granska`
  with advisory detail visible.

## Completion

Decision: `approved`.
