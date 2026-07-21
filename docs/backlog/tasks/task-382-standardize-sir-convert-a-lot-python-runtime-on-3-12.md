---
id: 'task-382-standardize-sir-convert-a-lot-python-runtime-on-3-12'
title: 'Standardize Sir Convert-a-Lot Python runtime on 3.12'
type: 'task'
status: 'in_progress'
priority: 'medium'
created: '2026-07-21'
last_updated: '2026-07-21'
related: []
labels: []
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make Python 3.12 the lower-bound runtime for the main Sir Convert-a-Lot
project, keep the repository's Python tool and dependency-image pins aligned,
and let PDM resolve the dependency lock under that target.

## PR Scope

- Update the main project metadata, Python tool configuration, and default
  service dependency-image inputs from Python 3.11 to Python 3.12.
- Regenerate `pdm.lock` through PDM for the resulting Python range.
- Do not change independently governed sidecar runtime boundaries.

## Deliverables

- [ ] Python 3.12 metadata and tool pins.
- [ ] PDM-resolved lockfile for the updated range.
- [ ] Focused dependency and repository validation evidence.

## Acceptance Criteria

- [ ] `pyproject.toml`, dependency-image defaults, and lock metadata identify
  Python 3.12 as the lower-bound runtime.
- [ ] PDM resolves dependencies successfully and writes the updated lockfile.
- [ ] Focused validation passes without changing unrelated work.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Evidence

- PDM 2.26.9 resolved `>=3.12,<3.14` and wrote `pdm.lock` successfully.
- `pdm install` completed under Python 3.12.12.
- `pdm lock --check`, lint, type-check, docs validation, skills validation,
  handoff validation, and `git diff --check` passed.
- Focused non-ML suite passed: `1421 passed, 6 skipped`.
- The complete `pdm run test` collection remains blocked in the separately
  governed Qwen ML lane because the existing environment contains NumPy 2.5.1
  while Numba requires NumPy 2.4 or lower. This is retained as a validation
  blocker rather than hidden or bypassed.
