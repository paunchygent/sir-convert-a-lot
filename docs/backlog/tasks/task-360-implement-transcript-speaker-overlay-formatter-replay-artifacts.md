---
id: task-360-implement-transcript-speaker-overlay-formatter-replay-artifacts
title: Implement transcript speaker-overlay formatter replay artifacts
type: task
status: completed
priority: high
created: '2026-06-13'
last_updated: '2026-06-13'
related:
  - docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md
  - docs/backlog/tasks/task-359-define-transcript-speaker-overlay-formatter-replay-contract.md
  - docs/backlog/tasks/task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0675-forward-transcript-formatter-replay-jobs-through-sir-convert-gateway-edge.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0347-st-21-08-overlay-aware-formatter-replay-client.md
labels:
  - transcript
  - formatter
  - replay
  - speaker-overlay
  - artifact-bundle
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the Story 56 / Task 359 overlay-aware formatter replay contract and
return named TXT, Markdown, WebVTT, and SRT artifacts through the existing v2
job lifecycle.

## PR Scope

- Register `source.format = transcript_json` with
  `conversion.output_format = transcript_bundle` in Service API v2 route
  policy.
- Accept uploaded canonical `transcript_json_v1` only; reject partial,
  malformed, unsupported, or non-canonical transcript payloads.
- Parse `transcript_formatter_options` into strict domain value objects.
- Validate `requested_artifacts` as exact lowercase closed enum values `txt`,
  `md`, `vtt`, and `srt`.
- Validate `speaker_label_overrides` against the transcript speaker inventory:
  unknown labels, duplicate labels, empty names, duplicate display names,
  control characters, and length violations fail closed.
- Apply overrides only to the formatter projection consumed by the Task 358
  formatter strategies.
- Emit requested `transcript_txt`, `transcript_md`, `transcript_vtt`, and
  `transcript_srt` artifacts with stable content types and named retrieval.
- Preserve operational retention and cancellation semantics from the v2 job
  lifecycle.
- Keep replay code independent from STT, diarization, alignment, sidecar,
  codec, and source-audio runtime modules.

## Deliverables

- [x] Route admission and request validation for
  `transcript_json -> transcript_bundle`.
- [x] Overlay projection over canonical transcript JSON that leaves canonical
  JSON unchanged.
- [x] Formatter artifact generation through the existing Task 358 strategies.
- [x] Result/artifact-list/named-artifact retrieval support for replay outputs.
- [x] OpenAPI and converter/downstream docs synchronized.

## Acceptance Criteria

- [x] Valid replay jobs produce requested overlay-aware formatter artifacts and
  no new canonical JSON truth.
- [x] Invalid speaker overlays or malformed transcript JSON fail before artifact
  generation.
- [x] Overlay-aware export requests never fall back to canonical-label artifacts
  after overlay validation fails.
- [x] JSON-only audio transcription behavior from Task 356 and formatter
  behavior from Task 358 remain unchanged.
- [x] Logs, metrics, and public errors exclude transcript text, utterances,
  display names, source content, media hashes as labels, and provider/model
  details.
- [x] Focused tests and repo quality gates pass.

## Implementation Evidence

- Added typed replay option models, route policy, `.json` inference,
  create-job admission, runtime replay, named artifact manifest/retrieval, and
  content-safe public validation error serialization.
- Replay runtime validates uploaded canonical `transcript_json_v1`, rejects
  malformed/partial/non-canonical payloads and unknown speaker labels before
  writing formatter artifacts, then applies display labels only to the
  formatter projection.
- Replay route validation rejects `pdf_options`, `execution`, artifact aliases,
  whitespace-padded artifact names, and whitespace-padded canonical speaker
  labels instead of normalizing or ignoring them.
- Replay jobs do not call STT, diarization, alignment, sidecar, codec, or
  source-audio modules. The dedicated sidecar-sentinel test proves the replay
  branch succeeds without touching the audio sidecar.
- Focused replay/OpenAPI proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  passed with `31 passed`, including requested, unrequested, invalid, canceled,
  artifact-retrieval, no-sidecar, exact artifact enum, exact speaker label, and
  no ignored replay `pdf_options`/`execution` coverage.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
