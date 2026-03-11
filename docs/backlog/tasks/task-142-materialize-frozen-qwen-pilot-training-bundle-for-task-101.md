---
id: 'task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101'
title: 'Materialize frozen qwen pilot training bundle for task 101'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-11'
last_updated: '2026-03-11'
related: []
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

## Deliverables

- [ ] Repo-owned surface that materializes the frozen pilot training bundle.
- [ ] Deterministic pilot bundle metadata/report written with the materialized
      root.
- [ ] Task 101 runner updated to consume the pilot bundle root canonically.
- [ ] Tests covering row ownership, manifest family projection, and reference
      integrity.

## Acceptance Criteria

- [ ] Task 101 has one canonical pilot bundle root derived from the frozen
      pilot root and no longer points at the generic promoted corpus view.
- [ ] The materialized bundle contains only retained owned pilot rows and
      excludes all frozen conflict rows.
- [ ] `swedish_pilot_train.prepared.jsonl` and
      `swedish_checkpoint_dev.prepared.jsonl` are present and deterministic.
- [ ] Every retained manifest row points at bundle-local `audio` and
      `ref_audio` artifacts that satisfy the existing Qwen preprocessing
      contract.
- [ ] The bundle writes machine-readable metadata sufficient for detached Task
      101 launch review and future pilot reproducibility.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
