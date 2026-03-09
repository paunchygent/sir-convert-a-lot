---
id: task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma
title: Add fault-tolerant resumable Qwen training checkpoints on Hemma
type: task
status: active
priority: critical
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - checkpoints
  - resume
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Design and implement a robust fault-tolerant checkpoint and resume path for the
Qwen Hemma training lane so longer unattended runs can continue from the latest
durable training state instead of restarting from model weights only.

## Why This Exists

The bounded `T101` pilot proved that Hemma can train the `1.7B` model
successfully, but the current training checkpoint behavior is still too weak
for longer unattended runs:

- checkpoints are exported at epoch boundaries and final completion only
- optimizer state is not persisted
- trainer/runtime state is not persisted
- exact mid-run continuation is not currently possible

That is acceptable for a short pilot, but not for planned multi-hour or
overnight Hemma training windows.

## PR Scope

- Extend the Task 101 training lane to persist durable trainer-state
  checkpoints at a bounded step cadence.
- Persist at least:
  - model weights
  - optimizer state
  - accelerator/training state required for resume
  - latest durable step metadata
- Add an explicit resume surface to the detached Task 101 runner.
- Record checkpoint cadence and latest durable checkpoint in machine-readable
  status/report output.
- Keep checkpoints on SSD scratch under the Task 101 run root.
- Preserve the current detached Hemma orchestration model.

## Chosen Resume Contract

The intended implementation is exact resume from a durable trainer-state
checkpoint, not "restart from exported weights and hope for the best."

- Checkpoints must be written on a bounded step cadence during training, not
  only at epoch boundaries.
- Each durable checkpoint must persist at least:
  - model weights,
  - optimizer state,
  - scheduler state if used,
  - `accelerate` trainer/runtime state needed to resume,
  - global step, epoch, and latest durable wall-clock timestamp.
- The Task 101 run root must expose a machine-readable latest-checkpoint
  pointer, for example `latest_checkpoint.json`, so detached recovery does not
  depend on scanning directories heuristically.
- The detached Task 101 command surface must support:
  - fresh launch,
  - `resume latest` from the current run root,
  - `resume --checkpoint-path <path>` for explicit operator recovery.
- The checkpoint cadence must be frequent enough that a multi-hour Hemma run
  does not lose most of its progress on interruption; the exact cadence can be
  tuned in implementation, but the contract is step-based mid-run durability.
- Exported inference-friendly checkpoints may still exist at epoch/final
  boundaries, but they are not the canonical resume mechanism.

## Expected Evidence

- Detached Task 101 status/report output records:
  - latest durable checkpoint path,
  - latest durable step,
  - checkpoint cadence configuration,
  - whether the run started fresh or resumed.
- One live Hemma proof must intentionally interrupt a bounded run after at
  least one durable step checkpoint and then resume it from that checkpoint in
  a fresh detached launch.

## Current Status

Committed implementation now exists for:

- step-based durable trainer-state checkpoints in the patched Qwen lane,
- run-root `latest_checkpoint.json` pointer emission,
- detached Task 101 `resume latest` and `resume --checkpoint-path` surfaces,
- status/report metadata recording resume/checkpoint details,
- focused unit coverage for checkpoint metadata and detached resume plumbing.

Remaining acceptance gap:

- one live Hemma interruption-and-resume proof is still required before the
  lane is treated as operationally ready for long unattended runs.

## Non-Goals

- Do not redesign the preprocessing pipeline again.
- Do not introduce a raw-host training path.
- Do not make Colab the default solution to interrupted training.

## Deliverables

- [ ] Committed trainer-state checkpoint implementation for the Hemma Qwen lane.
- [ ] Detached Task 101 resume command/flag surface.
- [ ] Machine-readable status/report fields for latest durable checkpoint.
- [ ] One live Hemma proof that a bounded interrupted run can resume from the
  latest durable checkpoint.

## Acceptance Criteria

- [ ] Checkpoints are written more frequently than end-of-epoch only.
- [ ] A resumed run continues training from a durable checkpoint rather than
  restarting from bare model weights.
- [ ] The detached Task 101 lane records the latest durable checkpoint path and
  step count in status/report artifacts.
- [ ] One live Hemma proof demonstrates interruption plus successful resume.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
