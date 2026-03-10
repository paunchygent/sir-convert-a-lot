---
id: 'task-128-add-colab-gpu-preflight-guard-before-portable-slice-row-processing'
title: 'Add Colab GPU preflight guard before portable-slice row-processing'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-10'
last_updated: '2026-03-10'
related:
  - docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md
  - docs/backlog/tasks/task-127-add-progress-logging-for-colab-portable-slice-staging-and-localization.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - notebook
  - gpu
  - bugfix
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add a Colab notebook GPU preflight guard before portable-slice row-processing
so the notebook fails fast with a clear runtime error when CUDA is unavailable,
instead of launching Task 103 and later dying after CPU fallback.

## PR Scope

- Check `nvidia-smi` availability before row-processing starts.
- Check `torch.cuda.is_available()` and GPU device count before launching Task
  103.
- Emit a small machine-readable preflight summary when CUDA is healthy.
- Keep the notebook thin and repo-owned; do not move row-processing logic into
  notebook-specific code paths.

## Deliverables

- [x] One notebook preflight that rejects CPU-only runtimes before
      row-processing starts.
- [x] One clear error message telling the operator to switch Colab to GPU and
      rerun from bootstrap.
- [x] One completed task doc recording the guardrail.

## Acceptance Criteria

- [x] The row-processing cell fails immediately when `nvidia-smi` is missing.
- [x] The row-processing cell fails immediately when PyTorch reports CUDA as
      unavailable.
- [x] Healthy GPU runtimes print one small preflight summary before launching
      Task 103.
- [x] The notebook remains valid JSON after the patch.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
