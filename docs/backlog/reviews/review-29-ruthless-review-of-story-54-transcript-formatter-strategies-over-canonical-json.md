---
id: 'review-29-ruthless-review-of-story-54-transcript-formatter-strategies-over-canonical-json'
title: 'Ruthless review of Story 54 transcript formatter strategies over canonical JSON'
type: 'review'
status: 'completed'
priority: 'high'
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
labels:
  - review
  - approved
  - story-54
  - stt
  - transcript-formatters
  - blocked-state
---
Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless review of Story 54's blocked implementation outcome.
- Decision frame: Story 54 may only be accepted as a truthful proposed/blocked
  state while Story 53 is accepted only as blocked/proposed in Review 28. This
  review does not approve formatter strategies, DI wiring, API fields, artifact
  persistence, public route behavior, or route registration.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
  - `docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
  - `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
  - `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
- Files reviewed:
  - `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
  - `tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py`
  - route/spec authority files inspected:
    `scripts/sir_convert_a_lot/domain/specs_v2.py`,
    `scripts/sir_convert_a_lot/domain/service_routes_v2.py`,
    `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py`, and
    `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py`.
- Working-tree and untracked-file inspection:
  - `git status --short` was inspected directly.
  - The expected Story 54 doc modification and new blocked-state test are in
    scope.
  - Two unrelated untracked input artifacts under `inputs/` are outside this
    review scope and are not approved for commit by this review.
- Public or operational surfaces affected:
  - No live Service API v2 create-job route is registered for
    `audio -> transcript_bundle`.
  - `JobSpecV2` does not accept `source.format = "audio"` or
    `conversion.output_format = "transcript_bundle"`.
  - Audio public options still reject formatter artifact requests such as
    `transcript_txt`, `transcript_md`, `transcript_vtt`, and `transcript_srt`.
  - No production formatter strategy, DI composition, named formatter artifact,
    API field, formatter persistence path, sidecar runtime route, or OpenAPI
    route surface is introduced by the reviewed patch.
- Compatibility posture:
  - Story 54 remains `proposed` and blocked until Story 53 is superseded by
    accepted route execution plus canonical `transcript_json` persistence.
  - Formatter outputs remain future downstream strategies over the JSON core,
    not parallel transcription or diarization pipelines.

## Review Evidence

- Existing retained reviews were searched with
  `rg -n "story-54|Story 54|transcript formatter|formatter strategies" docs/backlog/reviews docs/backlog/stories docs/index.md`;
  no prior Story 54 review artifact existed.
- Story 54 records `status: proposed` at
  `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md:5`.
- Story 54 records the blocked implementation decision at
  `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md:31`.
- Story 54 explicitly says not to implement formatter strategies, DI wiring, API
  fields, artifact persistence, or public route behavior from this story state at
  `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md:33`.
- Story 54 records the current runtime truth that the route remains absent,
  `JobSpecV2` rejects the route, and formatter artifact requests are unsupported
  at
  `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md:46`.
- Story 53 remains `proposed` and blocked by Story 52 production-profile
  rejection at
  `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md:5`
  and
  `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md:35`.
- Review 28 approved only Story 53's blocked state and explicitly did not
  authorize route registration, transcript artifact persistence, or formatter
  behavior at
  `docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md:28`.
- Epic 12 gates formatter outputs until after the JSON contract and core
  transcription path are proven at
  `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md:74`
  and
  `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md:97`.
- ADR-0013 states that plain text, Markdown, VTT, and SRT are formatter
  strategies over the JSON core at
  `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:249`.
- `SourceFormatV2` has no `audio` member and `OutputFormatV2` has no
  `transcript_bundle` member in
  `scripts/sir_convert_a_lot/domain/specs_v2.py`.
- `SERVICE_ROUTE_POLICIES_V2` does not include an audio route in
  `scripts/sir_convert_a_lot/domain/service_routes_v2.py`.
- `build_create_job_route_registry_v2()` registers only document routes and the
  DigiExam migration route in
  `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py`.
- `AudioTranscriptionPublicOptions.validation_failure()` rejects requested
  artifacts outside `DAY_ONE_OUTPUT_ARTIFACTS = {"json"}` in
  `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py`.
- Runtime search:
  `rg -n "formatter|Formatter|transcript_txt|transcript_md|transcript_vtt|transcript_srt|transcript_json|transcript_bundle|audio_transcription_options" scripts/sir_convert_a_lot --glob '!scripts/sir_convert_a_lot/tts_sidecar/**' --glob '!scripts/sir_convert_a_lot/ml/**'`
  returned only unrelated Markdown linting, Story 52 benchmark-profile
  blocked-state documentation, and Story 51 audio policy references. It did not
  find a runtime formatter strategy, DI binding, route key, request field,
  artifact key, or persistence path.
- Focused tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py`
  -> `6 passed`.

## Pass 2 Remediation Review

- Remediation scope reviewed on 2026-06-09:
  - `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
  - `tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py`
- The retained Review 28 path is now included in Story 54 `related` frontmatter
  at
  `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md:12`.
- The blocked-decision prose now points directly at the retained Review 28 path
  at
  `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md:35`.
- The docs-as-code guard now asserts that Story 54 frontmatter contains the
  exact retained Review 28 path at
  `tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py:100`.
- The runtime blocked-state assertions remain in place:
  - v2 route registry does not expose `audio -> transcript_bundle`;
  - `JobSpecV2` rejects an `audio -> transcript_bundle` request;
  - audio public options reject `transcript_txt`, `transcript_md`,
    `transcript_vtt`, and `transcript_srt`.
- Runtime search:
  `rg -n "formatter|Formatter|transcript_txt|transcript_md|transcript_vtt|transcript_srt|transcript_json|transcript_bundle|audio_transcription_options" scripts/sir_convert_a_lot --glob '!scripts/sir_convert_a_lot/tts_sidecar/**' --glob '!scripts/sir_convert_a_lot/ml/**'`
  returned only existing blocked-state or policy docstring references and an
  unrelated Markdown linting formatter reference. It did not find formatter
  strategy code, DI wiring, API fields, artifact persistence, or route
  registration.
- Focused pass 2 tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py`
  -> `6 passed`.

## Test Truthfulness Audit

- `test_transcript_formatters_stay_blocked_without_canonical_json_runtime` is
  behavior-focused for this blocked slice: it asks the real v2 create-job
  registry for registered route keys and validates that `JobSpecV2` rejects an
  `audio -> transcript_bundle` request.
- `test_formatter_artifact_requests_are_rejected_while_story_53_is_blocked`
  proves the public audio options boundary rejects the future formatter artifact
  names while only JSON is day-one accepted.
- `test_story_54_records_blocked_decision_without_runtime_completion` is a
  docs-as-code guard. Its string assertions are acceptable here because the
  governed artifact text is part of the reviewed state boundary, and the other
  tests carry runtime boundary proof.
- The tests do not claim to prove successful formatter output, DI composition,
  transcript artifact persistence, API publication, route execution, or sidecar
  behavior. Those remain unchecked runtime requirements for later governed
  slices.
- The retained-review-link proof is now complete for this blocked slice: the
  docs test requires Story 54 frontmatter to contain the exact retained Review
  28 path, and the story body names that same retained review as the current
  blocker authority.

## Findings

- [x] Pass 1 medium finding resolved. Story 54 now links the retained Review 28
  path in frontmatter and blocked-decision prose, and the blocked-state test
  guards that linkage.
- [x] No remaining blocking findings.

## Decision

approved

The Story 54 blocked outcome is accepted as truthful, governed, and sufficiently
protected for the current non-runtime state. Story 54 remains proposed/blocked
until Story 53 is superseded by accepted route execution plus canonical
`transcript_json` persistence.

## Response

The remediation resolves the retained-review linkage gap. No formatter strategy,
DI wiring, API field, artifact persistence, route registration, or runtime route
behavior was added or authorized by this review.

## Follow-up Actions

1. No additional runtime implementation follow-up is authorized by this review.

## Completion

Review artifact created and decision recorded on 2026-06-09. Docs validation was
run after this retained review was created. Pass 2 approved the remediation on
2026-06-09; see final response for command results.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
