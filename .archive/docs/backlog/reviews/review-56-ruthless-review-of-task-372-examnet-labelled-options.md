---
id: review-56-ruthless-review-of-task-372-examnet-labelled-options
title: Ruthless review of Task 372 Examnet labelled options
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-372-normalize-source-labelled-choice-options-for-examnet-pdf-replay.md
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - review
  - approved
  - task-372
  - exam-migration
  - examnet
  - pdf-renderer
  - correction-replay
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Independent ruthless review for Task 372. This reviewer did not author the
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
- `.codex/rules/090-documentation-standards.md`
- `docs/index.md`
- `docs/backlog/README.md`
- `docs/backlog/tasks/task-372-normalize-source-labelled-choice-options-for-examnet-pdf-replay.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`

Task 372 files reviewed:

- `docs/backlog/tasks/task-372-normalize-source-labelled-choice-options-for-examnet-pdf-replay.md`
- `scripts/sir_convert_a_lot/domain/examnet_pdf_item_strategies.py`
- `tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py`
- `tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py`

Public/runtime surfaces affected:

- Exam.net PDF target item rendering for DigiExam choice and multiple-response
  options.
- Exam authoring correction replay target readiness and artifact delivery for
  `correction_replay_examnet_pdf`.
- QTI package replay is included in service-boundary proof, but the production
  code change does not alter the QTI adapter.

Compatibility posture:

- Narrow behavior change at the Exam.net PDF target boundary.
- Source option IDs, source option order, effective answer-key binding, and QTI
  semantics remain on existing IR/QTI contracts.
- The previous `option_text_looks_labelled` blocker is intentionally retired
  for parseable leading source labels at the PDF target boundary.

Dirty-tree boundaries:

- Before this review artifact, the checkout already had unrelated dirty
  `docs/backlog/INDEX.md`,
  `docs/backlog/reviews/review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof.md`,
  and a formatting-only Task 372 doc diff. I did not edit, revert, normalize,
  or treat review 55 as Task 372 evidence.
- The Task 372 production and test files were already clean in the working tree
  and present in `HEAD` at `4ce447ef`.

## Checklist

- [x] Governing task and repo review rules read.
- [x] Exact Task 372 production, test, and task-doc surfaces inspected.
- [x] Public/runtime boundaries checked for PDF target behavior, correction
  replay, and QTI separation.
- [x] Focused behavioral tests and scoped quality gates rerun.
- [x] Decision recorded in this retained review artifact.

## Findings

No blocking findings.

The production change is scoped to the Exam.net PDF target strategy. The
renderer now collapses whitespace and strips one parseable leading option label
with `_target_option_text()` before building the PDF option text map
(`scripts/sir_convert_a_lot/domain/examnet_pdf_item_strategies.py:318`,
`scripts/sir_convert_a_lot/domain/examnet_pdf_item_strategies.py:334`).
Answer keys still bind through `correct_option_ids` into that option-id map
(`scripts/sir_convert_a_lot/domain/examnet_pdf_item_strategies.py:150`,
`scripts/sir_convert_a_lot/domain/examnet_pdf_item_strategies.py:198`), so
label stripping does not remap identities or reorder alternatives.

Duplicate safety remains fail-closed after normalization. If two source options
normalize to the same rendered text, `_option_text_by_id()` returns the
existing `alternative_answer_key_mismatch` warning and blocks rendering
(`scripts/sir_convert_a_lot/domain/examnet_pdf_item_strategies.py:329`).

The QTI path is not coupled to the new PDF normalizer. The QTI adapter still
builds choices from DigiExam IR alternatives and stable `choice_###`
identifiers without importing or calling the Exam.net PDF strategy
(`scripts/sir_convert_a_lot/domain/digiexam_examnet_qti_adapter.py:84`).
The Task 372 correction replay test also downloads
`correction_replay_qti_package`, proving this incident remediation did not
block the paired QTI artifact at the service boundary
(`tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py:108`).

The tests are truthful for the requested behavior. The renderer regression
exercises the real document builder and proves `A.`, `B)`, `1.`, and `3)` are
absent from rendered PDF HTML while answer-key text uses the normalized values
(`tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py:175`). The
duplicate regression proves labelled duplicates are detected only after label
stripping and remain blocked
(`tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py:197`). The
correction replay regression uses the v2 API fixtures, issues source state,
applies a manual teacher key, observes `examnet_pdf.export_enabled=true`, and
downloads the real `correction_replay_examnet_pdf` artifact before extracting
PDF text with PyMuPDF
(`tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py:30`).

Residual risk: the implementation inherits the existing empty-option policy.
A source option that normalizes to an empty string would still be dropped before
the answer-key availability/key-count checks. That edge case is not the Task
372 incident shape, but a later hardening task could make empty normalized
options emit a more explicit fail-closed warning if product evidence shows such
inputs occur.

## Follow-up Actions

No required follow-up actions block approval.

Optional later hardening: if production evidence shows source options that are
only a label token after normalization, create a separate governed task to emit
an explicit fail-closed empty-normalized-option warning instead of relying on
the existing empty-option drop behavior.

## Decision

approved

## Response

Task 372 is approved. The implementation satisfies the governed requirement:
parseable source labels are stripped only at the Exam.net PDF target boundary,
rendered alternatives and correct-answer text use the same normalized text,
duplicate normalized option text remains fail-closed, correction replay emits
downloadable `correction_replay_examnet_pdf` after a manual key correction, and
the paired QTI artifact remains available without moving QTI semantics onto the
PDF target policy.

## Completion

Decision: `approved`.

Reviewer-run evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py::test_examnet_pdf_document_strips_source_labelled_options_at_target_boundary tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py::test_examnet_pdf_document_blocks_duplicate_options_after_label_stripping tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py::test_digiexam_correction_replay_pdf_downloads_with_source_labelled_options -q`
  passed: `3 passed in 19.89s`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py -q`
  passed: `12 passed in 20.35s`.
- `pdm run ruff format --check --diff scripts/sir_convert_a_lot/domain/examnet_pdf_item_strategies.py tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py`
  passed: `3 files already formatted`.
- `pdm run ruff check scripts/sir_convert_a_lot/domain/examnet_pdf_item_strategies.py tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py`
  passed: `All checks passed!`.
- `pdm run mdformat --check docs/backlog/tasks/task-372-normalize-source-labelled-choice-options-for-examnet-pdf-replay.md`
  passed.
- `pdm run docs-validate` passed before this review artifact was added:
  `Validated 498 backlog files`; `Validated docs=574 rules=11`.
- First post-artifact `pdm run docs-validate` correctly failed because this
  new review artifact was missing required retained-review sections
  (`Checklist`, `Follow-up Actions`, and `Completion`); this artifact was then
  updated with those sections.

Worker-reported evidence considered:

- Red evidence for the three focused labelled-option regressions.
- Same three focused tests green.
- Broader focused renderer/API files green with `12 passed`.
- Scoped `ruff format --check --diff`, scoped `ruff check`, task mdformat,
  `typecheck-all`, `handoff-validate`, and `git diff --check` green.

Skipped in this review pass:

- Full `typecheck-all`, `coverage-gate`, and whole-repo mutating
  `format-all`/`lint-fix`; focused behavior and scoped quality checks were
  sufficient for this narrow review, and mutating whole-repo commands would
  risk normalizing unrelated dirty docs.
