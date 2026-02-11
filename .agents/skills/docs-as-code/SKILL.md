# docs-as-code

## Purpose

Run and maintain Sir Convert-a-Lot documentation-as-code workflow with minimal drift.

## Required Workflow

1. Create or update planning docs in `docs/backlog/` before behavior changes, following:
   `programme -> epic -> story -> task` (tasks are PR-sized and may be standalone).
2. Keep API docs (`docs/converters/`), ADRs (`docs/decisions/`), runbooks (`docs/runbooks/`),
   references (`docs/reference/`), and PDRs (`docs/pdr/`) aligned with code and intent.
3. Update `docs/backlog/current.md` and `.agents/work/session/handoff.md` after major phases.

## Canonical Commands

```bash
pdm run new-task "<title>"
pdm run new-programme "<title>"
pdm run new-epic "<title>"
pdm run new-story "<title>"
pdm run new-review "<title>"
pdm run new-doc converters/<name>.md --title "<Title>"
pdm run new-rule "<rule name>"
```

```bash
pdm run validate-tasks
pdm run validate-docs
pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing
```
