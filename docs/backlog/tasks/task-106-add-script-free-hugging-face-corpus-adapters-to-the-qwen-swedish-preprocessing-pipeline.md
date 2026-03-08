---
id: 'task-106-add-script-free-hugging-face-corpus-adapters-to-the-qwen-swedish-preprocessing-pipeline'
title: 'Add script-free Hugging Face corpus adapters to the Qwen Swedish preprocessing pipeline'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - preprocessing
  - huggingface
  - datasets
  - swedish
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extend the committed Task 103 preprocessing pipeline from repo-fixture smoke
rows to real `KBLab/rixvox`, `google/fleurs` Swedish, and labeled
`KTH/waxholm` inputs without depending on deprecated Hugging Face dataset
scripts or notebook-only ingestion logic, and without downloading large corpus
assets onto the local workstation.

## PR Scope

- Make script-free Hugging Face ingestion the canonical repo path for Swedish
  Qwen corpus preprocessing:
  - use Hemma-only, revision-pinned `huggingface_hub` downloads via targeted
    `hf_hub_download(...)` calls and narrowly scoped acquisition plans
  - parse raw supported repository assets directly
  - store large raw corpus assets on Hemma's DATA-backed disk, not on the local
    workstation and not on the Hemma OS disk
  - preserve deterministic outputs under
    `build/reference/qwen3-tts-swedish-corpus/`
- Add committed source adapters for:
  - `google/fleurs` Swedish from TSV plus audio tar members
  - labeled `KTH/waxholm` from repo snapshot plus `.wav` and `.smp.mix`
  - `KBLab/rixvox` from metadata parquet, with audio-materialization follow-up
    kept adapter-driven and revision-pinned
- Refactor the current Task 103 core so source enumeration is adapter-shaped
  rather than fixture-shaped.
- Keep the current inventory, curated, raw-manifest, prepared-manifest, and
  report contracts stable while broadening dataset coverage.
- Record the allowed and forbidden options explicitly so future work does not
  drift:
  - legacy `datasets<4` custom-script loading is forbidden, including as a
    fallback, because it is brittle and not robust enough for the repo contract
  - broad whole-dataset snapshot downloads are not the default acquisition
    posture for large corpora; fetch only the files needed for the active slice
  - Hub auto-converted parquet may be consumed opportunistically when
    available, but the repo must not require dataset-viewer automation to
    function

## Deliverables

- [x] One committed adapter surface for real Hugging Face targeted file
      downloads on Hemma.
- [x] One refactor of the Task 103 source-row contract so dataset adapters own
      raw source metadata and the core owns family assignment plus manifest
      materialization.
- [x] One `fleurs` Swedish adapter that emits deterministic
      `swedish_checkpoint_dev` and `swedish_final_test` rows.
- [x] One labeled `waxholm` adapter that emits deterministic
      `swedish_waxholm_control` rows from `.smp.mix` text.
- [x] One `rixvox` metadata adapter that ingests parquet metadata without
      `load_dataset(...)`.
- [x] Updated docs that make the script-free lane canonical and explain the
      hard prohibition on legacy dataset-script loading.

Committed runner surfaces in this slice:

- `pdm run task-106-acquire`
- `pdm run run-hemma -- pdm run task-106-acquire`
- `scripts/sir_convert_a_lot/devops/run_task106_hemma_qwen_corpus_acquisition.py`
- `scripts/sir_convert_a_lot/devops/task106_qwen_corpus_acquisition_runtime.py`

## Acceptance Criteria

- [x] The repo no longer depends on `datasets.load_dataset(...)` for
      `rixvox`, `fleurs`, or `waxholm` ingestion in the canonical T103 lane.
- [x] All Hugging Face dataset acquisition in this slice is revision-pinned and
      reproducible from committed code.
- [x] Large raw corpus assets are documented to live on Hemma's DATA-backed
      storage, not on the local workstation and not on the Hemma OS disk.
- [x] The acquisition approach uses targeted sequential downloads for large
      corpora rather than broad whole-repository fan-out.
- [x] The deterministic artifact/report structure under
      `build/reference/qwen3-tts-swedish-corpus/` remains unchanged at the
      contract level.
- [x] The implementation preserves the existing family contract:
      `swedish_smoke_train`, `swedish_pilot_train`, `swedish_scaleup_train`,
      `swedish_checkpoint_dev`, `swedish_final_test`,
      `swedish_waxholm_control`.
- [x] The docs explicitly state that raw file formats and automated data
      support are preferred long term over custom dataset scripts.
- [x] The task documents the allowed policy options:
      `script-free revision-pinned adapters` as canonical and
      `auto-converted parquet when available` as optional acceleration.
- [x] The task explicitly forbids legacy `datasets<4` custom-script loading,
      including as a fallback.

## Current Status

Implemented and validated in this slice:

- adapter-shaped source contracts
- `fleurs` TSV plus tar-member adapter
- labeled `waxholm` `.smp.mix` adapter
- `rixvox` parquet-metadata adapter
- Hemma-only targeted acquisition runner with retry/backoff and DATA-disk
  enforcement
- first live Hemma acquisition pass completed with:
  - `google/fleurs`: `4` staged files for `sv_se` `dev/test`
  - `KTH/waxholm`: `17` staged files from the bounded labeled subset
  - `KBLab/rixvox`: `2` staged metadata parquet files for `dev/test`
  - canonical Hemma DATA root:
    `/srv/scratch/sir-convert-a-lot/data/qwen3-tts-swedish-corpus`
  - canonical Hemma report path:
    `build/reference/qwen3-tts-swedish-corpus/acquisition/report.json`

Follow-on work after task close:

- wire the staged Hemma raw assets into a non-fixture public-corpus
  preprocessing run under `T103`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
