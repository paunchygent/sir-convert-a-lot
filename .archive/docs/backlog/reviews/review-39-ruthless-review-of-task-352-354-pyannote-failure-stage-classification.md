---
id: review-39-ruthless-review-of-task-352-354-pyannote-failure-stage-classification
title: Ruthless review of Task 352 354 pyannote failure-stage classification
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md
  - docs/backlog/reviews/review-38-ruthless-review-of-task-354-stt-sidecar-diarization-access-diagnostic.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - review
  - approved
  - task-352
  - task-354
  - stt
  - diarization
  - pyannote
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: bounded ruthless implementation review for pyannote
  diarization failure-stage classification.
- Scope under review:
  - runtime-probe bounded diarization `failure_stage` labels for staged
    pyannote execution after Hugging Face access opens;
  - live-observation backend failure projection of that stage;
  - focused tests covering the runtime-probe stage classification.
- Files reviewed:
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_runtime_probe.py`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observation_projection.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py`
- Governing authority:
  - `AGENTS.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md`
  - `docs/backlog/reviews/review-38-ruthless-review-of-task-354-stt-sidecar-diarization-access-diagnostic.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
- Public or operational surfaces affected:
  - retained runtime-probe JSON;
  - retained live-observation `backend_failures` JSON;
  - no public API, Gateway, route registration, persistence, or formatter
    output.
- Explicit non-scope:
  - This review does not approve Task 352 live proof completion.
  - This review does not claim pyannote diarization ran.
  - This review does not unblock Story 53.
  - This review does not approve `audio -> transcript_bundle` route
    registration, OpenAPI/Gateway publication, transcript persistence,
    formatter output, or replacement diarization implementation.
- Compatibility posture:
  - additive bounded diagnostic field only;
  - no compatibility shim, alias, retired field, or fallback success is
    accepted by this review.

## Evidence Reviewed

- Current uncommitted diff in `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot`.
- Context7 `/pyannote/pyannote-audio` current documentation confirms the
  relevant staged flow: `Pipeline.from_pretrained(..., token=...)`, GPU
  placement through `pipeline.to(torch.device(...))`, exact `num_speakers`,
  `min_speakers`/`max_speakers`, and exclusive diarization output.
- Red evidence reported by implementer:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py::test_runtime_probe_reports_bounded_diarization_failure_stage -q`
    failed before implementation because `failure_stage` was absent.
- Validation run by this reviewer:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py -q`
    passed `4 passed`.
  - `pdm run typecheck-all` passed with
    `Success: no issues found in 837 source files`.
  - `pdm run docs-sync` refreshed generated indexes after this retained review
    was created.
  - `pdm run docs-validate` passed with `Validated 463 backlog files` and
    `Validated docs=538 rules=11`.
  - `pdm run skills-validate` passed with `skills-validate: ok`.
  - `pdm run handoff-validate` passed with `handoff-validate: ok`.
  - `git diff --check` passed.
  - `git diff -- docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md`
    produced no output in the current worktree.

## Findings

1. [ ] `high` - The live-observation projection of `failure_stage` is
   untested.

   File references:

   - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observation_projection.py:321`
   - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observation_projection.py:323`
   - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py:78`
   - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py:85`
   - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py:185`

   The production projection now conditionally copies bounded
   `failure.failure_stage` into retained `backend_failures`, but the
   live-observation projection test never puts `failure_stage` in its fake
   runtime-probe diarization failure and therefore never asserts that the
   retained observation carries it. The focused green command can pass while
   `_backend_failure(...)` silently drops the stage, which defeats the purpose
   of this slice: diagnosing the post-access pyannote `NameError` stage in the
   sanitized live-observation evidence consumed by profile proof.

   Required fix:
   Add or update a red-first test in
   `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py`
   so the fake diarization failure includes
   `failure_stage="exact_speaker_count"` and the expected
   `backend_failures["diarization"]` contains that same bounded stage. Keep the
   existing content-safety assertions proving raw model ids, token values,
   private paths, raw backend messages, and transcript text are not retained.
   If the implementation is expected to drop unknown stages, add a small
   bounded negative assertion or fixture so unrecognized stage strings cannot
   leak.

   Proof command:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py -q`

## Decision

`changes_requested`

The runtime-probe stage classifier itself is on the right track and has a
focused behavioral test for the post-access `NameError` scenario. Approval is
blocked because the second changed boundary, live-observation backend failure
projection, is not truthfully covered.

## Response

Task 352/354's bounded failure-stage slice is not accepted yet. Add the
projection-boundary red test, make it green, rerun the focused tests and
non-mutating quality gates, then request another fixed review pass. This review
does not accept Task 352 live proof and does not unblock Story 53.

## Remediation Review

Date: 2026-06-10

Decision: `approved`

This remediation pass reviewed only the fix for Review 39's high finding. It
does not approve Task 352 live proof completion, does not claim pyannote
diarization ran successfully, and does not unblock Story 53.

### Remediation Evidence Reviewed

- `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py:89`
  now asserts `backend_failures.diarization.failure_stage="pipeline_load"` in
  the retained live-observation JSON.
- `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py:190`
  now feeds `failure_stage="pipeline_load"` through the fake diarization runtime
  payload.
- Existing content-safety assertions still prove raw backend messages, raw model
  identifiers, token values, Hugging Face cache paths, fixture paths, and
  transcript text are not retained.
- Validation run by this reviewer:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py -q`
    passed `4 passed`.
  - `pdm run typecheck-all` passed with
    `Success: no issues found in 837 source files`.
  - `pdm run docs-validate` passed with `Validated 463 backlog files` and
    `Validated docs=538 rules=11`.
  - `pdm run skills-validate` passed with `skills-validate: ok`.
  - `pdm run handoff-validate` passed with `handoff-validate: ok`.
  - `git diff --check` passed.

### Remediation Finding Status

1. [x] `high` - The live-observation projection of `failure_stage` is now
   tested.

   The test now proves the changed projection boundary: a bounded runtime-probe
   `failure.failure_stage` reaches retained
   `backend_failures.diarization.failure_stage` while raw model ids, token
   values, private paths, backend-native messages, and transcript text remain
   excluded.

### Remediation Response

Approved for the bounded failure-stage diagnostic classification slice. The
runtime probe can now classify staged pyannote failures, and the live-observation
projection retains that bounded stage for downstream profile-proof diagnostics.
This remains diagnostic evidence only.

## Follow-up Actions

1. Add projection-boundary test coverage for retained
   `backend_failures.diarization.failure_stage`.
1. Rerun:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py -q`,
   `pdm run typecheck-all`, `pdm run docs-validate`,
   `pdm run skills-validate`, `pdm run handoff-validate`, and
   `git diff --check`.

## Completion

Review retained with `approved` after remediation. This decision is bounded to
the failure-stage diagnostic slice and does not approve Task 352 live proof
completion or unblock Story 53.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
