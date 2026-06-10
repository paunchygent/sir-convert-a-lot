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
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md
  - docs/backlog/reviews/review-26-ruthless-review-of-story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/reviews/review-27-ruthless-review-of-story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/reviews/review-29-ruthless-review-of-story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/reviews/review-40-ruthless-review-of-stt-sidecar-hiprtc-live-proof.md
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

Story 55 coordination is completed as planning/alignment only. It is not
runtime Gateway proxy, sidecar execution, formatter, or UI work. Story 52's
governed production-profile rejection has been superseded by Task 352/354 and
Review 40. Task 355 registers the first Sir Convert Service API v2
`audio -> transcript_bundle` route-admission slice, but Story 53 still requires
accepted sidecar execution plus canonical `transcript_json` persistence before
downstream stories may treat transcript delivery as live. Story 54 remains
`proposed` and blocked until the JSON core is live.

## Scope

- Keep Sir Convert docs authoritative for:
  - route key and request shape;
  - artifact names and JSON schema;
  - owner-scoped artifact access;
  - short operational retention;
  - no direct browser, anonymous, public-grant, or sidecar ingress.
- Align HuleEdu planning around:
  - HuleEdu ST-01-08 as the governed Gateway companion story;
  - Gateway `/sir-convert/v2/convert/...` proxy coverage for audio jobs;
  - `InternalIdentityContextV1` propagation and Sir Convert audience;
  - entitlement/rate-limit/admission error mapping;
  - OpenAPI/client updates for the approved-but-not-runtime route.
- Align Skriptoteket planning around:
  - Skriptoteket ST-21-05 for transcript intake and diarization controls;
  - Skriptoteket ST-21-06 for transcript job lifecycle through HuleEdu
    Gateway;
  - Skriptoteket ST-21-07 for durable transcript saves and JSON-first
    downstream formatting;
  - audio upload UX;
  - known speaker count and min/max speaker controls;
  - polling and transcript artifact retrieval through Gateway;
  - durable transcript save and product retention;
  - JSON-first formatter strategy consumption.
- Preserve cross-repo stop conditions so downstream repos do not treat
  admission-registered audio jobs as completed transcript delivery or bypass the
  Gateway edge.

## Alignment Record

- HuleEdu ST-01-08, Skriptoteket ST-21-05, Skriptoteket ST-21-06, and
  Skriptoteket ST-21-07 are the downstream governed planning records linked
  from this completed coordination story.
- The shared access model is Gateway-only `/sir-convert/v2/convert` product
  access with HuleEdu-signed `InternalIdentityContextV1` for user-originated
  Sir Convert work.
- The Sir Convert audio route is admission-registered planning authority, but
  not a transcript execution or artifact-delivery surface until later Story 53
  tasks complete.
- Retention ownership is split intentionally: short Sir Convert operational
  retention for uploaded media and generated artifacts, durable Skriptoteket
  transcript retention after product save.
- Downstream sequencing is JSON-first durable save before formatter artifacts
  as follow-on outputs. Skriptoteket may plan formatting consumption, but Sir
  Convert Story 54 remains blocked until canonical transcript JSON persistence
  is live.
- The coordinated stop condition is no public, no-login, direct sidecar, or
  sidecar-public ingress for transcript delivery.

## Acceptance Criteria

- [x] HuleEdu and Skriptoteket have corresponding governed stories linked from
  their local backlog lanes.
- [x] Sir Convert downstream/internal adapter docs name the route as
  admission-registered while transcript execution and artifact persistence
  remain pending.
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
governed planning records for transcript delivery and no repo treats admitted
audio jobs as live transcript delivery before Sir Convert sidecar execution and
`transcript_json` persistence are accepted.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
