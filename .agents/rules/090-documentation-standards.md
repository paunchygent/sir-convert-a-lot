---
trigger: always_on
rule_id: RULE-090
title: Documentation Standards
status: active
created: '2026-02-11'
updated: '2026-02-28'
owners:
  - platform
tags:
  - docs-as-code
scope: repo
---

- Keep `docs/backlog/current.md` updated after each major implementation phase.
- Treat `docs/backlog/current.md` as canonical long-term task log (not `handoff.md`).
- Treat `docs/backlog/current.md` as the long-term memory index for completed sessions.
- `docs/backlog/current.md` must follow hard H2 template and order exactly:
  - `## Context`
  - `## Worklog`
  - `## Next Actions`
- Enforce cleanup/compression invariants for `docs/backlog/current.md`:
  - keep file at or below 220 lines,
  - keep dated `Worklog` entries at or below 12,
  - compress older detail into task/reference docs while keeping key outcomes.
- Session handoff cadence is mandatory:
  - each session must update `.agents/session/handoff.md` with current-session work, validation evidence, and next-session goals,
  - before clearing/pruning `handoff.md`, archive the completed session summary into `docs/backlog/current.md`,
  - archived session entries in `current.md` must include concrete date markers and links to changed story/task/epic docs.
- Status/checkbox synchronization invariants are mandatory:
  - preferred lifecycle is `proposed -> in_progress -> completed` (`done` is accepted as terminal compatibility status),
  - never check a task checkbox in epic/story tracking until that task file is terminal (`completed` or `done`),
  - never check a story checkbox in epic tracking until all linked tasks are terminal and the story is terminal,
  - never mark an epic terminal until all linked stories are terminal and epic checklists are complete,
  - status changes and checklist checkoffs must be updated together in the same session to prevent drift.
- New behavior requires a `programme`/`epic`/`story`/`task` document in `docs/backlog/`.
- Keep API docs, ADRs, runbooks, and CLI docs synchronized with implementation.
- Use Google-style module docstrings for discoverability in code modules.
- Run docs-as-code validations before commit:
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
