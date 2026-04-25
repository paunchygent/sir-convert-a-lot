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

- Keep `.codex/handoff.md` updated after each major implementation phase.
- Treat `.codex/handoff.md` as the canonical active planning pointer and
  current-session handoff.
- Treat `docs/index.md` as the generated root docs doorway.
- Treat `.codex/long-term-memory/index.md` as the session-history index for completed or compacted session context.
- Generated docs indexes are refreshed only through `pdm run docs-sync`; do not
  edit `docs/index.md` or lane `INDEX.md` files by hand.
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
  - `pdm run docs-sync`
  - `pdm run docs-validate`
  - `pdm run skills-validate`
  - `pdm run handoff-validate`
