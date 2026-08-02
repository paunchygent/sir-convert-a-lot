---
id: review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence
title: Ruthless review of STT sidecar post-deploy FasterWhisper ROCm evidence
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md
  - docs/backlog/reviews/review-36-ruthless-review-of-stt-sidecar-ctranslate2-rocm-rpath-image-correction.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
labels:
  - review
  - approved
  - stt
  - sidecar
  - faster-whisper
  - rocm
  - codec-boundary
  - diarization
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless post-deploy evidence review for the deployed STT
  sidecar CTranslate2 ROCm RPATH correction.
- Governing authority:
  - `AGENTS.md`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md`
  - `docs/backlog/reviews/review-36-ruthless-review-of-stt-sidecar-ctranslate2-rocm-rpath-image-correction.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
- Files reviewed:
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md`
  - `.codex/handoff.md`
- Ignored Hemma evidence reviewed:
  - `build/verification/stt-sidecar-live-observation-hemma-ctranslate2-rpath-bcde92a/live-observation.json`
  - `build/verification/stt-sidecar-profile-proof-live-ctranslate2-rpath-bcde92a/profile-proof.json`
  - `build/verification/stt-sidecar-profile-proof-live-ctranslate2-rpath-bcde92a/profile-proof.md`
- Decision frame:
  - accept only the bounded post-deploy conclusion that the prior
    FasterWhisper/CTranslate2 ROCm and codec-boundary blockers are resolved;
  - do not accept Task 352 as complete live proof;
  - do not unblock Story 53;
  - do not approve route registration, OpenAPI publication, transcript
    persistence, formatter output, Gateway publication, or main-service STT
    dependency promotion.
- Public or operational surfaces affected:
  - docs-only retained evidence state for the benchmark-only sidecar lane;
  - ignored benchmark artifacts under `build/verification/`;
  - no product API, public Gateway, persistence, or downstream delivery surface.
- Compatibility posture:
  - no compatibility shim, alias, wrapper, fallback, retired route, or legacy
    contract is introduced by this docs/evidence slice;
  - the profile-proof runner still fails closed with `proof_ready=false` while
    diarization evidence is missing.

## Evidence Reviewed

- Local deploy report `build/verification/hemma-deploy-verify/report.md`
  records status `passed`, expected revision
  `bcde92a04ce23a60aa88ac3bcb354cf5c9051b7a`, remote revision
  `bcde92a04ce23a60aa88ac3bcb354cf5c9051b7a`, and service revision
  `bcde92a04ce23a60aa88ac3bcb354cf5c9051b7a`.
- Remote `git rev-parse HEAD` in the canonical Hemma checkout returned
  `bcde92a04ce23a60aa88ac3bcb354cf5c9051b7a`.
- The post-deploy live observation records only one failure reason:
  `pyannote_audio_runtime_blocked`.
- Codec boundary is restored: `ffmpeg_available=true`,
  `ffprobe_available=true`, `valid_audio_probe_exercised=true`,
  `bounded_metadata_projected=true`, and bad/no-audio/unsupported media all
  fail closed.
- Backend dependencies are isolated and importable in the sidecar:
  `faster_whisper_importable=true`, `pyannote_audio_importable=true`,
  `huggingface_hub_importable=true`, `torch_importable=true`,
  `sidecar_runtime_isolated=true`, and
  `main_service_dependency_change_observed=false`.
- Runtime evidence is GPU-backed and non-degraded:
  `acceleration_family=rocm`, `gpu_execution_confirmed=true`,
  `cpu_fallback_observed=false`, `cache_roots_ready=true`, and
  `required_secret_values_exposed=false`.
- Profiles remain bounded:
  `stt_backend_family=faster_whisper`,
  `stt_profile=stt_sv_en_primary`,
  `diarization_backend_family=pyannote_audio`, and
  `diarization_profile=diarization_sv_en_primary`.
- English and Swedish STT execution evidence is present:
  the fixtures detect `en` and `sv`, both have
  `word_timestamps_available=true`, and both retain no transcript text.
- Diarization is not accepted:
  `backend_failures.diarization.backend_family=pyannote_audio`,
  `failure_code=gated_model_access_denied`,
  `exception_class=GatedRepoError`, and `status=blocked`.
- Speaker hints remain unexercised because diarization is blocked:
  exact speaker count and min/max speaker range are supported but not
  exercised.
- Hugging Face token and cache plumbing is present but model access is blocked:
  `token_env_vars_present=true`, `cache_status=scratch_backed`,
  `model_access_status=blocked`, and no secret values, private cache paths, or
  raw model identifiers are exposed.
- The 120-minute lifecycle shape remains represented by a synthetic-duration
  proof with 12 chunks of 600 seconds and progress, checkpoint, detached
  status, cancel, and retry semantics.
- Profile-proof ingestion records `proof_ready=false`. Required evidence is
  true for backend dependencies, batch lifecycle, codec boundary, content
  safety, GPU-required execution, live Hemma evidence, route unregistered, and
  sidecar launch. Required evidence remains false for Hugging Face readiness,
  English fixture completion, Swedish fixture completion, exact speaker count,
  and min/max speaker range.
- Profile-proof rejection reasons include
  `pyannote_audio_runtime_blocked`,
  `huggingface_readiness_not_ready`,
  missing diarized/exclusive/alignment evidence for both fixtures, and missing
  exact/min-max speaker hint execution.
- `git check-ignore -v` confirms the reviewed generated artifacts are ignored
  through the repo `build/` rule.

## Findings

No blocking findings remain for the bounded post-deploy evidence slice.

The local task and handoff docs accurately state that the deployed
`bcde92a04ce23a60aa88ac3bcb354cf5c9051b7a` image resolves the prior
FasterWhisper/CTranslate2 ROCm runtime blocker and the codec-boundary
regression. They also accurately keep Task 352 incomplete, keep
`proof_ready=false`, and keep Story 53 blocked because pyannote diarization
still lacks gated model access and speaker-hint execution evidence.

This approval does not accept the complete Task 352 live proof. It accepts only
the STT/codec blocker resolution and the truthful documentation of the
remaining diarization blocker.

## Decision

approved

## Response

Accept the post-deploy evidence as sufficient to close the prior
FasterWhisper/CTranslate2 ROCm and codec-boundary blockers for Task 353.

Do not close Task 352 and do not start Story 53. The next governed remediation
is to provision pyannote gated model access for the Hemma `HF_TOKEN` account or
to govern a library-backed diarization replacement that satisfies exact speaker
count and min/max speaker range hints. The profile-proof gate must remain
`proof_ready=false` until real diarization evidence is present.

## Follow-up Actions

1. Commit this docs evidence slice if the repo validation gates pass.
1. Keep Story 53 blocked until a later retained review accepts complete Task
   352 live proof, including real diarization execution.
1. Provision/accept pyannote gated model access for the Hemma `HF_TOKEN`
   account or create a governed replacement decision for a library-backed
   diarization backend.
1. Rerun live observation and profile-proof ingestion after the diarization
   blocker is resolved.

## Completion

Review completed on 2026-06-10. Decision is `approved` for the bounded
post-deploy STT/codec evidence only.

Validation run during review:

- `git status --short`
- `git diff -- .codex/handoff.md docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md`
- `pdm run run-hemma -- jq ... build/verification/stt-sidecar-live-observation-hemma-ctranslate2-rpath-bcde92a/live-observation.json`
- `pdm run run-hemma -- jq ... build/verification/stt-sidecar-profile-proof-live-ctranslate2-rpath-bcde92a/profile-proof.json`
- `pdm run run-hemma -- sed -n '1,220p' build/verification/stt-sidecar-profile-proof-live-ctranslate2-rpath-bcde92a/profile-proof.md`
- `sed -n '1,220p' build/verification/hemma-deploy-verify/report.md`
- `pdm run run-hemma -- git rev-parse HEAD`
- `git check-ignore -v build/verification/stt-sidecar-live-observation-hemma-ctranslate2-rpath-bcde92a/live-observation.json build/verification/stt-sidecar-profile-proof-live-ctranslate2-rpath-bcde92a/profile-proof.json build/verification/stt-sidecar-profile-proof-live-ctranslate2-rpath-bcde92a/profile-proof.md`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
