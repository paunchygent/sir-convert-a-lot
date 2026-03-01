---
id: task-62-fix-docx-output-regression-after-pandoc-sandbox-hardening
title: Restore docx output after pandoc sandbox hardening
type: task
status: in_progress
priority: high
created: '2026-03-01'
last_updated: '2026-03-01'
related:
  - docs/backlog/tasks/task-61-enforce-pandoc-sandbox-and-bounded-subprocess-stderr-handling.md
labels:
  - security
  - resilience
  - pandoc
  - v2
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Restore v2 DOCX output routes (`md -> docx`, `html -> docx`, `pdf -> docx`) in
production after discovering that `pandoc --sandbox` prevents Pandoc's DOCX
writer from accessing its required built-in data files.

Maintain SSRF/LFI protections by enforcing deterministic HTML resource
validation and workdir-bounded resource resolution, rather than relying on
Pandoc sandbox mode for DOCX output.

## PR Scope

- Remove `--sandbox` from Pandoc wrappers that must write DOCX artifacts:
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_html_to_docx.py`
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_markdown_to_html.py`
- Keep `--sandbox` enforced for Pandoc wrappers that do not require DOCX writer
  data files:
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_docx_to_markdown.py`
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_html_to_markdown.py`
- Add deterministic HTML resource validation for `md -> html -> docx` so that
  any external URLs / invalid local references fail closed with `422` before
  Pandoc is invoked.
- Update tests to reflect the revised security posture and to prevent
  reintroducing the DOCX writer regression.

## Deliverables

- [ ] DOCX output routes succeed again in live internet lane (`convert.hule.education`).
- [ ] SSRF/LFI is still blocked for DOCX routes via validation + workdir sandboxing.
- [ ] Tests updated for sandbox flag expectations and DOCX output behavior.

## Acceptance Criteria

- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py` passes.
- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py` passes.
- [x] `pdm run run-local-pdm typecheck-all` passes.
- [x] `pdm run run-local-pdm coverage-gate` remains >=90%.
- [ ] Live internet lane smoke:
  - `pdm run run-local-pdm convert-a-lot convert <md> --to docx --service-url https://convert.hule.education` succeeds.
  - `pdm run run-local-pdm convert-a-lot convert <pdf> --to docx --service-url https://convert.hule.education` succeeds.

## Validation Evidence

Local (laptop) validation (2026-03-01):

- Formatting:
  - `pdm run run-local-pdm format-all` (pass; "159 files left unchanged")
- Lint:
  - `pdm run run-local-pdm lint-fix` (pass; "Found 1 error (1 fixed, 0 remaining).")
- Type safety:
  - `pdm run run-local-pdm typecheck-all`
    (pass; "Success: no issues found in 157 source files")
- Coverage gate:
  - `pdm run run-local-pdm coverage-gate`
    (pass; total coverage `95.24%` with required threshold `90.0%`)
- Docs-as-code gates:
  - `pdm run validate-tasks` (pass; "Validated 87 backlog files")
  - `pdm run validate-docs` (pass; "Validated docs=109 rules=9")
- Task-targeted checks:
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py` (pass; 5 passed)
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py` (pass; 6 passed)

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
