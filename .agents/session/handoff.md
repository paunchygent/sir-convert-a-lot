# Session Handoff

## Session Summary (2026-03-12)

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
