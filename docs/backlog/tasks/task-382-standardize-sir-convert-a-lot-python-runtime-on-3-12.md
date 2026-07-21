---
id: 'task-382-standardize-sir-convert-a-lot-python-runtime-on-3-12'
title: 'Standardize Sir Convert-a-Lot Python runtime on 3.12'
type: 'task'
status: 'completed'
priority: 'medium'
created: '2026-07-21'
last_updated: '2026-07-21'
approval_protocol: 'agent-planning:user-closure-gate'
approval_note: 'User approval on 2026-07-21: "Great. Now close out task 382 in sir convert. Do not use another review. The env is confirmed to work."'
related:
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
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

- [x] Python 3.12 metadata and tool pins.
- [x] PDM-resolved lockfile for the updated range.
- [x] Focused dependency and repository validation evidence.

## Acceptance Criteria

- [x] `pyproject.toml`, dependency-image defaults, and lock metadata identify
      Python 3.12 as the lower-bound runtime.
- [x] PDM resolves dependencies successfully and writes the updated lockfile.
- [x] Focused validation passes without changing unrelated work.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Evidence

- PDM 2.26.9 resolved `>=3.12,<3.14` and wrote `pdm.lock` successfully.
- `pdm install` completed under Python 3.12.12.
- The user confirmed on 2026-07-21 that the environment works and explicitly
  authorized TASK-382 closeout without another review.
- `pdm lock --check`, lint, type-check, docs validation, skills validation,
  handoff validation, and `git diff --check` passed.
- Focused non-ML suite passed: `1421 passed, 6 skipped`.
- Complete root test collection still reaches the separately governed Qwen ML
  lane, where the existing environment contains NumPy 2.5.1 while Numba
  requires NumPy 2.4 or lower. TASK-383 owns that dependency and test
  isolation; it does not block the accepted TASK-382 Python 3.12 boundary.
