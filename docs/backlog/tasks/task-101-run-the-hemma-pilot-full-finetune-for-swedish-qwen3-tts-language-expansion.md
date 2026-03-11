---
id: task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion
title: Run the Hemma pilot full-finetune for Swedish Qwen3-TTS language expansion
type: task
status: active
priority: high
created: '2026-03-08'
last_updated: '2026-03-11'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
  - docs/backlog/tasks/task-141-define-frozen-qwen-pilot-dataset-use-for-finetuning.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - hemma
  - pilot
  - swedish
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the first bounded Hemma pilot full-finetune for Swedish language expansion
on `Qwen/Qwen3-TTS-12Hz-1.7B-Base` from the frozen pilot-owned dataset bundle
and capture deterministic runtime and memory evidence.

## PR Scope

- Use the committed Hemma runtime from Task 100 plus the deterministic pilot
  training bundle materialized from the frozen pilot root owned by `T140`.
- Use the detached committed Task 101 runner surface:
  - `pdm run run-hemma -- pdm run task-101-pilot launch`
- Treat the generic promoted Task 103 corpus view as insufficient for this run.
  The pilot must launch only from a deterministic bundle that contains:
  - `swedish_pilot_train.prepared.jsonl`
  - `swedish_checkpoint_dev.prepared.jsonl`
  - stable per-speaker `refs/`
  - machine-readable bundle metadata describing the frozen source root
- The canonical frozen pilot ownership source is:
  - `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`
- Capture:
  - clean idle GPU baseline,
  - startup/runtime metadata,
  - successful optimizer-step evidence,
  - peak VRAM/GPU usage,
  - checkpoint/output locations,
  - failure notes if the run does not complete.
- Keep the lane focused on pilot proof, not maximal dataset hours.
- Do not launch Task 101 against ad hoc row subsets or a manually edited
  manifest. `T142` must materialize the deterministic pilot bundle first.

## Deliverables

- [ ] Hemma pilot evidence under `build/verification/`.
- [ ] Detached launch and status metadata for the pilot lane.
- [ ] Machine-readable report for memory/runtime truth.
- [ ] Linked task/runbook updates with the exact command used.

## Acceptance Criteria

- [ ] The pilot uses the `1.7B` base model, not the `0.6B` lane.
- [ ] The run reaches a real Swedish full-finetune optimizer step with `AdamW`.
- [ ] The run consumes the deterministic pilot bundle projected from the frozen
      pilot root rather than the generic promoted preprocessing root.
- [ ] The evidence records actual VRAM usage and headroom on the R9700.
- [ ] The task explicitly states whether Hemma is good enough for the bounded
  pilot and what should move to Colab H100 for scale.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
