---
id: review-40-ruthless-review-of-stt-sidecar-hiprtc-live-proof
title: Ruthless review of STT sidecar HIPRTC live proof
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md
  - docs/backlog/reviews/review-39-ruthless-review-of-task-352-354-pyannote-failure-stage-classification.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - review
  - approved
  - task-352
  - task-354
  - stt
  - faster-whisper
  - pyannote
  - rocm
  - hiprtc
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: fixed ruthless post-deploy review for STT Task 354 after live
  proof succeeded.
- Commit range reviewed:
  `36c8435fe372354f6b591d154338d843364c05ba..fe566bd4a489f46df55d8168ac8a3a13d3dcea30`.
- Runtime proof reviewed:
  - `build/verification/hemma-deploy-verify/report.json`
  - `build/verification/hemma-deploy-verify/report.md`
  - `build/verification/stt-sidecar-live-observation-hemma-hiprtc-fe566bd/live-observation.json`
  - `build/verification/stt-sidecar-profile-proof-live-hiprtc-fe566bd/profile-proof.json`
  - `build/verification/stt-sidecar-profile-proof-live-hiprtc-fe566bd/profile-proof.md`
  - `build/verification/stt-sidecar-transcript-review-hiprtc-fe566bd/transcript-review.json`
  - `build/verification/stt-sidecar-transcript-review-hiprtc-fe566bd/transcript-review.md`
- Governing docs and handoff reviewed:
  - `.codex/handoff.md`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md`
- Files changed in the reviewed commit range:
  - `.codex/handoff.md`
  - `containers/stt-sidecar-benchmark/Dockerfile`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observation_projection.py`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_live_observations.py`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_contracts.py`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_profile_proof.py`
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_runtime_probe.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_runner.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py`
- Public or operational surfaces affected:
  - benchmark-only STT sidecar Docker image;
  - retained live-observation/profile-proof JSON and Markdown;
  - retained ignored human-review transcript artifact;
  - no Service API v2 route registration, OpenAPI/Gateway publication,
    transcript persistence, formatter output, or main-service STT dependency
    promotion.
- Compatibility posture:
  - additive benchmark evidence field only;
  - no compatibility shim, alias, fallback, retired route, or fake success is
    introduced.

## Evidence Reviewed

- Context7 `/systran/faster-whisper` current docs show `WhisperModel(..., device="cuda", compute_type="float16")` as the explicit GPU path.
- Context7 `/pyannote/pyannote-audio` current docs show authenticated
  `Pipeline.from_pretrained(..., token=...)`, GPU placement through
  `pipeline.to(torch.device("cuda"))`, exact `num_speakers`, min/max
  `min_speakers` and `max_speakers`, and exclusive diarization output.
- Context7 `/opennmt/ctranslate2` current docs confirm explicit GPU device
  selection through `device="cuda"` style APIs.
- Deploy report status is `passed`; expected, remote, and service revisions all
  equal `fe566bd4a489f46df55d8168ac8a3a13d3dcea30`.
- Live observation records:
  - `observation_failure_reasons=[]`;
  - `acceleration_family=rocm`;
  - `gpu_execution_confirmed=true`;
  - `cpu_fallback_observed=false`;
  - `faster_whisper_importable=true`;
  - `pyannote_audio_importable=true`;
  - `torchcodec_audio_decoder_importable=true`;
  - `miopen_hiprtc_headers_available=true`;
  - `token_env_vars_present=true`;
  - `cache_status=scratch_backed`;
  - `model_access_status=ready`;
  - `exact_speaker_count_exercised=true`;
  - `min_max_speaker_range_exercised=true`;
  - English fixture detected `en`, has word timestamps, and produced 151
    alignment-suitable exclusive diarized speaker segments;
  - Swedish fixture detected `sv`, has word timestamps, and produced 3
    alignment-suitable exclusive diarized speaker segments.
- Profile proof records:
  - `proof_ready=true`;
  - `profile_selection.selected=true`;
  - `rejection_reasons=[]`;
  - every required evidence gate is true;
  - `route_registration.audio_transcript_bundle_registered=false`.
- Human-review transcript artifact records speaker-labeled timestamped
  transcript segments under ignored `build/verification/` output. The artifact
  is useful for human review and deliberately not projected into retained docs.
- `git check-ignore -v` confirms the live observation, profile proof, and
  transcript review artifacts are ignored by the repo `build/` rule.
- `git ls-files` returned no tracked files for those generated proof artifacts.
- Code inspection found no `Any`, `typing.cast`, `# type: ignore`, `noqa`, or
  lint-ignore shortcuts in the reviewed code/test files.
- Changed production modules remain below the repo 500-line cap.

## Findings

No findings.

The reviewed slice installs the missing ROCm HIPRTC header dependencies
(`librocrand-dev` and `libc6-dev`) in the benchmark-only sidecar image, projects
`miopen_hiprtc_headers_available` through live observation and profile proof,
and gates profile readiness on that evidence. The live proof demonstrates
GPU-backed FasterWhisper, pyannote diarization, no CPU fallback, exact and
min/max speaker hints, route-unregistered state, and content-safe retained
reports. Transcript text is kept only in ignored human-review artifacts.

## Decision

approved

## Response

ACCEPTED for the Task 354 HIPRTC live-proof slice and the complete Task 352 STT
sidecar profile-proof evidence reviewed here.

This approval does not register the `audio -> transcript_bundle` route, publish
Gateway/OpenAPI fields, persist transcript artifacts through the product API, or
approve downstream formatter/delivery work. It approves the benchmark/live-proof
evidence that Story 53 may now continue under its own governed implementation
scope.

## Validation Run During Review

- `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_failure_projection.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_runner.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py -q`
  passed `37 passed`.
- `git diff --check 36c8435fe372354f6b591d154338d843364c05ba..fe566bd4a489f46df55d8168ac8a3a13d3dcea30`
  passed.
- Docs gates were run after retaining this review:
  - `pdm run docs-sync` refreshed generated indexes.
  - `pdm run docs-validate` passed with `Validated 464 backlog files` and
    `Validated docs=539 rules=11`.
  - `pdm run skills-validate` passed with `skills-validate: ok`.
  - `pdm run handoff-validate` passed with `handoff-validate: ok`.
  - `git diff --check` passed.

## Follow-up Actions

No follow-up actions are required for this reviewed HIPRTC live-proof slice.

## Completion

Review completed on 2026-06-10. Decision is `approved` with no findings.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
