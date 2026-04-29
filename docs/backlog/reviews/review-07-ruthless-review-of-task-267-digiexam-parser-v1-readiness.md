---
id: review-07-ruthless-review-of-task-267-digiexam-parser-v1-readiness
title: Ruthless review of Task 267 DigiExam parser v1 readiness
type: review
status: completed
priority: high
created: '2026-04-25'
last_updated: '2026-04-26'
related:
  - docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md
  - docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
  - inputs/examples/digiexam-exports/README.md
labels:
  - review
  - task-267
  - exam-migration
  - digiexam
  - parser
  - confidence
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Reviewed as a planning and readiness review for
  `docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md`.
- Governing authority:
  - `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`
  - `docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md`
  - `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`
  - `inputs/examples/digiexam-exports/README.md`
- Public surfaces under review:
  - Proposed DigiExam PDF parser v1 implementation authority.
  - Proposed parser result/confidence contract.
  - Proposed fixture-backed tests for the two checked-in DigiExam PDFs.
- Compatibility posture:
  - New conversion-parser lane under EPIC-10. It should be additive to current
    conversion surfaces and must not silently expand the v1/v2 PDF-to-Markdown
    service contracts, renderer behavior, or bulk migration workflow.
- Evidence gathered:
  - Current repo contains the two referenced PDFs under
    `inputs/examples/digiexam-exports/`.
  - Current PDF extraction stack includes
    `scripts/sir_convert_a_lot/infrastructure/pymupdf_backend.py`, built around
    PyMuPDF4LLM/PyMuPDF conversion.
  - A local `pdftotext -layout` probe reproduced Poppler
    `Adobe-Identity-H` warnings while still extracting Swedish text and the
    observed item headers.

## Findings

### Re-review Findings 2026-04-26

1. `high` - Multiple-choice prompt and option segmentation is corrupted while
   the parser still reports `renderer_ready`.

   - Evidence:
     `scripts/sir_convert_a_lot/domain/digiexam_parser.py` lines 291-304
     treats the first non-empty line after a multiple-choice header as prompt
     and every later line as an option. The real chemistry fixture has a
     two-line prompt for `Joner`, so the parser returns `stämmer?` as an option
     while still reporting `status == success` and `renderer_ready == true`.
     The same parser also leaves multiple-choice options inside
     `prompt_lines`, because lines 306-325 only remove matching structures, not
     multiple-choice options.
   - Why it matters:
     Task 267's typed contract separates prompt text from options. Downstream
     intermediate representation or renderer work would receive a success
     result with a prompt fragment as an option, and with duplicated option text
     in the prompt body. That violates the confidence gate: corrupted item
     structure is being marked renderer-ready.
   - Required fix:
     Parse multiple-choice blocks with an explicit prompt/options boundary that
     handles multi-line prompts. For the tracked fixtures, update the chemistry
     baseline and tests to assert exact `prompt_lines` and exact `options` for
     every multiple-choice item, including `Joner`. If a boundary cannot be
     established deterministically, block the parse with
     `unsupported_structure` instead of returning `renderer_ready == true`.
   - Proof requirement:
     Add assertions for exact multiple-choice prompt/options separation in
     `tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py`, then run
     `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
     plus `pdm run typecheck-all`.

1. `high` - A page-boundary option leaks into the following open-ended item.

   - Evidence:
     `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`
     line 101 records that `Grundämnen` has option text crossing a page
     boundary. The current parser splits a new block as soon as it sees a known
     header in `_split_blocks` at
     `scripts/sir_convert_a_lot/domain/digiexam_parser.py` lines 193-198, so
     the extracted `vatten` option that follows `Atomen` becomes the first
     `prompt_lines` entry for `Atomen`. The focused test only asserts headers,
     counts, types, and point markers, so this corruption is untested.
   - Why it matters:
     This is the exact cross-page failure mode the reference calls out. A
     renderer-ready parser result now contains the wrong source text in the
     wrong item, which breaks teacher traceability and would produce a bad
     migration artifact downstream.
   - Required fix:
     Handle the `Grundämnen` page-boundary option explicitly in the parser
     rules or mark that item/block as unsupported until a deterministic
     boundary rule exists. Extend fixture tests to assert that `Grundämnen`
     contains all expected options and `Atomen.prompt_lines` starts with the
     atom prompt, not `vatten`.
   - Proof requirement:
     Add the page-boundary option assertions and rerun
     `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`.

1. `medium` - Task 267's docs closeout expands renderer target semantics that
   are explicitly out of scope.

   - Evidence:
     Task 267 lines 51-52 keep Exam.net rendering outside this task, and
     EPIC-10 lines 105-107 say Story 38/Task 267 do not approve renderer or
     bulk workflow changes. The reference update nevertheless adds a
     production-style `Match answers` renderer schema, scoring rule, examples,
     and import validation at
     `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`
     lines 304-397, and adds `Match answers` to the bottom-line production
     renderer target at line 474.
   - Why it matters:
     This silently moves renderer target decisions into a parser task. It also
     looks like a promoted Exam.net import contract for matching even though
     the parser work only proves absence of answer keys in the DigiExam source
     PDFs and does not perform Exam.net matching import validation.
   - Required fix:
     Remove the new renderer schema from Task 267 closeout, or move it behind a
     new governed renderer/Exam.net-ingestion decision task with empirical
     import evidence. The parser reference may keep the observed matching
     source structure and the "do not synthesize matches" rule.
   - Proof requirement:
     After docs correction, run `pdm run docs-sync`, `pdm run docs-validate`,
     `pdm run skills-validate`, `pdm run handoff-validate`, and
     `git diff --check`.

### Initial Planning Findings 2026-04-25

1. `blocker` - The chemistry fixture acceptance target is not deterministic.

   - Evidence:
     `docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md`
     lines 49-54 require baseline assertions, but only give a numeric target
     for the ecology sample: 15 open-ended items. For the chemistry sample they
     only say it includes multiple-choice, matching, and open-ended items.
     Line 72 then requires item counts and type breakdowns to match the
     research baseline, while
     `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`
     lines 36-40 also only record the chemistry sample as "mixed item types"
     without exact counts or item identities.
   - Why it matters:
     The implementer can satisfy the task with any chemistry parser that finds
     at least one multiple-choice, one matching, and one open-ended item. That
     leaves item-boundary regressions invisible, especially around titled
     questions such as `Materia`, `Grundämnen`, `Atomen`, `Joner`, and
     `Para ihop`, where the parser cannot rely only on `Fråga N` anchors.
   - Required fix:
     Amend Task 267, Story 38, or the reference baseline with exact chemistry
     fixture expectations before implementation starts: total item count,
     ordered item identifiers/titles, per-type counts, which items carry
     `Max poäng : N`, which items have absent answer-key provenance, and the
     expected matching blank-row evidence.
   - Proof requirement:
     Add fixture tests that assert the exact ordered chemistry item list and
     per-type breakdown, then run
     `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
     plus the repo docs gates.

1. `high` - The confidence "gate" is specified as warnings, not an enforceable
   contract boundary.

   - Evidence:
     Task 267 lines 55-56 require a fail-closed confidence gate, but lines
     76-78 accept either a blocking warning or fail-closed behavior without
     defining the typed state that prevents downstream renderer-ready use. The
     deliverables at lines 64-65 mention warning details, but do not require a
     `parse_status`, `renderer_ready`, `blocking_warnings`, or equivalent
     machine-checkable invariant.
   - Why it matters:
     A parser can emit warnings while still returning a normal item stream that
     a renderer or intermediate representation later consumes. That preserves
     the exact failure class EPIC-10 is trying to avoid: unknown or lossy source
     shapes becoming migration output by accident.
   - Required fix:
     Define the parser v1 confidence contract explicitly in the task: success
     must be distinguishable from degraded and blocked parses by typed enum or
     value objects; blocked parses must make renderer-ready output unavailable
     or explicitly false; warning classes must identify unknown shape, lossy
     Swedish extraction, missing anchors, unsupported structures, and missing
     answer-key provenance separately.
   - Proof requirement:
     Add tests for high-confidence parses, lossy Swedish extraction, missing
     anchors, and unknown structures that assert blocked cases cannot be
     consumed as renderer-ready output.

1. `medium` - Implementation ownership and test paths are too vague for the
   repo's DDD/SRP boundary rules.

   - Evidence:
     Task 267 lines 33-37 say "under the Sir Convert code surface" and "use the
     existing PDF extraction stack where available", but they do not name the
     owned module paths, the layer split between domain result contracts and
     infrastructure extraction, or the focused test file. The current repo has
     `scripts/sir_convert_a_lot/domain/`,
     `scripts/sir_convert_a_lot/infrastructure/`, and existing PyMuPDF/PDF
     conversion infrastructure, so there is enough local topology to be
     specific.
   - Why it matters:
     A proposed task this broad can produce a catch-all parser module or reach
     through conversion-service internals. It also makes review harder because
     nobody knows whether the accepted shape is a pure domain parser, an
     infrastructure PDF-text adapter, a CLI helper, or a service-route
     extension.
   - Required fix:
     Amend the PR scope with intended paths and boundaries, for example a pure
     domain contract/parser module under `scripts/sir_convert_a_lot/domain/`, a
     small extraction adapter under `scripts/sir_convert_a_lot/infrastructure/`
     only if needed, and focused tests under `tests/sir_convert_a_lot/`. State
     explicitly that HTTP/API, CLI bulk workflow, renderer, and service-route
     integration remain out of scope for Task 267.
   - Proof requirement:
     Reviewers should be able to map each new module to one responsibility and
     run the focused test file without invoking unrelated service routes.

1. `medium` - Closeout gates omit the repo's backend quality proof.

   - Evidence:
     Task 267 line 81 requires focused parser tests and "repo docs gates", but
     it does not require the backend gates named by AGENTS.md for Python
     changes: `pdm run format-all`, `pdm run lint-fix`,
     `pdm run typecheck-all`, focused `pdm run pytest-root ...`, and
     `pdm run coverage-gate` where conversion-core coverage applies.
   - Why it matters:
     This task will add production Python code and typed contracts. Docs-only
     gates plus focused tests are not enough to catch typing shortcuts, lint
     drift, or unintended conversion-core regressions.
   - Required fix:
     Add a `Validation` section with exact required commands:
     `pdm run format-all`, `pdm run lint-fix`, `pdm run typecheck-all`,
     `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`,
     `pdm run docs-sync`, `pdm run docs-validate`,
     `pdm run skills-validate`, `pdm run handoff-validate`, `git diff --check`,
     and either `pdm run coverage-gate` or an explicit reason it is not
     conversion-core-applicable.
   - Proof requirement:
     Record the command outputs in the task closeout before moving the task to
     completed.

## Decision

changes_requested

## Response

The 2026-04-26 implementation resolves the original planning blockers around
baseline determinism, typed confidence state, ownership paths, and validation
commands. It is still not approval-ready because the returned parser result can
mark corrupted chemistry prompt/option structure as renderer-ready, and the
docs closeout widens renderer target semantics outside Task 267.

## Follow-up Actions

1. Fix multiple-choice prompt/option segmentation and assert exact
   prompt/options for all chemistry multiple-choice items.
1. Fix or block the `Grundämnen`/`Atomen` page-boundary option leakage.
1. Remove or re-govern the `Match answers` renderer schema added during Task
   267 closeout.

## Completion

Initial review completed on 2026-04-25 with changes requested. Re-review
completed on 2026-04-26 with changes still requested.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
