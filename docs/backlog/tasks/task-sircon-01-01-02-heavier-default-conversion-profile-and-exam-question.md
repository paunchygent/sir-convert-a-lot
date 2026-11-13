---
type: task
id: TASK-SIRCON-01-01-02
title: Heavier default conversion profile and exam-question ordering normalization
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-01-01
task_kind: story
acceptance_criteria:
- '- [ ] Default conversion path uses heavier Docling layout profile by contract.'
- '- [ ] Target PDF conversion output keeps question lines before alternatives.'
- '- [ ] Target PDF conversion output has consistent question numbering order.'
- '- [x] `scripts/sir_convert_a_lot/infrastructure/markdown_normalizer.py` stays below
  400 LoC with behavior preserved by tests.'
- '- [ ] Full quality/docs gates pass after implementation.'
- '- [ ] Hemma deploy/rebuild/lane verification pass on pushed revision.'
retired_ids:
- task-25-heavier-default-conversion-profile-and-exam-question-ordering-normalization
---
## Context

Source record: docs/backlog/tasks/task-25-heavier-default-conversion-profile-and-exam-question-ordering-normalization.md

### Objective

> Harden default conversion quality toward a heavier Docling profile and fix
> question/alternative ordering defects observed for:
> `data/conversion-inputs/Prövning i litteraturhistoria 2024.pdf`.

## Decision And Assumption Ledger

### Decision Lock

> 1. Heavier-default policy:
>    - Prefer heavier Docling layout model by default.
>    - Keep override capability explicit and deterministic through config/env.
> 1. Conversion correctness target:
>    - For the target exam PDF, question heading should precede alternatives.
>    - Numbering progression must remain monotonic and non-duplicated.
> 1. Maintainability target:
>    - `markdown_normalizer.py` remains a thin contract surface; heavy strict-mode
>      internals are split into focused modules.
>    - Normalization modules stay below 400 LoC each.
> 1. Validation path:
>    - Must include Hemma deployment cycle:
>      - commit + push,
>      - remote pull,
>      - container rebuild/restart,
>      - lane verification and target-document conversion evidence.

## Story Contract Slice

### PR Scope

> - Upgrade default Docling layout model selection to a heavier profile for better
>   reading-order fidelity.
> - Keep canonical CLI defaults aligned with quality-first conversion behavior.
> - Add targeted post-normalization correction for exam-style question blocks if
>   ordering remains inverted (alternatives before question).
> - Modularize markdown normalization internals to keep files below repository size
>   guardrails and preserve readability/maintainability.
> - Validate locally and on Hemma lanes after push/pull/rebuild/restart.
>
> Out of scope:
>
> - non-conversion product features,
> - persistence/retention changes (Task 23),
> - general runbook expansion beyond required evidence updates.

## Contract Inputs

## Plan

### Implementation and Evidence (2026-02-16, modularization slice)

> - Split strict normalization internals into focused modules:
>   - `scripts/sir_convert_a_lot/infrastructure/markdown_normalization/common.py`
>   - `scripts/sir_convert_a_lot/infrastructure/markdown_normalization/strict_reflow.py`
>   - `scripts/sir_convert_a_lot/infrastructure/markdown_normalization/strict_structure.py`
>   - `scripts/sir_convert_a_lot/infrastructure/markdown_normalization/__init__.py`
> - Kept public contract as a thin facade:
>   - `scripts/sir_convert_a_lot/infrastructure/markdown_normalizer.py`
> - Added/kept regression coverage for exam-ordering and references numbering defects:
>   - `tests/sir_convert_a_lot/test_markdown_normalizer.py`
> - Validation:
>   - `pdm run format-all`
>   - `pdm run pytest-root tests/sir_convert_a_lot/test_markdown_normalizer.py tests/sir_convert_a_lot/test_markdown_lint_normalizer.py -q`
>   - `pdm run lint-fix`
>   - `pdm run typecheck-all`
>   - `pdm run validate-tasks`
>   - `pdm run validate-docs`
>   - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Implementation Steps

## Proof

### Deliverables

> - [ ] Heavier default Docling configuration in service code.
> - [x] Regression tests for heavier-default config and exam-order normalization.
> - [x] Modularized normalization implementation with unchanged public contract.
> - [ ] Hemma lane execution evidence including target PDF output review.

## Validation

## Stop Conditions

## Lessons Learned

### Task 26 Follow-Up (2026-02-16)

> - Source-level ordering now handles primary repair path:
>   - Docling form ordering patch + structural quality-gated layout fallback in
>     backend (`task-26`) is now the primary mechanism for question/option order.
> - Strict normalization retained as safety net only:
>   - standalone-number coalescing for residual malformed prompt fragments,
>   - references section numbering reorder (section-scoped),
>   - pagination noise cleanup.
> - Strict normalization no longer primary for this defect class:
>   - exam question-before-options correction is now source-level first,
>     normalization second.

## Notes

## Plan Document Review

## Implementation Review
