---
id: task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing
title: Materialize RixVox audio and train-family mapping for Qwen preprocessing
type: task
status: completed
priority: high
created: '2026-03-08'
last_updated: '2026-03-09'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-106-add-script-free-hugging-face-corpus-adapters-to-the-qwen-swedish-preprocessing-pipeline.md
  - docs/backlog/tasks/task-107-run-the-staged-public-corpus-qwen-swedish-preprocessing-bundle-on-hemma.md
  - docs/backlog/tasks/task-114-hard-isolate-qwen-row-processing-and-finalization-on-hemma.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - rixvox
  - preprocessing
  - audio
  - swedish
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extend the committed Qwen Swedish preprocessing lane so `rixvox` moves from
metadata-only inventory into real audio-backed train-family manifests before
the first bounded Hemma pilot fine-tune.

## PR Scope

- Stage revision-pinned `rixvox` audio assets on Hemma's HDD-backed storage.
- Materialize real `source_audio_locator` values for admitted `rixvox` rows.
- Add the missing train-family mapping for admitted `rixvox` train rows:
  - `swedish_smoke_train`
  - `swedish_pilot_train`
  - `swedish_scaleup_train`
- Keep `fleurs` and labeled `waxholm` in control/eval roles only.
- Preserve the deterministic Task 103 artifact and report contract.

## Current Gap Review

The current repo state is already close to the required shape, but it stops at
metadata-only `rixvox` ingestion:

- `task106_qwen_corpus_acquisition_runtime.py` stages only
  `data/dev_metadata.parquet` and `data/test_metadata.parquet`
- `task103_qwen_staged_public_corpus.py` only loads staged `rixvox`
  `dev/test` parquet rows
- `task103_qwen_source_rixvox.py` currently emits `SourceRecord` rows without
  `source_audio_locator`
- `task103_qwen_family_assignment.py` maps `rixvox` `dev/test` into
  checkpoint-dev / final-test only and leaves train-family ownership undefined

That means the repo can currently inventory `rixvox`, but it cannot yet emit
real audio-backed train manifests for the bounded Hemma pilot.

## Planned Implementation

Execute `T108` in this order:

1. Extend the script-free `rixvox` acquisition lane.

   - stage `train_metadata.parquet` on Hemma with the same revision-pinned,
     targeted `huggingface_hub` path already used by `T106`
   - add one bounded audio-acquisition surface for only the admitted train rows
     needed by smoke/pilot planning, not a whole-corpus bulk fetch
   - keep all raw assets on Hemma's HDD-backed storage

1. Add `rixvox` audio materialization metadata.

   - parse `train_metadata.parquet` and preserve the dataset-native `filename`
     field as the canonical source-path identifier
   - resolve each admitted row to one real local audio source:
     - direct extracted file, or
     - archive path plus archive member via `AudioLocator`
   - keep the acquisition and locator contract script-free and
     revision-pinned

1. Add explicit train-family assignment rules.

   - extend `task103_qwen_family_assignment.py` so admitted `rixvox` train rows
     can map into:
     - `swedish_smoke_train`
     - `swedish_pilot_train`
     - `swedish_scaleup_train`
   - keep `rixvox` `dev` as checkpoint-dev and `rixvox` `test` as final-test
   - keep `fleurs` and labeled `waxholm` in control/eval-only roles

1. Thread bounded subset selection through the preprocessing lane.

   - define deterministic subset rules for smoke/pilot/scale-up train rows
   - apply the existing quality-tier and speaker-quality gates before audio
     materialization fan-out
   - preserve the current manifest/report structure under
     `build/reference/qwen3-tts-swedish-corpus/`

1. Prove the first live Hemma audio-backed train-manifest run.

   - run the container-backed public-corpus preprocessing lane
   - record that `swedish_smoke_train` and at least one broader train family
     are now non-empty
   - keep the report deterministic and revision-pinned

## Preferred Technical Approach

Use the modern Hugging Face Hub path as the canonical repo contract:

- `hf_hub_download(...)` for targeted dataset files
- revision-pinned acquisition by concrete commit SHA
- `repo_type="dataset"`
- narrow file-level downloads over deprecated dataset scripts
- directory/snapshot patterns only when file-level acquisition is genuinely
  insufficient

This task should not introduce:

- `datasets<4`
- custom dataset-script loading
- broad local-workstation corpus downloads
- host-venv-only preprocessing execution

## Open Technical Decisions

The only non-trivial technical choice to settle during implementation is the
bounded `rixvox` audio staging form:

- preferred first path:
  - targeted archive or file acquisition for only admitted rows plus
    `AudioLocator` support that can read from archives without full unpacking
- acceptable fallback inside the same repo contract:
  - targeted acquisition followed by deterministic extraction to HDD-backed
    local files when archive-member access proves too awkward operationally

Whichever path wins, the repo contract remains the same:

- script-free
- revision-pinned
- Hemma-only for large corpus assets
- canonical DATA-disk storage
- container-backed preprocessing execution

## Deliverables

- [x] One committed `rixvox` audio materialization surface.
- [x] One committed train-family mapping path for admitted `rixvox` train rows.
- [x] One live Hemma evidence bundle that proves real `rixvox` audio-backed
  train manifests exist before `T101`.

## Final Outcome

`T108` is now functionally complete.

The preserved crashed run root on Hemma was resumed without rerunning
row-processing:

- run root:
  - `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task108-4workers-pipeline-20260309T064950Z`
- recovered sequence:
  - fresh isolated `finalization` container for `swedish_scaleup_train`
  - fresh isolated `finalization` container for
    `swedish_checkpoint_dev,swedish_final_test,swedish_waxholm_control`
  - fresh isolated `reports` container
- final report:
  - `inventory_rows=216`
  - `curated_rows=186`
  - `admitted_rows=186`
  - `prepared_rows=186`
- final manifest counts:
  - `swedish_smoke_train=52`
  - `swedish_pilot_train=52`
  - `swedish_scaleup_train=58`
  - `swedish_checkpoint_dev=8`
  - `swedish_final_test=8`
  - `swedish_waxholm_control=8`

The canonical promoted corpus view on Hemma now points at the recovered run
root:

- `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus`

## Lessons Learned

- Immutable run roots plus spool-backed finalization made it possible to resume
  the crashed proof exactly where it failed instead of rerunning row
  processing.
- The host wedge was specifically a finalization-stage problem, not a
  row-processing problem.
- Fresh-process stage isolation on Hemma is mandatory for this lane.

## Current Implementation Slice

The first committed `T108` slice now exists and focuses on bounded raw-asset
staging plus staged-loader readiness:

- committed Hemma runner:
  - `pdm run task-108-stage-rixvox-train`
- committed runtime surfaces:
  - `scripts/sir_convert_a_lot/devops/run_task108_hemma_qwen_rixvox_train_staging.py`
  - `scripts/sir_convert_a_lot/devops/task108_qwen_rixvox_train_staging_runtime.py`
- staged-loader extension:
  - `task103_qwen_staged_public_corpus.py` can now attach real `AudioLocator`
    values for `rixvox` rows when staged train archives exist under:
    - `raw/kblab_rixvox/data/train/train_<n>.tar.gz`
- adapter extension:
  - `task103_qwen_source_rixvox.py` can now build archive-member locator
    indexes and emit `source_audio_locator` values for matching rows

This first slice does not yet complete train-family mapping or a live
audio-backed preprocessing proof, but it establishes the raw-staging and
loader foundation required for the next `T108` step.

The next live `T108` proof established one important runtime lesson on Hemma:

- bounded containerized preprocessing with:
  - `--rixvox-split train`
  - `--rixvox-split dev`
  - `--rixvox-split test`
  - `--rixvox-max-rows-per-split 64`
- when launched through the attached client path, exited with `137` before
  manifest/report emission
- that attached-mode exit is not used as canonical preprocessing failure
  evidence for this task
- follow-on detached repro work is the required truth surface for root-cause
  analysis and acceptance decisions

Observed evidence from that failed proof:

- `88` materialized `audio_24k` files
- `10` materialized reference files
- `6` inventory files
- no final `manifests/`
- no final `report.json`

Preferred remediation inside `T108`:

- keep the bounded train-row routing work
- enforce detached Hemma execution as the canonical proof mode for this task
- only choose runtime/code remediation after detached evidence identifies the
  actual failing phase or confirms that the attached `137` was client-path
  termination noise rather than a true pipeline failure

Detached repro evidence now closes that uncertainty:

- detached container:
  - `task109-debug-20260308a`
- detached result:
  - exited `137`
  - `OOMKilled=false` in Docker state
- kernel proof on Hemma:
  - `python invoked oom-killer`
  - `oom-kill: ... task=python,pid=1077392`
  - `Out of memory: Killed process 1077392 (python)`
- memory facts at kill time from the kernel log:
  - `total-vm:61900384kB`
  - `anon-rss:28714248kB`
- observed artifact progress before the kill:
  - `88` materialized `audio_24k` files
  - `10` materialized reference files
  - `51` curated `swedish_smoke_train` rows
  - no final `manifests/`
  - no final `report.json`

That means the current `T108` blocker is now better defined:

- detached execution remains mandatory on Hemma
- the detached repro proved a real host-memory OOM in the Python process
- future `T108` implementation should treat `T110` as the planned structural
  remediation path for reducing long-run in-memory pressure

Follow-on implementation state after the first `T110` slice:

- the preprocessing lane now supports:
  - disk-backed row spool records
  - separate row-processing and finalization stages
  - chunked `audio_codes` generation
  - explicit `row-worker-count`
  - explicit `gpu-asr-worker-count`
- the next canonical `T108` proof is therefore:
  - detached on Hemma
  - container-backed through Task 109
  - tuned against the earlier observed `~4.6 GB` GPU residency during the
    main row loop
  - accepted only if it emits non-empty audio-backed train manifests without
    repeating the prior host-RAM OOM pattern

Latest detached proof result on `2026-03-08`:

- committed detached runner:
  - `pdm run task-108-detached-proof`
- bounded proof launch:
  - `--rixvox-split train`
  - `--rixvox-split dev`
  - `--rixvox-split test`
  - `--rixvox-max-rows-per-split 64`
  - `--row-worker-count 10`
  - `--gpu-asr-worker-count 5`
  - `--audio-codes-chunk-size 4`

Latest recovered run-root lesson on `2026-03-09`:

- the preserved immutable run root proves the wedge happened after row-stage
  completion and during late finalization
- `swedish_smoke_train` and `swedish_pilot_train` completed successfully
- the freeze point was `swedish_scaleup_train` finalization
- therefore the next `T108` proof must run through the `T114` hard-isolation
  model:
  - detached row-processing first
  - detached fresh-process finalization second
  - detached reports/promotion afterward
- observed runtime facts:
  - detached container started correctly and remained independent of the local
    client session
  - GPU residency climbed to roughly `14.6 GB` before failure
  - no `audio_24k`, spool, curated, or manifest rows were durably emitted
    before the crash
- exact failure evidence:
  - Docker state:
    - `ExitCode=139`
    - `OOMKilled=false`
  - kernel log:
    - `segfault ... in libaotriton_v2.so.0.11.1`
- operational storage lesson:
  - Hemma root (`/`) is effectively full while `/srv/scratch` remains mostly
    empty
  - repo-root `build/` output is therefore no longer a safe write target for
    large detached preprocessing evidence on Hemma

That means the next `T108` continuation should not simply retry the same
configuration. It should:

- lower GPU ASR concurrency below the `5`-worker crash point
- move the large Hemma preprocessing output/evidence lane onto SSD-scratch-backed
  storage while preserving the documented artifact structure

Latest detached proof result on `2026-03-09`:

- canonical detached launch with:
  - `--row-worker-count 3`
  - `--gpu-asr-worker-count 3`
  - `--audio-codes-chunk-size 4`
  - immutable Task 103 run root on SSD scratch under:
    - `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task108-3workers-20260309T061303Z`
- detached runtime result:
  - container launched cleanly with the corrected scratch/home bind mounts
  - `ExitCode=1`
  - `OOMKilled=false`
- preserved run-scoped artifacts:
  - `inventory/*.jsonl`
  - `run.json`
  - `status.json`
  - `5` materialized `audio_24k` files
- exact failure recorded in the immutable run status:
  - `NotImplementedError: Cannot copy out of meta tensor; no data! Please use torch.nn.Module.to_empty() instead of torch.nn.Module.to() when moving module from meta to a different device.`
- measured live GPU evidence before failure:
  - approximately `8.1 GB` VRAM used on Hemma
  - detached execution and run-root preservation both held correctly

That means the current `T108` blocker is now narrower and better defined:

- detached execution is no longer the problem
- run-scoped persistence is working
- the next fix must address the meta-tensor model/device transition in the
  preprocessing runtime before the bounded audio-backed train-family proof can
  advance

## Acceptance Criteria

- [ ] `train_metadata.parquet` is staged on Hemma through the script-free
  revision-pinned acquisition lane.
- [ ] `rixvox` audio is staged on Hemma without dataset-script loading.
- [ ] The preprocessing lane produces admitted audio-backed `rixvox` rows, not
  just inventory metadata.
- [ ] The canonical train-family manifests are non-empty for the first bounded
  Hemma pilot lane.
- [ ] The current `fleurs` and `waxholm` control/eval separation is preserved.
- [ ] The live proof runs through the container-backed public-corpus
  preprocessing surface, not the Hemma host venv.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
