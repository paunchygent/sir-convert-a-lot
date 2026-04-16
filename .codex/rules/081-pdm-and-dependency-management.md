---
trigger: always_on
rule_id: RULE-081
title: PDM and Dependency Management
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - pdm
  - dependencies
scope: repo
---

- Use PDM for all Python dependency and script execution.
- Run PDM commands from repository root.
- Add scripts in `[tool.pdm.scripts]` instead of ad hoc module invocations when workflow is repeatable.
- Keep lockfile in sync with dependency changes (`pdm install` / `pdm lock`).
- Prefer wrapper scripts for environment-sensitive command context:
  - local: `pdm run run-local-pdm ...`
  - remote: `pdm run run-hemma -- ...`
