---
id: story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json
title: Transcript speaker-overlay formatter replay over canonical JSON
type: story
status: completed
priority: high
created: '2026-06-13'
last_updated: '2026-06-13'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/tasks/task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json.md
  - docs/backlog/tasks/task-359-define-transcript-speaker-overlay-formatter-replay-contract.md
  - docs/backlog/tasks/task-360-implement-transcript-speaker-overlay-formatter-replay-artifacts.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-09-expose-transcript-formatter-replay-through-sir-convert-auth-edge.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md
labels:
  - transcript
  - formatter
  - replay
  - speaker-overlay
  - json
  - gateway
---

Completed implementation slice with acceptance-driven scope.

## Objective

Add a stateless formatter replay lane over saved canonical
`transcript_json_v1` so downstream products can supply speaker display-name
overlays and receive producer-owned TXT, Markdown, WebVTT, and SRT artifacts
without re-transcription, source-audio access, or downstream formatter logic.

The replay lane extends the accepted Story 54 / Task 358 formatter authority.
Sir Convert still owns deterministic product-neutral formatter artifacts.
Skriptoteket owns durable saved transcripts, speaker naming intent, filenames,
download/save workflows, search, sharing, and product-specific derivatives.
HuleEdu owns the browser-session Gateway edge.

## Settled Route Contract

The replay lane uses the existing Service API v2 async lifecycle:

- `POST /v2/convert/jobs`
- `GET /v2/convert/jobs/{job_id}`
- `GET /v2/convert/jobs/{job_id}/result`
- `GET /v2/convert/jobs/{job_id}/artifacts`
- `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`
- `POST /v2/convert/jobs/{job_id}/cancel`

The route key is:

```json
{
  "source.format": "transcript_json",
  "conversion.output_format": "transcript_bundle"
}
```

The request accepts one uploaded canonical transcript JSON file and a typed
formatter replay options object:

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "saved-transcript.json",
    "format": "transcript_json"
  },
  "conversion": {
    "output_format": "transcript_bundle"
  },
  "transcript_formatter_options": {
    "schema_version": "transcript_formatter_replay_v1",
    "requested_artifacts": ["txt", "md", "vtt", "srt"],
    "speaker_label_overrides": [
      {
        "canonical_speaker_label": "SPEAKER_00",
        "display_name": "Anna Andersson"
      }
    ]
  },
  "retention": {
    "pin": false
  }
}
```

`requested_artifacts` is a closed enum of exact lowercase values: `txt`, `md`,
`vtt`, and `srt`. Replay does not request `json`; the input JSON remains the
canonical source truth. Returned artifact keys are `transcript_txt`,
`transcript_md`, `transcript_vtt`, and `transcript_srt`.

`canonical_speaker_label` values are case-sensitive exact inventory keys from
the uploaded canonical transcript JSON. Display names are trimmed of ordinary
surrounding whitespace only after raw control-character validation.

Replay job specs reject `pdf_options` and `execution`; those fields are not
ignored, normalized, or folded out of idempotency fingerprints.

Speaker overrides apply to formatter display labels only. Sir Convert must not
rewrite, repair, or reissue the canonical transcript JSON as overlay truth.

## Scope

- Define and implement `transcript_json -> transcript_bundle` route admission.
- Accept only valid canonical `transcript_json_v1` input.
- Accept only typed `transcript_formatter_replay_v1` options.
- Reject unknown canonical speaker labels, duplicate override labels, empty
  names, duplicate display names, control characters, malformed JSON, partial
  transcript state, unsupported requested artifacts, and `retention.pin=true`.
- Reuse the Task 358 formatter strategies after applying display labels to the
  formatter projection.
- Keep replay independent from STT, diarization, sidecar, codec, alignment, and
  source-audio runtime code.
- Return named formatter artifact references through the existing artifact
  bundle surfaces.
- Keep logs, metrics, traces, and error payloads content-safe.

## Acceptance Criteria

- [x] `transcript_json -> transcript_bundle` is documented as the only
  overlay-aware formatter replay route; no bespoke formatter endpoint is added.
- [x] Replay requests are strict typed requests, not catch-all dictionaries or
  loose string bags.
- [x] Speaker overrides are validated against the canonical transcript JSON
  speaker inventory and affect formatter display labels only.
- [x] Formatter artifacts preserve segment order, timestamps, language
  evidence where format-appropriate, and the overlay display names.
- [x] Invalid replay requests fail closed and cannot produce canonical-label
  fallback exports for an overlay-aware export request.
- [x] Sir Convert does not add durable product storage, user-file behavior,
  product filenames, search, sharing, or workflow-specific Markdown.

## Test Requirements

- [x] Contract tests for request validation and route admission.
- [x] Golden overlay formatter tests for TXT, Markdown, WebVTT, and SRT.
- [x] Tests proving canonical JSON is not rewritten or replaced.
- [x] Tests proving replay code does not call STT, diarization, alignment,
  sidecar, codec, or media-processing adapters.
- [x] API lifecycle tests for requested, unrequested, invalid, canceled, and
  artifact-retrieval states.
- [x] Content-safety tests for logs, metrics labels, and public errors.

Implementation evidence:

- `transcript_json -> transcript_bundle` is registered in Service API v2 route
  policy and create-job inference for `.json` uploads.
- Replay options are exposed as typed OpenAPI components:
  `TranscriptFormatterReplayOptionsV2`,
  `TranscriptFormatterRequestedArtifactV2`, and `SpeakerLabelOverrideV2`.
- Replay `/result` returns metadata for the primary
  `transcript_replay_bundle_manifest.json` artifact, while singular
  `/artifact` streams the content-safe
  `transcript_formatter_replay_result_v1` manifest body. Neither surface
  exposes transcript text, display names, or canonical JSON truth. Named replay
  artifacts remain only `transcript_txt`, `transcript_md`, `transcript_vtt`,
  and `transcript_srt`.
- Focused replay/OpenAPI proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  passed with `31 passed`, including requested, unrequested, invalid, canceled,
  artifact-retrieval, no-sidecar, exact artifact enum, exact speaker label, and
  no ignored replay `pdf_options`/`execution` coverage.

## Done Definition

The story is done when downstream products can submit saved canonical
transcript JSON plus speaker-label overlays and receive deterministic
producer-owned TXT, Markdown, WebVTT, and SRT artifacts through the normal v2
job lifecycle.

## Checklist

- [x] Task 359 contract slice complete
- [x] Task 360 runtime slice complete
- [x] Tests and validations complete
- [x] Docs synchronized
