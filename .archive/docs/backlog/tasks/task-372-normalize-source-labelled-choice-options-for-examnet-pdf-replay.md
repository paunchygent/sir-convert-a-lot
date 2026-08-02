---
id: task-372-normalize-source-labelled-choice-options-for-examnet-pdf-replay
title: Normalize source-labelled choice options for Examnet PDF replay
type: task
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - exam-migration
  - examnet
  - pdf-renderer
  - correction-replay
  - incident-remediation
---

PR-sized incident remediation for authenticated Exam Converter correction
replay.

## Objective

Fix the Exam.net PDF target boundary so source-labelled multiple-choice option
text such as `A. ...`, `B. ...`, `1. ...`, or `2) ...` is normalized before PDF
rendering instead of blocking the whole corrected PDF. Exam.net owns target
option labels and may shuffle alternatives; source-side labels must not become
student-visible option text in the imported exam.

## PR Scope

- Update the Exam.net PDF item rendering policy to strip source-visible option
  labels at the target interpretation boundary while preserving the underlying
  option order, answer-key binding, and duplicate-text safety checks.
- Keep the renderer fail-closed for genuinely unsafe alternatives, such as
  empty options or duplicate normalized option text after label removal.
- Cover correction-replay behavior so accepted manual/AI answer keys can
  unblock PDF rendering when the only remaining multiple-choice issue is
  source-labelled option text.
- Keep QTI package behavior unchanged; QTI owns option identity through
  metadata and must not rely on source-visible labels.
- Record downstream UI follow-up separately: Skriptoteket must distinguish
  question-review completion from target-specific artifact unavailability.

## Deliverables

- [x] Behavioral regression test for labelled MCQ options rendering without
  labels in Exam.net PDF output.
- [x] Correction replay regression proving a corrected labelled MCQ item emits
  `correction_replay_examnet_pdf` when no other target blockers remain.
- [x] Production code change scoped to Exam.net PDF option normalization.
- [x] Validation evidence retained in this task.

## Acceptance Criteria

- [x] Source labels are removed from option text before Exam.net PDF rendering.
- [x] Correct-answer text uses the same normalized option text as the rendered
  alternatives.
- [x] Duplicate option text is still detected after label stripping and remains
  fail-closed.
- [x] The incident class no longer blocks PDF generation solely because
  DigiExam source options include `A.`, `B.`, `C.`, or `D.` prefixes.
- [x] Target readiness and replay artifact tests prove PDF and QTI behavior at
  the service boundary.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Evidence

- Changed only the Exam.net PDF target item strategy to normalize source option
  text by collapsing whitespace and stripping one parseable leading label
  prefix before rendering alternatives, correct-answer text, and duplicate
  checks.
- Preserved option IDs, option order, and answer-key lookup; QTI behavior remains
  outside this target-boundary normalization.
- Kept duplicate safety fail-closed after normalization: labelled alternatives
  that both become `Alpha` emit the existing
  `alternative_answer_key_mismatch` duplicate warning.

## Validation Evidence

- Red:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py::test_examnet_pdf_document_strips_source_labelled_options_at_target_boundary tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py::test_examnet_pdf_document_blocks_duplicate_options_after_label_stripping tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py::test_digiexam_correction_replay_pdf_downloads_with_source_labelled_options`
  failed with the old policy: labelled PDF render stayed `blocked`, duplicate
  labelled options emitted `option_text_looks_labelled` instead of duplicate
  safety, and correction replay readiness had `examnet_pdf.export_enabled=false`.
- Green:
  same command passed with `3 passed in 10.76s`.
- Broader focused green:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py`
  passed with `12 passed in 12.04s`.
