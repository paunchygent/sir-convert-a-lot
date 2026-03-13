---
id: task-162-add-bounded-pytorch-and-rocm-profiling-surfaces-for-task-101-qwen-bottleneck-attribution
title: Add bounded PyTorch and ROCm profiling surfaces for Task 101 Qwen bottleneck attribution
type: task
status: proposed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation.md
  - docs/backlog/tasks/task-165-triage-and-remediate-miopen-workspace-warnings-in-the-task-101-rocm-qwen-training-lane.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - https://docs.pytorch.org/tutorials/recipes/recipes/profiler_recipe.html
  - https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/docs-6.3.0/how-to/using-rocprofv3.html
labels:
  - qwen
  - profiling
  - pytorch
  - rocm
  - bottlenecks
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Give the Task 101 lane one bounded, governed profiling surface for PyTorch and
ROCm so future bottleneck decisions are based on traces instead of only loss
logs and low-frequency utilization summaries.

## Why This Exists

The live Task 101 analysis could strongly infer starvation, but still could not
measure exact per-step time splits, memory-copy behavior, or whether the
repeated MIOpen warnings correspond to meaningful kernel slowdowns.

## PR Scope

- Add one bounded PyTorch profiler surface for the Task 101 runtime with a
  documented schedule and explicit trace output location.
- Add one governed ROCm profiling surface using `rocprofv3` or the canonical
  ROCm profiler toolchain already documented by AMD.
- Add explicit phase markers around at least:
  - startup
  - batch preparation
  - forward/backward
  - optimizer step
  - durable checkpoint save
- Keep the profiling surfaces bounded and opt-in so they do not become a
  permanent long-run overhead tax.

## Non-Goals

- Do not turn profiling traces into the everyday monitoring surface.
- Do not run ad hoc heredoc profiler payloads through `run-hemma --shell`.
- Do not treat profiler traces as a replacement for MLflow or the resource
  monitor.

## Deliverables

- [ ] One documented PyTorch profiler surface for Task 101.
- [ ] One documented ROCm profiler surface for Task 101.
- [ ] Bounded trace artifacts written under `build/verification/`.
- [ ] Phase markers or equivalent annotations sufficient to isolate checkpoint
  windows from steady-state training.

## Acceptance Criteria

- [ ] An operator can run one bounded Task 101 profiling command without
  inventing ad hoc shell payloads.
- [ ] The resulting traces are sufficient to answer whether time is dominated
  by data loading, host-device transfer, forward/backward, optimizer, or
  checkpoint-save windows.
- [ ] The profiling surfaces are bounded and documented enough that they can be
  reused during later MIOpen triage work.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task116_hemma_resource_monitor.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded profiler traces and operator commands are written under
  `build/verification/`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
