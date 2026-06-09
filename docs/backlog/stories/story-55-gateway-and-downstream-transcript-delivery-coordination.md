---
id: story-55-gateway-and-downstream-transcript-delivery-coordination
title: Gateway and downstream transcript delivery coordination
type: story
status: completed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-08-expose-sir-convert-audio-transcription-jobs-through-huleedu-auth-edge.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-05-conversion-hub-transcript-intake-and-diarization-controls.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-06-transcript-job-lifecycle-through-huleedu-gateway.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-07-durable-transcript-saves-and-json-first-downstream-formatting.md
labels:
  - gateway
  - skriptoteket
  - huleedu
  - downstream
  - transcript
  - stt
---

Implementation slice with acceptance-driven scope.

## Objective

Coordinate Sir Convert's accepted STT route contract with HuleEdu Gateway and
Skriptoteket downstream planning so product access uses the existing
`/sir-convert` edge and durable transcript retention remains outside Sir
Convert.

## Scope

- Keep Sir Convert docs authoritative for:
  - route key and request shape;
  - artifact names and JSON schema;
  - owner-scoped artifact access;
  - short operational retention;
  - no direct browser, anonymous, public-grant, or sidecar ingress.
- Align HuleEdu planning around:
  - Gateway `/sir-convert/v2/convert/...` proxy coverage for audio jobs;
  - `InternalIdentityContextV1` propagation and Sir Convert audience;
  - entitlement/rate-limit/admission error mapping;
  - OpenAPI/client updates for the approved-but-not-runtime route.
- Align Skriptoteket planning around:
  - audio upload UX;
  - known speaker count and min/max speaker controls;
  - polling and transcript artifact retrieval through Gateway;
  - durable transcript save and product retention;
  - JSON-first formatter strategy consumption.
- Preserve cross-repo stop conditions so downstream repos do not implement
  against an unregistered route or bypass the Gateway edge.

## Acceptance Criteria

- [x] HuleEdu and Skriptoteket have corresponding governed stories linked from
  their local backlog lanes.
- [x] Sir Convert downstream/internal adapter docs name the route as accepted
  planning authority but not an implemented runtime surface.
- [x] Cross-repo stories agree on Gateway-only product access and
  `InternalIdentityContextV1` ownership.
- [x] Cross-repo stories agree that Skriptoteket owns durable transcript
  retention after artifact save.
- [x] Downstream planning records that JSON is the first stable artifact and
  formatter artifacts are follow-on.

## Test Requirements

- [ ] Docs-only validation in all touched repos.
- [ ] Future implementation tasks must add Gateway proxy/auth tests, downstream
  client contract tests, and end-to-end product workflow smoke tests.

## Done Definition

The story is done when Sir Convert, HuleEdu, and Skriptoteket have aligned
governed planning records for transcript delivery and no repo treats the route
as live before Sir Convert registers it.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
