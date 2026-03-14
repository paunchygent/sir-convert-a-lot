# Session Handoff

## Implementation Handoff (2026-03-14, Story 26 T171 -> T173 -> T172)

### Scope for Next Developer

Implement the following tasks in strict order:

1. `docs/backlog/tasks/task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md`
1. `docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md`
1. `docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md`

Story to keep open while implementing:

- `docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md`

### Current Evidence Baseline (Must Be Treated as Source of Truth)

- `T161` cache-off run `task161-20260313t212725z-cache-off`:
  steady-state train GPU median `26%`
- `T161` cache-on run `task161-20260313t212725z-cache-on`:
  steady-state train GPU median `8%`
- `T162` profile run `task162-20260313t220644z-profile`:
  steady-state train GPU median `3%`
- cache stats in all three runs were effectively dead:
  `cache_hits=0`, `cache_misses=0`, `cache_size=0`
- `T162` ROCm attribution:
  - HIP API `98.74s`
  - kernels `102.08s`
  - memory copy `1.73s`
  - top HIP API:
    `hipLaunchKernel=44.18s`,
    `hipMemcpyWithStream=21.52s`,
    `hipEventSynchronize=17.89s`

Interpretation:

- lane is host-orchestration/synchronization bound
- runtime ref-mel cache is not currently engaged in practice on this lane
- persistent `NaN` loss is a quality blocker for trustworthy saturation claims

### What Was Updated Before This Handoff

- Evidence and RCA synced into:
  - `task-161...md`
  - `task-162...md`
  - `story-26...md`
  - `epic-08...md`
  - `runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
  - `ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md`
  - `docs/backlog/current.md`
- New task docs created and filled:
  - `task-171...md`
  - `task-173...md`
  - `task-172...md`

Validation status for docs updates in this handoff:

- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`
- `PASS` `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Critical Environment / Repo Risks (Read Before Coding)

1. Local branch is `main` with substantial uncommitted Story 27 migration state.
1. Legacy `devops/taskXXX` scripts are deleted locally, while `pyproject` still
   contains old script entrypoints (for example `task-101-pilot`,
   `task-161-ref-mel-cache-comparison`, `task-162-task101-profiling`).
1. Some new CLI files under `scripts/sir_convert_a_lot/cli/ml/` still import
   old deleted `devops` modules.
1. Do not revert unrelated user changes. Work with the dirty tree.

Implication:

- First step for the implementer should be stabilizing executable command
  surfaces used by `T171/T173/T172` in the current domain-centric layout.

### Canonical Code Areas for T171/T173/T172

Training loop and hot-path behavior:

- `scripts/devops/qwen_finetuning_patches/sft_12hz.py`
- `scripts/devops/qwen_finetuning_patches/dataset.py`
- `scripts/devops/qwen_finetuning_patches/sft_12hz_tracking.py`
- `scripts/devops/qwen_finetuning_patches/sft_12hz_ref_mel_cache.py`

Domain-centric orchestration and reporting:

- `scripts/sir_convert_a_lot/ml/qwen/training/trainer.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/reporting.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/orchestrator.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/monitoring.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/metadata.py`
- `scripts/sir_convert_a_lot/ml/qwen/training/bundles.py`

Potential CLI surfaces to align:

- `scripts/sir_convert_a_lot/cli/ml/qwen_train.py`
- `scripts/sir_convert_a_lot/cli/ml/qwen_ref_mel_cache_comparison.py`
- `pyproject.toml` script entries for any affected commands

### Execution Plan (Do Not Reorder)

1. **T171**: remove per-step host sync overhead and add finite-loss guard.
1. Run focused tests + local gates.
1. Run bounded Hemma evidence for T171 and capture profile/monitor deltas.
1. **T173**: persist and consume precomputed reference inputs at bundle level.
1. Run focused tests + local gates.
1. Run bounded Hemma evidence for T173 and compare against T161 baseline.
1. **T172**: increase per-launch work (bucketing + vectorized codebook path).
1. Run focused tests + local gates.
1. Run bounded Hemma sweep and pick one default profile with evidence.
1. Update task/story docs with measured evidence only.

### Guardrails

- Do not close Story 26 in this slice.
- Do not claim acceptance from `NaN` runs.
- Do not claim saturation success without monitor-backed evidence.
- Use canonical wrappers:
  - local: `pdm run run-local-pdm <script>`
  - Hemma: `pdm run run-hemma -- <command>`
- Merge-only workflow; never rebase.
- BuildKit only.

### Minimum Required Gates Per Task

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root <focused-paths>`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Completion Standard for This Handoff Scope

This handoff scope is complete only when `T171`, `T173`, and `T172` each have:

- implementation complete
- validation complete
- live Hemma evidence attached in docs
- and Story 26 remains open unless its explicit saturation gate is actually met

## Session Update (2026-03-13, Story 27 T166-T170)

- Completed the domain-centric Qwen ML refactor implementation for Story 27
  and Tasks `166-170`, moving the canonical code surface to
  `scripts/sir_convert_a_lot/ml/qwen/` with `common/`, `preprocessing/`, and
  `training/` packages plus thin public CLI wrappers under
  `scripts/sir_convert_a_lot/cli/ml/`.
- Main implementation outcomes:
  - removed task-prefixed Qwen filenames and internal symbols from the active
    ML domain
  - decomposed former "god task" modules into SRP-aligned modules such as
    `asr.py`, `orchestrator.py`, `bundles.py`, and typed shared contracts
  - updated the Qwen Hemma container and the Qwen fine-tuning runbook to use
    the new domain-centric paths and command surfaces
- Current follow-up gap:
  - the moved tests under `tests/sir_convert_a_lot/ml/qwen/` still need the
    remaining import-path cleanup so the full Story 27 test surface is aligned
    with the new package layout
  - Story 27 backlog docs currently need final terminal status synchronization
    once that remaining test import cleanup is complete and verified

## Validation Status (Story 27 implementation)

- `NOT RUN IN THIS HANDOFF UPDATE` `pdm run format-all`
- `NOT RUN IN THIS HANDOFF UPDATE` `pdm run lint-fix`
- `PASS` `pdm run typecheck-all`
- `NOT YET PASSING / FOLLOW-UP REQUIRED` `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/`
- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`

## Active Blocker

- The remaining blocker for full Story 27 closure is import refactoring in the
  moved Qwen test modules under `tests/sir_convert_a_lot/ml/qwen/`; until that
  lands, the refactor implementation is complete but the test-alignment
  acceptance step is not yet closed.

## Immediate Next Step

- Start from the moved Qwen tests and finish import rewrites so they point at
  `scripts.sir_convert_a_lot.ml.qwen...` and the new `cli/ml/` wrappers rather
  than the removed `devops/taskXXX` modules.
- Run the focused Story 27 validation lane:
  - `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/`
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
- After the focused test lane passes, synchronize Story 27 / Tasks `166-170`
  backlog statuses and checklists to terminal state in strict hierarchy order.

## Session Update (2026-03-13, Story 26 T161-T162)

- Implemented the remaining Story 26 `T161` and `T162` code surfaces while
  preserving the live Hemma pilot rule (no branch switching or pilot stop).
- `T161` implementation outcomes:
  - added bounded runtime ref-mel cache module
    `scripts/devops/qwen_finetuning_patches/sft_12hz_ref_mel_cache.py`
  - wired cache into Task 101 dataset/trainer path and propagated cache config
    plus stats through Task 101 launch/runtime/probe/status/report contracts
  - added bounded Hemma comparison surface:
    `scripts/sir_convert_a_lot/devops/run_task161_hemma_ref_mel_cache_comparison.py`
    with helper module
    `scripts/sir_convert_a_lot/devops/task161_qwen_ref_mel_cache_runtime.py`
- `T162` implementation outcomes:
  - added bounded PyTorch profiling helper module
    `scripts/devops/qwen_finetuning_patches/sft_12hz_profiling.py`
  - patched trainer now supports opt-in profiler config plus phase markers for
    `batch-preparation`, `forward-backward`, `optimizer-step`, and
    `checkpoint-save`
  - added committed ROCm wrapper:
    `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe_with_rocprof.py`
    (explicit `--runtime-trace`, CSV output)
  - added bounded profiling orchestration and artifact collector:
    - `scripts/sir_convert_a_lot/devops/run_task162_hemma_task101_profiling.py`
    - `scripts/sir_convert_a_lot/devops/task162_qwen_profile_artifacts.py`
- Docs and runbook updates:
  - Story/task docs now include concrete implementation maps for `T161-T163`
  - `T161` and `T162` task docs moved to `in_progress` with local validation
    checklists updated
  - Qwen runbook now documents canonical `task-161-ref-mel-cache-comparison`
    and `task-162-task101-profiling` command surfaces

## Validation Status (T161-T162 local)

- `PASS` `pdm run format-all`
- `PASS` `pdm run lint-fix`
- `PASS` `pdm run typecheck-all`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_qwen_training_tracking.py tests/sir_convert_a_lot/test_task101_qwen_status_reporter.py tests/sir_convert_a_lot/test_qwen_training_ref_mel_cache.py tests/sir_convert_a_lot/test_task161_qwen_ref_mel_cache_comparison.py tests/sir_convert_a_lot/test_qwen_training_profiling.py tests/sir_convert_a_lot/test_task101_qwen_profiling.py tests/sir_convert_a_lot/test_task101_qwen_resource_monitor.py tests/sir_convert_a_lot/test_qwen_training_dataloader_tuning.py -q`
- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`
- `PASS` `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Active Blocker

- `T161` and `T162` still require live Hemma evidence artifacts to reach
  terminal status:
  - run the bounded cache-off/cache-on comparison surface and capture
    `build/verification/task-161-ref-mel-cache-comparison/<run-id>/`
  - run the bounded profiling surface and capture
    `build/verification/task-162-task101-profiling/<run-id>/`
  - record explicit `T164` go/no-go decision from real run evidence

## Immediate Next Step

- Commit and push the current Story 26 `T158-T162` implementation slice.
- On Hemma, keep merge-only workflow and wrapper-only execution:
  - `pdm run run-hemma -- git status --short`
  - `pdm run run-hemma -- git pull --ff-only`
- Run live bounded evidence captures:
  - `pdm run run-hemma -- pdm run task-161-ref-mel-cache-comparison`
  - `pdm run run-hemma -- pdm run task-162-task101-profiling`
- Use resulting artifacts to close `T161/T162` acceptance and then proceed to
  `T163` saturation-oriented profile/gate execution.

## Session Summary (2026-03-13)

- Implemented `T156` and `T157` in Story 26 order rather than skipping ahead.
- Code landed across:
  - `containers/qwen-finetune-hemma/requirements.txt`
  - `pyproject.toml`
  - `pdm.lock`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_progress.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_tracking.py`
  - `scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py`
  - `scripts/sir_convert_a_lot/devops/task100_qwen_finetune_smoke_probe.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_metadata.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe_reporting.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime_contract.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_status_reporter.py`
  - `tests/sir_convert_a_lot/test_qwen_training_resume.py`
  - `tests/sir_convert_a_lot/test_qwen_training_tracking.py`
  - `tests/sir_convert_a_lot/test_task100_qwen_finetune_smoke.py`
  - `tests/sir_convert_a_lot/test_task101_qwen_pilot.py`
  - `tests/sir_convert_a_lot/test_task101_qwen_status_reporter.py`
  - `docs/backlog/tasks/task-156-activate-first-class-mlflow-and-accelerate-tracking-for-task-101-qwen-training.md`
  - `docs/backlog/tasks/task-157-add-truthful-live-heartbeat-and-phase-accounting-to-the-task-101-qwen-pilot-runtime.md`
  - `docs/backlog/current.md`
- Main implementation outcomes:
  - governed Qwen dependencies now include `mlflow==3.10.1`, and the Task 101
    lane now initializes Accelerate tracking explicitly for MLflow plus
    TensorBoard rather than relying on the earlier half-wired posture
  - Task 101 launch/status/report artifacts now persist tracking metadata such
    as run name, experiment name, tracking URI, artifact roots, and live
    MLflow run ids once trackers initialize
  - `sft_12hz.py` now emits smoothed loss plus bounded live progress heartbeats
    with explicit phase accounting for `startup`, `train`,
    `checkpoint-save`, and `signal-stop`
  - the detached in-container probe now persists truthful `status.json`
    heartbeats during training, maintains `phase_history`, merges tracker
    metadata back into `launch.json`, and preserves the live fields in terminal
    completed/failed payloads
  - Task 101 markdown status rendering now surfaces live phase, step, loss,
    checkpoint timestamp, and MLflow run id directly instead of burying that
    information only inside the raw nested JSON block

## Validation Status

- `PASS` `pdm run format-all`
- `PASS` `pdm run lint-fix`
- `PASS` `pdm run typecheck-all`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/test_task100_qwen_finetune_smoke.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_qwen_training_tracking.py tests/sir_convert_a_lot/test_task101_qwen_status_reporter.py -q`
- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`
- `PASS` `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Active Blocker

- Local implementation and validation are complete for `T156` and `T157`.
- The remaining acceptance work is live Hemma evidence:
  verify that a resumed detached Task 101 run produces reviewable MLflow and
  TensorBoard artifacts while `status.json` updates truthfully during training.
- That Hemma acceptance proof is now active:
  - branch: `codex/story26-t156-t157-tracking-heartbeat`
  - launch id: `task101-20260313t184836z`
  - resumed checkpoint:
    `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001060`
  - live tracker proof:
    `mlflow_run_id=0e24db0d2c7642b8a6d8120551e260e2`
  - live TensorBoard proof:
    `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/trackers/tensorboard/task101-qwen-pilot/events.out.tfevents.1773427767.5c74d6ec17b4.1.0`
  - live heartbeat proof:
    `status.json` moved from `startup` to `train`, then recorded
    `checkpoint-save` at step `1062`, then returned to `train` with
    `current_step=1064`, `latest_loss=6.834901332855225`,
    `smoothed_loss=6.780460999965669`, and `latest_durable_checkpoint_step=1062`

## Immediate Next Step

- Commit and push the current Story 26 `T156` + `T157` slice.
- Pull the branch on Hemma through the canonical repo wrapper.
- Resume the detached Task 101 run from the latest durable checkpoint.
- Inspect the resumed run root for:
  - `status.json` heartbeat movement while training is still running
  - `launch.json` tracking metadata with live MLflow ids
  - TensorBoard event files under `trackers/tensorboard/`
  - MLflow artifacts and DB under `trackers/mlflow/`
- Next implementation step after this verified proof:
  begin `T158` so the high-resolution Hemma resource monitor becomes the
  canonical sibling surface for long Task 101 runs.

## Earlier Session Summary (2026-03-12)

- `T152` is now grounded in actual Hemma runtime truth rather than guesswork.
- Code landed across:
  - `scripts/sir_convert_a_lot/devops/task103_qwen_preprocessing_finalization.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_execution.py`
  - `tests/sir_convert_a_lot/test_task103_qwen_preprocessing_finalization.py`
  - `tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py`
- Main implementation outcomes:
  - direct preloaded-waveform encode path now bypasses the redundant tokenizer
    normalization loop and records per-chunk timing fields
  - batch-completed events now include machine-readable audio-code timing
    evidence:
    `audio_codes_preload_seconds`,
    `audio_codes_feature_extract_seconds`,
    `audio_codes_model_encode_seconds`,
    `audio_codes_write_seconds`,
    `audio_codes_chunk_total_seconds`,
    `audio_codes_batch_total_seconds`,
    plus effective chunk-size and OOM-retry fields
  - attempted in-batch OOM backoff/reset logic was implemented and tested
    locally, but live Hemma proof showed that requested
    `audio_codes_chunk_size=128` is still not viable on the current governed
    lane
  - the public Task 101 default is now back to `audio_codes_chunk_size=64`
    because `128` repeatedly OOMed on Hemma
- Hemma benchmark truth:
  - baseline:
    `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312c/baseline-chunk8-span1`
    - `swedish_pilot_train:batch-00000` = `9m 02s`
  - preload + chunk64:
    `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312e-hostuser/preload-chunk64-span1`
    - `swedish_pilot_train:batch-00000` = `7m 07s`
  - direct-encode + chunk64:
    `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1`
    - `duration_seconds=481.3638345239997`
    - `rows_per_minute=15.954667652991478`
    - train batch timing from `reports/task101_pilot_bundle_events.jsonl`:
      `audio_codes_model_encode_seconds=424.4988881419995` out of
      `audio_codes_chunk_total_seconds=425.61176394299764`
  - requested `chunk128` proofs that failed on Hemma:
    - `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312f/direct-encode-chunk128-span1`
    - `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312g/direct-encode-chunk128-span1`
    - `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312i/direct-encode-chunk128-span1`
- Commits pushed:
  - `07b9e31` `Cut Task 101 audio-code overhead further`
  - `480f016` `Back off Task 101 audio-code chunks on GPU OOM`
  - `fb14eda` `Reset warm Task 101 encoder after GPU OOM`

## Validation Status

- `PASS` `pdm run format-all`
- `PASS` `pdm run lint-fix`
- `PASS` `pdm run typecheck-all --cache-dir /tmp/scl-mypy-cache-task152-final`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/test_task103_qwen_preprocessing_finalization.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle_runtime.py tests/sir_convert_a_lot/test_run_task152_hemma_task101_finalization_benchmark.py -q`
- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`
- `PASS` `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `PASS` Hemma governed benchmark:
  - `direct-encode-chunk64-span1`
  - benchmark root:
    `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1`

## Active Blocker

- No blocking implementation bug remains in the stable chunk-64 governed lane.
- The remaining limitation is runtime truth: model encode dominates, and
  requested `chunk128` is not safe on the current Hemma GPU posture.

## Immediate Next Step

- Rerun the stopped bounded Hemma Task 101 pilot-bundle root through the
  governed `build` surface with the stable defaults:
  - `audio_codes_chunk_size=64`
  - `container_batch_span=4`
- Inspect:
  - `reports/task101_pilot_bundle_plan.json`
  - `reports/task101_pilot_bundle_events.jsonl`
  - `reports/task101_pilot_bundle_status.json`
  - `reports/task101_pilot_bundle_runtime.json`
  - `reports/task101_pilot_bundle_audio_codes_runtime.json`
- Treat any future `chunk128` retry as a new experiment, not as the default
  production path, unless the runtime or hardware changes.
