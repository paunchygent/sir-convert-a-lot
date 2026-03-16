---
id: task-201-resolve-pytest-import-collision-by-renaming-duplicated-qwen-test-support-module
title: Resolve pytest import collision by renaming duplicated qwen test support module
type: task
status: completed
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/current.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
labels:
  - qwen
  - testing
  - pytest
  - quality-gate
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Eliminate the permanent pytest module-import collision caused by duplicated
`test_support.py` basenames under Qwen preprocessing and training test trees.

## PR Scope

- Rename one duplicated support module to a unique filename that is not matched
  by the test discovery pattern.
- Update all import sites and supporting docstrings/comments that reference the
  old module path.
- Preserve test helper behavior and data contracts.

## Deliverables

- [x] The training helper module has a unique non-colliding filename.
- [x] All affected imports reference the new module path.
- [x] Full test collection from repo root no longer fails on import mismatch.

## Acceptance Criteria

- [x] `pdm run run-local-pdm pytest-root tests` collects without
  `import file mismatch` for Qwen support modules.
- [x] No compatibility shim module is retained under the old duplicated name.
- [x] `pdm run run-local-pdm validate-tasks` and
  `pdm run run-local-pdm validate-docs` pass.

## Validation

- [x] `pdm run run-local-pdm format-all`
- [x] `pdm run run-local-pdm pytest-root tests`
  - collection no longer fails with `import file mismatch`
  - unrelated existing failure remains:
    `tests/sir_convert_a_lot/ml/qwen/training/test_codebook_fusion.py::test_fuse_auxiliary_codebook_embeddings_matches_manual_sum`
- [x] `pdm run run-local-pdm validate-tasks`
- [x] `pdm run run-local-pdm validate-docs`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
