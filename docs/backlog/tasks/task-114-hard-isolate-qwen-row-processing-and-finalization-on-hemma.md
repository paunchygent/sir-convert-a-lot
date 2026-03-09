---
id: task-114-hard-isolate-qwen-row-processing-and-finalization-on-hemma
title: Hard-isolate Qwen row-processing and finalization on Hemma
type: task
status: completed
priority: critical
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma.md
  - docs/backlog/tasks/task-110-split-qwen-preprocessing-into-disk-backed-row-processing-and-finalization.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - preprocessing
  - hemma
  - gpu
  - isolation
  - rocm
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the remaining unsafe cross-stage coupling in the Qwen Swedish
preprocessing lane so Hemma never carries row-processing GPU state into the
high-risk finalization stage.

## Why This Exists

The latest detached `T108` proof did not fail during row-processing. It reached
late finalization and produced complete `swedish_smoke_train` and
`swedish_pilot_train` outputs before the host hard-wedged while building
`swedish_scaleup_train`.

Recovered run-root evidence on Hemma shows:

- immutable run root preserved under SSD scratch
- `52` curated/prepared rows for `swedish_smoke_train`
- `52` curated/prepared rows for `swedish_pilot_train`
- incomplete temp files for the next family at the freeze point
- the active in-flight family was `swedish_scaleup_train`

This means the current `stage=all` posture is still too weak operationally:

- row-processing can use bounded concurrent GPU ASR workers
- finalization is a different GPU-heavy runtime with tokenizer/model inference
- those stages must not share one long-lived process/container lifecycle on
  Hemma

## Hard Rule

On Hemma, the canonical public-corpus preprocessing path is no longer:

- `stage=all`

It is now:

1. detached row-processing in one fresh container/process
1. detached finalization in a separate fresh container/process
1. detached reports in a separate fresh container/process when needed
1. promotion only after the earlier stages have succeeded

No canonical Hemma run may roll directly from concurrent row-processing into
finalization inside one long-lived container.

## PR Scope

- Make separate-process stage orchestration the canonical Hemma execution path.
- Treat `stage=all` as non-canonical for GPU-backed public-corpus runs on
  Hemma.
- Add an explicit committed runner that orchestrates:
  - `row-processing`
  - `finalization`
  - `reports`
  - optional `promotion`
- Ensure every stage reopens the immutable run root rather than reusing live
  in-memory runtime state.
- Ensure finalization starts from a cold GPU runtime:
  - no carried-over Whisper worker pool
  - no carried-over row-stage thread pools
  - no carried-over model handles
- Make finalization conservative by default:
  - one finalization process
  - one tokenizer runtime
  - bounded `audio_codes` chunk size
  - family selection explicit
- Add stage-level heartbeat/status updates so the exact last successful family
  and chunk are visible in `status.json`.
- Keep the run-root and promotion contract from `T110`.

## Non-Goals

- Do not revert the durable spool/run-root work.
- Do not return to host-venv preprocessing on Hemma.
- Do not add speculative parallel tokenizer/finalization workers.
- Do not let finalization share GPU runtime state with row-processing.
- Do not hide this behavior behind undocumented wrapper shell tricks.

## Expected Outcome

After this task:

- row-processing and finalization are fully isolated operationally
- a row-processing success can be followed by a clean fresh-process
  finalization rerun
- failures in finalization do not require rerunning completed row-processing
- Hemma no longer attempts the unsafe transition from multi-worker ASR into
  tokenizer finalization inside one live process

## Required Implementation Shape

### Canonical Hemma Orchestrator

Add one committed orchestration surface that:

- allocates or accepts one existing run id
- launches `row-processing` detached
- waits for and verifies row-processing completion
- launches `finalization` detached in a fresh container/process
- waits for and verifies finalization completion
- launches `reports` detached if required
- promotes only after all earlier stages are complete

### Finalization Isolation Rules

Finalization must:

- construct its own tokenizer runtime in that process only
- release all GPU memory when the process exits
- default to one family at a time
- default to one finalization process only
- persist status after every completed family
- persist status after every completed `audio_codes` chunk

### Acceptance Evidence

The first accepted live Hemma rerun after this task must prove:

- row-processing completed in one run root
- finalization resumed from spool in a separate process/container
- `swedish_smoke_train` and `swedish_pilot_train` still succeed
- the run either:
  - finishes `swedish_scaleup_train`, or
  - fails without wedging the host and leaves precise stage/chunk status

## Deliverables

- [x] One committed detached stage-orchestration runner for Hemma.
- [x] One updated Task 103/109 runtime contract that makes `stage=all`
  non-canonical on Hemma.
- [x] One live Hemma evidence bundle proving separated row-processing and
  finalization execution against the preserved `T108` run-root contract.

## Acceptance Criteria

- A committed Hemma runner exists that executes `row-processing` and
  `finalization` as separate detached stages against the same immutable run
  root.
- The canonical Hemma path no longer relies on one GPU-backed `stage=all`
  process for public-corpus preprocessing.
- Stage status persists enough detail to identify the last completed family and
  chunk without postmortem guesswork.
- A live Hemma proof shows row-processing can complete and finalization can
  start later in a fresh process/container without rerunning completed rows.
- Docs, runbooks, and task references all describe the same isolation model.

## Checklist

- [x] Add the dedicated detached stage orchestrator.
- [x] Make the Hemma public-corpus runner use the staged orchestration path.
- [x] Persist stage/family/chunk heartbeat updates to `status.json`.
- [x] Rerun the bounded `T108` proof with isolated row-processing and
  finalization.
- [x] Record exact evidence and lessons learned in the runbook and task docs.

## Execution Outcome

The isolated-stage remediation succeeded on Hemma against the preserved crashed
`T108` run root.

What was proven:

- `row-processing` did not need to be rerun
- `swedish_scaleup_train` was finalized successfully in one fresh detached
  container
- the remaining eval/control families were finalized successfully in a second
  fresh detached container
- the `reports` stage completed in a third fresh detached container
- the recovered run root was promoted into the canonical shared corpus view

Recovered run root:

- `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task108-4workers-pipeline-20260309T064950Z`

Promoted canonical view:

- `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus`

## Close-Out

`T114` is complete.

What is now true:

- Hemma no longer treats one GPU-backed `stage=all` process as the canonical
  public-corpus path
- the public command surface now points at the detached Task 114 orchestrator
- `status.json` persists row and finalization heartbeat detail
- finalization keeps one warm tokenizer runtime per process rather than
  recreating the tokenizer for every chunk
- reports-stage promotion is the only canonical promotion path
