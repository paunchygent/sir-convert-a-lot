---
id: task-116-expand-rixvox-staging-and-run-a-sustained-detached-row-processing-window-for-the-bounded-hemma-pilot
title: Expand RixVox staging and run a sustained detached row-processing window for the bounded Hemma pilot
type: task
status: active
priority: critical
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-114-hard-isolate-qwen-row-processing-and-finalization-on-hemma.md
  - docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - rixvox
  - preprocessing
  - hemma
  - sustained-run
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Move from the current bounded single-speaker proof corpus toward the real
bounded Hemma pilot corpus by staging a much broader `rixvox` train raw pool
and then running one detached sustained `row-processing` window long enough to
produce a materially larger high-trust multi-speaker train candidate.

## Why This Exists

The current promoted Task 103 corpus view is operationally valid but still too
small and too narrow for the intended bounded Hemma pilot:

- `swedish_smoke_train=52`
- `swedish_pilot_train=52`
- `swedish_scaleup_train=58`
- current train-side prepared rows are still effectively one-speaker

That makes the current corpus good for:

- pipeline proof,
- Hemma runtime proof,
- detached recovery proof,
- and training-resume proof,

but not yet for the real bounded multi-speaker Swedish pilot target from
`T102`.

## PR Scope

- Stage a much broader bounded `rixvox` train shard set on Hemma's HDD storage
  tier before the next long preprocessing run.
- Keep the next long preprocessing run focused on `row-processing` only.
- Run the preprocessing window detached on Hemma with:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=2`
- Use a `2` hour minimum health gate, then allow the same detached run to
  continue into an `8` to `10` hour window if heartbeat remains healthy.
- Monitor the run every `10` minutes with a simple stall rule based on:
  - Task 103 processed-row heartbeat
  - and aggregate spool-row growth
- Do not auto-enter finalization after row-processing.

## Chosen Acquisition Plan

The next train expansion should be breadth-first rather than depth-first.

Initial bounded shard plan:

- keep the already staged `train_0`
- add `train_1` through `train_23`

Reason:

- the current staged raw train pool is too narrow to yield a real bounded
  multi-speaker Hemma pilot corpus
- a broader raw train pool is more important now than squeezing more runtime
  out of the same tiny staged slice
- Hemma's HDD data tier has enough space to support this breadth-first pass

Canonical staging surface:

- `pdm run run-hemma -- pdm run task-108-stage-rixvox-train ...`

Raw corpus storage must remain on:

- `/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus/`

## Chosen Row-Processing Plan

Canonical next run:

- detached
- `row-processing` only
- `rixvox` split selection:
  - `train`
- initial worker settings:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=2`
- keep `fleurs` and `waxholm` stable as already prepared eval/control corpora
- defer held-out `rixvox` audio completion until after the train expansion has
  produced a meaningful pilot candidate

Reason:

- the urgent blocker is the training backbone, not held-out breadth
- row-processing is now the only concurrent stage
- finalization remains isolated and single-process after row-processing ends

## Monitoring Plan

Monitor every `10` minutes with:

- detached Task 114 status inspection
- Task 103 `status.json` heartbeat
- aggregate spool-row count
- detached Task 116 GPU monitor summary when Hemma does not already provide a
  historical GPU time-series for the host

If Hemma lacks host-level Prometheus/Grafana GPU history or another real
time-series collector, start the committed Task 116 GPU monitor in parallel
with the row-processing window and use its `summary` surface for:

- median GPU busy
- peak GPU busy
- lowest GPU busy
- median VRAM use
- peak VRAM use

Do not treat `journald` alone as sufficient historical GPU monitoring unless a
separate sampler service is already writing periodic GPU samples into the
journal.

Healthy progress means at least one of:

- `processed_row_count` increases
- spool-row count increases

Treat the run as stalled only if both remain flat for two consecutive
`10` minute checks.

## Continue / Stop Rule

- Do not stop automatically at `2` hours.
- Use `2` hours only as the first health gate.
- If the run is healthy at `2` hours, let the same detached row-processing run
  continue into the `8` to `10` hour window.
- Stop only when:
  - the staged train pool is exhausted,
  - the run stalls under the monitoring rule,
  - or the admitted spool yield is already sufficient to justify finalization
    toward the bounded Hemma pilot target.

## Target Outcome

This task is complete when the repo has:

- a much broader staged `rixvox` train raw pool,
- one successful sustained detached row-processing run over that pool,
- a materially larger spool-backed high-trust train candidate than the current
  `52`-row proof slice,
- and enough evidence to decide whether one more train-shard expansion pass is
  needed before finalization and the next Hemma training window.

## Deliverables

- [ ] Expanded staged `rixvox` train shard set on Hemma.
- [ ] Detached row-processing evidence bundle for the sustained run.
- [ ] Machine-readable status snapshots proving the `2` hour health gate and
  later sustained progress.
- [ ] Updated corpus summary describing whether the bounded Hemma pilot target
  is now within reach.

## Acceptance Criteria

- [ ] The staged raw train pool includes `train_0` plus `train_1` through
  `train_23`.
- [ ] The next long preprocessing run uses `row-processing` only.
- [ ] The run launches detached and survives local client disconnects.
- [ ] The worker settings are exactly:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=2`
- [ ] The first `2` hour health gate is recorded from detached evidence.
- [ ] If healthy, the same run is allowed to continue into the `8` to `10`
  hour window instead of being restarted.
- [ ] The resulting spool/train yield is large enough to inform the next pilot
  finalization decision.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
