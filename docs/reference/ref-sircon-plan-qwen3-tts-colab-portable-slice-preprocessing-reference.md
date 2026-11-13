---
type: reference
id: REF-SIRCON-PLAN-qwen3-tts-colab-portable-slice-preprocessing-reference
title: Qwen3-TTS Colab Portable Slice Preprocessing Reference
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: plan
summary: Qwen3-TTS Colab Portable Slice Preprocessing Reference
retired_ids:
- REF-qwen3-tts-colab-portable-slice-preprocessing
---

## Outcome And Purpose

## Planning Boundary

## Evidence Basis

## Confirmed Contract

## Backlog Derivation

## Planning Stop Conditions

## Historical Source Content

### Purpose

Define the first portable Colab row-processing lane for Qwen Swedish corpus
expansion without creating a second preprocessing implementation or drifting
from the canonical Hemma artifact contract.

### Canonical Principle

Colab may preprocess rows, but Colab must not decide which rows to preprocess.

Row selection stays on Hemma through the canonical `source-selection` stage.
Colab only consumes a deterministic portable slice bundle issued from that
selection.

### First Supported Scope

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

### Portable Slice Bundle Contract

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

### Unique Slice Rule

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

### Canonical Ownership Rule

Once real preprocessing work exists, row ownership must be governed by two
immutable artifacts:

- one canonical processed root built from completed Task 103 run roots
- one shard registry built from the remaining source-selection universe

Future processing units must be issued from shard ids, not from freeform slice
math over the remaining universe.

Frozen pilot rule:

- once the canonical pilot root is frozen, future shard issuance must exclude
  both:
  - owned pilot rows from that canonical processed root
  - quarantined conflict rows from
    `canonical_processed_root_conflict_row_keys.jsonl`

Canonical commands:

- build the canonical processed root
  - `python -m scripts.sir_convert_a_lot.devops.task103_qwen_canonical_processed_root build`
- build the immutable shard registry
  - `task-121-colab-slice-bundle build-shard-registry`
- issue one processing unit from shard ids
  - `task-121-colab-slice-bundle issue-processing-unit-from-shards`

Default posture:

- target roughly `5000` rows per shard
- combine shard ids into one processing unit when a worker needs more than one
  shard
- pass `--exclude-row-keys-path` for frozen conflict-row manifests during
  shard-registry or remaining-unique recovery builds

### Incident Recovery Rule

`plan-remaining-unique` remains available only for bounded incident recovery
when an in-flight manifest must be salvaged against already-owned rows.

Recovery command:

- `task-121-colab-slice-bundle plan-remaining-unique`

Recovery exclusions:

- completed Task 103 run roots through `--exclude-completed-run-root`
- already issued selected-source manifests through
  `--exclude-selected-source-records-path`

### Required File Staging

Portable preprocessing must use modern `huggingface_hub` file download
surfaces:

- `hf_hub_download(...)` for individual required archives
- revision pinning when available
- local notebook-side data root, not Hemma paths

The notebook or remote runtime stages only the required files from
`required_hub_files.json` into a local raw-data tree that mirrors the canonical
Task 103 expectations.

### Task 103 Consumption Contract

Portable Colab row-processing must still go through
`qwen_preprocess.py`.

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

### Notebook Role

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

### Localized Slice Follow-On

The first live Colab proof exposed a real throughput issue: archive-member
resolution plus staged-raw startup overhead can dominate small proof slices and
make reruns expensive. The next approved optimization is therefore a
repo-owned portable-slice localization stage.

That stage must:

1. read one portable selected-source bundle
1. resolve the required local archive members from staged raw files
1. extract those members into a deterministic plain-file tree under the slice
   root
1. persist one localized selected-source manifest with plain-file
   `source_audio_locator` values

After localization, the notebook should invoke Task 103 row-processing against
the localized manifest instead of the original portable manifest. That keeps
the notebook thin while removing repeated archive-resolution costs on rerun.

The first follow-on worker mix for the localized Colab lane is:

- `row_worker_count=8`
- `gpu_asr_worker_count=2`

This is an explicit throughput experiment on disposable Colab hardware, not a
new default for Hemma.

### In-Flight Deduplication Rule

If a portable Colab run has already started and a cross-campaign overlap is
discovered, the recovery path must stay repo-owned:

- use `task-121-colab-slice-bundle dedupe-selected-source-records`
- point it at the current portable or localized selected-source manifest
- subtract every known completed run root through
  `--exclude-completed-run-root`
- optionally subtract already issued manifests through
  `--exclude-selected-source-records-path`

The output is one deduplicated remaining selected-source JSONL that the
notebook can resume against without moving overlap logic into notebook cells.

### First Live Proof Shape

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

### Open Follow-On

This lane now has canonical ownership and allocation governance, but it still
does not solve:

- finalization across federated row-processing runs
- downstream pilot/train-set construction from multiple canonicalized roots
