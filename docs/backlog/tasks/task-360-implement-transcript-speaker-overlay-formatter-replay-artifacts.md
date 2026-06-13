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
- Remediation proof tightened ambiguous client docs: `/result` is documented as
  a metadata envelope whose `result.artifact` points at
  `transcript_replay_bundle_manifest.json`; singular `/artifact` is documented
  as the route that streams the replay manifest body.
- Red-first observability proof
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_replay_observability_v2.py -q`
  first failed because replay logs did not include the caller correlation id,
  then passed after the HTTP middleware emitted content-safe request-completion
  logs with correlation id, method, route template, status, and duration. The
  combined replay-focused suite later passed with `32 passed`:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_transcript_replay_observability_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`.
- Deployed producer proof: `pdm run run-local-pdm hemma-deploy-and-verify --expected-revision f721296cc8a0e9065aae9a12485365717435b19f --lane host`
  passed with service, remote, and expected revisions all matching
  `f721296cc8a0e9065aae9a12485365717435b19f`.
- Live Gateway-to-producer proof from HuleEdu TASK-0675 passed against Sir
  Convert revision `f721296cc8a0e9065aae9a12485365717435b19f` and Gateway
  revision `cef615161aac0070f70233461fd85f1cf4a636c0`: public browser-auth
  replay job `jobv2_33914fad35674215a70820ae7e` reached `succeeded`, `/result`
  stayed metadata-only, `/artifact` and `/artifacts` returned content-safe
  replay manifests with only `transcript_txt`, `transcript_md`,
  `transcript_vtt`, and `transcript_srt`, all four named artifacts contained
  the projected overlay label and transcript content, and
  `transcript_json` named artifact retrieval returned `404`.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
