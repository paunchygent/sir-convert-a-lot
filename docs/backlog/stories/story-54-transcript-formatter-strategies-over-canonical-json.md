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

Implementation slice with acceptance-driven scope.

## Objective

Add optional human-readable transcript formatter artifacts as modular
strategies over the canonical `transcript_json` artifact after the JSON core is
stable.

## Scope

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

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
