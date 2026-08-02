---
id: task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json
title: Implement product-neutral transcript formatter artifacts over canonical JSON
type: task
status: completed
priority: high
created: '2026-06-12'
last_updated: '2026-06-12'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/tasks/task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json.md
  - docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/backlog/reviews/review-42-ruthless-review-of-task-356-audio-transcript-runtime-json-persistence.md
  - docs/backlog/reviews/review-43-ruthless-review-of-task-357-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/backlog/reviews/review-44-ruthless-review-of-task-358-product-neutral-transcript-formatter-artifacts.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-07-durable-transcript-saves-and-json-first-downstream-formatting.md
labels:
  - stt
  - audio
  - transcript
  - formatter
  - artifact-bundle
  - v2
---

PR-sized execution unit linked to Story 54.

## Objective

Implement Sir Convert's product-neutral transcript formatter authority for
TXT, Markdown, WebVTT, and SubRip/SRT artifacts over the accepted canonical
`transcript_json` runtime.

Task 356 and Review 42 accepted canonical JSON transcript persistence. Task
357 and Review 43 accepted the chunked progress/runtime hardening needed for
long-running audio jobs. This task is therefore no longer blocked on the old
Story 53 proposed state. It must still preserve the ownership split: Sir
Convert owns deterministic standard-format transformations; downstream
applications own product meaning, UX labels, durable saves, filenames, and
workflow-specific derivatives.

## PR Scope

- Add purpose-named domain/application formatter components for:
  - `transcript_txt`;
  - `transcript_md`;
  - `transcript_vtt`;
  - `transcript_srt`.
- Consume only validated canonical `transcript_json` payloads and metadata.
  Formatters must not call STT, diarization, codec, alignment, sidecar, or
  provider-runtime code.
- Preserve segment ordering, start/end timestamps, speaker labels, language
  evidence where format-appropriate, and content-safe warnings/notes where the
  target format can represent them.
- Define deterministic escaping and cue serialization rules for plain text,
  Markdown, WebVTT, and SubRip/SRT outputs.
- Extend `audio_transcription_options.output_artifacts` so callers may request
  `json`, `txt`, `md`, `vtt`, and `srt`, with `json` remaining the canonical
  required authority.
- Expose requested formatter artifacts through the existing Service API v2
  result, artifact list, and named artifact retrieval surfaces using the
  governed artifact keys and content types.
- Represent unrequested formatter artifacts explicitly as unrequested/not
  produced in bundle metadata when the route advertises formatter support.
- Fail closed for invalid canonical JSON or formatter precondition failures;
  do not silently produce malformed subtitle files or substitute a product
  app-specific fallback.
- Keep Sir Convert artifact retention short and operational. Do not add
  product-owned durable transcript save, user-file, search, sharing, or
  presentation workflow behavior.
- Update OpenAPI/converter/downstream docs so HuleEdu and Skriptoteket can
  consume formatter artifact availability without copying formatter logic.

Out of scope:

- Skriptoteket durable transcript save/readback.
- Lesson-material, subtitle-workbench, meeting-note, or handout semantics.
- Product-specific Markdown beyond a neutral transcript rendering.
- Local re-transcription, transcript repair, or source-audio reprocessing.
- Any direct browser, anonymous public, or direct sidecar access.

## Deliverables

Implementation checkpoint on 2026-06-12:

- Added a pure formatter domain module for TXT, Markdown, WebVTT, and SRT over
  validated canonical `transcript_json`.

- Normalized `audio_transcription_options.output_artifacts` so `json` remains
  canonical and required while callers may request `txt`, `md`, `vtt`, and
  `srt`; unsupported aliases still fail closed.

- Added requested formatter sibling artifacts, manifest metadata, and named
  retrieval while representing unrequested formatters as `unrequested`.

- Preserved product-neutral boundaries: formatter code does not import or call
  STT, diarization, sidecar, alignment, codec, or media-processing modules.

- Review 44 accepted the implementation after the pass-two module extraction
  kept `specs_v2.py` below the repo line-limit/SRP gate.

- [x] Product-neutral formatter domain/application components for TXT,
  Markdown, WebVTT, and SRT.

- [x] Service API v2 request validation that accepts requested formatter
  artifacts only for `audio -> transcript_bundle` jobs backed by canonical
  `transcript_json`.

- [x] Artifact bundle metadata and named retrieval for
  `transcript_txt`, `transcript_md`, `transcript_vtt`, and `transcript_srt`.

- [x] Golden fixture tests for JSON-to-TXT/Markdown/VTT/SRT output.

- [x] API/result/artifact tests for requested, unrequested, and invalid
  formatter artifacts.

- [x] OpenAPI/converter/downstream docs synchronized.

## Acceptance Criteria

- [x] `audio_transcription_options.output_artifacts` accepts `txt`, `md`,
  `vtt`, and `srt` only alongside or after a valid canonical JSON transcript
  authority; no request path can ask a formatter to run from source audio or
  partial transcript state.
- [x] Successful requested formatter artifacts are listed with stable artifact
  keys, content types, byte sizes, checksums where the bundle contract supports
  them, and named artifact retrieval URLs.
- [x] WebVTT and SRT outputs have deterministic cue ordering, timestamp
  formatting, escaping, and speaker-label rendering for single-speaker and
  multi-speaker fixtures.
- [x] Plain text and neutral Markdown outputs preserve transcript ordering and
  speaker/timestamp information without adding product-specific headings,
  classroom workflow labels, lesson-material sections, or downstream file
  naming policy.
- [x] Formatter errors cannot corrupt, rewrite, or replace the canonical
  `transcript_json` artifact and cannot be reported as successful missing
  files.
- [x] Existing JSON-only audio requests continue to work unchanged.
- [x] Existing PDF, DOCX, Markdown-document, HTML, DigiExam, TTS, and Gateway
  access behavior is unchanged except for documented audio formatter artifact
  availability.

## Test Requirements

- [x] Red-first unit tests for formatter output over checked-in canonical
  transcript JSON fixtures.
- [x] Red-first WebVTT/SRT tests for cue numbering, timestamp precision,
  ordering, escaping, and overlapping or adjacent segments.
- [x] Red-first tests proving formatter components do not call STT,
  diarization, alignment, sidecar, or media-processing adapters.
- [x] Red-first API lifecycle tests for JSON-only, JSON plus each formatter,
  all-format request, unsupported artifact requests, invalid JSON authority,
  and named artifact retrieval.
- [x] Content-safety tests proving logs, metadata labels, and error messages do
  not include transcript text, source content, utterances, provider/model
  internals, or media hashes as labels.
- [x] Validation commands:
  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run typecheck-all`
  - focused `pdm run pytest-root <formatter-test-paths>`
  - `pdm run docs-sync`
  - `pdm run docs-validate`
  - `pdm run skills-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

Validation evidence:

- Red-first focused suite failed before implementation with `10 failed, 47 passed` for missing formatter module/writer, formatter admission rejection,
  and `not_implemented` manifest behavior.
- Focused Task 358 suite passed after implementation and pass-two extraction:
  `57 passed`.
- `pdm run format-all`, `pdm run lint-fix`, `pdm run typecheck-all`,
  `pdm run docs-sync`, `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check` passed for the accepted
  slice.
- `pdm run coverage-gate` reached the conversion-core threshold but failed on
  an unrelated Qwen checkpoint/training disk precondition; Review 44 records
  the residual validation risk.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
