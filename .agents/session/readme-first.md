# Session Readme First

- Start with `.agents/rules/000-rule-index.md`.

- Review `.agents/session/readme-first.md` and `.agents/session/handoff.md`.

- Confirm planning hierarchy in `docs/backlog/`: `programme -> epic -> story -> task` (tasks may be standalone).

- For active conversion work, start from:

  - `docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md`
  - `docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `docs/decisions/0002-multi-format-service-api-v2.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`

- Confirm active context in `docs/backlog/current.md`.

- Enforce planning hierarchy: `programme -> epic -> story -> task` (tasks may be standalone).

- Validate before finalizing work:

  - `pdm run format-all`
  - `pdm run lint`
  - `pdm run typecheck-all`
  - `pdm run pytest-root tests`
  - `pdm run validate-tasks`
  - `pdm run validate-docs`

- Mandatory end-of-session close-out:

  - Update `.agents/session/handoff.md` with:
    - what was done in the current session,
    - validation evidence,
    - explicit next-session goals.
  - Archive completed session summary into `docs/backlog/current.md` (long-term memory index) before pruning `handoff.md`.
  - Synchronize statuses and checkboxes in strict order:
    - task status terminal before task checkbox is checked in epic/story tracking,
    - all task statuses terminal before story status/checkbox terminalization,
    - all story statuses terminal before epic status/checkbox terminalization.
