---
type: reference
id: REF-qwen3-tts-colab-portable-slice-preprocessing
title: Qwen3-TTS Colab Portable Slice Preprocessing Reference
status: active
created: 2026-03-10
updated: 2026-03-10
owners:
  - Olof
links:
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-122-run-the-first-live-colab-gpu-portable-slice-qwen-row-processing-proof.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
---

## Purpose

Define the first portable Colab row-processing lane for Qwen Swedish corpus
expansion without creating a second preprocessing implementation or drifting
from the canonical Hemma artifact contract.

## Canonical Principle

Colab may preprocess rows, but Colab must not decide which rows to preprocess.

Row selection stays on Hemma through the canonical `source-selection` stage.
Colab only consumes a deterministic portable slice bundle issued from that
selection.

## First Supported Scope

The first portable remote lane is intentionally narrow:

- dataset: `rixvox`
- split: `train`
- stage: `row-processing`

Not in scope for the first slice:

- `fleurs`
- `waxholm`
- finalization
- reports
- promotion
- Hemma/Colab spool merging

## Portable Slice Bundle Contract

One portable slice bundle contains:

- `selected_source_records.jsonl`
  - serialized `SourceRecord` payloads for the chosen slice
  - portable form: local Hemma locator fields are stripped
- `required_hub_files.json`
  - exact Hub dataset files required to reconstruct local locators for the
    chosen slice
- `slice_summary.json`
  - deterministic metadata about the slice:
    - `slice_count`
    - `slice_index`
    - `selected_row_count`
    - datasets
    - splits

## Unique Slice Rule

Portable slices must be disjoint.

The first deterministic partitioning rule is:

1. start from one completed Hemma `source-selection` artifact set
1. keep only `rixvox train` rows
1. sort rows by:
   - dataset
   - split
   - speaker
   - dataset row id
1. assign rows by modulo:
   - row `i` belongs to slice `i % slice_count`

This guarantees:

- deterministic partitioning
- no overlap between slices
- full coverage of the chosen bounded source-selection universe

## Required File Staging

Portable preprocessing must use modern `huggingface_hub` file download
surfaces:

- `hf_hub_download(...)` for individual required archives
- revision pinning when available
- local notebook-side data root, not Hemma paths

The notebook or remote runtime stages only the required files from
`required_hub_files.json` into a local raw-data tree that mirrors the canonical
Task 103 expectations.

## Task 103 Consumption Contract

Portable Colab row-processing must still go through
`run_task103_qwen_swedish_preprocessing.py`.

The added source mode is:

- `selected-source-records`

Expected behavior:

1. load the portable selected-source JSONL
1. locally re-resolve missing audio locators from the staged required files
1. run canonical Task 103 `row-processing`
1. emit the normal Task 103 run-root artifacts

That preserves output compatibility with Hemma:

- `inventory/`
- `audio_24k/`
- `spool/rows/`
- `run.json`
- `status.json`

## Notebook Role

The notebook is an operator shell, not an implementation surface.

Allowed notebook responsibilities:

- install dependencies
- set local paths
- invoke repo-owned CLI/module surfaces
- display progress and summaries

Forbidden notebook behavior:

- independent row selection
- notebook-only row-processing logic
- notebook-only artifact shapes
- diverging output contract

## First Live Proof Shape

The first real Colab execution should use:

- a fresh Hemma-issued `source-selection` run root dedicated to the proof
- `rixvox train` only
- bounded cap around `512` train rows
- deterministic partitioning with `slice_count=2`
- Colab assigned `slice_index=1`
- Colab worker mix:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=1`

That keeps the proof unique, auditable, and operationally small while still
using the same hybrid CPU/GPU row-processing model as the Hemma lane.

## Open Follow-On

This first lane does not yet solve:

- Hemma-plus-Colab shared slice reservation for a single live 10k-row run
- multi-slice merge semantics
- finalization across federated row-processing runs

Those should become separate tasks after the first portable slice lane is
proven locally and, later, in one real Colab execution.
