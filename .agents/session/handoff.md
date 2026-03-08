# Session Handoff

## Current Session Summary (2026-03-08)

- Committed and pushed the Task 85 runtime-source switch to `main`:

  - `ec17e180efb48ad8f228e1df15f4e597ade156ff` switches the F5 sidecar from
    `SWivid/F5-TTS@1.1.17` to `ChiliOlavi/F5-TTS@swedish-tts`
  - `af36f5085d137bc20116086376e4d7e9b36dc9b1` adds `torchcodec` to the image
    so the branch-backed runtime can complete `torchaudio.load()`

- Ran the canonical live Hemma `T85` benchmark on the updated repo head:

  - command:
    `pdm run run-hemma -- pdm run benchmark:task-85 --reference-audio build/verification/task-85-f5-tts-hemma/inputs/reference_10s_sv.wav --reference-transcript-file build/verification/task-85-f5-tts-hemma/inputs/reference_10s_sv.txt`
  - branch-backed rerun succeeded with:
    - `run_id=20260308T002337Z`
    - `repo_head=af36f5085d137bc20116086376e4d7e9b36dc9b1`
    - `image_id=sha256:e69ffa81f883369bbde227fee1d910da3b249484c0e595e210011b147e6eb04e`
    - `readiness_seconds=6.123`
    - `sample_sha256=2735c0536aebc3f5324333d3a9deb95492721230b2e10ff3d4989019078e1c82`

- Synced the refreshed Hemma evidence back locally under:

  - `build/verification/task-85-f5-tts-hemma/report.json`
  - `build/verification/task-85-f5-tts-hemma/report.md`
  - `build/verification/task-85-f5-tts-hemma/docker_logs.txt`
  - `build/verification/task-85-f5-tts-hemma/f5_help.txt`
  - `build/verification/task-85-f5-tts-hemma/reference_transcript.txt`
  - `build/verification/task-85-f5-tts-hemma/artifacts/sample_sv.wav`

- `T85` is closed as a technically successful but qualitatively rejected Swedish cloning lane.

- `T86` remains the canonical Chatterbox benchmark surface on Hemma and has already been proven
  end to end with official multilingual runtime startup, smoke synthesis, and Swedish cloning.

- Implemented and merged `T89`:

  - `containers/textprep-espeak-phonemizer/Dockerfile`
  - `scripts/sir_convert_a_lot/textprep/__init__.py`
  - `scripts/sir_convert_a_lot/textprep/espeak_phonemizer_cli.py`
  - `scripts/sir_convert_a_lot/devops/run_task89_chatterbox_espeak_experiment.py`
  - `scripts/sir_convert_a_lot/devops/run_task89_hemma_chatterbox_espeak_experiment.py`
  - `tests/sir_convert_a_lot/test_task89_chatterbox_espeak.py`

- Extended the Task 86 benchmark surface to support file-backed text input via
  `--probe-text-file`.

- Fixed two real runtime issues discovered while running `T89` on Hemma:

  - Chatterbox startup was relying on a live `spacy_pkuseg` model download, so
    `containers/tts-sidecar-chatterbox/Dockerfile` now prefetches the
    `spacy_ontonotes` asset during image build.
  - Task 89 could not explicitly request a Chatterbox image rebuild; the
    benchmark surface now uses `--build-benchmark-image` for that path.

- Completed the live Hemma `T89` experiment and synced the evidence bundle back locally:

  - `build/verification/task-89-chatterbox-espeak-hemma/report.json`
  - `build/verification/task-89-chatterbox-espeak-hemma/report.md`
  - `build/verification/task-89-chatterbox-espeak-hemma/baseline/artifacts/scenario-a-sv-ref-sv-out.wav`
  - `build/verification/task-89-chatterbox-espeak-hemma/espeak_sv/artifacts/scenario-a-sv-ref-sv-out.wav`
  - `build/verification/task-89-chatterbox-espeak-hemma/inputs/probe_text_original.txt`
  - `build/verification/task-89-chatterbox-espeak-hemma/inputs/probe_text_espeak_sv.txt`
  - `build/verification/task-89-chatterbox-espeak-hemma/inputs/espeak_metadata.json`

- Verified runtime truth from the live `T89` reports:

  - baseline lane: `duration_seconds=32.571`, `peak_vram_used_bytes=8898465792`
  - eSpeak lane: `duration_seconds=41.997`, `peak_vram_used_bytes=9103962112`
  - Chatterbox image rebuilt successfully on Hemma after the deterministic
    `spacy_pkuseg` prefetch fix
  - helper image reused successfully without rebuild

- Cleaned up dangling Hemma images after the failed attempts:

  - removed dangling images only
  - did not touch BuildKit/build cache
  - reclaimed `14.77GB`

- Implemented and ran `T90` on live Hemma:

  - deterministic segmentation, chunk execution, and cross-fade stitching are
    now part of the Chatterbox sidecar path
  - evidence is synced locally under
    `build/verification/task-90-chatterbox-segmented-hemma/`
  - single-pass Swedish clone duration: `51.904`, peak VRAM `5959815168`
  - segmented Swedish clone duration: `57.473`, peak VRAM `5742292992`
  - segmented debug evidence includes:
    - `segment_plan.json`
    - `chunk_01.wav`
    - `chunk_02.wav`
    - `chunk_03.wav`
    - `stitched.wav`

- Updated docs-as-code records for:

  - `docs/backlog/tasks/task-89-implement-benchmark-only-espeak-ng-preprocessing-for-chatterbox-swedish-lanes.md`
  - `docs/backlog/tasks/task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma.md`
  - `docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md`
  - `docs/reference/ref-espeak-ng-swedish-phoneme-integration-for-chatterbox.md`
  - `docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md`
  - `docs/backlog/current.md`

- Switched the current Task 85 F5 runtime source locally from
  `SWivid/F5-TTS@1.1.17` to `ChiliOlavi/F5-TTS@swedish-tts`:

  - `containers/tts-sidecar-f5/Dockerfile` now clones the ChiliOlavi fork by default
  - Task 85 runtime defaults/reporting now advertise backend version `swedish-tts`
  - Task 85 docs now explicitly mark the preserved Hemma evidence as pre-switch and require a rerun

Validation evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_tts_sidecar_chatterbox_adapter.py tests/sir_convert_a_lot/test_task86_chatterbox_benchmark.py -q` (pass: `9 passed`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_task86_chatterbox_benchmark.py tests/sir_convert_a_lot/test_task89_chatterbox_espeak.py -q` (pass: `12 passed`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_tts_sidecar_f5_adapter.py -q` (pass: `3 passed`)
- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run coverage-gate` (pass: `545 passed, 5 skipped`, total coverage `95.99%`)
- `pdm run validate-tasks` (pass)
- `pdm run validate-docs` (pass)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

Known remaining work / current state:

- `T89` is complete.
- `T90` implementation and Hemma benchmark evidence are complete, but the task
  is still open for the qualitative comparison verdict.
- Story 23 is still not recommendation-complete; the next qualitative decision
  is whether the segmented Chatterbox result is better, worse, or unchanged
  versus the single-pass baseline.

## Next Session Goals (2026-03-07)

- Listen to the Task 90 single-pass and segmented Chatterbox outputs.
- Record the qualitative verdict in `T90` and Story 23.
- Decide whether Chatterbox remains the lead Swedish cloning candidate or
  whether Story 23 advances to `T83`.
