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
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
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

- [ ] Runtime route registration is gated by accepted Story 51 admission caps
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

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
