# Session Handoff

## Session Summary (2026-03-13)

- Completed `T154` to reconcile the post-`T153` runtime, test, and docs gaps.
- Completed `T155` to bring the remaining Qwen checkpoint and Task 101 pilot
  god files and remaining runtime/probe surfaces back into SRP alignment
  without changing runtime contracts.
- Code landed across:
  - `scripts/devops/qwen_finetuning_patches/sft_12hz.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_checkpointing.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_training_rows.py`
  - `scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_metadata.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime_contract.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime_artifacts.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe_reporting.py`
  - `tests/sir_convert_a_lot/test_qwen_training_resume.py`
  - `tests/sir_convert_a_lot/test_task101_qwen_pilot.py`
  - `docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md`
  - `docs/backlog/tasks/task-154-remediate-t153-checkpoint-compatibility-scratch-guard-sizing-and-docs-proof-drift.md`
  - `docs/backlog/tasks/task-155-refactor-qwen-checkpoint-and-task-101-pilot-god-files-into-srp-modules.md`
  - `docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md`
  - `docs/backlog/current.md`
- Main implementation outcomes:
  - pre-`T153` Task 101 `launch.json` payloads now fall forward with canonical
    durable-checkpoint defaults during `status` and `resume`
  - first durable-checkpoint saves now use a conservative fallback size based
    on the measured Hemma trainer-state footprint
  - durable trainer-state saves now stage through an incomplete directory and
    clean failed attempts so one bad save does not wedge the same step forever
  - the focused regression tests now prove validation-before-prune ordering,
    export preservation, first-save threshold behavior, and launch/status/report
    checkpoint-policy fields
  - durable checkpoint persistence now lives in its own helper module, training
    row manifest resolution now lives in its own helper module, and the
    patched `sft_12hz.py` entrypoint is back under `500` lines
  - detached Task 101 metadata/path/status parsing and artifact rendering now
    live in a dedicated helper module, and
    `run_task101_hemma_qwen_pilot.py` is back under `500` lines
  - detached Task 101 runtime contracts and artifact/Docker-inspect parsing
    now live in dedicated helper modules, and
    `task101_qwen_pilot_runtime.py` is down to `272` lines
  - in-container probe report/status payload assembly now lives in a dedicated
    helper module, and `task101_qwen_pilot_probe.py` is down to `146` lines
  - Task 101, Story 25, `current.md`, and the session handoff now agree on the
    bounded pilot state and the active Epic 08 lane

## Validation Status

- `PASS` `pdm run format-all`
- `PASS` `pdm run lint-fix`
- `PASS` `pdm run typecheck-all`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`
- `PASS` `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Active Blocker

- No remediation blocker remains in the bounded checkpoint contract or its
  planning surfaces.
- The remaining decision is operational: choose the real Task 101 uncapped
  launch settings and start the run under the remediated bounded checkpoint
  contract.

## Immediate Next Step

- Launch the uncapped Hemma Task 101 run from the completed governed pilot
  bundle using the remediated bounded checkpoint policy:
  - `durable_checkpoint_retention=2`
  - `durable_checkpoint_min_free_bytes=17179869184`
- Observe `latest_checkpoint.json`, `status.json`, `report.json`, and
  `/srv/scratch` free space during the first checkpoint interval to confirm the
  live first-save behavior matches the conservative fallback estimate.

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
