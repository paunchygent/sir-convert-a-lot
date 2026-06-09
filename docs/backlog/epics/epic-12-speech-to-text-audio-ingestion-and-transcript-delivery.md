---
id: 'epic-12-speech-to-text-audio-ingestion-and-transcript-delivery'
title: 'Speech-to-text audio ingestion and transcript delivery'
type: 'epic'
status: 'proposed'
priority: 'high'
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
  - new draft route key `audio -> transcript_bundle`;
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

Planned story slices to scaffold after this epic is accepted:

1. Publish the speech-to-text sidecar, route-policy, and transcript JSON
   contract.
1. Benchmark STT and diarization sidecar candidates on Hemma with 120-minute
   batch-processing evidence.
1. Implement `audio -> transcript_bundle` route registration, validation,
   execution, and JSON artifact persistence.
1. Add formatter strategies for plain text, Markdown, VTT, and SRT as
   downstream modules wired by DI after the JSON core stabilizes.
1. Cut Skriptoteket and HuleEdu Gateway consumers to the authenticated
   `/sir-convert` product edge for transcript jobs.

## Acceptance Criteria

- [ ] Route-specific converter contract is published and linked from the v2 API
  contract and downstream integration guide.
- [ ] ADR-0013 or its successor is accepted before runtime implementation
  treats STT sidecar, diarization, or non-PDF GPU policy as production
  authority.
- [ ] Review 25's remediated readiness approval is preserved before ADR-0013
  changes status from `proposed`.
- [ ] The accepted route contract defines the STT sidecar health/capability
  contract, untrusted media limits, fail-closed diarization behavior,
  model/cache/secret governance, retention classes, and audio long-job
  progress/cancel/retry semantics.
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

- [ ] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
