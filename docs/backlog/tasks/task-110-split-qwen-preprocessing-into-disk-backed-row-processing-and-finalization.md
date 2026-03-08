---
id: task-110-split-qwen-preprocessing-into-disk-backed-row-processing-and-finalization
title: Split Qwen preprocessing into disk-backed row processing and finalization
type: task
status: active
priority: high
created: '2026-03-08'
last_updated: '2026-03-09'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - preprocessing
  - manifests
  - durability
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Refactor the Qwen Swedish preprocessing lane so the main per-row preprocessing
work persists durable row results to disk as it progresses, and a later
finalization phase consumes those row results to emit curated manifests,
`audio_codes`, prepared manifests, and reports.

## Why This Exists

The current Task 103 flow does the right work, but it still couples too much of
the bounded public-corpus run into one long in-memory pass:

- materialize `audio_24k`
- run Whisper ASR mismatch scoring
- assign quality tiers and manifest families
- select or emit per-family refs
- accumulate row state in memory
- only later write curated/manifests/reports

That shape makes long detached Hemma runs harder to resume, harder to diagnose,
and harder to scale out safely even when VRAM usage during the row loop stays
modest.

Detached `T108` proof on Hemma has now confirmed this is not only a design
concern. The bounded public-corpus run hit the kernel OOM killer in the Python
process after producing partial `audio_24k`, `refs`, and curated output, which
means the disk-backed split is now evidence-backed hardening rather than a
purely speculative refactor.

## PR Scope

- Split the preprocessing lane into two canonical phases:
  - row-processing
  - finalization
- Persist row-level outputs to deterministic disk artifacts as each row
  completes:
  - normalized transcript
  - ASR transcript
  - WER
  - quality tier
  - speaker-quality gate
  - manifest-family targets
  - `audio_24k` path
  - reference-audio path
- Add one deterministic spool subtree under:
  - `build/reference/qwen3-tts-swedish-corpus/`
- Ensure finalization reads the disk-backed spool rather than depending on a
  whole-run in-memory accumulator.
- Preserve containerized execution as the only canonical runtime for the
  public-corpus lane.
- Make stage selection and resource control explicit rather than implicit:
  - choose which stage to run
  - control row-worker concurrency
  - control GPU ASR concurrency
  - control `audio_codes` chunk size and finalization-family selection
- Modularize the current preprocessing script so the hardening work does not
  collapse into one oversized god file.

## Non-Goals

- Do not change the corpus policy from Task 102.
- Do not silently alter transcript text for admitted rows.
- Do not introduce host-venv-only execution or ad hoc local caches.
- Do not make parallel workers the primary goal of this task.
- Do not keep piling new stage logic into one monolithic preprocessing module.

## Expected Outcome

After this task:

- interrupted long runs leave usable row-level progress on disk
- phase boundaries are explicit and observable
- finalization can be rerun without recomputing every successful row
- future bounded parallelism decisions can be based on a durable staged
  pipeline rather than a single long in-memory loop

## Canonical Pipeline Design

The intended pipeline shape after `T110` is:

1. inventory
   - deterministic source-row inventory only
   - no Whisper, no Qwen tokenizer work
1. row-processing
   - one row at a time from source row to durable spool record
   - outputs:
     - normalized `audio_24k`
     - canonical `ref`
     - ASR transcript
     - WER
     - quality tier
     - speaker-quality gate
     - manifest-family targets
     - row-complete spool record
1. curated projection
   - rebuild `curated/*.jsonl` from the durable spool only
1. manifest finalization
   - rebuild raw/prepared manifests from the durable spool only
   - generate `audio_codes` in bounded chunks, never as one family-sized
     all-at-once batch
1. reports
   - write report surfaces last from deterministic on-disk state

## Control Model

The pipeline must be independently controllable.

Expected control surfaces:

- stage selection:
  - run inventory only
  - run row-processing only
  - run finalization only
  - run reports only
- family selection:
  - finalize one family at a time when needed
- bounded row concurrency:
  - row-worker count
  - CPU-side audio-materialization concurrency
  - GPU-side ASR worker count
- bounded finalization concurrency:
  - one family at a time by default
  - configurable `audio_codes` chunk size
- explicit upper bound for concurrent tokenizer work

Current implemented controls:

- `run_task103_qwen_swedish_preprocessing.py`
  - `--stage`
  - `--finalization-families`
  - `--audio-codes-chunk-size`
  - `--row-worker-count`
  - `--gpu-asr-worker-count`
- `task-103-preprocess-public-corpus` / Task 109 containerized wrapper
  - forwards the same chunk-size and row/GPU concurrency controls into the
    canonical Qwen container runtime on Hemma

Default posture:

- detached Hemma execution
- conservative GPU concurrency
- conservative `audio_codes` chunk size
- restart from durable spool rather than rerunning completed rows

Current implementation progress:

- row-processing and finalization now live in separate modules
- durable spool rows are emitted under `build/reference/qwen3-tts-swedish-corpus/spool/rows`
- finalization now rebuilds canonical family reference clips from the spool
  instead of depending on row-stage-managed refs
- `audio_codes` generation is chunked rather than family-wide all-at-once
- row-worker concurrency and GPU ASR concurrency are explicit runtime controls

Remaining acceptance work:

- prove the bounded detached Hemma `T108` lane against the chunked spool-based
  pipeline
- tune row/GPU concurrency from live Hemma evidence rather than static
  assumptions

Latest concurrency evidence:

- detached Hemma proof with:
  - `row-worker-count=10`
  - `gpu-asr-worker-count=5`
  - `audio-codes-chunk-size=4`
- result:
  - Docker `ExitCode=139`
  - `OOMKilled=false`
  - kernel log recorded a segfault in `libaotriton_v2.so.0.11.1`
  - GPU residency reached roughly `14.6 GB` before the crash

Current interpretation:

- the staged spool/finalization split removed the earlier whole-run Python OOM
  as the only explanation
- aggressive GPU ASR concurrency is now a separate ROCm/AOTriton stability
  limit that must be tuned below the `5`-worker crash point
- Hemma root-disk pressure is now also a practical blocker for large detached
  preprocessing output written under the repo-root `build/` subtree

## Durability And Atomicity

The row-processing stage should treat each row as an atomic durable unit.

Required atomicity rules:

- write row results to a temp file in the spool subtree first
- rename into the canonical completed-row path only when the row is complete
- never treat partially written row artifacts as admitted state
- write manifests and reports through temp-file plus atomic-rename semantics
- reports are emitted last so they summarize a completed consistent view

Required restart rules:

- completed row-spool records are authoritative for reruns
- rerunning finalization must not require rerunning Whisper or audio
  materialization for already completed rows
- rerunning one manifest family must not invalidate other completed families

## Resource Posture

The detached `T108` proof indicates host-memory pressure is the primary
observed failure mode today, not VRAM exhaustion.

That means `T110` should explicitly optimize for:

- bounded host-memory growth
- bounded tokenizer/finalization batch size
- stable GPU residency for Whisper and later Qwen tokenizer work
- durable progress over maximal one-shot throughput

The first implementation should therefore favor:

- one GPU ASR worker by default
- bounded CPU row workers
- chunked `audio_codes` generation
- sequential family finalization by default

Only after the split pipeline is proven should higher parallelism become the
next optimization target.

## Modularization Requirement

This task must also decompose the current preprocessing implementation into
clear stage-oriented modules.

Expected module boundaries:

- one runner or orchestration surface
- one inventory/source-loading module
- one row-processing module
- one ASR scoring module
- one spool read/write module
- one finalization or manifest-emission module
- one reporting module

Design rules:

- stage logic should not keep growing inside one central god file
- spool schema and manifest schema should live in dedicated model/contract
  modules
- stage entrypoints should be independently testable
- resource-control logic should be close to the stage it governs, not hidden in
  one top-level monolith

## Deliverables

- [ ] One committed disk-backed row-spool contract for Task 103 preprocessing.
- [ ] One committed finalization path that consumes the spool and emits the
  existing curated/raw/prepared/report artifacts.
- [ ] One live Hemma evidence bundle proving the split pipeline still produces
  deterministic outputs under
  `build/reference/qwen3-tts-swedish-corpus/`.

## Acceptance Criteria

- [ ] Row preprocessing persists durable row records to disk as work completes.
- [ ] Finalization consumes disk-backed row results rather than requiring a
  whole-run in-memory accumulator.
- [ ] The canonical artifact layout remains deterministic and documented.
- [ ] The containerized Hemma runtime remains the only supported execution unit
  for this lane.
- [ ] The task documents restart and rerun expectations clearly enough for
  later `rixvox` scale-up work.

## Checklist

- [ ] Implementation complete
- [x] Validation complete
- [x] Docs updated
