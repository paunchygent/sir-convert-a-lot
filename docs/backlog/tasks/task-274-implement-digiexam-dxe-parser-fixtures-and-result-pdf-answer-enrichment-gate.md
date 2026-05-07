---
id: task-274-implement-digiexam-dxe-parser-fixtures-and-result-pdf-answer-enrichment-gate
title: Implement DigiExam .dxe parser fixtures and result-PDF answer enrichment gate
type: task
status: completed
priority: high
created: '2026-05-07'
last_updated: '2026-05-08'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-40-digiexam-dxe-source-parser-and-answer-key-provenance.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/README.md
labels:
  - exam-migration
  - digiexam
  - dxe
  - parser
  - tests
  - answer-key-provenance
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first `.dxe`-first DigiExam parser slice: fixture-backed parsing
for the 2026-05-07 mixed-question `.dxe` exports, plus an optional
sanitized-result-PDF enrichment gate that imports only correct machine-marked
answers and discards all student-result data.

## PR Scope

- Add a small SRP-focused `.dxe` parser under the Sir Convert code surface,
  keeping module files below the repo size limit and adding Google-style module
  docstrings to new or materially changed Python modules.
- Own typed `.dxe` parser contracts under `scripts/sir_convert_a_lot/domain/`
  or a similarly narrow domain boundary that can later feed the renderer-neutral
  intermediate exam representation.
- Use Python structured JSON parsing and explicit value-object mapping; do not
  parse `.dxe` with ad hoc string matching.
- Parse fixture files:
  - `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/1772718003-test-samma-prov-i-digiexam.dxe`;
  - `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/1772718003-test-duplicate.dxe`.
- Preserve `.dxe` structure fields required by the evidence reference:
  question order, title, `bodyHTML`/`about`, type code, `maxScore`,
  alternatives, gap identifiers, `dxWordGap` spans, and observed grading-policy
  fields.
- Add optional enrichment from
  `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/graded-student-result-sanitized.pdf`
  only for correct machine-marked answers.
- Discard all incorrect selections, student free-text answers, per-student
  scores, student identity, and student-performance history from the parser
  result.
- Keep blank/student-view PDF parsing as a legacy fallback path from Task 267;
  do not make PDF output the structure source when `.dxe` is available.
- Keep Exam.net renderer syntax, QTI/native import, service/API routes, CLI
  bulk workflow, and generic Sir Convert exam IR outside Task 274.

## Deliverables

- [x] `.dxe` parser module and typed result contract.
- [x] Fixture-backed tests for both observed `.dxe` files.
- [x] Optional sanitized-result-PDF enrichment helper or adapter with tests that
  prove correct-answer-only behavior.
- [x] Typed provenance states covering `.dxe_populated_key`,
  `graded_result_pdf_correct_labels`, `manual_teacher_key` when externally
  supplied later, and `absent`.
- [x] Documentation closeout in EPIC-10, Story 40, and the evidence reference if
  implementation discovers new fixture-backed truth.

## Acceptance Criteria

- [x] Parsing `DXE-2026-05-07-structure` emits exactly 7 ordered items.
- [x] Parsed item type sequence is `0, 1, 1, 2, 2, 2, 3`, mapped to typed domain
  item types without losing the original DigiExam code.
- [x] Parsed max-score sequence is `5, 2, 2, 2, 4, 6, 3`.
- [x] The parser preserves all observed alternatives for the 5 MCQ items and
  treats all observed `right:false` flags as absent answer-key provenance.
- [x] The parser preserves gap-fill `dxWordGap` structure and empty
  `validations` arrays as absent accepted-answer provenance.
- [x] Duplicate `.dxe` fixture parsing proves the same schema/content shape while
  allowing checksum/timestamp metadata differences.
- [x] Result-PDF enrichment captures only labels that prove correct alternatives
  or correct gap values and never retains `(Fel svar)` as migrated data.
- [x] Result-PDF enrichment fails closed when a correct alternative label binds
  to zero or multiple `.dxe` alternatives.
- [x] Result-PDF gap enrichment fails closed unless result values bind by count
  and order to observed `.dxe` gap identifiers.
- [x] Result-PDF enrichment does not retain student free-text answers, awarded
  points, or student identity fields.
- [x] Unsupported `.dxe` item types and malformed required sections fail closed
  with typed warnings/status.
- [x] Output remains renderer-neutral; no Exam.net import/rendering behavior is
  introduced.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
- [x] `pdm run coverage-gate`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

Validation evidence on 2026-05-07:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
  (`23 passed` after changes-requested follow-up)
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all` (`Success: no issues found in 591 source files`)
- `pdm run coverage-gate` was attempted and failed outside Task 274 scope:
  Task 274 focused tests passed inside the run, total coverage reached `95.47%`,
  but the command exited non-zero because of 9 Qwen checkpoint/training
  free-space failures and 1 pre-existing Task72 parallel-resume conflict.
  This failed attempt is superseded by the 2026-05-08 passing closeout below.
- Changes-requested follow-up on 2026-05-07 fixed the parser review blockers:
  duplicate and unmatched result-PDF MCQ labels now fail closed with blocking
  `unsupported_structure` warnings; result-PDF gap answers now require
  count/order binding to `.dxe` gap GUIDs; and result-PDF answer extraction uses
  an explicit sanitized student-block delimiter instead of the fixture identity
  literal.
- `pdm run docs-sync`
- `pdm run docs-validate` (`Validated 339 backlog files`; `Validated docs=393 rules=11`)
- `pdm run skills-validate` (`skills-validate: ok`)
- `pdm run handoff-validate` (`handoff-validate: ok`)
- `git diff --check`

Closeout evidence on 2026-05-08:

- Review decision changed to `accepted` after the stale generated-index finding
  was remediated.
- `pdm run docs-sync` regenerated `docs/backlog/INDEX.md`,
  `docs/reference/INDEX.md`, `docs/runbooks/INDEX.md`, and `docs/index.md`.
- `pdm run docs-validate` passed (`Validated 339 backlog files`;
  `Validated docs=393 rules=11`).
- `pdm run coverage-gate` passed (`1097 passed, 5 skipped`; total coverage
  `95.55%`).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
