---
id: task-275-implement-digiexam-intermediate-exam-representation-and-manifest-schema-contract
title: Implement DigiExam intermediate exam representation and manifest schema contract
type: task
status: completed
priority: high
created: '2026-05-08'
last_updated: '2026-05-08'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md
  - docs/backlog/tasks/task-274-implement-digiexam-dxe-parser-fixtures-and-result-pdf-answer-enrichment-gate.md
labels:
  - exam-migration
  - digiexam
  - intermediate-representation
  - manifest
  - tests
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first DigiExam intermediate exam representation and manifest
schema contract. The slice translates completed parser outputs into a
renderer-neutral model that later Exam.net renderer, parity report, and bulk
workflow stories can consume without re-reading parser-specific fields.

## PR Scope

- Add a small domain module for the versioned DigiExam IR contract.
- Add a narrow builder that maps `DigiExamParseResult` into the IR and manifest
  summary.
- Preserve structure, provenance, warnings, parser status, and manual follow-up
  semantics from Task 267 and Task 274 outputs.
- Cover the current real fixture family:
  - `.dxe` mixed-question fixture without answer enrichment;
  - `.dxe` mixed-question fixture enriched from sanitized graded-result PDF;
  - legacy chemistry PDF fallback fixture with matching structure.
- Keep the module files below repo size limits and add Google-style module
  docstrings to new Python modules.
- Do not implement an Exam.net renderer, QTI/native import, service/API routes,
  CLI bulk workflow, PDF layout policy, or answer synthesis.

## Deliverables

- [x] Versioned DigiExam IR value objects.
- [x] Versioned DigiExam IR manifest summary value objects.
- [x] Parser-output-to-IR builder.
- [x] Fixture-backed tests proving the mapped real-data behavior.
- [x] Converter contract documentation for the IR and manifest schema.
- [x] EPIC-10 and handoff updates that keep the next renderer/import decisions
  separate from this task.

## Acceptance Criteria

- [x] `.dxe` parse output maps to an IR with exactly 7 ordered items and the
  observed type sequence `0, 1, 1, 2, 2, 2, 3` preserved as source metadata.
- [x] The IR item stream preserves titles, prompt HTML/text, max scores,
  ordered alternatives, gap GUIDs, matching structures, source spans, warnings,
  and grading-policy metadata where present.
- [x] The IR stores answer-key provenance separately from item structure and
  carries correct MCQ IDs and gap GUID/value answers only when parser evidence
  supplied them.
- [x] Graded-result PDF enrichment serializes only correct machine-marked answer
  evidence and excludes incorrect selections, student free-text answers, earned
  scores, identity markers, and student-performance history from the IR and
  manifest.
- [x] The IR creates manual follow-up records for open-ended manual marking and
  missing machine-answer keys without inventing answers.
- [x] Blocked parser results remain blocked in the manifest and set
  `renderer_ready=false`.
- [x] The manifest summary is deterministic and includes schema version, source
  metadata, parse status, renderer readiness, item count, warning count, and
  manual-follow-up count.
- [x] The manifest includes ordered item summaries with item id, sequence,
  title, item type, answer-key provenance, and manual-follow-up flag.
- [x] Tests prove no Exam.net renderer syntax or target-specific labels are
  required for the IR contract.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
- [x] `pdm run coverage-gate`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

Validation evidence on 2026-05-08:

- `pdm run format-all`
- `pdm run lint-fix` (`All checks passed!`; stale generated index fixed later
  with `docs-sync`)
- `pdm run typecheck-all` (`Success: no issues found in 593 source files`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
  (`28 passed` after review remediation)
- Review remediation: `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py -q`
  (`5 passed`) proves graded-result PDF negative-data serialization and
  manifest item-summary shape.
- `pdm run coverage-gate` (`1102 passed, 5 skipped`; total coverage `95.55%`)
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
