---
id: story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy
title: STT sidecar adapter contract, media admission caps, and route policy
type: story
status: completed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/backlog/reviews/review-25-ruthless-review-of-adr-0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - stt
  - sidecar
  - admission-control
  - audio
  - v2
  - hemma
---

Implementation slice with acceptance-driven scope.

## Objective

Turn accepted ADR-0013 into the first executable design slice for the
`audio -> transcript_bundle` route by locking the internal STT sidecar adapter
shape, route policy, media admission limits, and route-level
concurrency/admission caps before any runtime registration.

## Scope

- Define the Sir-owned STT sidecar adapter contract in implementation-ready
  terms:
  - `GET /health`;
  - `GET /capabilities`;
  - normalized `POST /transcribe`;
  - cancellation propagation;
  - deterministic sidecar error mapping.
- Define route policy and validation for:
  - accepted source containers;
  - local-upload-only media inputs;
  - exact speaker count and min/max speaker range options;
  - fail-closed diarization;
  - GPU-required execution;
  - rejected `retention.pin=true` for the first slice.
- Define concrete route-level concurrency/admission caps before runtime
  registration:
  - max active STT jobs per service instance;
  - max active probe/normalization workers;
  - max active sidecar transcription/diarization requests;
  - GPU slot accounting;
  - queue or reject behavior;
  - deterministic admission errors such as `audio_route_capacity_exceeded`.
- Keep all backend-native model ids, device settings, beam/VAD knobs, and cache
  paths behind bounded sidecar capability/profile labels.
- Prepare PR-sized implementation tasks after this story accepts the admission
  and sidecar policy shape.

## Acceptance Criteria

- [x] The audio converter contract names concrete route-level concurrency and
  admission caps.
- [x] Route policy rejects unsupported media, remote/URL inputs, missing audio
  streams, unsupported diarization options, non-GPU execution, and
  `retention.pin=true`.
- [x] Sidecar health/capability parsing is implementation-ready and fails
  closed on unavailable GPU, missing model/cache access, or published-port
  exposure.
- [x] Deterministic public error codes exist for route-disabled,
  capacity-exceeded, sidecar-unavailable, media-probe, normalization,
  diarization, and alignment failures.
- [x] No browser, Gateway, Skriptoteket, or local operator request can select
  raw model ids or backend-native tuning knobs.
- [x] Follow-on implementation tasks are small enough to land route validation,
  sidecar client integration, and Compose/runtime exposure checks separately.

## Test Requirements

- [x] Red-first route validation tests for request shape, diarization options,
  media limits, GPU-required policy, and retention pin rejection.
- [x] Contract tests for sidecar capability parsing and fail-closed readiness.
- [x] Runtime exposure contract tests proving published-port exposure fails
  sidecar readiness; no live Compose STT sidecar service is introduced in this
  story.
- [x] Admission tests for concurrency caps and deterministic capacity errors.
- [x] Docs validation: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Implementation Evidence

- Red command before the final test-file split:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_policy.py`
  failed during collection with
  `ModuleNotFoundError: No module named 'scripts.sir_convert_a_lot.domain.audio_transcription_policy'`.
- Review-remediation red command before the final test-file split:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_policy.py`
  failed with 8 targeted failures for non-positive public duration guardrails,
  probed duration over the public guardrail, and missing/invalid sidecar
  `media.normalized_audio` contract truth.
- Green command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`
  passed with `35 passed`.
- Implemented policy modules:
  `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py` and
  `scripts/sir_convert_a_lot/domain/audio_transcription_policy.py`.
- Runtime route registration remains out of scope. `JobSpecV2`,
  `service_routes_v2`, and `http_create_job_routes_v2` still do not accept a
  live `audio -> transcript_bundle` create-job route.

## Done Definition

The story is done when the route policy and sidecar/admission caps are accepted
as task-ready docs/code contracts, with red-first tests named for each
production behavior slice and no runtime route registered yet.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
