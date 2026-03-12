---
id: 'task-152-optimize-task101-gpu-bundle-finalization-throughput-and-benchmark-on-hemma'
title: 'optimize task101 gpu bundle finalization throughput and benchmark on hemma'
type: 'task'
status: 'in_progress'
priority: 'high'
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-148-batch-task101-pilot-bundle-finalization-and-progress-logging-on-hemma.md
  - docs/backlog/tasks/task-149-containerize-task101-pilot-bundle-batch-finalization-runtime.md
  - docs/backlog/tasks/task-150-accelerate-task101-pilot-bundle-finalization-with-gpu-backed-audio-code-encoding.md
  - docs/backlog/tasks/task-151-repair-task101-container-output-root-bind-fallback-for-hemma.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - hemma
  - gpu
  - pilot
  - training-bundle
  - throughput
  - benchmark
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Recover Task 101 pilot-bundle finalization throughput on Hemma after the first
governed GPU-backed runtime proved correct but slower than the earlier
CPU-bound host lane for bounded `128`-row batches.

## PR Scope

- Keep the governed Task 101 bundle runtime, provenance, and fail-closed GPU
  posture from `T149-T151`.
- Change the runtime shape so the GPU path can amortize tokenizer/process
  startup cost better than the current `128`-row / `chunk_size=8` default.
- Increase the Task 101 `audio_codes` chunk size substantially for the GPU
  lane.
- Reduce repeated fresh-process warmup overhead across small contiguous Task
  101 batches.
- Persist the Triton cache across governed Task 101 batch containers when the
  ROCm/flash-attn stack uses it.
- Add a committed Task 152 benchmark surface that can compare baseline and
  optimized Task 101 finalization variants on Hemma against the same selected
  pilot-bundle rows.
- Update Task 101 defaults and docs only after benchmark evidence shows the
  optimized shape is credibly faster in rows/minute.

## Non-Goals

- Do not weaken the governed GPU requirement or reintroduce silent CPU
  fallback.
- Do not broaden this slice into multi-host or Colab benchmarking.
- Do not discard resumability, per-batch progress evidence, or shard
  validation just to make the benchmark faster.
- Do not change the frozen pilot row ownership contract.

## Why This Slice Exists

Live Hemma evidence on `2026-03-12` showed:

- CPU-host batch `00012` completed in about `3m 51s` for `128` rows
- first governed GPU batch `00013` completed in about `9m 10s` for the same
  `128` rows
- `rocm-smi` showed `99-100%` GPU utilization during the slower GPU run, so
  the problem is not “GPU unused”; it is “GPU runtime shape inefficient”

The most likely causes are:

- `audio_codes_chunk_size=8` is too small to amortize GPU/tokenizer overhead
- one fresh container/process per `128` rows makes the governed tokenizer
  warmup cost dominate
- Triton/flash-attn compilation or cache warmup may be repeated because the
  current Task 101 batch runtime does not yet persist a dedicated Triton cache

## Required Implementation Shape

1. Add explicit Task 101 throughput controls for the governed GPU lane.
   - Raise the default `audio_codes_chunk_size` substantially above `8`.
   - Reduce per-container warmup frequency relative to the current
     `128`-row batch default.
1. Persist the Triton cache for the Task 101 governed batch runtime.
   - Reuse the shared bind-root helper pattern for any new cache mount.
   - Keep the in-container cache path deterministic and operator-visible in
     launch diagnostics.
1. Keep the existing Task 101 progress/report/provenance artifacts stable.
   - If container launch units change, batch-level progress evidence must stay
     truthful.
1. Add a committed benchmark surface for Hemma.
   - It must prepare a deterministic Task 101 benchmark root from selected
     existing bundle rows rather than mutating the live operator bundle.
   - It must emit machine-readable timing and rows/minute evidence for each
     tested variant.
1. Benchmark at least:
   - a baseline shape equivalent to the current GPU runtime (`128` rows,
     chunk `8`)
   - one optimized shape with larger chunk size and reduced warmup frequency
   - if Triton cache persistence is implemented independently, evidence should
     state whether it materially changed the result

## Deliverables

- [ ] Task 101 governed runtime updated so the GPU path no longer pays the old
  warmup/throughput penalty by default.
- [ ] Persistent Triton cache support for Task 101 governed batch containers.
- [ ] Committed Task 152 benchmark surface plus machine-readable benchmark
  report.
- [ ] Tests covering new runtime defaults, new cache mount behavior, and
  benchmark-root preparation logic.
- [ ] Docs updates that state the measured optimized Task 101 throughput
  posture and operator defaults.

## Acceptance Criteria

- [ ] The optimized governed Task 101 GPU path is measurably faster than the
  current `128`-row / `chunk_size=8` governed baseline on Hemma for the same
  selected benchmark rows.
- [ ] Task 101 no longer pays a fresh governed tokenizer/container warmup cost
  every `128` rows by default.
- [ ] The governed Task 101 batch runtime persists a deterministic Triton cache
  mount and records it in launch diagnostics.
- [ ] Task 101 progress artifacts, batch shard validation, and runtime
  provenance remain correct after the throughput changes.
- [ ] The runbook and current-session log describe the benchmarked Task 101
  throughput posture truthfully.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] focused pytest for Task 101 runtime, Task 101 bundle orchestration, and
  the Task 152 benchmark helper
- [ ] Hemma benchmark evidence comparing baseline and optimized variants
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Implementation Notes

- The current live resumable bundle root remains:
  `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h`
- That root should not be used as an ad hoc benchmark scratchpad; benchmark
  variants must run in separate generated output roots.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
