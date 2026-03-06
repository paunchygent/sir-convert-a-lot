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
- Live `T81` benchmark now exists on Hemma and has reached technical success:
  - sidecar booted,
  - canonical caches were reused,
  - Swedish cloned output was generated from the approved teacher reference clip.
- Manual listening review rejected the current sample quality:
  - timbre not close enough to the teacher voice,
  - strange artifacts,
  - uneven pacing.
- Current conclusion:
  - the pipeline works,
  - the current model setup is bad,
  - `T81` remains open for setup remediation and rerun.
- The remediation order is now implementation-grounded:
  - fix the sample-rate mismatch between the Swedish base model and the OpenVoice converter,
  - switch the reference clip to the intended OpenVoice preprocessing path,
  - preserve processed-reference plus base-vs-cloned artifacts in the next rerun.
- The local remediation slice is now implemented:
  - `scripts/sir_convert_a_lot/tts_sidecar/openvoice_support.py` owns the OpenVoice-specific
    VAD-only reference preprocessing and runtime helpers,
  - `openvoice_runtime.py` is back under the 500-line split guideline,
  - the sidecar image no longer installs `faster-whisper`, which was the broken PyAV build path
    on Hemma Python 3.12,
  - the main service image remains untouched.

Validation evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_tts_sidecar_openvoice_adapter.py tests/sir_convert_a_lot/test_task81_openvoice_benchmark.py -q` (pass: `11 passed`)
- `pdm run format-all` (pass)
- `pdm run typecheck-all` (pass: `Success: no issues found in 227 source files`)
- `pdm run validate-tasks` (pass before implementation and pending final rerun after docs closeout)
- `pdm run validate-docs` (pass before implementation and pending final rerun after docs closeout)

Known remaining work / current state:

- The approved teacher reference clip is currently available locally at:
  - `/Users/olofs_mba/Library/Containers/com.apple.VoiceMemos/Data/tmp/.com.apple.uikit.itemprovider.temporary.PCc9m1/Övre Olskroksgatan 10.m4a`
- The approved teacher reference clip is cloning input only; Task 81 no longer couples that clip to transcript evidence.
- Current Hemma evidence path:
  - `build/verification/task-81-openvoice-v2-hemma/`
- Current failed-quality artifact baseline:
  - `build/verification/task-81-openvoice-v2-hemma/artifacts/sample_sv.wav`
- The next work is setup remediation, not more infrastructure proving.
- The next rerun must preserve:
  - the processed reference artifact,
  - the Swedish base artifact before cloning,
  - the corrected cloned artifact after conversion.

## Next Session Goals (2026-03-06)

- Preserve the current failed-quality `T81` sample as baseline evidence.
- Correct the OpenVoice setup rather than adding more analysis:
  - the code/setup fixes are already in place locally and validated,
  - the next action is to rerun the benchmark with the rebuilt sidecar image on Hemma using the
    same approved teacher reference clip.
- Update `Task 81` and `Story 23` with:
  - what changed in setup,
  - whether artifacts/pacing improved,
  - whether timbre match improved enough to keep OpenVoice credible.
- If the corrected setup is still poor, record OpenVoice as technically feasible but not the lead
  Swedish teacher-voice candidate, then proceed to `T82`.
