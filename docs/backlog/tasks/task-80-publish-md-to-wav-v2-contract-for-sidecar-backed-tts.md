---
id: task-80-publish-md-to-wav-v2-contract-for-sidecar-backed-tts
title: Publish md to wav v2 contract for sidecar-backed TTS
type: task
status: completed
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/tasks/task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy.md
  - docs/reference/ref-hemma-sidecar-tts-md-to-wav-contract-outline.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - contract
  - tts
  - audio
  - md-to-wav
  - v2
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish an implementation-grade, provider-neutral v2 contract for `md -> wav` that assumes a
Hemma sidecar TTS backend from day one, without falsely claiming that runtime support already
exists.

## PR Scope

- Extend the normative v2 API docs to define `md -> wav` as the first TTS route.
- Publish provider-neutral request fields for `tts_options` and explicit phase-1 exclusions.
- Define result metadata, artifact content type, stage markers, and error semantics.
- Define fail-closed acceleration-policy behavior for TTS routes.

## Deliverables

- [x] Updated `docs/converters/multi_format_conversion_service_api_v2.md`.
- [x] Reference contract outline capturing proposed field shape and rationale.
- [x] Backlog links synchronized to the published contract surface.

## Acceptance Criteria

- [x] `md -> wav` is documented in the normative API docs as the approved next v2 route and is
  clearly marked as not yet implemented in the runtime.
- [x] Contract remains provider-neutral and does not leak Qwen/vLLM task taxonomy.
- [x] `tts_options` defines phase-1 fields only:
  - `voice`
  - `language`
  - `style_instructions`
  - `normalize_for_speech`
- [x] `execution` is required for TTS routes in phase 1 and only `acceleration_policy="gpu_required"`
  is accepted.
- [x] Success payload specifies `audio/wav` artifact delivery and TTS-specific metadata additions.
- [x] Phase-1 exclusions are explicit:
  - no voice cloning,
  - no reference-audio uploads,
  - no Swedish quality guarantee,
  - no compressed-format contract requirement yet.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Published the sidecar-backed `md -> wav` contract shape into the reference docs and the
  normative API documentation as the approved next v2 route.
- Kept the active-route list truthful by marking `md -> wav` as not yet implemented in the runtime.
- Updated the CLI usage guide to point planned TTS work to the sidecar-backed service path rather
  than a local auxiliary command.

## Validation Evidence (2026-03-06)

- `pdm run validate-tasks` (pass: `Validated 114 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=144 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
