---
trigger: always_on
rule_id: RULE-090
title: Documentation Standards
status: active
created: '2026-02-11'
updated: '2026-02-16'
owners:
  - platform
tags:
  - docs-as-code
scope: repo
---

- Keep `docs/backlog/current.md` updated after each major implementation phase.
- Treat `docs/backlog/current.md` as canonical long-term task log (not `handoff.md`).
- `docs/backlog/current.md` must follow hard H2 template and order exactly:
  - `## Context`
  - `## Worklog`
  - `## Next Actions`
- Enforce cleanup/compression invariants for `docs/backlog/current.md`:
  - keep file at or below 220 lines,
  - keep dated `Worklog` entries at or below 12,
  - compress older detail into task/reference docs while keeping key outcomes.
- New behavior requires a `programme`/`epic`/`story`/`task` document in `docs/backlog/`.
- Keep API docs, ADRs, runbooks, and CLI docs synchronized with implementation.
- Use Google-style module docstrings for discoverability in code modules.
- Run docs-as-code validations before commit:
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
