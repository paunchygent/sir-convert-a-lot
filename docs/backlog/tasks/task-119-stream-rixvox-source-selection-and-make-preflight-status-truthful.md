---
id: task-119-stream-rixvox-source-selection-and-make-preflight-status-truthful
title: Stream RixVox source selection and make preflight status truthful
type: task
status: active
priority: critical
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-110-split-qwen-preprocessing-into-disk-backed-row-processing-and-finalization.md
  - docs/backlog/tasks/task-116-expand-rixvox-staging-and-run-a-sustained-detached-row-processing-window-for-the-bounded-hemma-pilot.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - rixvox
  - preprocessing
  - parquet
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the current `rixvox` train startup bottleneck by turning bounded source
selection into one streaming preflight step that enforces caps during parquet
iteration, resolves only the required audio locators, and exposes truthful
status before row-processing begins.

## Why This Exists

The failed `12:3` and non-productive `12:2` probes did not reach the worker
pool at all. Live Hemma evidence showed the process spending startup time in
compressed parquet inflate work against the staged `rixvox` train metadata
blob while:

- `status.json` remained `allocated`
- `spool_rows=0`
- `audio_24k=0`
- GPU activity was either absent (`12:2`) or unrelated to productive row
  completion (`12:3`)

Root cause:

- the current `rixvox` loader materializes the full train split into Python
  rows before `max_rows_per_split` is applied
- audio-locator resolution is also front-loaded too early for large staged
  train pools
- the runtime reports an apparently idle `allocated` state while it is
  performing expensive preflight work

That makes bounded row-processing launches misleading and prevents aggressive
worker probes from testing the actual worker configuration.

## PR Scope

- Introduce an explicit `source-selection` preflight stage for staged public
  corpora.
- Stream `rixvox` parquet iteration and apply the configured train cap during
  iteration instead of after full materialization.
- Stop converting the full staged `rixvox` train parquet into Python objects
  before the cap is satisfied.
- Resolve only the audio locators required by the selected bounded row set.
- Persist the bounded selected row set and locator map as deterministic run
  artifacts so later row-processing consumes those artifacts directly.
- Make status/reporting truthful during preflight:
  - `allocated`
  - `resolving-source-records`
  - `resolving-audio-locators`
  - `writing-inventory`
  - `row-processing`
- Preserve the existing immutable run-root and promotion architecture.

## Non-Goals

- Do not redesign Whisper concurrency in this task.
- Do not change the accepted corpus policy for `high_trust` / `medium_trust`.
- Do not reopen finalization concurrency; that remains isolated and
  single-process.
- Do not treat this as permission to reintroduce `stage=all` as canonical on
  Hemma.

## Chosen Design

### Stage split

Canonical staged-public-corpus preprocessing on Hemma should become:

1. `source-selection`
1. `row-processing`
1. `finalization`
1. `reports`
1. `promotion`

`row-processing` must consume persisted bounded selection artifacts rather than
performing full train parquet discovery on startup.

### Bounded parquet selection

For `rixvox train`, enforce `max_rows_per_split` while iterating parquet
batches:

- iterate row groups / batches
- normalize and admit rows incrementally
- stop once the requested bounded count is satisfied

Do not parse the remainder of the train parquet after the bounded target is
reached.

### Bounded locator resolution

After the bounded metadata row set is chosen:

- collect the exact required dataset-relative audio filenames
- scan staged train archives only until all required filenames have a resolved
  locator
- persist the resulting locator map for the run root

Do not build one full locator index for all staged train shards when the run
only needs a bounded subset.

### Truthful status

Preflight work must no longer appear as a fake idle `allocated` state.

Status during preflight should expose:

- current stage
- current split
- target row cap
- selected row count
- current parquet batch index
- resolved locator count
- required locator count

That makes “alive but still selecting rows” distinguishable from “alive but
stalled”.

## Deliverables

- [x] One committed `source-selection` stage in the staged-public-corpus lane.
- [x] One streaming `rixvox` train loader that enforces caps during iteration.
- [x] One persisted bounded source-selection artifact set in the run root.
- [x] One truthful status model for preflight phases.
- [ ] One bounded Hemma repro proving a `12:2`-style launch reaches actual
  row-processing instead of spending the whole probe in parquet preflight.

## Acceptance Criteria

- [x] A bounded `rixvox train` launch no longer needs full-train parquet
  materialization before row-processing can begin.
- [x] `max_rows_per_split` is enforced during parquet iteration for `rixvox`
  train, not after a whole-split Python list has been built.
- [x] The run root records one persisted bounded selected-row artifact before
  row-processing starts.
- [x] The run root records one persisted bounded audio-locator artifact for the
  selected train rows.
- [x] Status clearly distinguishes:
  - source selection
  - audio-locator resolution
  - inventory writing
  - row-processing
- [ ] A rerun of the aggressive Hemma probe reaches first spool-row output fast
  enough to be a real worker/concurrency experiment.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task103_qwen_preprocessing.py tests/sir_convert_a_lot/test_task114_qwen_isolated_stages.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [ ] Docs updated

## Progress Notes

- 2026-03-09: Implemented the committed `source-selection` stage, bounded
  `rixvox` parquet iteration, bounded audio-locator resolution, persisted
  selected-source artifacts, and truthful preflight status fields.
- 2026-03-09: Live Hemma validation succeeded under detached Task 114 launch
  `task114-source-selection-20260309t221342z` against run root
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task119-source-selection-20260309a`.
  The run completed cleanly with:
  - `stage="source-selection"`
  - `status="completed"`
  - `current_split="train"`
  - `current_parquet_batch_index=1`
  - `target_row_cap=1000`
  - `selected_row_count=1024` total bounded rows across datasets
  - `required_audio_locator_count=1000`
  - `resolved_audio_locator_count=1000`
- Remaining acceptance gap: rerun an aggressive Hemma row-processing probe on
  top of the new `source-selection` stage and confirm it reaches first spool
  row quickly enough to be a real concurrency experiment.
