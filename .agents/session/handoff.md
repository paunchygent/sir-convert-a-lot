# Session Handoff

## Current Session Summary (2026-03-06)

- Started `T81` (`docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md`) against `ADR-0007`.
- Added the first reusable normalized internal TTS sidecar contract and FastAPI app factory:
  - `scripts/sir_convert_a_lot/tts_sidecar/contracts.py`
  - `scripts/sir_convert_a_lot/tts_sidecar/app_factory.py`
- Added the first backend-specific adapter around OpenVoice V2 with Swedish MMS base synthesis:
  - `scripts/sir_convert_a_lot/tts_sidecar/openvoice_runtime.py`
  - `scripts/sir_convert_a_lot/tts_sidecar/openvoice_app.py`
- Added the dedicated OpenVoice sidecar image build surface:
  - `containers/tts-sidecar-openvoice/Dockerfile`
- Added the Hemma benchmark/report command surface for Task 81:
  - `scripts/sir_convert_a_lot/devops/run_task81_hemma_openvoice_benchmark.py`
  - `scripts/sir_convert_a_lot/devops/task81_openvoice_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task81_openvoice_reporting.py`
  - `pdm run benchmark:task-81`
- Added local regression coverage for the normalized contract and Task 81 harness:
  - `tests/sir_convert_a_lot/test_tts_sidecar_openvoice_adapter.py`
  - `tests/sir_convert_a_lot/test_task81_openvoice_benchmark.py`
- Updated docs/runbook/task state for the new implementation slice:
  - `docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md`
  - `docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - `docs/backlog/current.md`
- Important design choice in the current implementation:
  - the Task 81 adapter uses `facebook/mms-tts-swe` as the Swedish base speaker,
  - then applies OpenVoice V2 tone-color conversion for cloning,
  - which keeps the benchmark honest about Swedish generation instead of faking unsupported output.

Validation evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_tts_sidecar_openvoice_adapter.py tests/sir_convert_a_lot/test_task81_openvoice_benchmark.py -q` (pass: `11 passed`)
- `pdm run format-all` (pass)
- `pdm run typecheck-all` (pass: `Success: no issues found in 227 source files`)
- `pdm run validate-tasks` (pass before implementation and pending final rerun after docs closeout)
- `pdm run validate-docs` (pass before implementation and pending final rerun after docs closeout)

Known remaining work / current state:

- `lint-fix` exposed a docs-governance issue in `docs/backlog/current.md`; this session already compressed the file back under the 220-line limit, but the full repo-wide validation/lint pass still needs one clean rerun.
- The live Hemma benchmark has not been executed yet in this implementation session.
- The approved teacher reference clip is currently available locally at:
  - `/Users/olofs_mba/Library/Containers/com.apple.VoiceMemos/Data/tmp/.com.apple.uikit.itemprovider.temporary.PCc9m1/Övre Olskroksgatan 10.m4a`
- The approved teacher reference clip is cloning input only; Task 81 no longer couples that clip to transcript evidence.

## Next Session Goals (2026-03-06)

- Rerun the remaining repo-wide gates now that `current.md` is compressed:
  - `pdm run lint-fix`
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- Stage the approved teacher reference clip onto Hemma in a disciplined way, then execute:
  - `pdm run run-hemma -- pdm run benchmark:task-81 --reference-audio <remote-path>`
- Capture deterministic evidence under `build/verification/task-81-openvoice-v2-hemma/` and listen to the generated Swedish sample.
- If Task 81 runtime/bootstrap fails on Hemma, debug it without adding hidden fallbacks or container-local long-lived cache paths.
- Once live evidence exists, decide whether OpenVoice V2 remains the primary cloning-capable Swedish candidate before moving to `T82` and `T83`.
