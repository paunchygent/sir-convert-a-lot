---
id: task-26-docling-form-cluster-ordering-source-patch-with-deterministic-quality-gate-and-fallback
title: Docling form cluster ordering source patch with deterministic quality gate and fallback
type: task
status: in_progress
priority: high
created: '2026-02-16'
last_updated: '2026-02-16'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-25-heavier-default-conversion-profile-and-exam-question-ordering-normalization.md
  - docs/reference/ref-docling-form-ordering-exam-pdf-2026-02-16.md
labels:
  - docling
  - source-ordering
  - quality-gate
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Move ordering repair upstream to the Docling extraction stage for exam/form PDFs,
so conversion correctness does not depend primarily on strict markdown
post-normalization heuristics.

## PR Scope

- Add a deterministic Docling ordering patch layer in service code (no vendored
  fork) that applies geometric ordering where Docling currently uses PDF object
  index ordering for form clusters.
- Guard the patch with explicit service configuration for safe rollout and
  immediate kill-switch capability.
- Add a post-backend structural quality gate (source output, `normalize=none`)
  for exam-form ordering signals:
  - question-number continuity,
  - question-before-options sequencing.
- Add deterministic layout-model fallback execution when quality gate fails
  primary output and select the best candidate by stable scoring.
- Reassess strict MCQ normalization heuristics as safety net only; keep only
  residual behavior that is still needed after source-level fix.

Out of scope:

- API contract shape changes.
- Non-PDF converter features.
- Runtime persistence and deployment topology changes.

## Deliverables

- [x] Source-ordering patch module integrated into Docling backend path.
- [x] Structural ordering quality gate with deterministic scoring contract.
- [x] Deterministic fallback sequence for poor-quality source ordering output.
- [x] Regression tests for target exam PDF and non-regression on existing
  scientific quality fixtures.
- [x] Task 25 normalization scope update documenting retained vs retired
  heuristics.

## Acceptance Criteria

- [x] For target document class, source-level output places question prompts
  before options for Q2/Q3-class defects.
- [x] Numbering continuity for target exam output is preserved after backend
  selection + fallback policy.
- [x] Behavior is deterministic under fixed input/spec and produces stable
  artifact output across repeated runs.
- [x] Normalization is no longer the primary mechanism for question-order repair.
- [x] `format-all`, `lint-fix`, `typecheck-all`, targeted pytest, `validate-tasks`,
  and `validate-docs` pass.
- [ ] Hemma lane evidence confirms contract-compatible behavior after deploy.

## Checklist

- [x] Implementation complete
- [ ] Validation complete
- [x] Docs updated

## Implementation and Evidence (2026-02-16, local implementation slice)

- Isolation A/B (no repo edits) established minimum source patch requirements:

  - `clusters_only` did not fix ordering defects.
  - `cells_only` fixed trailing-number merges but not all option-before-question
    sequencing.
  - `cells + clusters` fixed the full defect pattern in Heron isolation runs.

- Current service default model (`docling_layout_egret_large`) still shows a
  residual Q13 numbering defect on the target PDF, so rollout requires
  quality-gated fallback, not patch-only enablement.

- Evidence artifacts:

  - `build/docling-isolated-ordering-ab-20260216T184204Z/`
  - `build/docling-isolated-ordering-egret-ab-20260216T184833Z/`

- Source-level implementation (service code):

  - Added Docling patch + quality utilities:
    - `scripts/sir_convert_a_lot/infrastructure/docling_ordering.py`
  - Added deterministic ordering fallback scoring/warning policy:
    - `scripts/sir_convert_a_lot/infrastructure/docling_ordering_fallback.py`
  - Added layout-model resolution and fallback candidate policy module:
    - `scripts/sir_convert_a_lot/infrastructure/docling_layout_models.py`
  - Added formula fallback orchestration and quality heuristics modules:
    - `scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py`
    - `scripts/sir_convert_a_lot/infrastructure/docling_formula_quality.py`
  - Integrated all policies in backend orchestration while preserving API contract:
    - `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`

- Regression coverage:

  - Existing backend behavior suite retained:
    - `tests/sir_convert_a_lot/test_docling_backend.py`
  - Added focused ordering fallback/quality-gate suite:
    - `tests/sir_convert_a_lot/test_docling_ordering_fallback.py`

- Validation (local):

  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run typecheck-all`
  - `pdm run pytest-root tests/sir_convert_a_lot/test_docling_backend.py tests/sir_convert_a_lot/test_docling_ordering_fallback.py`
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

- Remaining close-out:

  - Hemma lane deployment/rebuild verification evidence is still pending.
