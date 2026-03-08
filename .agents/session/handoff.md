# Session Handoff

## Current Session Summary (2026-03-08)

- Opened the new Epic 08 Qwen Swedish fine-tuning lane as a parallel track to
  Epic 07 rather than overloading the existing sidecar-delivery scope:

  - `docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md`
  - `docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md`
  - `docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md`
  - `docs/backlog/tasks/task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark.md`
  - `docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md`
  - `docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md`
  - `docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md`
  - `docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md`
  - `docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md`

- Added the dedicated Qwen Swedish fine-tuning operational surfaces:

  - `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
  - `.agents/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md`
  - `.agents/skills/speech-model-finetuning-on-hemma/SKILL.md`

- Re-enabled Triton flash attention as the default in the Task 79 Qwen Hemma
  benchmark lane:

  - `scripts/sir_convert_a_lot/devops/run_task79_hemma_tts_sidecar_benchmark.py`
  - `scripts/sir_convert_a_lot/devops/task79_hemma_tts_sidecar_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task79_hemma_tts_sidecar_reporting.py`
  - `tests/sir_convert_a_lot/test_task79_hemma_tts_sidecar_benchmark.py`
  - benchmark reports now record whether Triton flash attention was enabled

- Cross-linked the existing TTS planning docs so Epic 07 / Story 23 stay
  delivery-and-benchmark focused while Epic 08 owns the Sir-trained Qwen lane:

  - `docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md`
  - `docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md`
  - `docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - `docs/backlog/current.md`

- Added the research-handoff surface for the next Epic 08 decisions:

  - `docs/backlog/tasks/task-105-build-qwen3-tts-swedish-finetuning-research-repomix-package.md`
  - `docs/reference/ref-qwen3-tts-swedish-finetuning-research-map-2026-03-08.md`
  - `.agents/repomix_packages/research-qwen3-swedish-finetuning-brief.md`
  - `.agents/repomix_packages/repomix-qwen3-swedish-finetuning-research-context.xml`

- Validation evidence for this session's Qwen planning/runtime work:

  - `pdm run format-all` (pass after cleanup)
  - `pdm run lint-fix` (pass)
  - `pdm run typecheck-all` (pass)
  - `pdm run pytest-root tests/sir_convert_a_lot/test_task79_hemma_tts_sidecar_benchmark.py -q` (pass: `15 passed`)
  - `pdm run validate-tasks` (pass)
  - `pdm run validate-docs` (pass)
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

- Implemented and pushed `e3a3a83be2656f2ad1bae46dad83a59fcbc5c1dc`
  (`feat: align F5 reference duration and add segmented lane`):

  - the F5 sidecar reference-prep cap is now configurable and defaults to
    `12.0` seconds instead of the earlier hard `10`
  - Task 85 now supports a repo-owned segmented F5 lane with deterministic
    segment planning, chunk artifacts, stitching, and segment-debug evidence
  - the public ADR-0007 sidecar contract is unchanged; segmentation lives at
    the benchmark layer

- Ran the live Hemma `T97` corrected Christian Hedlund rerun successfully:

  - command root:
    `pdm run run-hemma -- pdm run benchmark:task-85 --output-root build/verification/task-97-f5-reference-12s-hemma ... --reference-max-seconds 12.0`
  - succeeded with:
    - `run_id=20260308T015946Z`
    - `repo_head=e3a3a83be2656f2ad1bae46dad83a59fcbc5c1dc`
    - `image_id=sha256:f2161b09aefd1b000b4a6c8476e334784dd00ce9f7d5a7101259e458a53eafab`
    - `reference_audio_duration_seconds=11.5`
    - `sample_sha256=46c31cbb6f8eb685d64a321afde81e5387c60fed444d6d9ba2e71d91bf9f9ab7`
    - output duration `18.538` seconds
  - synced evidence locally under
    `build/verification/task-97-f5-reference-12s-hemma/`

- Ran the live Hemma segmented `T97` comparison lane successfully:

  - command root:
    `pdm run run-hemma -- pdm run benchmark:task-85 --output-root build/verification/task-97-f5-segmented-hemma ... --segment-text --segment-max-chars 160 --segment-cross-fade-ms 80 --segment-stitch-mode simple --skip-build`
  - succeeded with:
    - `run_id=20260308T020119Z`
    - `repo_head=e3a3a83be2656f2ad1bae46dad83a59fcbc5c1dc`
    - reused image `sha256:f2161b09aefd1b000b4a6c8476e334784dd00ce9f7d5a7101259e458a53eafab`
    - `segment_count=4`
    - `sample_sha256=12255eb80ab66b897425b00c09ab8feb87243e7e1008afacdcc25d7e14307b01`
    - output duration `18.362` seconds
  - synced evidence locally under
    `build/verification/task-97-f5-segmented-hemma/`

- Current `T97` recommendation is evidence-backed:

  - the biggest improvement came from fixing the `10s`/`11.5s` reference
    mismatch
  - segmented F5 is worth keeping as a comparison/debug lane
  - segmented F5 is not yet justified as the default path because its measured
    output length is very close to the corrected single-pass run

- Implemented and pushed `ec3d6ebecf9de24de6aab3d8c836ffc4e7aa2254`
  (`feat: expose F5 tuning controls on Hemma`):

  - Task 85 now exposes `speed`, `fix_duration`, `cross_fade_duration`,
    `target_rms`, `load_vocoder_from_local`, and `--probe-text-file`
  - the F5 sidecar now writes file-backed prompt text through `gen_file`
  - opened and documented `T95` for the exact upstream F5 voice-tag surface

- Ran the live Hemma `T95` Christian Hedlund reference rerun successfully:

  - command root:
    `pdm run run-hemma -- pdm run benchmark:task-85 --output-root build/verification/task-95-f5-tuning-controls-and-exact-voice-tag-support-on-hemma ...`
  - succeeded with:
    - `run_id=20260308T012850Z`
    - `repo_head=ec3d6ebecf9de24de6aab3d8c836ffc4e7aa2254`
    - `image_id=sha256:3ab9b7a15f25da99ea677670a3bce217055cf2a06ec4be2d54f1166d7d21327e`
    - `readiness_seconds=3.13`
    - `sample_sha256=50b38ad889dbe993668c370d28092c7a3e867052dffe7dc2e1e3c5f7a25117c5`
  - synced evidence locally under
    `build/verification/task-95-f5-tuning-controls-and-exact-voice-tag-support-on-hemma/`

- Confirmed exact upstream `infer_cli` voice-tag behavior:

  - accepted form is `[voice_name]`
  - actual parser regex is `\[(\w+)\]`
  - unknown/missing tags fall back to `main`
  - no explicit IPA or SSML/paralinguistic tag support was found in the
    installed CLI path

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
