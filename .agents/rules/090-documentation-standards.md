---
trigger: always_on
rule_id: RULE-090
title: Documentation Standards
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - docs-as-code
scope: repo
---

- Keep `docs/backlog/current.md` updated after each major implementation phase.
- New behavior requires a `programme`/`epic`/`story`/`task` document in `docs/backlog/`.
- Keep API docs, ADRs, runbooks, and CLI docs synchronized with implementation.
- Use Google-style module docstrings for discoverability in code modules.
- Run docs-as-code validations before commit:
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
