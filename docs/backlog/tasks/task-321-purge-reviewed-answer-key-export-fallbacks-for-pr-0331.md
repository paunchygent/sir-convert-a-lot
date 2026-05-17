---
id: task-321-purge-reviewed-answer-key-export-fallbacks-for-pr-0331
title: Purge reviewed answer-key export fallbacks for PR-0331
type: task
status: completed
priority: high
created: '2026-05-17'
last_updated: '2026-05-17'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/backlog/tasks/task-308-define-examnet-pdf-manual-unkeyed-accepted-current-state-profile-and-multigap-readiness.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - answer-key-completion
  - reviewed-overlay
  - qti
  - examnet-pdf
  - target-readiness
  - pr-0331
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the destructive fallback paths exposed by PR-0331 where reviewed or
accepted answer keys could be applied into effective IR but then disappear from
downloaded QTI/PDF artifacts.

The product contract is source-neutral: DigiExam is one source dialect, not the
definition of target support. Choice, matching, single-gap, and multi-gap
gap/open-cloze answer keys are supported by the intermediate/generic contract.
The Exam.net PDF target may render gap/open-cloze items as free text, but it
must include the accepted key values in the artifact. A proof gap for native
Exam.net gap fields or live Exam.net QTI import is not permission to drop
accepted keys.

## PR Scope

- Add keyed QTI text-entry output for reviewed/source/teacher gap-fill accepted
  values.
- Keep QTI package download unavailable when any source item is omitted,
  unsupported, or still missing required accepted values.
- Render keyed PDF gap/open-cloze items as Exam.net PDF free-text items with
  accepted values included for every gap.
- Remove internal diagnostic wording from user-facing PDF artifacts.
- Keep accepted-current-state/manual-unkeyed fallbacks only where a teacher
  explicitly sends that review decision and no trusted key exists.
- Document every remaining degraded-output fallback and why it is allowed.

## Definitions

- "Exam.net live import proof-gated" means the local QTI package/report records
  `target_support_status: proof_gated` and `examnet_proof_status: not_proven`
  for gap-fill or matching items. It does not mean package generation is
  blocked. A package with proof-gated items may still be downloadable when local
  QTI validation passes; the report simply does not claim live Exam.net import
  proof.
- "Adapter follow-up" in this task means a `DigiExamExamNetQtiAdapterResult`
  manual follow-up emitted because a DigiExam IR item could not be mapped to any
  QTI item. The current mapped instance is a DigiExam item type outside the
  adapter's governed set: open-ended, single-choice, multiple-choice,
  multiple-response, and gap-fill. When this happens, package generation is
  blocked because otherwise the ZIP would omit a source item.
- "Gap value" means one non-empty accepted answer string bound to one source gap
  GUID in `DigiExamIrItem.answer_key.correct_gap_answers`. Values may come from
  source-proven evidence, a teacher manual answer-key overlay, or a
  teacher-reviewed completion overlay. A gap is "still missing" when an item has
  a gap in `item.gaps` but no non-empty accepted value for that gap GUID in the
  effective renderer input.
- "Unsafe content or binding" means the exact blocking PDF branches where the
  renderer cannot preserve a correct artifact: parser/result state blocks
  rendering, an embedded asset payload/reference cannot be resolved, the prompt
  has no renderable text or image, the item has no point value for a target that
  needs points, a submitted key references unknown source options/gaps or lacks
  required keys, option text is duplicated in a way that would make the key
  ambiguous, or no governed target renderer exists for the item type.

## Fallback Map

| Surface | Branch | Decision | Defense |
| --- | --- | --- | --- |
| QTI choice with missing key and explicit accepted current state | Manual/unkeyed choice interaction, no `correctResponse` or automatic `responseProcessing` | Keep | This is a teacher review decision that preserves visible alternatives while making no key claim. It is not used for reviewed/accepted key application. |
| QTI gap/open-cloze with reviewed/source/teacher accepted values | `textEntryInteraction` with per-gap response declarations, correct response, and value mappings | Fix and keep keyed | Accepted values are first-class keys and must be emitted. The local package/report marks live Exam.net import status as `examnet_proof_status: not_proven` and `target_support_status: proof_gated` for gap-fill, but that status does not block package generation when local QTI validation passes. |
| QTI gap/open-cloze with missing key and explicit accepted current state | Manual/free-text preservation | Keep | This preserves visible content only after an explicit accepted-current-state decision. It carries manual follow-up and no key/evaluation claim. |
| QTI item omitted by the DigiExam adapter | Previously a partial package could still be offered | Remove | A package that silently drops source items is a degraded product outcome. The package is now unavailable with item-level follow-up. |
| QTI validation failure | Failed artifact with `qti_validation_failed` | Keep as failure | This does not accept degraded output; it blocks download until package validation passes. |
| QTI unsupported resources | Resource omitted with item-addressable manual follow-up | Keep | Only target-unsupported resources are omitted. The item remains visible, the omission is explicit, and the report carries the manual action. |
| PDF choice with missing key and explicit accepted current state | Free-text/manual rendering with visible alternatives and no key claim | Keep | This is a teacher review decision for export without trusted key data. It is not an approve-AI-suggestion path. |
| PDF gap/open-cloze with reviewed/source/teacher accepted values | Free-text-style PDF item with accepted values included | Fix and keep keyed | PDF may use a free-text target shape for gaps, but accepted key values must be present in the artifact. |
| PDF gap/open-cloze with missing key and explicit accepted current state | Free-text/manual rendering preserving blanks/media/order and no accepted-value claim | Keep | This is the Task 308 content-preserving fallback. It is explicit, reported, and only applies when no trusted key exists. |
| PDF missing asset, empty prompt, invalid points, malformed key binding, or unsupported item type | Blocked/unavailable artifact | Keep as failure | These branches do not accept degraded output. They block artifact creation when the renderer cannot bind referenced assets, cannot produce visible prompt content, cannot assign points to automatically evaluated target items, cannot bind submitted keys to known source options/gaps, or has no governed target renderer for the item type. |
| Matching in generic IR/QTI/PDF contracts | Source-neutral matching contract and QTI/PDF matching stay independent of DigiExam | Keep keyed when source evidence exists | DigiExam not carrying matching items cannot define generic target support. Source-neutral matching supports repeated source or target associations when the item-level matching bounds allow them. No DigiExam matching adapter is introduced. |

## Live Proof Boundary

- Live dev-container proof for PR-0331 is not the same as local API/domain
  tests. A live proof requires the auth edge, Sir Convert service, and the
  tunneled LLM container to be running together.

## Deliverables

- [x] Keyed QTI text-entry output for reviewed/source/teacher gap-fill accepted
  values.
- [x] QTI package blocking when adapter follow-up would omit source items or
  gap-fill items still lack required accepted values.
- [x] Exam.net PDF rendering for keyed gap/open-cloze items that preserves
  accepted values in the artifact.
- [x] Forbidden internal diagnostics removed from user-facing PDF artifact
  text.
- [x] Governed fallback map documenting each remaining degraded-output branch
  and its defense.
- [x] Focused tests and docs closeout evidence.

## Acceptance Criteria

- [x] Reviewed choice and gap-fill overlays create downloadable artifacts with
  the accepted keys present.
- [x] QTI cannot be marked available when adapter follow-up means an item was
  omitted from the package.
- [x] Reviewed multi-gap gap/open-cloze PDF output includes every accepted gap
  value.
- [x] User-facing PDF artifacts contain no internal fallback text such as
  `Manuell bedömning. Ursprunglig ... utan betrodda ...`.
- [x] All remaining degraded-output fallbacks are source-bound, explicit,
  reported, and not used for reviewed/accepted keys.
- [x] Local focused tests cover QTI keyed gap output, QTI package blocking for
  missing gap values, reviewed gap overlay artifact downloads, and PDF artifact
  text.
- [x] Live verification is recorded separately if the auth edge, Sir Convert,
  and tunneled LLM container are available.

## Validation Plan

- `pdm run pytest-root tests/sir_convert_a_lot/test_examnet_qti_package.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_advisory_completion_report_does_not_mutate_artifacts tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_reviewed_completion_apply_uses_overlay_without_provider tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_reviewed_gap_completion_keeps_keys_in_pdf_and_qti tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_qti_without_correct_response tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_examnet_pdf_without_key_claims tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_examnet_pdf_for_item_013_multigap`
- `pdm run examnet-qti-samples`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Validation Evidence

- `pdm run format-all` - passed; reformatted 2 files.
- `pdm run lint-fix` - passed after `pdm run docs-sync` refreshed generated
  indexes.
- `pdm run examnet-qti-samples` - passed; generated the keyed
  `gap-fill-text-entry` QTI sample with `examnet_proof_status: not_proven`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_examnet_qti_package.py tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py`
  - 21 passed.
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`
  - 12 passed, including repeated source and repeated target associations for
    the Exam.net PDF matching profile when source-neutral bounds allow them.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_advisory_completion_report_does_not_mutate_artifacts tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_reviewed_completion_apply_uses_overlay_without_provider tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_reviewed_gap_completion_keeps_keys_in_pdf_and_qti tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_qti_without_correct_response tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_examnet_pdf_without_key_claims tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_accept_current_state_enables_manual_unkeyed_examnet_pdf_for_item_013_multigap`
  - 6 passed.
- `pdm run typecheck-all` - passed; no issues in 708 source files.
- `pdm run docs-validate` - passed; 403 backlog files and docs/rules
  validated.
- `pdm run skills-validate` - passed.
- `pdm run handoff-validate` - passed.
- `git diff --check` - passed.

Live dev-container verification was not run in this slice. That proof requires
the auth edge, Sir Convert service, and tunneled LLM container to be available
together.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
