---
id: task-178-harden-qwen-training-cli-operator-argument-parsing-and-import-safe-help-surfaces
title: Harden Qwen training CLI operator argument parsing and import-safe help surfaces
type: task
status: completed
priority: high
created: '2026-03-14'
last_updated: '2026-03-14'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-174-rebuild-the-task-101-bundle-on-the-t173-contract-and-remove-legacy-bundle-fallbacks-after-stable-throughput-proof.md
  - docs/backlog/tasks/task-175-close-the-remaining-task-101-throughput-truth-gaps-from-the-review-alignment.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - training
  - cli
  - operator
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make the canonical `qwen-train` operator surface harder to misuse by fixing the
two operator failures seen in live Hemma work:

- boolean arguments are too brittle for real operator usage and reject natural
  explicit values like `--flag false`
- `qwen-train --help` and subcommand help can fail in lightweight environments
  because the top-level CLI imports training-only modules too early

This task also tightens the training-bundle preflight error so missing manifest
families are reported with the bundle's actually available manifest set.

## PR Scope

- Harden boolean flag parsing for the canonical Qwen training CLI so operators
  can use either:
  - `--flag`
  - `--no-flag`
  - `--flag true|false`
- Keep the canonical render path unchanged for generated command tokens so the
  detached orchestrator still emits deterministic `--flag` / `--no-flag`
  surfaces.
- Move the persisted ref-input contract constants behind one lightweight module
  that does not import `numpy`, `torch`, or audio helpers at import time.
- Make `scripts/sir_convert_a_lot/cli/ml/qwen_train.py` import-safe for help
  and parser-only usage in environments that do not have the full training
  extras installed.
- Improve the missing-manifest bundle preflight so the raised error lists:
  - the missing manifest paths
  - the manifest families that actually exist under the selected bundle root

## Non-Goals

- Do not redesign the Task 101 bundle contract in this task.
- Do not change the detached training launch contract beyond safer CLI parsing
  and clearer preflight errors.
- Do not mask real bundle-layout defects; missing eval/train manifests must
  still fail closed.

## Deliverables

- [x] `qwen-train` boolean options accept explicit boolean values in addition
  to `--flag` / `--no-flag`.
- [x] `python -m scripts.sir_convert_a_lot.cli.ml.qwen_train --help` no longer
  depends on heavyweight training extras at import time.
- [x] Missing-manifest launch failures surface the available manifest families
  under the selected bundle root.

## Acceptance Criteria

- [x] The parser accepts:
  - `--data-path-proof-mode`
  - `--no-data-path-proof-mode`
  - `--data-path-proof-mode false`
- [x] Importing `scripts.sir_convert_a_lot.cli.ml.qwen_train` for parser/help
  surfaces no longer requires `numpy` through the top-level ref-input module.
- [x] A missing eval-manifest launch failure reports both the missing path and
  the manifest families that do exist in the bundle root.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_cli_flags.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
