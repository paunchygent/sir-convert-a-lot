---
id: task-166-establish-domain-centric-directory-structure-and-shared-common-logic
title: Establish Domain-Centric Directory Structure and Shared Common Logic
type: task
status: completed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-27-transition-to-domain-centric-ml-pipeline-structure.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
labels:
  - refactor
  - architecture
  - common
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Create the physical directory structure for the domain-centric ML pipeline and
migrate shared infrastructure logic (Docker, ROCm, Storage) into a dedicated
`common` package.

## PR Scope

- Create `scripts/sir_convert_a_lot/ml/qwen/{common,preprocessing,training}/`
- Create `scripts/sir_convert_a_lot/cli/ml/`
- Migrate `task100_qwen_finetune_runtime.py` to `ml/qwen/common/runtime.py`
- Migrate `task112_hemma_storage_runtime.py` to `ml/qwen/common/storage.py`
- Extract shared models from `task103_*` and `task101_*` into `ml/qwen/common/models.py`
- Update all task-prefixed imports within these moved files.

## Deliverables

- [x] Directory structure established.
- [x] `ml/qwen/common/` package populated with infrastructure logic.
- [x] No task-prefixed filenames in `ml/qwen/common/`.

## Acceptance Criteria

- [x] `scripts/sir_convert_a_lot/ml/qwen/common/` exists and contains functional ROCm/Docker/Storage logic.
- [x] Unit tests for shared common logic pass.
- [x] Files moved in this PR do not depend on the old `devops/taskXXX` paths for their own functionality.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
