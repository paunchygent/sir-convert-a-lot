---
id: task-284-reconcile-active-surface-docs-state-before-exam-net-runtime-work
title: Reconcile active surface docs state before Exam.net runtime work
type: task
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/tasks/task-253-cut-over-sir-convert-a-lot-agents-to-thin-skill-router.md
  - docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md
  - .codex/rules/030-conversion-workflows.md
labels:
  - docs-state
  - cleanup
  - examnet
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Land the first cleanup PR as a docs-state-only reconciliation pass before more
Exam.net runtime work. The repo should stop presenting retired paths,
nonexistent facades, stale backlog pointers, or contradictory service commands
as active truth.

## PR Scope

- Replace stale `.agents` references with the active `.codex`/`AGENTS.md`
  surfaces where those references are meant to describe current repo procedure.
- Remove links that point at retired `docs/backlog/current.md` and route active
  planning references through `.codex/handoff.md`, generated indexes, or the
  owning backlog item.
- Reconcile Task 271 status, checklists, and proof wording against the retained
  review state and current OCR benchmark evidence. If the proof is still
  blocked, keep the status honest and name the exact remaining proof.
- Align `.codex/rules/030-conversion-workflows.md` with the AGENTS/README
  command policy so host service commands do not contradict wrapper-first local
  execution guidance.
- Correct docs that describe nonexistent service facades such as removed or
  uncreated `cli.py`, `client.py`, or `models.py` entrypoints.
- Keep this PR out of runtime, converter, CLI, Qwen implementation, and
  migration behavior.

## Deliverables

- [x] Stale `.agents` references are either removed or explicitly marked as
  historical.
- [x] Retired `docs/backlog/current.md` links are removed from active docs and
  backlog files.
- [x] Task 271's frontmatter status, checklist state, and evidence sections
  agree with the retained review/current proof state.
- [x] Conversion workflow command docs agree with AGENTS/README command policy.
- [x] Nonexistent facade documentation is corrected to name the real package
  and interface entrypoints.

## Acceptance Criteria

- [x] The diff contains no Python/runtime behavior changes.
- [x] `rg -n "\.agents|docs/backlog/current\.md" AGENTS.md README.md docs .codex`
  returns only intentional historical references, if any.
- [x] `rg -n "serve:sir-convert-a-lot" README.md docs .codex` no longer shows
  that command as the default active local service command when wrapper policy
  is required.
- [x] Task 271 no longer claims completion and blocked proof at the same time.
- [x] `scripts/sir_convert_a_lot/README.md` names existing current entrypoints
  rather than nonexistent facades.
- [x] Close-out validation passes: `pdm run docs-sync`,
  `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.

## Validation Evidence

- `rg -n "\.agents|docs/backlog/current\.md" AGENTS.md README.md docs .codex`
  now returns only intentional references: negative-retired `.agents` guidance,
  long-term-memory history, and this cleanup task/story.
- `rg -n "serve:sir-convert-a-lot" README.md docs .codex` no longer reports the
  command as the active local service lane; active docs either forbid it or
  mention it in historical v1/old-task context.
- `rg -n "Start with Task 284|Start Story 46 with Task 284" .codex/handoff.md`
  returns no matches after Task 284 became terminal.
- `rg -n "docker compose (up -d|logs -f) sir_convert_a_lot_prod" README.md`
  returns no matches; the root active command list uses `pdm run prod-*`
  wrappers.
- `rg -n "cli\.py|client\.py|models\.py|runtime\.py" scripts/sir_convert_a_lot/README.md docs/converters/sir_convert_a_lot.md`
  returns no matches.
- Close-out commands:
  - `pdm run docs-sync` -> refreshed generated docs indexes.
  - `pdm run docs-validate` -> Validated 363 backlog files; Validated docs=422
    rules=11.
  - `pdm run skills-validate` -> ok.
  - `pdm run handoff-validate` -> ok.
  - `git diff --check` -> clean.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
