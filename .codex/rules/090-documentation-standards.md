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
- Treat `docs/backlog/current.md` as the canonical active task log, not as a session handoff.
- Treat `.codex/long-term-memory/index.md` as the session-history index for completed or compacted session context.
- `docs/backlog/current.md` must follow hard H2 template and order exactly:
  - `## Context`
  - `## Worklog`
  - `## Next Actions`
- Enforce cleanup/compression invariants for `docs/backlog/current.md`:
  - keep file at or below 220 lines,
  - keep dated `Worklog` entries at or below 12,
  - compress older detail into task/reference docs while keeping key outcomes.
- Session handoff cadence is mandatory:
  - each session must update `.codex/handoff.md` with current-session work, validation evidence, and next-session goals,
  - durable session history belongs under `.codex/long-term-memory/` rather than a separate session folder,
  - before clearing/pruning `handoff.md`, archive durable session history under `.codex/long-term-memory/entries/`,
  - long-term-memory entries must be indexed from `.codex/long-term-memory/index.md` and link changed story/task/epic docs when relevant.
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
  - `pdm run docs-validate`
  - `pdm run skills-validate`
  - `pdm run handoff-validate`
