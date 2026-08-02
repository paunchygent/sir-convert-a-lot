---
id: review-31-ruthless-review-of-task-352-live-hemma-stt-sidecar-benchmark-profile-proof
title: Ruthless review of Task 352 live Hemma STT sidecar benchmark profile proof
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-351-add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/reviews/review-27-ruthless-review-of-story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - review
  - approved
  - task-352
  - stt
  - diarization
  - benchmark
  - hemma
  - sidecar
  - gpu
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless implementation review of Task 352's current workspace
  diff.
- Decision frame: Task 352 may be accepted only if it provides a governed live
  Hemma STT sidecar benchmark/profile-proof surface. Dry-run, projection, or
  caller-supplied report evidence cannot supersede Story 52's accepted
  production-profile rejection.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/tasks/task-351-add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight.md`
  - `docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md`
  - `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
  - `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
- Files reviewed:
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
- Public or operational surfaces affected:
  - No Service API v2 audio route registration was found.
  - No OpenAPI publication, transcript persistence, formatter generation, main
    service dependency change, sidecar image, sidecar launch contract, or live
    Hemma command surface is added by the reviewed diff.
  - The new code adds a devops report-projection module and expands domain
    benchmark evidence with `word_timestamps_available`.
- Compatibility posture:
  - The `audio -> transcript_bundle` route remains blocked and unregistered.
  - A live-proof report is a production-enabling gate for later Story 53 work;
    therefore any false-ready report is a blocker, not an additive convenience.

## Review Evidence

- `git status --short` shows the Task 352 task doc, profile-proof devops module,
  and profile-proof test as untracked, with modifications to the benchmark
  domain profile/type files and profile-selection tests.
- Existing retained reviews were searched with
  `rg -n "Task 352|task-352|review-31|sidecar benchmark|profile proof" docs/backlog/reviews docs/backlog/tasks docs/backlog/stories docs/backlog/epics`.
  No prior Task 352 review artifact existed.
- Runtime route exposure remains absent:
  - `SourceFormatV2` has no `audio` value and `OutputFormatV2` has no
    `transcript_bundle` value in `scripts/sir_convert_a_lot/domain/specs_v2.py`.
  - `SERVICE_ROUTE_POLICIES_V2` still lists document routes plus DigiExam
    migration only in `scripts/sir_convert_a_lot/domain/service_routes_v2.py`.
  - `build_create_job_route_registry_v2()` registers document create-job
    handlers plus DigiExam migration only in
    `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py`.
- Focused behavioral tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `24 passed`.
- Focused mypy passed:
  `pdm run mypy scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `Success: no issues found in 5 source files`.
- Focused ruff failed:
  `pdm run ruff check scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `I001` unsorted import block in
  `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py`.
- Forbidden typing shortcut search found no `Any`, `typing.cast`, `type: ignore`, or lint bypasses in the reviewed files.

## Test Truthfulness Audit

- The tests prove that a report builder rejects missing fields and redacts
  sentinel strings from its projection.
- The tests do not prove live Hemma behavior. They do not execute `ffmpeg` or
  `ffprobe`, do not create corrupt/no-audio/unsupported media probes, do not
  load or run `faster-whisper`, do not run `pyannote.audio`, do not inspect Torch
  device identity, do not validate Hugging Face token/cache/model access against
  the live sidecar environment, do not run Swedish or English audio fixtures, and
  do not exercise a detached/status-capable 120-minute lifecycle.
- The accepted-path test constructs an in-memory
  `AudioTranscriptionSidecarProfileProofEvidence` object with every gate already
  set to `True`. That would still pass if no live benchmark runner, sidecar
  launch surface, backend runtime, or Hemma artifact existed.

## Findings

### Resolved: Live proof is projected from caller-supplied booleans instead of being collected by a live Hemma runner

- References:
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md:50`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md:73`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md:83`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py:210`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py:248`
  - `pyproject.toml:156`
- What is wrong: Task 352 requires a committed live benchmark runner surface,
  sidecar image/build or launch contract, Hemma live-proof evidence, and command
  evidence. The reviewed implementation only builds and writes a report from an
  already-populated `AudioTranscriptionSidecarProfileProofEvidence` object.
  There is no live CLI entrypoint, no PDM command beyond the older preflight
  command, no sidecar launch/build contract, no probe collection, and no Hemma
  artifact ingestion path.
- Why it matters: `build_live_profile_proof_report()` can return
  `proof_ready=True` without any live codec probe, backend import/execution,
  Torch GPU identity, Hugging Face readiness probe, Swedish/English fixture
  execution, diarization speaker-hint run, or 120-minute lifecycle run. That is a
  false proof on the exact gate that is supposed to unblock Story 53 route work.
- Corrected shape: add a purpose-named live runner and stable PDM command for
  Task 352, separate from the Task 351 preflight. The runner must collect typed
  observations from the benchmark-only sidecar runtime or fail closed with
  concrete blockers. It must record sanitized JSON/Markdown under
  `build/verification/` or the governed Hemma artifact root and must not accept
  arbitrary operator-supplied `True` evidence as profile-ready proof.
- Proof requirement: add red/green tests around the runner boundary showing that
  missing live artifacts, missing sidecar launch metadata, missing fixture
  results, CPU execution, and absent lifecycle status all reject profile
  selection. Then run the focused pytest, focused ruff, focused mypy, and the
  actual Hemma command through `pdm run run-hemma -- ...`, recording the sanitized
  artifact path in the task doc.
- Resolution on re-review: resolved by the
  `benchmark:stt-sidecar-profile-proof` PDM command, the purpose-named runner,
  the sidecar launch/build contract, projection mode, live observation ingestion,
  fail-closed live-missing-observation behavior, and focused runner tests.

### Resolved: Tests pass while proving only projection mechanics, not Task 352 behavior

- References:
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py:51`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py:54`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py:274`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py:308`
- What is wrong: the accepted-path test calls `complete_sidecar_profile_proof()`,
  which creates synthetic in-memory evidence with live mode, codec success,
  import success, GPU success, fixture success, speaker hints, and lifecycle
  success prefilled. The test never crosses the CLI/operator boundary and never
  checks that those observations came from the live sidecar runtime.
- Why it matters: these tests would stay green if the implementation never
  shipped a live runner or if a future operator accidentally promoted dry-run
  evidence as production proof. That violates the testing skill's truthfulness
  rule and Task 352's stop condition against treating dry-run/preflight evidence
  as production profile proof.
- Corrected shape: keep pure report-builder unit tests, but add behavior tests
  for the real runner/collector boundary. Use fakes only at external process,
  sidecar, and backend seams while asserting that real runner outputs are derived
  from collected observations and reject absent/partial observations.
- Proof requirement: focused tests must fail against the current report-only
  implementation and pass only after the live runner/collector exists.
- Resolution on re-review: resolved by
  `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_runner.py`,
  which exercises the operator command boundary, PDM command contract,
  projection mode, live mode without an observation, complete sanitized live
  observation ingestion, CPU rejection, and missing sidecar-launch rejection.

### Resolved: Focused lint gate fails on the new profile-proof test file

- Reference:
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py:15`
- What is wrong: `pdm run ruff check ...` reports `I001` for an unsorted import
  block in the new test file.
- Why it matters: Rule 070 requires focused quality gates for behavior-changing
  work. A failing lint gate blocks acceptance even before the live-proof design
  gap is considered.
- Corrected shape: organize the imports with the repo formatter/linter, without
  adding lint ignores or bypasses.
- Proof requirement: rerun the same focused ruff command and record a passing
  result.
- Resolution on re-review: resolved. The focused ruff and format-check commands
  over the scoped STT files now pass.

## Re-review 2026-06-10 Remediation

- Reviewed only the user-scoped STT/doc paths. Formula/docling files in the
  shared worktree were intentionally ignored and are not part of this STT
  decision.
- The remediation adds the PDM command
  `benchmark:stt-sidecar-profile-proof` in `pyproject.toml`, which points at
  `scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_profile_proof`.
  Context7 `/pdm-project/pdm` confirms this string script form is a supported
  PDM custom-script shape and that extra arguments can be forwarded after the
  script name.
- `run_audio_transcription_sidecar_profile_proof.py` now provides the
  operator-facing command boundary:
  - projection mode writes a blocked, content-safe report and returns `0` unless
    `--fail-on-blocked` is requested;
  - live mode without a sanitized observation JSON writes a blocked,
    content-safe report and returns `2`;
  - live mode with a sanitized observation JSON validates the observation schema
    and maps bounded observations into typed profile-proof evidence.
- `audio_transcription_sidecar_profile_contracts.py` adds a bounded sidecar
  launch/build contract with image name/tag, compose service, BuildKit contract,
  launch-observed flag, isolated runtime marker, required tools/packages,
  GPU-required flag, and Hugging Face environment variable names.
- `audio_transcription_sidecar_profile_proof.py` now requires
  `sidecar_launch` before selection. Projection records the launch contract but
  does not satisfy `required_evidence.sidecar_launch`.
- Route non-registration remains intact: `SourceFormatV2` has no `audio`,
  `OutputFormatV2` has no `transcript_bundle`, `SERVICE_ROUTE_POLICIES_V2` still
  lists document routes plus DigiExam migration only, and
  `build_create_job_route_registry_v2()` still registers document handlers plus
  DigiExam migration only.
- The reviewed code has no `Any`, `typing.cast`, `type: ignore`, or lint-bypass
  shortcuts in the scoped STT files.
- Module sizes remain within the repo limit for the scoped production files:
  contracts 230 lines, proof report 412 lines, live observations 477 lines,
  runner 107 lines, benchmark types 350 lines, and benchmark profiles 286 lines.
- Generated projection and live-missing-observation reports are ignored under
  `build/` and redact the reviewed token, private-model, private-path, fixture,
  and transcript sentinels.
- Task 352 remains `in_progress` and does not yet claim complete live Hemma
  observation acceptance. That is correct for the current evidence state and
  does not block accepting this remediation.

## Decision

approved

The Task 352 remediation is accepted for the runner/contract/profile-proof
surface. The original blocker and high findings are resolved: the patch now has
a purpose-named PDM command, a runner boundary, a bounded sidecar launch/build
contract, fail-closed live observation handling, truthful command-boundary tests,
passing focused quality gates, content-safe generated reports, and no route
registration.

This approval does not close Task 352 as full live Hemma proof. The actual
complete live Hemma observation remains open and must be recorded before Story
52's production-profile rejection can be superseded or Story 53 can proceed.

## Response

Accept the remediation as the governed profile-proof runner surface. Keep Story
53 blocked until a complete sanitized live Hemma observation is produced by the
benchmark-only sidecar runtime and recorded in Task 352.

## Follow-up Actions

1. Non-blocking for this remediation review: run the actual Hemma sidecar live
   benchmark, write the sanitized observation JSON, ingest it with
   `pdm run benchmark:stt-sidecar-profile-proof -- --mode live --live-observation-json <path>`,
   record the generated ignored report path in Task 352, and then request a
   final live-proof review before unblocking Story 53.

## Validation

- `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `24 passed`.
- `pdm run ruff check scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> failed with `I001` import sorting in
  `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py`.
- `pdm run mypy scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `Success: no issues found in 5 source files`.
- Docs sync was not run before creating this artifact because the review brief
  restricted writes to this review file only.
- `pdm run docs-validate` first caught missing review `## Response` and
  `## Completion` sections; those sections were added in this retained artifact.
- `pdm run docs-validate` then validated 453 backlog files but failed
  `generated-docs-indexes` because `docs/backlog/INDEX.md` is stale and requires
  `pdm run docs-sync`. That generated-index write is outside this review's
  allowed write path.
- `pdm run skills-validate` -> `skills-validate: ok`.
- `pdm run handoff-validate` -> `handoff-validate: ok`.
- `git diff --check` passed.
- Re-review focused tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_runner.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_preflight.py tests/sir_convert_a_lot/test_audio_transcription_route_registration_gating.py`
  -> `36 passed`.
- Re-review focused lint:
  `pdm run ruff check scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_contracts.py scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observations.py scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_runner.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `All checks passed!`.
- Re-review focused format:
  `pdm run ruff format --check scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_contracts.py scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observations.py scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_runner.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `9 files already formatted`.
- Re-review focused typecheck:
  `pdm run mypy scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_contracts.py scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observations.py scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_profile_proof.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_runner.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `Success: no issues found in 9 source files`.
- Re-review command proof:
  `pdm run benchmark:stt-sidecar-profile-proof -- --mode projection --output-root build/verification/stt-sidecar-profile-proof-local-contract`
  -> exit `0`, wrote `profile-proof.json` and `profile-proof.md`.
- Re-review fail-closed live proof:
  `pdm run benchmark:stt-sidecar-profile-proof -- --mode live --output-root build/verification/stt-sidecar-profile-proof-live-missing-observation`
  -> exit `2`, wrote blocked `profile-proof.json` and `profile-proof.md`.
- `git check-ignore -v` confirmed the generated profile-proof reports are
  ignored through the repo `build/` rule.
- Redaction search over those generated reports for token/private-model,
  private-path, fixture-path, and transcript sentinel strings returned no
  matches.
- Re-review docs validation:
  `pdm run docs-validate` -> `Validated 453 backlog files`;
  `Validated docs=528 rules=11`.
- Re-review skill and handoff validation:
  `pdm run skills-validate` -> `skills-validate: ok`;
  `pdm run handoff-validate` -> `handoff-validate: ok`.
- Re-review scoped whitespace check:
  `git diff --check -- <scoped Task 352 STT/doc paths>` passed.

## Completion

Review artifact created and initial changes-requested decision recorded on
2026-06-10. Re-review on 2026-06-10 accepts the remediation and closes the
original findings as resolved. A later final live-proof review is still required
after Task 352 records complete live Hemma observation evidence.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
