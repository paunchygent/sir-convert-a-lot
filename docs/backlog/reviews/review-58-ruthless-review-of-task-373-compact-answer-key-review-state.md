---
id: review-58-ruthless-review-of-task-373-compact-answer-key-review-state
title: Ruthless review of Task 373 compact answer-key review state
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md
  - docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md
  - docs/backlog/tasks/task-337-remove-accepted-current-state-from-authoring-correction-contracts.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
labels:
  - review
  - approved
  - task-373
  - exam-migration
  - answer-key-review
  - skriptoteket
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Independent ruthless review for Task 373. This reviewer did not author the
implementation or tests, did not deploy, did not restart services, did not
commit, and did not modify production or test implementation files. The only
intentional mutation from this review pass is this retained review artifact.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/081-pdm-and-dependency-management.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/index.md`
- `docs/backlog/README.md`
- `docs/_meta/docs-contract.yaml`
- `docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md`
- `docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md`
- `docs/backlog/tasks/task-337-remove-accepted-current-state-from-authoring-correction-contracts.md`
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- `docs/converters/exam-authoring-corrections-apply-contract.md`
- `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`

Task 373 files reviewed:

- `.codex/handoff.md`
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
- `docs/backlog/INDEX.md`
- `docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md`
- `docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md`
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- `docs/converters/exam-authoring-corrections-apply-contract.md`
- `scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state.py`
- `scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state_models.py`
- `scripts/sir_convert_a_lot/application/exam_authoring_answer_key_review_projection.py`
- `scripts/sir_convert_a_lot/application/exam_authoring_matching_readiness.py`
- `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py`
- `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_models.py`
- `scripts/sir_convert_a_lot/application/openapi_contracts_v2.py`
- `scripts/sir_convert_a_lot/domain/digiexam_migration_bundle_contracts.py`
- `scripts/sir_convert_a_lot/domain/digiexam_schema_versions.py`
- `scripts/sir_convert_a_lot/infrastructure/correction_replay_artifact_writer.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_manifest.py`
- `scripts/sir_convert_a_lot/interfaces/http_openapi_contract_v2.py`
- `tests/sir_convert_a_lot/test_digiexam_answer_key_review_state.py`
- `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`
- `tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py`
- `tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py`
- `tests/sir_convert_a_lot/test_openapi_contract_v2.py`

Public/runtime surfaces affected:

- First-pass DigiExam migration bundle named artifacts and manifest shape.
- `digiexam_answer_key_review_state_v1` Pydantic/OpenAPI component schema.
- `answer_key_review_state_report` artifact exposure.
- `POST /v2/exam-authoring/corrections/apply` response shape through top-level
  `answer_key_review_state`.
- Correction replay artifact-reference projection for PDF/QTI replay artifacts.

Compatibility posture:

- Clean additive producer contract for current v2 surfaces.
- No compatibility layer for `history`, `review_decision`,
  `accept_current_state_for_export`, or accepted-current-state substitutes is
  allowed by Task 337 or Task 373.
- `target_readiness_report_v1` remains the export-action authority.

Dirty-tree boundaries:

- This review was performed against the already dirty Task 373 implementation
  working tree. I did not revert or normalize any implementation changes.
- No existing retained Task 373 review was present under `docs/backlog/reviews/`.
  The retained review lane previously ended at review 57.

## Checklist

- [x] Governing task, story, boundary baseline, converter contracts, ADR, and
  repo review rules read.
- [x] Exact Task 373 production, test, schema, docs, and OpenAPI surfaces
  inspected.
- [x] Public contracts, data/runtime boundaries, typing risks, forbidden
  compatibility surfaces, and module-size/SRP constraints audited.
- [x] Focused reviewer tests rerun.
- [x] Decision recorded in this retained review artifact.

## Findings

### High: pending advisory provenance detail is never emitted by the producer

`scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py:290`
builds the first-pass `answer_key_review_state_report` without passing
`include_advisory_provenance_detail=True`, while the shared builder defaults
that flag to `False` at
`scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state.py:47`.
No production call site enables the flag. As a result, a pending usable advisory
candidate can be represented as `review_required`, but the bounded
`provenance_detail` that Task 373 requires for detail display is always absent.

Why this matters: Task 373 explicitly requires pending usable advisory
candidates to have advisory provenance available for detail display
(`docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md:111`).
The implementation therefore forces Skriptoteket either to show no detail/audit
lineage for `Granska` rows or to rejoin against the first-pass completion report
and re-derive provenance locally, which is the consumer-side inference Task 373
is meant to remove.

Fix shape: make the producer call site include bounded advisory
`provenance_detail` for authorized/authenticated product rows, while preserving
the documented public-lane exclusion for unauthorized public rows. If the
intended product decision is to omit detail everywhere, amend Task 373 and the
contract docs before claiming completion, because that changes the accepted
consumer contract.

Proof required:

- Add/update a behavioral first-pass bundle test with a valid advisory
  completion candidate. It must fetch `answer_key_review_state_report` and
  assert the row has `review_state = review_required`, reason
  `advisory_candidate_pending`, and bounded `provenance_detail` fields such as
  candidate id/digest/profile/schema/prompt-template metadata, while still
  excluding raw provider payloads, raw source/student data, source-state
  signatures, identity/grant data, private paths, generic `history`,
  `review_decision`, and `accept_current_state_for_export`.
- Run:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_review_state.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_route_produces_named_pdf_qti_and_reports -q`
- Re-run the Task 373 focused apply/replay/OpenAPI tests and docs gates after
  the contract/code/test update.

## Non-Blocking Observations

The strict schema pieces are otherwise on the right track. The reviewed DTOs use
literal-bounded state, origin, reason, submission-origin, correction-affordance,
and replay-reference vocabularies with `extra="forbid"`. The OpenAPI component
exports `DigiExamAnswerKeyReviewStateV1`, the apply response exposes top-level
`answer_key_review_state`, and replay references are attached only after the
replay writer has produced `correction_replay_examnet_pdf` or
`correction_replay_qti_package`.

Code search over the changed implementation did not find new `Any`,
`typing.cast`, `# type: ignore`, lint-ignore bypasses, or active legacy
compatibility shims for the new projection. The new/changed modules stayed
under the repo's 500-line module limit and include top-level Google-style
module docstrings.

## Follow-up Actions

Required before approval:

- Fix the missing first-pass advisory `provenance_detail` emission or amend the
  governing contract to remove that requirement.
- Add truthful behavioral proof for the pending advisory detail-display case.
- Re-run focused Task 373 tests plus docs validation.

No optional follow-up is recorded separately because the finding is a Task 373
acceptance blocker.

## Decision

changes_requested

## Response

Task 373 is not approved yet. The implementation establishes the strict compact
projection and the two exposure points, but it does not satisfy the governed
pending-advisory detail contract because bounded `provenance_detail` is never
enabled by production code.

## Completion

Decision: `changes_requested`.

Reviewer-run evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_review_state.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_route_produces_named_pdf_qti_and_reports tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_entries_apply_and_recompute_effective_state tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_choice_advisory_candidate_digest_match_is_reviewed tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_gap_teacher_edited_candidate_allows_digest_drift tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py::test_digiexam_correction_replay_pdf_downloads_with_source_labelled_options tests/sir_convert_a_lot/test_openapi_contract_v2.py::test_service_api_v2_consumer_components_are_published -q`
  passed: `14 passed in 6.28s`.
- Code search over changed implementation/test surfaces for `Any`,
  `typing.cast`, `cast(`, `type: ignore`, lint ignores, compatibility/shim
  language, and legacy accepted-current-state names found only historical
  contract/test rejection text or pre-existing model fields outside the new
  projection.

Skipped in this review pass:

- Full `format-all`, `lint-fix`, `typecheck-all`, and `coverage-gate`; approval
  is already blocked by the missing contract behavior above.

## Review Pass 2

Review pass 2 inspected the remediation for the pass-1 finding. The
authenticated first-pass bundle gap is fixed: the bundle builder now calls the
shared projection with `include_advisory_provenance_detail=True`, and the new
route-level regression fetches the named `answer_key_review_state_report`
artifact, proves a pending advisory row has bounded `provenance_detail`, keeps
the row at `review_required` / `current_key_origin = none` /
`advisory_candidate_pending`, verifies replay references are empty, and checks
the target readiness rows remain export-disabled.

### High: advisory provenance detail is now enabled for the public grant path too

`scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py:306`
enables `include_advisory_provenance_detail=True` unconditionally for every
DigiExam migration bundle. Public Exam Converter grant jobs use the same create
and execution path: `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:210`
accepts public grant job creation, stores that public owner scope, and passes
`public_grant_request=True` only to structured-LLM admission at
`scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:293`.

That admission path forbids remote public providers, but it does not forbid a
public job from requesting advisory completion with a local structured provider.
`scripts/sir_convert_a_lot/infrastructure/structured_llm_admission.py:89`
only applies the remote-provider policy, and
`scripts/sir_convert_a_lot/domain/specs_v2.py:201` accepts
`completion_mode = local_llm_suggest_missing_machine_marked` in route options.
The public grant policy evaluates route, target, timing, and ownership, but it
does not authorize advisory `provenance_detail`.

Why this matters: Task 373 explicitly says public rows must omit advisory
`provenance_detail` unless a later signed public grant contract authorizes it
(`docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md:180`).
The pass-2 remediation therefore fixes the authenticated product-detail case
but opens the same bounded advisory detail to public-grant artifacts whenever a
public job can produce advisory candidates.

Fix shape: thread the authenticated/public ownership context into the bundle
review-state projection decision, or otherwise make public-grant jobs omit
`provenance_detail` while authenticated Skriptoteket product jobs include it.
The public path must still emit the compact row and public-safe state/reason
codes, but `provenance_detail` must remain absent unless a later governed public
grant explicitly authorizes it.

Proof required:

- Add a public-grant route test that submits a DigiExam job with advisory
  completion using a local structured provider, fetches
  `answer_key_review_state_report` through the public artifact-read lease, and
  proves pending advisory rows have `provenance_detail = null` while still
  exposing only public-safe state/reason fields.
- Keep the authenticated regression proving bounded `provenance_detail` present
  for the product path.
- Run:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_public_exam_converter_grant_runtime_v2.py -q`
- Re-run the Task 373 focused suite and docs gates.

## Review Pass 2 Decision

changes_requested

## Review Pass 2 Response

Task 373 is still not approved. The original authenticated first-pass
`provenance_detail` finding is remediated, but the remediation applies the
detail flag globally and violates the Task 373 public-lane exclusion for
advisory `provenance_detail`.

## Review Pass 2 Completion

Decision: `changes_requested`.

Reviewer-run evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail -q`
  passed: `1 passed in 5.12s`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_review_state.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_route_produces_named_pdf_qti_and_reports tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_entries_apply_and_recompute_effective_state tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_choice_advisory_candidate_digest_match_is_reviewed tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_gap_teacher_edited_candidate_allows_digest_drift tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py::test_digiexam_correction_replay_pdf_downloads_with_source_labelled_options tests/sir_convert_a_lot/test_openapi_contract_v2.py::test_service_api_v2_consumer_components_are_published -q`
  passed: `15 passed in 6.57s`.

Skipped in review pass 2:

- Full `format-all`, `lint-fix`, `typecheck-all`, `coverage-gate`, and
  `openapi-export-v2`; approval is blocked by the public-lane contract finding,
  and the implementer reported those broad gates green except for the deliberate
  OpenAPI skip because schema shape did not change.

## Review Pass 3

Review pass 3 inspected the second remediation for the public-lane finding. The
bundle builder now derives the detail decision from persisted job ownership:
`_include_advisory_provenance_detail(job)` returns false when
`job.owner_api_key_scope` starts with the canonical public owner scope prefix.
This is the existing public-grant owner boundary used by the public access
policy, not a request-header inference or a parallel review-state machine.

The behavior now matches Task 373:

- authenticated/product DigiExam bundle jobs include bounded
  `provenance_detail` for pending advisory rows;
- public-grant DigiExam bundle artifact reads keep the same compact
  `review_required` / `none` / `advisory_candidate_pending` row but emit
  `provenance_detail = null`;
- target readiness remains separate and export-blocking;
- no generic `history`, `review_decision`, or
  `accept_current_state_for_export` surface is introduced.

No new blocking findings were found in pass 3.

## Review Pass 3 Decision

approved

## Review Pass 3 Response

Task 373 is approved. Both retained Review 58 findings are fixed: the
authenticated first-pass producer exposes bounded advisory detail for pending
advisory rows, and the public-grant lane omits advisory detail while preserving
public-safe compact state/reason output.

## Review Pass 3 Completion

Decision: `approved`.

Reviewer-run evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_public_exam_converter_grant_runtime_v2.py::test_public_exam_converter_grant_review_state_omits_advisory_provenance_detail -q`
  passed: `2 passed in 23.69s`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_review_state.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_route_produces_named_pdf_qti_and_reports tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_entries_apply_and_recompute_effective_state tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_choice_advisory_candidate_digest_match_is_reviewed tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py::test_non_matching_gap_teacher_edited_candidate_allows_digest_drift tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py::test_digiexam_correction_replay_pdf_downloads_with_source_labelled_options tests/sir_convert_a_lot/test_openapi_contract_v2.py::test_service_api_v2_consumer_components_are_published tests/sir_convert_a_lot/test_public_exam_converter_grant_runtime_v2.py -q`
  passed: `19 passed in 39.19s`.
- Code search over the pass-3 remediation files for `Any`, `typing.cast`,
  `cast(`, `type: ignore`, lint ignores, compatibility/shim language, and
  legacy accepted-current-state names found only negative assertion strings in
  the public-lane test.
- Module-size check: `digiexam_migration_bundle_builder.py` is 424 lines;
  `test_public_exam_converter_grant_runtime_v2.py` is 411 lines.

Skipped in review pass 3:

- Full `format-all`, `lint-fix`, `typecheck-all`, `coverage-gate`, and
  `openapi-export-v2`; the implementer reported the broad quality gates green
  and OpenAPI unchanged. Reviewer reran the focused behavioral and contract
  proof needed for the retained findings.
