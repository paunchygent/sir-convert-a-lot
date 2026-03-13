---
id: task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation
title: Tune the Task 101 Qwen dataloader and device-transfer path for GPU saturation
type: task
status: proposed
priority: critical
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-118-profile-the-qwen-finetuning-dataloader-and-decide-whether-to-precompute-ref-mels.md
  - docs/backlog/tasks/task-159-correct-task-101-checkpoint-cadence-and-step-semantics-for-throughput-oriented-qwen-runs.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html
  - https://docs.pytorch.org/docs/stable/data.html
labels:
  - qwen
  - finetuning
  - dataloader
  - throughput
  - gpu
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Tune the Task 101 dataloader and host-to-device transfer path so the GPU is
fed continuously instead of waiting on synchronous host-side preparation.

## Why This Exists

The current live code still:

- loads reference audio through `librosa` in `__getitem__`
- computes `ref_mel` in `__getitem__`
- and constructs a `DataLoader` without explicit workers, prefetch, or
  persistent-worker tuning

while the live `2026-03-13` monitor measured a GPU-busy median of only `5%`.

## PR Scope

- Add the canonical dataloader tuning knobs required for real GPU training:
  - `num_workers`
  - `pin_memory`
  - `persistent_workers`
  - `prefetch_factor`
- Add non-blocking host-to-device tensor transfer where the runtime permits it.
- Benchmark a bounded Hemma sweep to identify one evidence-backed default for
  the R9700 Task 101 lane.
- Persist the chosen tuning values into Task 101 launch metadata and trackers.
- Keep the dataset contract backward-compatible for existing bundles.

## Non-Goals

- Do not yet expand the pilot-bundle contract to persisted `ref_mel` artifacts.
- Do not change learning rate or other optimizer hyperparameters here.
- Do not treat MIOpen warnings as the primary cause until the input pipeline is
  no longer obviously starved.

## Deliverables

- [ ] Task 101 exposes tuned dataloader and transfer controls.
- [ ] One bounded Hemma tuning sweep records candidate settings and selects a
  canonical default.
- [ ] Launch metadata and trackers record the selected dataloader posture.
- [ ] Focused tests cover the new configuration surface.

## Acceptance Criteria

- [ ] The live Task 101 lane no longer relies on implicit synchronous
  dataloader defaults alone.
- [ ] One evidence-backed Hemma default is documented for the saturation story.
- [ ] A bounded Hemma verification run shows materially better throughput and
  GPU-busy behavior than the `2026-03-13` baseline, even if the full
  `>= 90%` gate still depends on follow-on tasks.
- [ ] The tuned path does not break resume compatibility or bundle-path
  assumptions.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_qwen_training_resume.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma evidence records the selected dataloader defaults and the
  resulting resource summary.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
