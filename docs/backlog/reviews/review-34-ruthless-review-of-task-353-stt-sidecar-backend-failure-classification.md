---
id: review-34-ruthless-review-of-task-353-stt-sidecar-backend-failure-classification
title: Ruthless review of Task 353 STT sidecar backend failure classification
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/reviews/review-33-ruthless-review-of-task-352-post-deploy-stt-sidecar-live-proof-blocker.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
labels:
  - review
  - stt
  - sidecar
  - backend-failures
  - task-353
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless implementation review of the first Task 353 diagnostic
  slice.
- Governing authority:
  - `AGENTS.md`
  - `docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/reviews/review-33-ruthless-review-of-task-352-post-deploy-stt-sidecar-live-proof-blocker.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
- Scope under review:
  - bounded runtime-probe backend failure classification;
  - retained live-observation `backend_failures` projection and redaction;
  - Task 353 documentation clarifying that GPU-backed Whisper-family STT is the
    invariant, FasterWhisper is the preferred first path, and CPU fallback or
    non-Whisper STT substitution is not acceptable.
- Files reviewed:
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_runtime_probe.py`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observation_projection.py`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observation_runtime.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py`
  - Task 352, Task 353, Review 33, and `.codex/handoff.md` wording updates
- Compatibility posture:
  - Diagnostic schema extension only. The live observation gains an additive
    `backend_failures` section for retained benchmark evidence.
  - This review does not accept live STT or diarization backend execution, does
    not unblock Story 53, and does not authorize `audio -> transcript_bundle`
    route registration.

## Findings

No blocking findings remain.

Resolved review-loop findings:

1. [x] `high` - Runtime-probe classifier behavior was under-proven.

   The first implementation pass only projected an already-classified fake
   payload. Review required a CLI-boundary test that exercised the actual
   runtime-probe classifier. The implementation added
   `tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py::test_runtime_probe_classifies_backend_exceptions_without_raw_values`,
   which installs fake backend modules and verifies that:

   - CUDA driver/runtime `RuntimeError` becomes
     `gpu_backend_runtime_unavailable`;
   - `GatedRepoError` becomes `gated_model_access_denied`;
   - stdout omits raw exception messages, model ids, token values, private
     fixture paths, and transcript text.

1. [x] `medium` - The initial test placement worsened an already oversized
   live-observation test module.

   The implementation moved the new coverage out of
   `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py`.
   The current slice no longer modifies that pre-existing 548-line file, and
   the new focused modules are under 500 lines.

1. [x] `high` - Live-observation `backend_failures` retention was under-proven.

   The second implementation pass proved the classifier but not the retained
   observation projection. The implementation added
   `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py::test_live_observation_projects_bounded_backend_failures_without_raw_values`,
   which drives the live-observation producer with noisy runtime-probe failure
   maps and verifies that retained JSON contains only `backend_family`,
   `status`, `failure_code`, and `exception_class` for STT and diarization.
   The same test verifies that raw messages, model ids, token values, cache
   paths, fixture paths, and transcript text are not persisted.

## Decision

approved

## Response

Task 353's bounded backend failure-classification slice is accepted. The slice
is correctly scoped as diagnostic evidence: it improves retained live
observation reviewability and redaction, but it does not prove that STT or
diarization backends execute successfully on Hemma.

Task 352 and Story 53 remain blocked until a later retained review accepts live
GPU-backed Whisper-family STT execution and live diarization execution for the
governed fixtures. FasterWhisper remains the preferred first STT path; CPU
fallback and non-Whisper STT substitution remain unacceptable.

## Follow-up Actions

1. Continue Task 353 with backend execution remediation:
   - first attempt CTranslate2/FasterWhisper HIP/ROCm proof on Hemma;
   - if that is not viable, govern and prove a GPU-backed Whisper-family
     replacement before unblocking Task 352.
1. Provision or accept the required Hugging Face gated-model access for the
   selected pyannote account/token, or govern a different library-backed
   diarization profile that satisfies exact and min/max speaker hints.
1. Do not start Story 53 implementation until Task 352 receives an accepted
   retained review for live STT and diarization execution.

## Completion

Review completed on 2026-06-10. Decision is `approved` for the bounded Task 353
backend failure-classification slice only. The live-proof loop remains open.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
