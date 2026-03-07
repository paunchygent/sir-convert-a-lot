# Session Handoff

## Current Session Summary (2026-03-07)

- `T85` is now closed as a technically successful but qualitatively rejected Swedish cloning lane.
- Implemented the active `T86` Chatterbox Multilingual benchmark slice:
  - `containers/tts-sidecar-chatterbox/Dockerfile`
  - `scripts/sir_convert_a_lot/tts_sidecar/chatterbox_app.py`
  - `scripts/sir_convert_a_lot/tts_sidecar/chatterbox_runtime.py`
  - `scripts/sir_convert_a_lot/devops/run_task86_hemma_chatterbox_benchmark.py`
  - `scripts/sir_convert_a_lot/devops/task86_chatterbox_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task86_chatterbox_reporting.py`
  - `tests/sir_convert_a_lot/test_tts_sidecar_chatterbox_adapter.py`
  - `tests/sir_convert_a_lot/test_task86_chatterbox_benchmark.py`
  - `pdm run benchmark:task-86`
- Kept the implementation inside the documented Hemma-first execution model:
  - canonical remote wrapper `pdm run run-hemma -- ...`
  - BuildKit image builds
  - internal-only sidecar network contract from ADR-0007
- Resolved the initial Hemma GPU runtime mismatch:
  - first live run failed with `HIP error: invalid device function`,
  - current container runtime now uses `torch==2.10.0+rocm7.1` and `torchaudio==2.10.0+rocm7.1`,
  - upstream Chatterbox package is still `chatterbox-tts==0.1.6`.
- Ran the first successful live Task 86 Hemma benchmark on commit
  `a93bf39edcf62b456bf65eff4e4b5f20b23ce769`.
- Current successful T86 evidence on Hemma:
  - `build/verification/task-86-chatterbox-hemma/report.json`
  - `build/verification/task-86-chatterbox-hemma/report.md`
  - `build/verification/task-86-chatterbox-hemma/capabilities.json`
  - `build/verification/task-86-chatterbox-hemma/voices.json`
  - `build/verification/task-86-chatterbox-hemma/package_versions.json`
  - `build/verification/task-86-chatterbox-hemma/gpu-before.txt`
  - `build/verification/task-86-chatterbox-hemma/gpu-after.txt`
  - `build/verification/task-86-chatterbox-hemma/docker_logs.txt`
  - `build/verification/task-86-chatterbox-hemma/artifacts/smoke-test-en.wav`
  - `build/verification/task-86-chatterbox-hemma/artifacts/scenario-a-sv-ref-sv-out.wav`
- Verified runtime truth from the live Hemma report:
  - backend: `chatterbox_multilingual`
  - Swedish support: `official`
  - reference transcript required: `false`
  - first startup: `33.207` seconds
  - warm restart: `21.065` seconds
  - smoke probe peak VRAM: `7714471936` bytes
  - Swedish clone peak VRAM: `8982421504` bytes
  - GPU: `AMD Radeon AI PRO R9700` (`gfx1201`)
  - cached model snapshot reused from
    `/srv/scratch/sir-convert-a-lot/cache/huggingface/models--ResembleAI--chatterbox/snapshots/05e904af2b5c7f8e482687a9d7336c5c824467d9`
- Updated docs-as-code records for Task 86 in:
  - `docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md`
  - `docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md`
  - `docs/backlog/current.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`

Validation evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_tts_sidecar_chatterbox_adapter.py tests/sir_convert_a_lot/test_task86_chatterbox_benchmark.py -q` (pass: `9 passed`)
- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run validate-tasks` (pass)
- `pdm run validate-docs` (pass)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

Known remaining work / current state:

- `T86` is technically successful but not recommendation-complete.
- The evidence bundle currently exists on Hemma; it has not been mirrored back to the laptop repo.
- The next decision is qualitative:
  - listen to `scenario-a-sv-ref-sv-out.wav`,
  - compare it against `T81` OpenVoice and `T85` F5-TTS,
  - decide whether Chatterbox becomes the lead Swedish teacher-voice candidate.

## Next Session Goals (2026-03-07)

- Perform listening review of the successful `T86` Swedish cloning artifact.
- Record explicit comparison notes in
  `task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md`
  and `story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md`.
- Decide whether Chatterbox becomes the new lead Swedish cloning candidate or whether Story 23
  advances to `T83`.
