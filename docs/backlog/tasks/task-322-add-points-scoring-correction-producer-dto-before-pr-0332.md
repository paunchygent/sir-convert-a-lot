---
id: task-322-add-points-scoring-correction-producer-dto-before-pr-0332
title: Add points/scoring correction producer DTO before PR-0332
type: task
status: completed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - answer-key-completion
  - teacher-overlay
  - scoring
  - effective-ir
  - skriptoteket
  - pr-0332
---

Small producer-owned prerequisite immediately before Skriptoteket `PR-0332`.

## Objective

Add the Sir Convert producer DTO and route contract needed for source-bound
teacher correction of item points before Skriptoteket implements the full
teacher correction workflow in `PR-0332`.

Point correction is not a browser-local affordance and must not be routed
through `effective_item_patch`, `manual_answer_key`,
`reviewed_completion_answer_key`, or `review_decision`. It needs its own
producer-owned overlay field so Sir Convert can validate the correction, apply
it only to effective renderer input, recompute target readiness, and prove the
result in effective IR plus PDF/QTI artifacts.

## Product Decisions

- The external overlay field is `point_correction`; the corrected item point
  value is carried as `max_score` inside that DTO.
- `max_score` corrections must be positive integers. Zero, negative values,
  fractional values, non-numeric values, and scoring-policy/rubric payloads are
  out of scope for this task.
- `point_correction` is orthogonal to answer-key provenance. It may be submitted
  with manual or reviewed answer-key overlays for the same source-bound item,
  but Sir Convert must report every applied field explicitly so Skriptoteket
  projects returned producer state instead of trusting local UI edits.

## Implementation Decisions And Final Shape

Task 322 is an additive producer-owned overlay/runtime change. It does not
introduce a new overlay schema version, does not change parser-owned source IR,
and does not authorize Skriptoteket UI work.

Final overlay shape:

```json
{
  "item_id": "item-001",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source",
  "point_correction": {
    "kind": "item_points",
    "max_score": 3
  }
}
```

Implementation decisions:

- Add `point_correction` as a first-class field on
  `DigiExamIngestionOverlayItem`, not as an `effective_item_patch`, answer-key
  payload, reviewed-completion payload, or review decision.
- Validate `point_correction.max_score` with Pydantic as a positive integer.
  Fractional, zero, negative, non-numeric, rubric, marking-matrix,
  partial-credit, and scoring-policy payloads must fail before rendering.
- Keep source binding unchanged: source file SHA-256, source IR schema version,
  source IR SHA-256, item id, sequence, item type, and source item fingerprint
  remain mandatory and are validated before application.
- Apply accepted point corrections by creating effective renderer input with a
  replaced `DigiExamIrItem.max_score`. Do not mutate parser source IR,
  parser provenance, answer-key provenance, advisory completion metadata, or
  source manifest summaries.
- Add an effective-report summary field, `effective_point_correction`, that
  includes at least the original source `max_score`, corrected effective
  `max_score`, and enough source binding for Skriptoteket to project returned
  producer state.
- Add `point_correction` to the accepted overlay report `applied_fields` when
  applied. If a point correction is submitted with `manual_answer_key` or
  `reviewed_completion_answer_key`, the accepted entry must list both fields in
  application order.
- Keep source item fingerprints source-owned. Because `max_score` is part of
  the source-item fingerprint, target-readiness rows must continue to report
  fingerprints computed from the original source IR even when target rendering
  consumes corrected effective points.
- Recompute target readiness after applying point corrections and build PDF/QTI
  artifacts from the corrected effective renderer input.
- Prove target propagation by inspecting returned PDF text for the corrected
  Swedish point label and returned QTI XML for the corrected `MAXSCORE`
  outcome value.
- Keep unsupported scoring semantics explicit: this task supports only the
  bounded item `max_score` correction. Any future target scoring feature beyond
  a positive integer point value requires a separate governed task.

## PR Scope

- Define the source-bound points/scoring correction DTO in the v2 ingestion
  overlay contract.
- Bind each point correction to the same invariant used by other teacher
  overlays: source file SHA-256, source IR schema version, source IR SHA-256,
  item id, sequence, item type, and source item fingerprint.
- Validate point corrections before rendering. Invalid, stale, mismatched,
  duplicated, non-numeric, negative, or target-incompatible values must fail
  before PDF/QTI generation.
- Apply accepted point corrections to effective renderer input without mutating
  source IR, parser provenance, answer-key provenance, or advisory completion
  metadata.
- Include applied point corrections in the effective IR/report surface so
  Skriptoteket can project returned state instead of trusting local UI edits.
- Recompute target readiness after point correction application.
- Publish the generated OpenAPI/consumer contract impact needed by
  Skriptoteket before `PR-0332` starts implementation.
- Add PDF and QTI artifact proof that corrected points are present where the
  targets represent points and that target-specific unsupported scoring
  features are reported without silently dropping the item or the correction.

## Out of Scope

- Skriptoteket UI controls for editing points.
- Teacher correction of stems, prompts, choices, matching keys, or
  gapped/open-cloze accepted values.
- Scoring-policy, rubric, marking-matrix, partial-credit, or free-text
  assessment semantics beyond the bounded positive integer item point value
  required by the existing renderer targets.
- Any fallback that lets local UI state unlock artifact downloads before the
  corrected Sir Convert bundle is returned.

## Deliverables

- [x] Source-bound points/scoring correction DTO added to the v2 ingestion
  overlay contract.
- [x] DTO validation fails before rendering for stale binding, duplicate
  binding, invalid values, and target-incompatible point changes.
- [x] Effective IR/report output includes applied point corrections and their
  source binding.
- [x] Target readiness is recomputed from the corrected effective renderer
  input.
- [x] Generated OpenAPI and consumer-impact notes are refreshed for
  Skriptoteket.
- [x] Focused tests prove point corrections reach effective IR and returned
  PDF/QTI artifacts without source IR mutation.

## Acceptance Criteria

- [x] A valid source-bound point correction is accepted and appears in the
  returned effective IR/report.
- [x] A stale or mismatched point correction fails before rendering and does
  not create downloadable artifacts.
- [x] A point correction cannot be submitted through item-content patches,
  answer-key overlays, or review decisions.
- [x] Point correction may coexist with manual/reviewed answer-key overlays,
  and the returned overlay report lists every applied field.
- [x] PDF and QTI outputs include the corrected point value wherever the target
  artifact represents item points.
- [x] Unsupported target scoring semantics are explicit readiness/report
  failures, not silent artifact degradation.
- [x] Source IR, parser provenance, answer-key provenance, advisory completion
  metadata, and internal diagnostics are not mutated or leaked into
  teacher-facing artifacts.

## Validation Plan

- Focused overlay DTO/schema tests.
- Focused effective IR/report projection tests.
- Focused PDF/QTI artifact inspection tests for corrected point values.
- OpenAPI generation no-drift proof.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Evidence

Completed on 2026-05-18.

- Added strict `point_correction` DTO support to
  `DigiExamIngestionOverlayItem`; `max_score` is validated as a positive,
  strict integer.
- Added a small point-correction domain helper so overlay application remains
  SRP-focused and does not mutate parser-owned source IR.
- Added `effective_point_correction` to effective IR/report output with source
  and effective point values plus the source item fingerprint.
- Preserved source-bound target-readiness fingerprints by passing original
  source item fingerprints into readiness construction after effective
  renderer input changes.
- Refreshed the generated v2 OpenAPI snapshot so Skriptoteket can generate
  consumer types before `PR-0332`.
- Updated the converter contract with the final `point_correction` overlay
  shape, strict positive-integer semantics, combined `applied_fields`, and
  source-fingerprint preservation notes.
- Remediated review findings by pinning `DigiExamOverlayPointCorrection`,
  `DigiExamEffectivePointCorrectionV1`, `point_correction`, and
  `effective_point_correction` in the semantic OpenAPI consumer-component
  test.
- Added direct readiness coverage proving item-level readiness rows keep the
  original source item fingerprint after effective `max_score` changes.
- Added reviewed-completion coexistence coverage proving
  `applied_fields == ("point_correction", "reviewed_completion_answer_key")`
  and the effective IR report contains both reviewed key lineage and effective
  point correction.
- Regenerated Skriptoteket's checked-in Sir Convert OpenAPI DTOs from the
  Task 322 snapshot and added a consumer-side preflight assertion for
  `point_correction` and `effective_point_correction`.

Validation evidence:

- `pdm run openapi-export-v2`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_digiexam_ingestion_overlay.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_applies_point_correction_to_effective_pdf_and_qti`
- `pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_digiexam_ingestion_overlay.py::test_point_correction_can_coexist_with_reviewed_completion_overlay tests/sir_convert_a_lot/test_digiexam_target_readiness.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_applies_point_correction_to_effective_pdf_and_qti`
- `pdm run coverage-gate` passed with 1340 passed, 6 skipped, and 95.49%
  total coverage.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
