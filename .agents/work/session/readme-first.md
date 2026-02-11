# Session Readme First

- Read `.agents/rules/000-rule-index.md` first.
- Confirm active context in `docs/backlog/current.md`.
- Enforce planning hierarchy: `programme -> epic -> story -> task` (tasks may be standalone).
- Validate before finalizing work:
  - `pdm run format-all`
  - `pdm run lint`
  - `pdm run typecheck-all`
  - `pdm run pytest-root tests`
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
