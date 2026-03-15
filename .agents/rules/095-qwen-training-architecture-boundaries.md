---
trigger: always_on
rule_id: RULE-095
title: Qwen Training Architecture Boundaries
status: active
created: '2026-03-15'
updated: '2026-03-15'
owners:
  - platform
tags:
  - architecture
  - qwen
  - ml
scope: repo
---

- Hot-path Qwen training and control-plane modules must stay at or below `400`
  lines of code. This stricter cap applies to:
  - `scripts/sir_convert_a_lot/cli/ml/qwen_train.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/control_plane/**`
  - `scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/**`
  - `scripts/sir_convert_a_lot/ml/qwen/training/reporting/**`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz*.py`
- CLI entrypoints are composition roots only:
  - parse args
  - dispatch commands
  - return exit codes
    They must not own domain validation, path policy, bundle integrity checks, or
    detached runtime orchestration logic.
- Detached runtime responsibilities must stay split:
  - ids and snapshots
  - path/containerization helpers
  - Docker command building
  - launch service
  - inspection service
  - artifact freshness filtering
  - stop service
- Reporting responsibilities must stay split:
  - config
  - live status writing
  - status payload construction
  - report building
  - failure projection
  - step semantics
  - artifact I/O
  - runtime version helpers
- Patched training runtime responsibilities must stay split:
  - resume/runtime bootstrap
  - one optimizer-step execution window
  - phase transitions and checkpoint/eval/stop control
  - loss-observer draining and tracking emission
  - terminal summary projection
- Keep code DRY and SOLID:
  - no duplicated bundle/path policy across CLI use cases
  - no duplicated artifact-writing helpers across metadata/reporting
  - no repeated optimizer-boundary or forensic assembly logic across runtime modules
- Do not add compatibility wrappers, deprecated alias modules, or pass-through
  shim layers to preserve old internal imports. Update imports in one pass.
- Tests must follow the same module boundaries. Do not keep enlarging broad
  test files once a focused module exists.
