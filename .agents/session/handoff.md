# Session Handoff

## Current Session Summary (2026-03-07)

- Started the active `T85` F5-TTS lane after the documented negative quality decision on `T81`
  OpenVoice.
- Added the dedicated F5 implementation slice:
  - `containers/tts-sidecar-f5/Dockerfile`
  - `scripts/sir_convert_a_lot/tts_sidecar/f5_app.py`
  - `scripts/sir_convert_a_lot/tts_sidecar/f5_runtime.py`
  - `scripts/sir_convert_a_lot/devops/run_task85_hemma_f5_smoke.py`
  - `tests/sir_convert_a_lot/test_tts_sidecar_f5_adapter.py`
  - `pdm run benchmark:task-85`
- Added one important benchmark usability fix before remote execution:
  - `run_task85_hemma_f5_smoke.py` now accepts `--reference-transcript-file`, so the canonical
    Hemma run can stay in argv mode instead of relying on shell interpolation for transcript text.
- Prepared deterministic F5 reference-input evidence:
  - source clip: `build/verification/task-85-f5-tts-hemma/inputs/reference_source_sv.m4a`
  - prepared clip: `build/verification/task-85-f5-tts-hemma/inputs/reference_10s_sv.wav`
  - prepared clip properties: `10.000000` seconds, `24 kHz`, mono
  - Whisper transcript:
    `Jag har ofta tänkt på att man inte ska liksom ta scenen dit man kommer, men vad vet jag om det?`
- Pushed branch `codex/task85-f5-tts-hemma` and switched the Hemma repo clone to the same commit:
  - branch head: `f1343104e625a5118fe713c0a10f8f5c41ea00c3`
- Ran the first real Task 85 Hemma benchmark successfully:
  - the dedicated F5 image built successfully,
  - `f5-tts_infer-cli --help` passed inside the running sidecar,
  - the sidecar reached ready state in `6.153` seconds,
  - `sir_convert_a_lot_prod` could probe the sidecar internally,
  - the benchmark synthesized and preserved
    `build/verification/task-85-f5-tts-hemma/artifacts/sample_sv.wav`.
- The successful T85 evidence bundle now exists both on Hemma and locally:
  - `build/verification/task-85-f5-tts-hemma/report.json`
  - `build/verification/task-85-f5-tts-hemma/report.md`
  - `build/verification/task-85-f5-tts-hemma/f5_help.txt`
  - `build/verification/task-85-f5-tts-hemma/docker_logs.txt`
  - `build/verification/task-85-f5-tts-hemma/reference_transcript.txt`
  - `build/verification/task-85-f5-tts-hemma/artifacts/sample_sv.wav`
- The successful run recorded the exact Swedish model inventory:
  - `model_last.pt`
  - `setting.json`
  - `vocab.txt`
- The remaining Task 85 work is qualitative:
  - listen to the F5 sample,
  - compare it against the preserved OpenVoice Task 81 baseline,
  - record whether F5 becomes the lead Swedish teacher-voice candidate.

Validation evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_tts_sidecar_f5_adapter.py -q` (pass: `3 passed`)
- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass: `Success: no issues found in 232 source files`)
- `pdm run validate-tasks` (pass: `Validated 120 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=151 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

Known remaining work / current state:

- `T85` is technically successful but not recommendation-complete.
- Current T85 local/remote evidence path:
  - `build/verification/task-85-f5-tts-hemma/`
- Current T85 synthesized artifact:
  - `build/verification/task-85-f5-tts-hemma/artifacts/sample_sv.wav`
- Current T85 successful output properties:
  - `24 kHz`
  - mono
  - duration `15.423333` seconds
- Current Task 81 comparison baseline remains:
  - `build/verification/task-81-openvoice-v2-hemma/artifacts/sample_sv.wav`

## Next Session Goals (2026-03-07)

- Perform listening review of `T85` against the preserved `T81` OpenVoice baseline.
- Record explicit comparison notes in `task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md`
  and `story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md`.
- Decide whether F5-TTS becomes the lead Swedish teacher-voice candidate or whether Story 23
  must advance to `T83` and potentially reopen the deferred `T82` comparison.
