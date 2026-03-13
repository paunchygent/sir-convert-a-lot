---
id: task-156-activate-first-class-mlflow-and-accelerate-tracking-for-task-101-qwen-training
title: Activate first-class MLflow and Accelerate tracking for Task 101 Qwen training
type: task
status: in_progress
priority: critical
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - https://huggingface.co/docs/accelerate/en/usage_guides/tracking
  - https://www.mlflow.org/docs/latest/ml/tracking/
  - https://www.mlflow.org/docs/latest/ml/tracking/system-metrics/
labels:
  - qwen
  - finetuning
  - tracking
  - mlflow
  - tensorboard
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the current half-wired tracker posture with a real first-class training
tracking surface for Task 101: MLflow as the canonical experiment record,
TensorBoard as the classical scalar/event view, and repo-owned metadata that
persists tracker identity into launch/status/report artifacts.

## Why This Exists

The live Task 101 analysis on `2026-03-13` confirmed:

- `Accelerator(log_with="tensorboard")` is configured,
- but the live run root exposed no TensorBoard event files,
- no MLflow run existed,
- and operators had to reconstruct curves from stdout.

That is too weak for a serious Hemma finetuning lane and leaves future
throughput work blind.

## PR Scope

- Add the required MLflow dependencies to the governed Qwen training image.
- Initialize Accelerate trackers explicitly rather than relying on the current
  partial `log_with="tensorboard"` posture alone.
- Use MLflow as the primary tracker and TensorBoard as the secondary tracker.
- Persist run params at startup, including at least:
  - model id
  - pilot bundle root
  - manifest families
  - batch size
  - learning rate
  - gradient accumulation setting
  - checkpoint cadence and retention settings
- Log core scalars during training, including at least:
  - raw training loss
  - EMA or moving-average training loss
  - current step
  - current epoch
- Enable MLflow system metrics for CPU, memory, and GPU where the runtime
  supports them, while keeping the host-level Task 116 monitor as a separate
  operational surface.
- Persist tracker metadata into Task 101 launch/status/report artifacts so the
  operator can jump from Task 101 status directly to the canonical tracker run.

## Non-Goals

- Do not make JSON status artifacts the primary metrics store.
- Do not solve resource-monitor auto-launch in this task.
- Do not change checkpoint cadence or dataloader behavior here.

## Deliverables

- [ ] Governed Qwen image includes MLflow and any required system-metrics
  support packages.
- [ ] Task 101 training initializes MLflow and TensorBoard trackers through
  Accelerate.
- [ ] Live tracker artifacts are created during a bounded Task 101 run.
- [ ] Task 101 metadata/report surfaces expose tracker ids and artifact paths.
- [ ] Focused tests cover tracker configuration and metadata persistence.

## Acceptance Criteria

- [ ] A bounded Task 101 run creates one MLflow run and one TensorBoard event
  stream while training is still in progress.
- [ ] Launch metadata records the tracker backend, run id, and artifact root.
- [ ] The canonical tracked params include the live training configuration and
  checkpoint policy.
- [ ] The canonical tracked scalars include at least raw loss, smoothed loss,
  current step, and current epoch.
- [ ] The live operator no longer has to reconstruct a classical loss curve
  only from stdout.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_qwen_training_resume.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma proof writes reviewable MLflow/TensorBoard artifacts under
  `build/verification/`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
