---
id: story-54-transcript-formatter-strategies-over-canonical-json
title: Transcript formatter strategies over canonical JSON
type: story
status: proposed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
labels:
  - transcript
  - formatter
  - json
  - vtt
  - srt
  - markdown
---

Proposed implementation slice with acceptance-driven scope.

## Objective

Add optional human-readable transcript formatter artifacts as modular
strategies over the canonical `transcript_json` artifact after the JSON core is
stable.

## Blocked Implementation Decision

Story 54 remains `proposed` and is blocked by Story 53's current governed
state. The retained review at
`docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
accepted only a blocked/proposed Story 53 outcome: no runtime
`audio -> transcript_bundle` route, no canonical `transcript_json` persistence,
and no API route surface. Because Story 54 depends on a valid canonical
`transcript_json` artifact from Story 53, this story cannot truthfully
implement formatter strategies, DI wiring, API fields, artifact persistence, or
public route behavior yet.

Do not implement formatter strategies from this story state. The next
production-enabling slice must first replace Story 53's blocked state with
accepted route execution and canonical `transcript_json` persistence, then
return to this story or a smaller linked task for formatter implementation.

Current runtime truth:

- Service API v2 create-job route registration remains absent for
  `audio -> transcript_bundle`.
- `JobSpecV2` does not accept an `audio -> transcript_bundle` create-job
  request.
- Audio public options still reject formatter artifact requests such as
  `transcript_txt`, `transcript_md`, `transcript_vtt`, and `transcript_srt`.
- No production formatter strategy, DI composition, named formatter artifact,
  API field, or formatter persistence path is authorized by this story state.

## Scope

Future runtime scope, after Story 53 has accepted route execution and canonical
`transcript_json` persistence:

- Implement formatter strategies for:
  - plain text;
  - Markdown;
  - WebVTT;
  - SubRip/SRT.
- Keep formatter logic downstream of JSON artifact assembly; formatters must
  not call STT, diarization, or segment-alignment code.
- Wire formatter strategies with small DDD/Clean components and DI where route
  composition benefits from it.
- Preserve diarization and timestamp truth in subtitle formats.
- Fail or omit formatter artifacts explicitly when the JSON core does not meet
  formatter prerequisites.
- Keep future Skriptoteket-specific presentation choices out of Sir Convert's
  core formatter strategy layer.

## Acceptance Criteria

- [ ] `transcript_txt`, `transcript_md`, `transcript_vtt`, and
  `transcript_srt` can be requested only after `transcript_json` is valid.
- [ ] Formatter artifacts are named, typed, and represented explicitly in
  bundle metadata.
- [ ] Formatters preserve segment ordering, timestamps, speaker labels, and
  warnings where the target format supports them.
- [ ] No formatter duplicates transcription, diarization, or alignment logic.
- [ ] Formatter-specific errors do not corrupt or replace the canonical JSON
  artifact.

## Test Requirements

- [ ] Golden JSON-to-TXT/Markdown/VTT/SRT formatter tests.
- [ ] Timestamp formatting and cue ordering tests for subtitle outputs.
- [ ] Speaker-label rendering tests for multi-speaker transcripts.
- [ ] Error-path tests for invalid JSON core and unsupported formatter
  requests.
- [ ] DI composition tests for route formatter strategy selection.
- [ ] Docs validation: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Done Definition

The story is done when transcript formatter artifacts are available as
side-effect-free strategies over canonical JSON and downstream consumers can
choose JSON-first persistence without waiting for every human-readable format.

Current blocked state: this done definition is not satisfied. Story 54 cannot
move to runtime implementation completion until Story 53 has accepted route
execution and canonical `transcript_json` persistence.

## Checklist

- [x] Blocked implementation decision recorded
- [x] Formatter runtime remains unimplemented
- [x] Story 53 blocked retained review linked as current blocker
- [ ] Runtime formatter implementation complete
- [ ] Runtime tests and validations complete
- [ ] Runtime docs synchronized
