---
id: 'task-117-harden-the-qwen-hemma-training-runtime-for-graceful-stop-and-cold-start-safety'
title: 'Harden the Qwen Hemma training runtime for graceful stop and cold-start safety'
type: 'task'
status: 'in_progress'
priority: 'high'
created: '2026-03-09'
last_updated: '2026-03-11'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - runtime
  - hemma
  - hardening
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Harden the Hemma Qwen training lane so detached operator actions do not lose
avoidable progress and cold-start behavior is operationally explicit instead of
looking hung or fragile.

## Why This Exists

The current Epic 08 training lane is operationally real:

- `T100` proved the dedicated ROCm container runtime,
- `T101` proved detached pilot training,
- `T115` proved durable mid-run checkpoint and resume.

What is still too weak for longer unattended Hemma windows is the lifecycle
around that training core:

- `docker stop` currently lands as an ungraceful termination path because the
  patched training loop does not trap `SIGTERM`,
- the fallback cache copy path in Task 100 still uses synchronous `cp -a`
  loops that can be slow, opaque, and awkward to resume safely,
- a cold image build can still block a launch in a way that looks like a stall
  to the operator unless they already know a heavy BuildKit compile is coming.

These are not new architecture lanes. They are hardening gaps in the already
chosen Hemma training path.

Execution order note:

- `T142` should land first so the next canonical Task 101 pilot runs against
  the correct deterministic pilot bundle.
- `T117` then hardens the lifecycle of that corrected training lane for longer
  unattended execution.

## PR Scope

- Add graceful stop handling to the patched Qwen training loop so an intended
  detached stop can persist one last durable checkpoint before exit.
- Replace the Task 100 fallback cache sync loop with an incremental resumable
  transfer surface that is safer for large HF caches.
- Make cold image-build behavior operator-visible when a Task 100/101 launch
  will trigger a heavy `docker buildx build`.
- Keep the current detached Task 101 runtime contract, checkpoint format, and
  ROCm image family intact.
- Keep the scope on Hemma runtime hardening only.

## Non-Goals

- Do not redesign the Qwen dataloader or move mel generation into Task 103 in
  this task.
- Do not activate the Colab/H100 lane or add `Dockerfile.cuda` here.
- Do not reopen the completed durable-checkpoint contract from `T115`.
- Do not introduce a raw-host training path.
- Do not weaken the repo's BuildKit-only Docker rule.

## Chosen Implementation Shape

### Graceful Stop Path

- The patched `sft_12hz.py` loop should install explicit signal handling for:
  - `SIGTERM`
  - `SIGINT`
- The handler should request a clean stop rather than killing the process in
  the middle of a step.
- When a stop is requested, the loop should:
  - finish the current safe boundary,
  - emit one final durable trainer-state checkpoint if progress advanced beyond
    the latest saved durable step,
  - write status that makes the intentional stop visible to detached operators,
  - exit cleanly before Docker escalates to `SIGKILL`.

Operational boundary:

- this task improves stop behavior around the existing detached Task 101 run
  root contract
- it does not change dataset ownership, pilot manifest families, or the
  pilot-bundle materialization contract

### Cache Sync Hardening

- Replace the python-level `cp -a` loop in Task 100 with one incremental
  `rsync`-based transfer path.
- The copy surface should remain deterministic and wrapper-friendly.
- The operator should get explicit failure text if the sync command fails.

### Cold-Build Visibility

- If Task 100 or Task 101 is about to build the training image, the launch
  surface should emit an explicit operator-facing warning before the heavy
  BuildKit work begins.
- The warning should name:
  - the image tag,
  - the Dockerfile path,
  - that the launch may spend significant time compiling dependencies before
    container start.
- `--skip-build` remains the explicit reuse control; this task is about
  visibility, not changing the build contract.

## Ordered Execution

1. Finish the deterministic pilot-bundle bridge in `T142`.
1. Add graceful signal handling and final-checkpoint-on-stop semantics.
1. Replace fallback cache sync with one explicit incremental sync surface.
1. Add launch-time cold-build warnings to the Task 100/101 entrypoints.
1. Prove the stop/resume lifecycle on Hemma and update runbook language.

## Deliverables

- [ ] Graceful stop/checkpoint hardening in the patched Qwen training loop.
- [ ] Incremental `rsync`-based Task 100 cache sync path.
- [ ] Operator-visible cold-build warning in the Task 100/101 launch surfaces.
- [ ] Updated runbook/task docs that describe the new stop/build behavior.

## Acceptance Criteria

- [ ] An intentional Task 101 stop requests a clean training shutdown rather
  than relying entirely on Docker's default forced termination path.
- [ ] If progress advanced beyond the latest durable checkpoint, the stop path
  writes one final durable checkpoint before exit.
- [ ] Task 100 no longer uses python-wrapped `cp -a` loops for the fallback
  home-cache-to-data-disk sync path.
- [ ] Task 100/101 launch output makes a cold image build explicit before the
  blocking BuildKit compile begins.
- [ ] Tests cover:
  - graceful stop signaling semantics,
  - cache sync command construction or execution contract,
  - launch warning behavior.
- [ ] Docs and runbook language match the implemented Hemma operator behavior.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task100_qwen_finetune_runtime.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- [ ] `pdm run validate-docs`

## Notes

Current planning position after `T141`:

- dataset/input correctness now has priority through `T142`
- `T117` is the immediate next hardening slice once the Task 101 pilot bundle
  exists and the runner points at it

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
