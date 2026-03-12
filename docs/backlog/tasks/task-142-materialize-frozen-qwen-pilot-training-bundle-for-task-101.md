---
id: task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101
title: Materialize frozen qwen pilot training bundle for task 101
type: task
status: completed
priority: high
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
  - docs/backlog/tasks/task-141-define-frozen-qwen-pilot-dataset-use-for-finetuning.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-guide.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - pilot
  - dataset
  - training-bundle
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Materialize one deterministic Task 101 pilot training bundle from the frozen
canonical pilot root so the Hemma full-finetune lane consumes an immutable,
reviewable training input instead of a generic promoted corpus view.

## Why This Exists

`T141` established the governance rule for pilot fine-tuning, but the runtime
still lacks the concrete bridge from frozen ownership into the exact Task 101
inputs.

Right now the repo has:

- one frozen pilot ownership root,
- one detached Task 101 runner,
- one rule that the pilot may not launch from the generic promoted Task 103
  corpus view.

What is still missing is the deterministic training bundle that makes those
three things line up operationally.

## PR Scope

- Project the frozen pilot root at
  `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`
  into one Task 101-specific training bundle root.
- Materialize the canonical training/eval artifacts needed by the detached Task
  101 runner:
  - `manifests/swedish_pilot_train.prepared.jsonl`
  - `manifests/swedish_checkpoint_dev.prepared.jsonl`
  - stable per-speaker `refs/`
  - machine-readable bundle metadata describing source freeze, row counts, and
    manifest families
- Update the Task 101 runner contract so it targets the deterministic pilot
  bundle root instead of the generic promoted preprocessing root.
- Keep the bundle immutable and fail-closed:
  - every manifest row must resolve to retained owned pilot rows
  - every `ref_audio` must exist inside the bundle and remain `24 kHz`
  - no quarantined conflict row may appear in the bundle

## Non-Goals

- Do not redesign Task 103 family assignment or reopen the frozen pilot
  ownership decision from `T140`.
- Do not add ad hoc notebook-only or operator-only bundle assembly steps.
- Do not change the training hyperparameter policy in this task.
- Do not fold runtime graceful-stop hardening into this task; that remains
  `T117`.

## Chosen Implementation Shape

### Canonical Input

- The only source root is:
  - `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`
- The only pilot families materialized for Task 101 in this slice are:
  - `swedish_pilot_train`
  - `swedish_checkpoint_dev`

### Canonical Output

- Materialize one immutable pilot bundle root with:
  - `manifests/swedish_pilot_train.prepared.jsonl`
  - `manifests/swedish_checkpoint_dev.prepared.jsonl`
  - bundle-local `refs/`
  - bundle-local machine-readable metadata under `reports/`

### Bundle Metadata Contract

- The bundle metadata must record at least:
  - frozen source root path
  - retained row counts per manifest family
  - speaker count per manifest family
  - bundle generation timestamp
  - repo `HEAD`
  - explicit statement that frozen conflict rows were excluded

### Runner Contract

- The detached Task 101 runner must point at the pilot bundle root directly.
- The runner must fail closed if either required prepared manifest is missing.
- The runner must not accept the generic promoted preprocessing root as the
  canonical pilot input once this task lands.

## Ordered Execution

1. Add one repo-owned materializer surface for the Task 101 pilot bundle.
1. Emit deterministic bundle metadata and reports.
1. Update the Task 101 runner to target the new pilot bundle root contract.
1. Add focused tests for:
   - retained-row projection,
   - conflict exclusion,
   - bundle-local `ref_audio` resolution,
   - fail-closed missing-manifest behavior.
1. Update the runbook/task docs with the exact launch path.

## Deliverables

- [x] Repo-owned surface that materializes the frozen pilot training bundle.
- [x] Deterministic pilot bundle metadata/report written with the materialized
  root.
- [x] Task 101 runner updated to consume the pilot bundle root canonically.
- [x] Tests covering row ownership, manifest family projection, and reference
  integrity.

## Acceptance Criteria

- [x] Task 101 has one canonical pilot bundle root derived from the frozen
  pilot root and no longer points at the generic promoted corpus view.
- [x] The materialized bundle contains only retained owned pilot rows and
  excludes all frozen conflict rows.
- [x] `swedish_pilot_train.prepared.jsonl` and
  `swedish_checkpoint_dev.prepared.jsonl` are present and deterministic.
- [x] Every retained manifest row points at bundle-local `audio` and
  `ref_audio` artifacts that satisfy the existing Qwen preprocessing
  contract.
- [x] The bundle writes machine-readable metadata sufficient for detached Task
  101 launch review and future pilot reproducibility.

## Validation

- [x] `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py`
- [x] `pdm run python -m mypy scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Notes

Implementation order is intentional:

- `T142` must land before the next canonical Task 101 pilot launch.
- `T117` remains the next runtime-hardening follow-on after this dataset/input
  bridge exists.

## Outcome

`T142` is now implemented through one canonical repo-owned surface:

- `pdm run task-101-pilot-bundle build`

The committed bundle materializer now:

- projects the frozen pilot root into one deterministic Task 101 bundle root
- emits:
  - `manifests/swedish_pilot_train.prepared.jsonl`
  - `manifests/swedish_checkpoint_dev.prepared.jsonl`
  - stable bundle-local `refs/`
  - `reports/task101_pilot_bundle_report.json`
- retargets the detached Task 101 runner to the pilot bundle root through the
  `--pilot-bundle-root` contract
- fails closed when required train/eval manifests or bundle metadata are missing

Follow-on hardening in `T148` preserves that outer contract while changing the
internal materialization shape:

- `build` now emits a deterministic plan file plus events/status artifacts
  under `reports/`
- finalization now happens batch by batch through committed `copy`,
  `finalize-batch`, and `assemble` surfaces
- the final `manifests/*.prepared.jsonl` and
  `reports/task101_pilot_bundle_report.json` outputs remain unchanged for
  downstream Task 101 launch

The next training hardening slice is now clearly `T117`.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
