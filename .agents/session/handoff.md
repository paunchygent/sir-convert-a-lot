# Session Handoff

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
