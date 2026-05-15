---
id: task-308-define-examnet-pdf-manual-unkeyed-accepted-current-state-profile-and-multigap-readiness
title: Define Exam.net PDF manual-unkeyed accepted-current-state profile and multi-gap readiness
type: task
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-277-implement-digiexam-exam-net-oriented-pdf-renderer-and-live-validation.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - digiexam
  - examnet-pdf
  - accepted-current-state
  - manual-unkeyed
  - target-readiness
  - gap-fill
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and implement the governed Exam.net PDF counterpart to Task 303's
manual/unkeyed QTI accepted-current-state profile.

When a teacher submits `accept_current_state_for_export`, Sir Convert must be
able to say exactly whether the Exam.net PDF target can preserve the visible
question content without trusted automatic answer-key data. For missing-key
single-choice, missing-key multiple-response, and item-013-style multi-gap
gap/open-cloze items, this is a product requirement: if the user explicitly
requests accepted-current-state PDF export, Sir Convert must render a PDF that
preserves the visible item content and manual/unkeyed review semantics. Native
Exam.net auto-evaluation may be unavailable, but content-preserving manual or
degraded PDF output must not be blocked only because a trusted key or native
multi-gap import contract is absent.

The motivating live case is `item-013` from the ecology DigiExam fixture:
a DigiExam `Lucktext`/gap item with five blanks, an embedded image, and no
accepted values in blank validations. Current live output correctly refuses to
claim PDF readiness, but the artifact-level unavailable code is selected from
the first blocking warning (`manual_answer_key_required`), which masks the more
specific multi-gap Exam.net PDF limitation. This task must make that reporting
precise and add a governed render path for the user-requested manual/unkeyed
PDF case. Native multi-gap `Lucktext` PDF-to-exam conversion should be promoted
only with fixture proof; otherwise the safe fallback is degraded manual/free-text
rendering that preserves the prompt, blanks, embedded image, and teacher
manual-follow-up state.

## Product Boundary

- Source IR remains unchanged. A missing key in DigiExam source data is still
  missing source evidence.
- Accepted-current-state is a teacher review decision, not an answer key.
- The PDF renderer must never infer answers from prompt text, gap labels,
  images, result PDFs, advisory LLM candidates, or display order.
- Missing keys may remove automatic answer-key/evaluation claims only when the
  target output still preserves the visible question content and manual review
  semantics.
- If native Exam.net PDF-to-exam import cannot safely preserve a shape, Sir
  Convert must degrade to a governed manual/free-text PDF representation when
  that representation preserves visible content. It may keep the target
  disabled only for fatal blockers such as dropped prompt text, dropped
  alternatives, dropped blanks, missing embedded assets, invalid PDF bytes, or
  no safe content-preserving degradation.

## PR Scope

- Define an Exam.net PDF manual/unkeyed profile for accepted-current-state
  exports, separate from Task 303's QTI profile.
- Thread accepted-current-state item IDs or an equivalent target policy into
  the Exam.net PDF renderer. The current QTI path already receives this policy;
  the PDF path does not.
- Define supported PDF manual/unkeyed shapes for at least:
  - single-choice and multiple-response items with visible alternatives but no
    trusted correct-response data;
  - gap/open-cloze items where visible text, blanks, images, and manual
    follow-up can be preserved without claiming accepted values.
- Promote a native multi-gap `Lucktext` PDF shape if fixture proof shows the
  Exam.net PDF-to-exam converter can preserve the structure. Use item-013 as
  the regression case and include its embedded image.
- If native multi-gap PDF preservation cannot be promoted in this slice, render
  item-013-style items through a governed degraded manual/free-text PDF shape
  and emit item-specific warning/degradation rows instead of a blocking
  `unsupported_target_shape` row. The target remains unavailable only when no
  content-preserving degradation can be produced.
- Replace first-warning artifact-code selection where it hides a more specific
  item limitation. Artifact-level unavailability may remain one code, but
  target-readiness rows and warnings must expose the item-specific causes.
- Keep missing answer-key readiness distinct from unsupported target shape:
  an item may need a teacher answer key for automatic evaluation and also be
  unsupported by the current PDF target profile.
- Update converter/reference docs and generated OpenAPI only if the public JSON
  shape changes. Prefer existing enum/string fields when more specific
  `reason_code` values are sufficient.

## Out Of Scope

- Inferring gap accepted values or choice answer keys.
- Changing DigiExam parser behavior or source IR provenance.
- Adding a new Exam.net PDF source parser.
- Changing Skriptoteket UI behavior except through existing readiness rows and
  generated types if the API schema changes.
- Claiming live Exam.net PDF-to-exam import success without a reproducible
  fixture/proof path.

## Deliverables

- Exam.net PDF manual/unkeyed accepted-current-state profile documented in the
  Swedish PDF renderer profile and migration artifact contract.
- PDF renderer and bundle-builder changes that produce profile-valid
  manual/unkeyed PDF output for missing-key choice items and item-013-style
  multi-gap items when the user explicitly accepts current state.
- Item-013 regression coverage for five blanks, embedded image, absent
  accepted values, accepted-current-state overlay, and readiness output.
- Warning/unavailable-code precedence rules that keep item-specific
  multi-gap/gap-open-cloze limitations visible to downstream consumers while
  distinguishing degraded manual PDF output from fatal target unavailability.
- OpenAPI snapshot and Skriptoteket impact note if public JSON shape changes.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
- [x] Consumer impact checked

## Acceptance Criteria

- [x] The PDF renderer has a named manual/unkeyed accepted-current-state target
  profile, with explicit supported and unsupported item shapes.
- [x] Accepted-current-state PDF rendering can preserve visible question text,
  alternatives, gaps, embedded images, and manual follow-up semantics without
  emitting answer-key claims when trusted keys are absent.
- [x] Missing-key single-choice and multiple-response items render to Exam.net
  PDF under explicit accepted-current-state policy without `Correct answer`,
  `Correct answers`, accepted-value, score-key, or automatic-evaluation claims.
- [x] Item-013-style multi-gap gap/open-cloze items render to Exam.net PDF
  under explicit accepted-current-state policy with all visible blanks,
  embedded images, display order, and manual-follow-up semantics preserved.
- [x] The migration bundle builder passes accepted-current-state policy into
  the PDF renderer or an equivalent PDF target validator before target
  readiness is computed.
- [x] `target_readiness_report_v1` can report
  `ready_after_accepted_current_state` for Exam.net PDF only after PDF bytes
  are created and the PDF target profile validates in native or degraded
  manual/unkeyed mode.
- [x] `item-013` no longer reports only the coarse accepted-current-state
  missing-key path when native multi-gap/gap-open-cloze PDF target support is
  unproven or degraded.
- [x] Multi-gap `Lucktext` PDF output is either promoted as native with fixture
  proof and renderer tests, or rendered through a documented degraded
  manual/free-text profile with item-specific warning rows and teacher action
  for review or manual recreation.
- [x] Warning and unavailable-code precedence is deterministic and documented:
  artifact-level status may be coarse, but item-level readiness must preserve
  all material blockers needed by Skriptoteket.

## Test Requirements

- [x] PDF renderer unit tests cover accepted-current-state single-choice and
  multiple-response output without answer-key claims and with visible
  alternatives preserved.
- [x] PDF renderer unit tests cover accepted-current-state gap/open-cloze
  output, including item-013's five blanks and embedded image, without accepted
  values.
- [x] Bundle API tests prove Exam.net PDF remains unavailable before accepted
  current-state when keys are missing.
- [x] Bundle API tests prove Exam.net PDF becomes
  `ready_after_accepted_current_state` for profile-valid native or degraded
  manual/unkeyed PDF shapes after accepted-current-state.
- [x] Target-readiness tests prove multi-gap/gap-open-cloze native limitations
  are not masked by the first `manual_answer_key_required` warning and do not
  block degraded manual PDF rendering when content is preserved.
- [x] Contract tests prove no source/parser provenance is changed and no answer
  key is invented.
- [x] If OpenAPI changes, regenerate and snapshot
  `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`.

## Implementation Notes

- Added a named Exam.net PDF render policy for accepted-current-state
  manual/unkeyed output.
- Threaded accepted-current-state item IDs from the migration bundle builder
  into the Exam.net PDF renderer.
- Rendered missing-key single-choice and multiple-response items as
  manual/free-text PDF output with visible alternatives preserved and no
  correct-answer claims.
- Rendered item-013-style multi-gap `Lucktext` items as degraded
  manual/free-text PDF output with prompt text, five blanks, embedded images,
  display order, and manual follow-up preserved.
- Kept native multi-gap PDF-to-exam support vendor-unproven; the implemented
  profile is a governed degraded manual/free-text profile, not a native
  auto-evaluation claim.
- Preserved existing public JSON shape. The slice adds specific warning and
  reason-code values through existing string fields, so no OpenAPI snapshot
  regeneration or Skriptoteket generated-type update was required.

## Validation Evidence

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_examnet_pdf_without_key_claims tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_examnet_pdf_for_item_013_multigap tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_qti_without_correct_response tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_unavailable_pdf_target_returns_named_artifact_error`
  (`11 passed`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`
  (`21 passed`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_gap_contracts.py tests/sir_convert_a_lot/test_digiexam_ingestion_overlay.py`
  (`23 passed`)
- `pdm run docs-sync`
- `pdm run docs-validate` (`Validated 389 backlog files`,
  `Validated docs=456 rules=11`)
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `pdm run coverage-gate` (`1262 passed, 5 skipped`, coverage `95.48%`)
- `git diff --check`

## Stop Conditions

- Stop if the PDF shape would drop visible prompts, alternatives, gaps, or
  embedded images.
- Stop if Exam.net PDF-to-exam fixture proof contradicts the proposed native
  `Lucktext`/multi-gap shape and no degraded manual/free-text PDF shape can
  preserve visible content.
- Stop if accepted-current-state would require inventing an answer key,
  accepted gap value, matching pair, or source provenance.
- Stop if warning specificity would require changing public JSON schema without
  a same-slice OpenAPI and Skriptoteket consumer update.
