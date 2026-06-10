---
id: epic-12-speech-to-text-audio-ingestion-and-transcript-delivery
title: Speech-to-text audio ingestion and transcript delivery
type: epic
status: in_progress
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/backlog/reviews/review-25-ruthless-review-of-adr-0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/stories/story-55-gateway-and-downstream-transcript-delivery-coordination.md
  - docs/backlog/tasks/task-351-add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-08-expose-sir-convert-audio-transcription-jobs-through-huleedu-auth-edge.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-05-conversion-hub-transcript-intake-and-diarization-controls.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-06-transcript-job-lifecycle-through-huleedu-gateway.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-07-durable-transcript-saves-and-json-first-downstream-formatting.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - stt
  - audio
  - transcription
  - diarization
  - gateway
  - sidecar
  - hemma
  - v2
---

Major capability increment managed through linked stories.

## Goal

Deliver speech-to-text ingestion through the canonical Service API v2 async job
contract, reachable through the local Hemma tunnel and the HuleEdu Gateway
`/sir-convert` product edge.

The capability starts with best-effort editable transcripts for uploaded audio
or video files. The first stable artifact authority is structured JSON with
speaker diarization and segment timestamps. Human-readable transcript formats
such as Markdown, plain text, VTT, and SRT are follow-on formatter strategies
that consume the JSON core rather than parallel transcription pipelines.

## In Scope

- API and product contract:
  - accepted ADR-0013 route key `audio -> transcript_bundle`;
  - uploaded audio files plus video containers with an audio stream;
  - Swedish and English language auto-detection as the day-one product target;
  - optional language override may be added by implementation tasks when the
    runtime contract can validate it cleanly;
  - optional diarization controls for `auto`, exact speaker count, or
    min/max speaker range;
  - 120-minute source duration target through stable batch or chunked
    processing, not a sync request path.
- Runtime architecture:
  - speech-to-text model/runtime dependencies stay out of the main Sir Convert
    service image;
  - the main service owns job lifecycle, idempotency, retention, authorization,
    and artifact persistence;
  - an internal-only sidecar owns codec probing, audio normalization,
    transcription, and diarization runtime concerns.
- Artifact model:
  - canonical transcript JSON first;
  - formatter strategies for `txt`, `md`, `vtt`, and `srt` after the JSON
    contract and core transcription path are proven;
  - short Sir Convert operational retention for uploaded source media and
    generated artifacts, with durable user-facing persistence owned by
    Skriptoteket or another consumer application.
- Access:
  - local/operator tunnel API remains supported;
  - authenticated product traffic enters through HuleEdu Gateway
    `/sir-convert/v2/convert/...`;
  - direct anonymous public access is out of scope.

## Out of Scope

- In-process STT, diarization, or codec/model dependencies inside the main Sir
  Convert service image.
- Direct public exposure of the STT sidecar.
- Treating Sir Convert as the durable transcript archive or user-file store.
- Assessment-grade transcript correctness guarantees in the first delivery
  slice.
- Hand-rolled toy diarization; implementation must evaluate and use an
  established diarization library or service adapter where feasible.
- Markdown, TXT, VTT, or SRT generation before the route has a stable structured
  JSON core and route-specific API contract.
- Public grant or anonymous no-login transcription lanes.

## Stories

Planned story slices:

1. `docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md`
   defines the STT sidecar adapter, media admission, route policy, and concrete
   route-level concurrency/admission caps.
1. `docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md`
   benchmarks and selects the first Hemma STT/diarization backend profile.
1. `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
   implements route registration, execution, progress, cancellation, retention,
   and canonical JSON artifact persistence.
1. `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
   adds plain text, Markdown, VTT, and SRT formatter strategies after JSON core
   behavior is stable.
1. `docs/backlog/stories/story-55-gateway-and-downstream-transcript-delivery-coordination.md`
   coordinates HuleEdu Gateway and Skriptoteket downstream story planning.
1. `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-08-expose-sir-convert-audio-transcription-jobs-through-huleedu-auth-edge.md`
   is the HuleEdu Gateway companion story.
1. `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-05-conversion-hub-transcript-intake-and-diarization-controls.md`,
   `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-06-transcript-job-lifecycle-through-huleedu-gateway.md`,
   and
   `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-07-durable-transcript-saves-and-json-first-downstream-formatting.md`
   are the Skriptoteket Conversion Hub companion stories.

## Runtime-Enabling Tasks

- `docs/backlog/tasks/task-351-add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight.md`
  adds the first STT sidecar benchmark preflight runner. It records
  content-safe readiness for codec tools, runtime packages, Hugging Face
  cache/token names, and the live evidence still required before a production
  profile can be selected. It does not satisfy the Hemma benchmark acceptance
  gate and does not register `audio -> transcript_bundle`.
- `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  and
  `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md`
  now provide accepted live Hemma proof for the selected FasterWhisper ROCm plus
  pyannote profile, including Swedish/English fixtures, exact and min/max
  speaker hints, GPU-required execution, content-safe proof artifacts, and human
  transcript-review acceptance.
- `docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md`
  is the first Story 53 runtime slice. It registers Service API v2 route
  admission only; sidecar execution and canonical `transcript_json` persistence
  remain later Story 53 tasks.

## Acceptance Criteria

- [x] Route-specific converter contract is published and linked from the v2 API
  contract and downstream integration guide.
- [x] ADR-0013 or its successor is accepted before runtime implementation
  treats STT sidecar, diarization, or non-PDF GPU policy as production
  authority.
- [x] Review 25's remediated readiness approval is preserved before ADR-0013
  changes status from `proposed`.
- [x] The route contract defines the STT sidecar health/capability contract,
  untrusted media limits, fail-closed diarization behavior, model/cache/secret
  governance, retention classes, and audio long-job progress/cancel/retry
  semantics.
- [x] The first implementation story defines concrete route-level
  concurrency/admission caps before runtime registration.
- [ ] Hemma benchmark evidence proves the selected codec, transcription, and
  diarization stack can process representative Swedish and English recordings.
- [ ] Implementation tasks prove stable processing for audio or video sources
  up to 120 minutes without relying on a synchronous request path.
- [ ] Successful jobs produce a canonical JSON transcript bundle with segment
  timestamps, speaker labels, language evidence, warnings, and runtime metadata.
- [ ] Formatter outputs are generated by modular downstream strategies wired by
  DI and do not duplicate transcription or diarization business logic.
- [ ] Product/browser traffic uses HuleEdu Gateway `/sir-convert/v2/convert/...`
  with Sir Convert audience `InternalIdentityContextV1`; local operator traffic
  uses the sanctioned tunnel lane.
- [ ] Sir Convert retention remains short and operational; durable artifact
  ownership and user-facing storage remain in Skriptoteket or the consuming
  product.

## Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
