---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-04-16'
---

## Purpose

Keep only volatile Sir Convert-a-Lot agent state, blockers, validation evidence,
and next actions. Move durable session history to
`.codex/long-term-memory/entries/` and governed doctrine to docs, rules,
runbooks, or skills.

## Current State

- `TASK-0046` compacted this handoff, moved durable March 2026 history into
  long-term memory, and added the real `pdm run handoff-validate` command
  surface.
- `TASK-0043` completed the direct governance cutover from `.agents/` paths to
  `.codex/` paths. Do not recreate compatibility shims.
- `TASK-0045` added the shared command grammar now available in this repo:
  `pdm run docs-validate` and `pdm run skills-validate`.
- Generated repomix packages belong under ignored `.codex/repomix_packages/`;
  do not track generated XML packages.

## Active Pointers

- Active planning log: `docs/backlog/current.md`.
- Active Qwen Task 101 ledger:
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Qwen experiment governance:
  `.codex/rules/096-qwen-experiment-governance.md`.
- Hemma/Qwen runbook:
  `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`.
- Durable session-history index:
  `.codex/long-term-memory/index.md`.

## Durable Memory

- TASK-0043 governance cutover memory:
  `.codex/long-term-memory/entries/session-2026-04-16-task-0043.md`.
- March 2026 service, local runtime, service image, and Qwen operator
  history compacted from the former long handoff:
  `.codex/long-term-memory/entries/session-2026-03-25-service-and-qwen-operator-history.md`.

## Next Actions

1. Commit TASK-0046 changes in Sir Convert-a-Lot and skill-repository when the
   user asks for the closeout commit.
1. Before any future Hemma Qwen run, use:
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
   and
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`.

## Validation

- `pdm run ruff format scripts/docs_as_code/validate_handoff.py`: passed
- `pdm run ruff check scripts/docs_as_code/validate_handoff.py`: passed
- `pdm run handoff-validate`: passed
- `pdm run docs-validate`: passed
- `pdm run skills-validate`: passed
- `git diff --check`: passed
- Skill-repository closeout also passed:
  `pdm run docs-sync`, `pdm run docs-validate`, and `git diff --check`.

## Stop Conditions

- Stop before deleting durable Qwen, service, or Hemma evidence that is not
  already preserved in governed docs or long-term memory.
- Stop before changing service runtime behavior, Hemma deployment semantics,
  generated artifact retention, or Qwen experiment interpretation.
