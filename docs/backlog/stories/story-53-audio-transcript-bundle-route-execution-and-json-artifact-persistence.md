---
id: story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence
title: Audio transcript bundle route execution and JSON artifact persistence
type: story
status: proposed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md
  - docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md
  - docs/backlog/reviews/review-40-ruthless-review-of-stt-sidecar-hiprtc-live-proof.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/backlog/tasks/task-351-add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight.md
labels:
  - stt
  - audio
  - v2
  - artifact-bundle
  - transcript-json
  - diarization
---

Implementation slice with acceptance-driven scope.

## Objective

Implement the accepted `audio -> transcript_bundle` Service API v2 route once
Story 51 defines route policy/admission caps and Story 52 proves the backend
profile, producing a canonical owner-scoped JSON transcript artifact.

## Implementation Gate Resolution

Story 53 previously remained blocked by Story 52's governed production-profile
rejection. That gate is now superseded by Task 352 and Task 354. Review 40
accepted the deployed Hemma proof for the FasterWhisper ROCm plus pyannote
sidecar profile, and human review accepted the ignored transcript-review
artifacts for the English two-speaker and Swedish one-speaker fixtures on
2026-06-10.

The story may now proceed through small runtime tasks. Task 355 is the first
runtime slice and is limited to Service API v2 route admission. It must not
persist transcript artifacts, call the sidecar for production transcription, or
implement formatter outputs. Later Story 53 tasks own sidecar execution,
progress, cancellation cleanup, retry, retention, and canonical
`transcript_json` artifact persistence.

Current runtime truth:

- Service API v2 create-job route admission exists for
  `audio -> transcript_bundle` through Task 355, with API-key tunnel and
  Gateway signed-identity owner scopes.
- `JobSpecV2` accepts the governed day-one audio transcription request shape,
  including Swedish/English auto language selection, exact speaker count, and
  min/max speaker range hints.
- Downstream and internal adapter docs must continue to distinguish admitted
  route requests from completed transcript generation until later execution and
  artifact tasks are accepted.

## Scope

- Register the route in the v2 route/spec surfaces without adding legacy or
  anonymous lanes.
- Validate uploaded audio/video-with-audio inputs, language options,
  diarization options, duration limits, GPU-required execution, idempotency, and
  owner-scoped access.
- Execute probe, normalization, transcription, diarization, alignment,
  checkpoint, cancellation, retry, and retention behavior through small
  domain/application components.
- Persist `transcript_json` as the first canonical named artifact.
- Expose route-specific `audio_*` progress fields without overloading PDF page
  counters.
- Enforce short Sir Convert retention and product-owned durable save handoff.
- Keep Gateway/Skriptoteket access through existing `/sir-convert/v2/convert/...`
  and internal adapter boundaries.

## Acceptance Criteria

- [x] Runtime route registration is gated by accepted Story 51 admission caps
  and Story 52 backend profile evidence.
- [ ] Successful jobs produce `transcript_json` with schema version, timestamps,
  speaker labels, language evidence, warnings, and bounded runtime metadata.
- [ ] Jobs fail deterministically when media probing, normalization,
  transcription, diarization, alignment, GPU readiness, or sidecar capacity
  fails.
- [ ] Audio progress reports stage, heartbeat, `audio_total_media_seconds`,
  `audio_processed_media_seconds`, `audio_percent_complete`,
  `audio_current_chunk_index`, and `audio_total_chunks` where applicable.
- [ ] Cancellation propagates to sidecar work and purges incomplete media,
  chunks, and partial transcript state.
- [ ] Owner-scoped job/artifact access uses verified
  `InternalIdentityContextV1` for Gateway/user-originated work.
- [ ] OpenAPI and downstream/internal adapter docs are synchronized.

## Test Requirements

- [ ] Route validation tests for accepted/rejected request shapes.
- [ ] Idempotency replay and different-payload conflict tests.
- [ ] Owner-scoped status/result/artifact/cancel tests.
- [ ] Media safety failure tests for no-audio, corrupt, oversized,
  duration-exceeded, timeout, and unsupported codec inputs.
- [ ] Sidecar unavailable, capacity-exceeded, diarization-failed, and
  alignment-failed tests proving no false success.
- [ ] Cancellation cleanup and retry idempotency tests.
- [ ] Focused Hemma live proof for the selected backend profile.
- [ ] Docs validation: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Done Definition

The story is done when the v2 runtime can accept governed audio transcript jobs
and return owner-scoped `transcript_json` artifacts through the canonical
Service API v2 lifecycle, with no formatter artifacts required yet.

Current implementation state: the backend-profile blocker is resolved, but the
done definition is not satisfied. Task 355 opens route admission only; Story 53
still needs later tasks for sidecar execution, progress, cancellation, retry,
retention cleanup, and canonical `transcript_json` persistence.

## Checklist

- [x] Backend-profile implementation gate resolved
- [x] Runtime route admission slice created; execution remains unimplemented
- [x] Task 355 route-admission slice created
- [ ] Runtime route implementation complete
- [ ] Runtime tests and validations complete
- [ ] Runtime docs synchronized
