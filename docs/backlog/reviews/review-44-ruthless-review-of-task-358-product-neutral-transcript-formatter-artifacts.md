---
id: review-44-ruthless-review-of-task-358-product-neutral-transcript-formatter-artifacts
title: Ruthless review of Task 358 product-neutral transcript formatter artifacts
type: review
status: completed
priority: high
created: '2026-06-12'
last_updated: '2026-06-12'
related:
  - docs/backlog/tasks/task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json.md
  - docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/reviews/review-42-ruthless-review-of-task-356-audio-transcript-runtime-json-persistence.md
  - docs/backlog/reviews/review-43-ruthless-review-of-task-357-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
labels:
  - review
  - approved
  - task-358
  - story-54
  - stt
  - audio
  - transcript-formatters
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: fixed ruthless implementation review for Task 358 working tree.
- Reviewer independence: reviewer did not author the production implementation
  or material Task 358 docs under review; this artifact is the only review edit.
- Required instructions read:
  - `AGENTS.md`
  - `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
  - `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
  - `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
  - `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
  - `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
  - `.codex/rules/000-rule-index.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/030-conversion-workflows.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
- Governing authority:
  - `docs/backlog/tasks/task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json.md`
  - `docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/downstream_integration_contract_v2.md`
- Existing retained-review search:
  - `rg -n "Task 358|task-358|358|Story 54|story-54|transcript formatter|formatter" docs/backlog/reviews`
  - No existing Task 358 review artifact was found. Review 29 covers the
    historical blocked Story 54 state, not the Task 358 implementation.
- Working tree scope reviewed:
  - `scripts/sir_convert_a_lot/domain/transcript_formatter_artifacts.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py`
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_artifacts.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py`
  - `tests/fixtures/transcript_formatter_canonical.json`
  - `tests/sir_convert_a_lot/test_transcript_formatter_artifacts.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py`
  - `tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py`
  - deleted `tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py`
  - Task/story/converter/downstream docs listed in the governing authority and
    generated docs surfaces touched by prior `docs-sync`.
- Public surfaces affected:
  - Service API v2 `audio -> transcript_bundle`
    `audio_transcription_options.output_artifacts` accepts `json`, `txt`,
    `md`, `vtt`, and `srt`, with `json` normalized as canonical authority.
  - Service API v2 audio named-artifact manifest now includes requested
    formatter artifacts with stable keys, content types, filenames, byte sizes,
    checksums, and retrieval paths when available.
  - Service API v2 named artifact retrieval now serves `transcript_txt`,
    `transcript_md`, `transcript_vtt`, and `transcript_srt` when requested and
    written, and reports explicit `unrequested` or `unavailable` states.
- Compatibility posture:
  - Additive public availability for formatter aliases and named artifacts over
    the already accepted canonical `transcript_json`.
  - Existing JSON-only audio requests remain valid and formatters are explicit
    `unrequested`.
  - No legacy blocked-state compatibility is required; deleting the stale
    blocked-state test is consistent with Story 54 becoming active.

## Pass 2 Scope

- Re-review trigger: Dalton resolved the Review 44 `changes_requested` finding
  by extracting audio public-option key validation and formatter
  `output_artifacts` normalization from `domain.specs_v2` into
  `domain.audio_transcription_options_v2`.
- Pass 2 files inspected:
  - `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py`
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`
  - `docs/backlog/reviews/review-44-ruthless-review-of-task-358-product-neutral-transcript-formatter-artifacts.md`
- Pass 2 boundary check:
  - `AudioTranscriptionOptionsV2` now delegates normalization and unsupported
    key rejection to purpose-named domain helpers.
  - The new helper module has a Google-style module docstring describing domain
    purpose and relationships.
  - No compatibility shim, retired blocked-state behavior, or formatter fallback
    was introduced by the extraction.
- Pass 2 line-count proof:
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`: 488 lines.
  - `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py`: 69 lines.
  - `scripts/sir_convert_a_lot/domain/transcript_formatter_artifacts.py`: 361 lines.
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_artifacts.py`: 215 lines.

## Evidence Reviewed

- Code inspection found the formatter domain module validates canonical
  `transcript_json` and renders deterministic TXT, Markdown, WebVTT, and SRT
  outputs without importing or calling STT, diarization, sidecar, codec,
  alignment, or media-processing modules.
- Request validation accepts only `json`, `txt`, `md`, `vtt`, and `srt`;
  unsupported aliases fail with `audio_public_options_unsupported`, and route
  policy still confines `audio_transcription_options` to
  `audio -> transcript_bundle`.
- Artifact publication fails closed on invalid canonical JSON before terminal
  success can be marked, preserves the canonical JSON bytes already written,
  and does not report success for missing requested formatter files.
- Tests are behavioral enough for the formatter slice: they assert golden
  formatter bytes, API request normalization, manifest metadata, named
  retrieval bytes/content types, explicit unrequested states, invalid JSON
  fail-closed behavior, and JSON-only compatibility.
- Handoff and story/task docs correctly keep terminal Task 358 and Story 54
  acceptance pending review rather than prematurely marking completion.
- No `typing.Any`, `typing.cast`, `cast(...)`, `# type: ignore`, or `# noqa`
  patterns were found in the reviewed implementation/test files.
- Pass 2 code inspection found no `typing.Any`, `typing.cast`, `cast(...)`,
  `# type: ignore`, or `# noqa` patterns in the extracted
  `audio_transcription_options_v2.py` or the remaining `specs_v2.py` audio
  validator wiring.

## Validation

- Passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_artifacts.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py`
  with `57 passed`.
- Passed: `pdm run docs-validate`.
- Passed: `git diff --check`.
- Pass 2 passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_artifacts.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py`
  with `57 passed`.
- Pass 2 passed: `pdm run typecheck-all` with
  `Success: no issues found in 868 source files`.
- Pass 2 passed line-count proof:
  `wc -l scripts/sir_convert_a_lot/domain/specs_v2.py scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py scripts/sir_convert_a_lot/domain/transcript_formatter_artifacts.py scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_artifacts.py`.
- Not rerun by reviewer:
  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run coverage-gate`
- Residual validation risk:
  - Implementer reported `format-all` passed and `lint-fix` fixed one
    import/order issue then passed. Reviewer did not independently rerun those
    formatting gates.
  - Implementer previously reported `coverage-gate` reached coverage threshold
    but failed on an unrelated Qwen checkpoint/training disk free-space
    precondition and a stale blocked-state test that has since been retired.
    Reviewer did not independently rerun `coverage-gate`.

## Findings

1. [x] `medium` - `specs_v2.py` now violates the repo's module-size/SRP gate.

   Evidence:

   - Task 358 adds output-artifact normalization inside
     `AudioTranscriptionOptionsV2` at
     `scripts/sir_convert_a_lot/domain/specs_v2.py:267`.
   - The module now ends at
     `scripts/sir_convert_a_lot/domain/specs_v2.py:522`.
   - `.codex/rules/010-foundational-principles.md` requires splitting before
     files exceed 500 LoC, and `.codex/rules/070-testing-and-quality-gates.md`
     repeats the same limit.

   Why it matters:
   `specs_v2.py` is the central v2 request model surface for PDF, DOCX,
   DigiExam, and audio routes. Task 358 pushed more route-specific audio
   behavior into that already broad module, crossing the explicit repo limit
   and making future route-specific validation harder to keep DRY and SRP
   aligned. The formatter behavior itself is not failing, but approving the
   change would bless a known violation of the repo's strict module-boundary
   rule.

   Required fix:
   Extract the audio transcription option model/normalization logic from
   `domain.specs_v2` into a purpose-named domain module, for example an audio
   v2 options/contracts module, and import the typed model back into
   `JobSpecV2`. Keep route validation behavior unchanged, preserve the
   Google-style module docstring, and keep both the extracted module and
   `specs_v2.py` under the repo limit.

   Proof requirement:
   Run the focused suite plus typecheck after the extraction:
   `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_artifacts.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py`
   and `pdm run typecheck-all`. Include `wc -l` evidence for the affected
   modules in the re-review notes.

   Pass 2 disposition:
   Resolved. Audio-specific option key validation and formatter
   `output_artifacts` normalization now live in
   `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py`, while
   `AudioTranscriptionOptionsV2` in `specs_v2.py` only wires Pydantic
   validators to the helper functions. The affected modules are under the repo
   limit: `specs_v2.py` is 488 lines and
   `audio_transcription_options_v2.py` is 69 lines. The focused suite passed
   with `57 passed`, and `pdm run typecheck-all` passed with no issues in 868
   source files.

## Decision

`approved`.

Task 358 is approved after pass 2. Formatter artifacts are derived from
canonical JSON, the API semantics are explicit, formatter failures fail closed,
the focused behavioral proof passed, typecheck passed, and the prior
module-size/SRP blocker is resolved.

## Response

No further Task 358 code changes are requested by this review.

## Follow-up Actions

1. None required for Task 358 approval from this review.

## Completion

Review retained with `changes_requested` on pass 1 and updated to `approved`
after pass 2 on 2026-06-12.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up actions recorded
- [x] Review closed
