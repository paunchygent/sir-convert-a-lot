---
id: review-33-ruthless-review-of-task-352-post-deploy-stt-sidecar-live-proof-blocker
title: Ruthless review of Task 352 post-deploy STT sidecar live proof blocker
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/reviews/review-31-ruthless-review-of-task-352-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - review
  - changes-requested
  - task-352
  - stt
  - diarization
  - hemma
  - sidecar
  - gpu
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless post-deploy review of Task 352's live Hemma STT
  sidecar proof attempt.
- Decision frame: Task 352 may unblock Story 53 only if the live observation
  and profile-proof artifacts show accepted STT and diarization execution for
  the Swedish and English fixtures, speaker hints, Hugging Face readiness,
  GPU-required execution, codec boundary, and 120-minute lifecycle.
- Governing authority:
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md`
  - `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
- Files reviewed:
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `containers/stt-sidecar-benchmark/Dockerfile`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observation_runtime.py`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_runtime_probe.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py`
- Evidence artifacts reviewed on Hemma:
  - `build/verification/stt-sidecar-live-observation-hemma-post-stdout-fix/live-observation.json`
  - `build/verification/stt-sidecar-profile-proof-live-post-stdout-fix/profile-proof.json`
  - `build/verification/stt-sidecar-profile-proof-live-post-stdout-fix/profile-proof.md`
- Public or operational surfaces affected:
  - No `audio -> transcript_bundle` route registration is accepted by this
    review.
  - No transcript persistence, formatter output, Gateway publication, or main
    service STT dependency promotion is accepted by this review.

## Review Evidence

- The post-deploy live observation returns exit code `2` and records
  `observation_failure_reasons`:
  - `faster_whisper_runtime_blocked`;
  - `pyannote_audio_runtime_blocked`.
- The same live observation does prove the non-backend surfaces:
  - sidecar launch/build contract and BuildKit image;
  - FFmpeg/ffprobe codec boundary and fail-closed invalid media behavior;
  - package importability for `faster-whisper`, `pyannote.audio`,
    `huggingface_hub`, and ROCm Torch;
  - `HF_TOKEN` presence by environment-variable name only;
  - scratch-backed Hugging Face cache roots;
  - ROCm GPU execution and no CPU fallback;
  - 120-minute synthetic lifecycle with progress, checkpoint, detached-status,
    cancel, and retry semantics;
  - content-safety flags.
- The profile-proof runner ingests the live observation and returns exit code
  `2` with `proof_ready=false`.
- Profile-proof `required_evidence` is true for backend dependencies, batch
  lifecycle, codec boundary, content safety, GPU-required execution, live Hemma
  evidence, route unregistered, and sidecar launch.
- Profile-proof `required_evidence` remains false for Hugging Face readiness,
  English fixture, Swedish fixture, exact speaker count, and min/max speaker
  range because neither backend completed runtime execution.
- Sanitized backend diagnostics from the same benchmark image show:
  - `faster-whisper` load fails with `RuntimeError`: `CUDA failed with error CUDA driver version is insufficient for CUDA runtime version`;
  - `pyannote.audio` pipeline loading fails with `GatedRepoError` after the
    Hub-version pin.
- Context7 `/systran/faster-whisper` documentation confirms the documented GPU
  path is CUDA-oriented through CTranslate2, not a proven ROCm path.
- Context7 `/pyannote/pyannote-audio` documentation confirms pretrained
  diarization pipeline loading uses Hugging Face token-gated access and supports
  exact and min/max speaker constraints once the pipeline loads.
- Validation for the committed fixes passed:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py -q`
    -> `7 passed`;
  - `pdm run format-all` -> `881 files left unchanged`;
  - `pdm run lint-fix` -> `All checks passed!`, `Validated docs=529 rules=11`,
    `Validated 454 backlog files`;
  - `pdm run typecheck-all` -> `Success: no issues found in 832 source files`;
  - `git diff --check` -> passed.
- Hemma deploy verification passed for deployed revision
  `5e63c9ce1bf2dbd7fc96d3525b9abb85294a4145`.

## Findings

### High: Task 352 still lacks accepted STT execution on Hemma

The live sidecar imports `faster-whisper`, proves ROCm Torch GPU availability,
and avoids CPU fallback, but `faster-whisper` itself fails during model load
with a CUDA runtime/driver mismatch. Because the accepted profile requires
bounded STT runtime evidence for English and Swedish fixtures, Task 352 cannot
claim the STT backend criterion or unblock Story 53.

Required resolution: prove GPU-backed Whisper-family STT with no CPU fallback
on the governed execution lane. FasterWhisper remains the preferred first
option; any replacement must be a governed Whisper-family backend, not a
non-Whisper STT substitute.

### High: Task 352 still lacks accepted diarization execution on Hemma

The live sidecar imports `pyannote.audio`, proves token presence, and pins a
Hub version compatible with pyannote, but pipeline loading fails with
`GatedRepoError`. Exact speaker count and min/max speaker range support are
documented and projected as supported, but they are not exercised because the
pipeline never loads.

Required resolution: accept or provision the required Hugging Face gated-model
access for the account/token used on Hemma, then rerun the live observation; or
govern a different diarization backend/profile that satisfies ADR-0013 without
toy diarization.

### Medium: The retained live observation has blocker codes but not backend failure classes

Task 352 now records the sanitized backend diagnostic root causes, but the
`live-observation.json` itself still only carries generic backend blocker
codes. That is acceptable for keeping Story 53 blocked, but the next acceptance
attempt should either retain sanitized backend failure classifications in the
observation schema or retain a governed diagnostic report alongside the proof
artifact.

Required resolution: before the next acceptance review, make backend runtime
failure classification a bounded, redacted evidence field or a governed
sidecar diagnostic artifact.

Disposition on 2026-06-10: resolved by Task 353's bounded diagnostic slice and
approved in Review 34. The high STT and diarization execution blockers in this
review remain open, and Task 352 is still not accepted as complete live Hemma
proof.

## Decision

changes_requested

The post-deploy blocker record is accepted as truthful, but Task 352 is not
accepted as complete live Hemma proof. Story 53 must remain blocked.

## Response

Do not proceed to `audio -> transcript_bundle` route registration or transcript
persistence from this evidence. The implementation fixes are valid and should
remain committed, but the product-enabling proof is still rejected until both
STT and diarization runtime evidence are green on the governed execution lane.

## Follow-up Actions

1. Create a governed follow-up slice for GPU-backed Whisper-family execution:
   first prove CTranslate2/FasterWhisper on the Hemma GPU lane, preferably
   HIP/ROCm if viable; if not viable, govern and prove another Whisper-family
   backend before unblocking Task 352.
1. Provision/accept the required Hugging Face gated-model access for the
   pyannote diarization pipeline token, or govern an alternative diarization
   backend/profile that satisfies exact and min/max speaker hints.
1. Add bounded backend failure classification to the live observation or a
   retained diagnostic artifact before the next live-proof acceptance review.
   Completed by Task 353 and approved in Review 34.

## Completion

Review completed on 2026-06-10. Decision is `changes_requested` for Task 352
completion and Story 53 unblocking. The blocked evidence path is recorded in
Task 352, and the live-proof loop remains open.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
