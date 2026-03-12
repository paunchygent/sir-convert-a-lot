---
id: task-121-add-portable-colab-slice-based-qwen-preprocessing-lane
title: Add portable Colab slice-based Qwen preprocessing lane
type: task
status: active
priority: high
created: '2026-03-10'
last_updated: '2026-03-10'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-122-run-the-first-live-colab-gpu-portable-slice-qwen-row-processing-proof.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-116-expand-rixvox-staging-and-run-a-sustained-detached-row-processing-window-for-the-bounded-hemma-pilot.md
  - docs/backlog/tasks/task-119-stream-rixvox-source-selection-and-make-preflight-status-truthful.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - preprocessing
  - notebook
  - slicing
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and scaffold one portable Colab row-processing lane that consumes a
Hemma-issued unique slice of `rixvox` train rows, stages only the raw files
needed for that slice, and emits the exact same Task 103 run-root artifacts as
the canonical Hemma preprocessing pipeline.

## PR Scope

- Define one portable slice-bundle contract rooted in a completed Hemma
  `source-selection` run.
- Ensure Colab never selects its own rows and never overlaps with rows already
  assigned to Hemma or another remote worker.
- Keep the notebook thin: it should orchestrate repo-owned scripts rather than
  embedding a second preprocessing implementation in notebook cells.
- Reuse the canonical Task 103 row-processing code path so Colab outputs the
  same `inventory/`, `audio_24k/`, `spool/rows/`, `run.json`, and
  `status.json` shapes as Hemma.
- Restrict the first portable lane to `rixvox train` row-processing only; held
  out corpora and finalization remain on Hemma.
- Provide one local proof that the slice planner yields disjoint slices and
  that the runner can consume a portable selected-source JSONL after locally
  staging the required raw archives.

## Chosen Design

1. Hemma remains the source of truth for `source-selection`.
1. A new portable slice planner emits:
   - one portable `selected_source_records.jsonl`
   - one `required_hub_files.json`
   - one `slice_summary.json`
1. Portable slice bundles are deterministic and disjoint by:
   - sorted bounded `rixvox train` row order
   - modulo partitioning by `slice_index` and `slice_count`
1. Portable selected-source rows intentionally drop Hemma-local locators.
1. Colab stages only the required dataset files for the chosen slice into a
   local raw-data root, then runs Task 103 in a new
   `selected-source-records` source mode that re-resolves local locators before
   row-processing starts.
1. Each Colab worker writes its own independent Task 103 run root; later
   Hemma-side merge/finalization remains a separate follow-on concern.

## Deliverables

- [x] One documented portable slice-bundle contract for Colab preprocessing.
- [x] One repo-owned slice planner and required-file staging surface.
- [x] One Task 103 source mode that consumes portable selected-source JSONL.
- [x] One notebook scaffold that orchestrates the repo-owned Colab lane.
- [x] One local proof that slice planning is disjoint and artifact-compatible.
- [ ] One real Colab execution proof against a portable slice bundle.

## Acceptance Criteria

- [x] The Colab lane does not independently select rows.
- [x] The first portable lane is explicitly limited to `rixvox train`
  row-processing.
- [x] Slice bundles are deterministic and disjoint for the same bounded source
  selection.
- [x] Portable selected-source records do not rely on Hemma-local absolute
  locator paths.
- [x] Colab can stage only the required raw files for the chosen slice using
  modern `huggingface_hub` download methods.
- [x] Task 103 can consume the portable slice and emit the same run-root
  structure as Hemma row-processing.
- [x] The notebook is only an orchestrator around repo-owned script surfaces,
  not a second implementation.
- [ ] One real Colab execution produces a valid Task 103 row-processing run
  root from a portable slice bundle.

## Current State

The repo now has:

- one portable-slice planner that emits disjoint `selected_source_records`
  bundles from a Hemma-issued `source-selection` run root
- one required-file staging surface that uses `hf_hub_download(...)`
- one `selected-source-records` Task 103 source mode that re-resolves local
  locators from staged raw files before row-processing starts
- one notebook scaffold that acts only as an orchestrator

The remaining gap is one real Colab execution proof. Until that exists, this
task should be treated as locally proven and operationally promising, not fully
closed.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
- [ ] Real Colab execution proof complete
