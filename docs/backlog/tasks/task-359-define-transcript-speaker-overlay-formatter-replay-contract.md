---
id: task-359-define-transcript-speaker-overlay-formatter-replay-contract
title: Define transcript speaker-overlay formatter replay contract
type: task
status: completed
priority: high
created: '2026-06-13'
last_updated: '2026-06-13'
related:
  - docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md
  - docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/tasks/task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0675-forward-transcript-formatter-replay-jobs-through-sir-convert-gateway-edge.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0347-st-21-08-overlay-aware-formatter-replay-client.md
labels:
  - transcript
  - formatter
  - replay
  - contract
  - speaker-overlay
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the exact Service API v2 contract for overlay-aware transcript formatter
replay before runtime implementation.

This task settles the product/API shape: reuse the existing async conversion
job lifecycle with route key `transcript_json -> transcript_bundle`; accept a
single uploaded canonical `transcript_json_v1`; accept typed
`transcript_formatter_replay_v1` options; return only producer-owned formatter
artifact references for `transcript_txt`, `transcript_md`, `transcript_vtt`,
and `transcript_srt`.

## PR Scope

- Update `docs/converters/audio-transcription-service-api-artifact-contract.md`
  with the replay request shape, validation rules, artifact keys, retention
  behavior, and downstream ownership boundary.
- Update the downstream integration contract and v2 API docs if they enumerate
  supported route keys or transcript artifact families.
- Define typed domain/API request shapes for:
  - `transcript_formatter_options.schema_version = transcript_formatter_replay_v1`;
  - `requested_artifacts` as exact lowercase closed enum values `txt`, `md`,
    `vtt`, and `srt`;
  - `speaker_label_overrides[]` with `canonical_speaker_label` and
    `display_name`.
- Specify validation failures for unknown labels, duplicate labels, empty
  names, duplicate display names, control characters, partial transcript state,
  malformed JSON, unsupported artifacts, replay `pdf_options`, replay
  `execution`, and `retention.pin=true`.
- Specify that replay does not request or emit a new canonical JSON artifact;
  the uploaded JSON remains the source truth.
- Keep runtime route registration and artifact writing in Task 360.

## Deliverables

- [x] Converter/API docs describe the settled replay route without open
  endpoint alternatives.
- [x] Typed request/response model plan is linked from Story 56 and Task 360.
- [x] OpenAPI expectations are explicit enough for HuleEdu and Skriptoteket
  consumers to implement strict clients.
- [x] Stop conditions are recorded for any proposal to add a bespoke endpoint,
  Gateway formatter logic, local downstream formatting, or source-audio replay.

## Acceptance Criteria

- [x] The contract names `transcript_json -> transcript_bundle` as the single
  overlay-aware replay route.
- [x] The request shape contains no untyped `dict[str, object]`, free-form
  artifact strings, compatibility aliases, or wrapper shims in the planned
  implementation surface.
- [x] The docs state that HuleEdu only forwards the route through
  `/sir-convert/v2/convert/jobs*` and must not rewrite responses.
- [x] The docs state that Skriptoteket owns durable saved transcript records,
  speaker overlay intent, filenames, download/save UX, and product workflows.
- [x] The docs state that Sir Convert owns only deterministic product-neutral
  formatter artifacts over canonical JSON and short operational retention.

## Implementation Evidence

- `docs/converters/audio-transcription-service-api-artifact-contract.md`,
  `docs/converters/multi_format_conversion_service_api_v2.md`, and
  `docs/converters/downstream_integration_contract_v2.md` now document
  `transcript_json -> transcript_bundle` as the single replay route.
- The generated OpenAPI snapshot publishes strict typed components for
  `TranscriptFormatterReplayOptionsV2`,
  `TranscriptFormatterRequestedArtifactV2`, and `SpeakerLabelOverrideV2`.
- Red-first replay/OpenAPI suite initially failed with missing
  `transcript_json` enum, missing `transcript_formatter_options`, HTTP `415`
  for `.json`, and missing OpenAPI components. The same focused suite later
  passed with `31 passed` after retained Review 45 strictness fixes for exact
  replay artifact enums, exact speaker labels, and rejected replay
  `pdf_options`/`execution`.

## Checklist

- [x] Contract docs updated
- [x] Validation complete
- [x] Docs updated
