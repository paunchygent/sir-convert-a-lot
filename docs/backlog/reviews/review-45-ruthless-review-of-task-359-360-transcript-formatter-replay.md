---
id: review-45-ruthless-review-of-task-359-360-transcript-formatter-replay
title: Ruthless review of Task 359 360 transcript formatter replay
type: review
status: completed
priority: high
created: '2026-06-13'
last_updated: '2026-06-13'
related:
  - docs/backlog/tasks/task-359-define-transcript-speaker-overlay-formatter-replay-contract.md
  - docs/backlog/tasks/task-360-implement-transcript-speaker-overlay-formatter-replay-artifacts.md
  - docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md
  - docs/backlog/tasks/task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json.md
  - docs/backlog/reviews/review-44-ruthless-review-of-task-358-product-neutral-transcript-formatter-artifacts.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
labels:
  - review
  - approved
  - task-359
  - task-360
  - story-56
  - transcript-formatters
  - replay
  - speaker-overlay
---

Structured review artifact for implementation or readiness checks.

## Findings

1. [x] `high` - The replay route silently accepts and drops non-contract
   `pdf_options` and `execution` fields.

   Evidence:

   - `scripts/sir_convert_a_lot/domain/service_routes_v2.py:241` defines the
     `transcript_json -> transcript_bundle` policy with
     `ignores_pdf_options=True` and `ignores_execution=True`.
   - `scripts/sir_convert_a_lot/domain/specs_v2.py:389` strips route-ignored
     runtime options before `JobSpecV2` route validation runs.
   - `scripts/sir_convert_a_lot/domain/service_routes_v2.py:348` also removes
     those ignored fields from the request fingerprint.

   Why it matters:
   Task 359/360 are explicitly the strict replay contract clients are supposed
   to implement against. Accepting and normalizing away `pdf_options` or
   `execution` lets clients send a shape that is not part of the replay
   contract, then receive a successful job anyway. It also means two create
   requests that differ only by those non-contract fields collapse to the same
   idempotency fingerprint, hiding producer/consumer drift instead of failing
   closed.

   Required fix:
   Treat `pdf_options` and `execution` as unsupported for
   `transcript_json -> transcript_bundle`: remove the replay route's
   `ignores_pdf_options` / `ignores_execution` behavior while leaving any
   separately governed non-replay route behavior alone. The replay route should
   reject those fields with a typed validation error, not accept a compatibility
   shape.

   Proof requirement:
   Add focused tests proving `JobSpecV2` and `POST /v2/convert/jobs` reject
   replay specs containing `execution` or `pdf_options`, and that the replay
   idempotency path no longer treats those fields as ignored route noise. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`.

   Pass 2 disposition:
   Resolved. The replay route policy no longer sets `ignores_pdf_options` or
   `ignores_execution` in
   `scripts/sir_convert_a_lot/domain/service_routes_v2.py`, so `JobSpecV2`
   reaches route validation with those fields intact and rejects them as
   unsupported replay options. `tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py`
   proves both model-level rejection and HTTP idempotency behavior, including
   that a rejected replay request with `execution` is not replayed from an
   existing idempotent success.

1. [x] `medium` - Replay option validation still accepts aliases and silently
   normalizes values that the settled contract says must be strict.

   Evidence:

   - `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py:213`
     implements `normalize_transcript_formatter_requested_artifacts`, and
     lines `223-233` strip/lower-case entries before mapping them back to the
     enum order. That accepts values such as `"TXT"` or `" txt "` even though
     Task 359 defines a closed enum of exact values `txt`, `md`, `vtt`, and
     `srt`.
   - `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py:116`
     validates both `canonical_speaker_label` and `display_name` by first
     applying `value.strip()` at line `120`, then checking control characters
     at line `123`. Leading or trailing control characters such as
     `"Anna\n"` or `"SPEAKER_00\t"` are therefore removed instead of rejected.
   - The same strip behavior changes `canonical_speaker_label` before runtime
     inventory validation, so labels with leading/trailing whitespace can match
     the uploaded transcript even though the contract describes exact
     canonical labels.

   Why it matters:
   The point of Task 0359 landing first is to keep HuleEdu and Skriptoteket from
   building against stale or loose replay shapes. This normalization creates
   undocumented aliases and a partial fail-open path for malformed overlay
   input. It is especially risky for the overlay lane because invalid overlay
   intent should fail before artifact generation rather than be repaired into a
   different request.

   Required fix:
   For replay `requested_artifacts`, require exact enum strings without
   whitespace or case normalization. For `canonical_speaker_label`, preserve
   the submitted value and let runtime inventory validation enforce exact label
   identity. For `display_name`, check raw input for control characters before
   any intentional trimming; if trimming remains desired for ordinary spaces,
   document it and keep it after the raw control-character gate.

   Proof requirement:
   Add replay option tests for uppercase/whitespace artifact aliases, speaker
   labels with surrounding whitespace or control characters, and display names
   with leading/trailing control characters. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py`.

   Pass 2 disposition:
   Resolved. `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py`
   now requires exact replay artifact strings, preserves
   `canonical_speaker_label` verbatim, rejects raw control characters before
   display-name trimming, and lets runtime inventory validation fail padded
   speaker labels. The new strict replay tests cover uppercase artifacts,
   whitespace-padded artifacts, raw control characters, and whitespace-padded
   speaker labels that must fail with `unknown_speaker_label`.

1. [x] `low` - The public replay examples use a speaker label shape that is
   easy to copy into an invalid request for Sir Convert-emitted transcripts.

   Evidence:

   - `docs/converters/audio-transcription-service-api-artifact-contract.md:129`
     uses `"canonical_speaker_label": "speaker_00"`.
   - `docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md:82`
     uses the same lowercase example.
   - The checked-in canonical transcript fixture and current audio runtime
     behavioral tests use `SPEAKER_00` / `SPEAKER_01`, for example
     `tests/fixtures/transcript_formatter_canonical.json:42`.

   Why it matters:
   Runtime overlay validation is exact against the uploaded canonical transcript
   speaker inventory. Since this contract is supposed to guide downstream
   clients before they implement against the new shape, examples should not
   imply label normalization or a lowercase convention that current
   Sir Convert-emitted transcripts do not use.

   Required fix:
   Update replay examples to use exact labels from the uploaded canonical JSON,
   preferably `SPEAKER_00` / `SPEAKER_01` for examples derived from the current
   audio transcript output, and state that labels are case-sensitive exact
   inventory keys.

   Proof requirement:
   Run `pdm run docs-sync`, `pdm run docs-validate`, and the focused replay
   tests after the docs/test update.

   Pass 2 disposition:
   Resolved. The replay examples in
   `docs/converters/audio-transcription-service-api-artifact-contract.md` and
   `docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md`
   now use `SPEAKER_00`, and the converter/story/task/downstream docs state
   exact lowercase artifact values, case-sensitive exact speaker inventory
   labels, and replay rejection for `pdf_options` / `execution`.

## Pass 2 Review

- Re-review trigger: remediation for all three Review 45 findings.
- Pass 2 files inspected:
  - `scripts/sir_convert_a_lot/domain/service_routes_v2.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py`
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`
  - `tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py`
  - `tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/downstream_integration_contract_v2.md`
  - `docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md`
  - `docs/backlog/tasks/task-359-define-transcript-speaker-overlay-formatter-replay-contract.md`
  - `docs/backlog/tasks/task-360-implement-transcript-speaker-overlay-formatter-replay-artifacts.md`
- Pass 2 boundary check:
  - The replay route now fails closed on non-contract runtime options.
  - Replay formatter artifacts remain the only named replay artifacts; no
    `transcript_json` replay artifact is introduced.
  - The strictness tests exercise public request/model behavior and idempotency,
    not helper-call internals.
  - Audio `audio -> transcript_bundle` compatibility remains covered by the
    focused audio runtime and formatter artifact tests.
- Pass 2 line-count proof:
  - `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py`: 240 lines.
  - `scripts/sir_convert_a_lot/domain/service_routes_v2.py`: 356 lines.
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`: 426 lines.
  - `tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py`: 139 lines.

## Validation Evidence

Implementer-reported passed gates:

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all` with no issues in 873 source files.
- `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  with `23 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_artifacts.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py -q`
  with `17 passed`.
- `pdm run coverage-gate` with `1692 passed`, `6 skipped`, and total coverage
  `95.79%`.
- `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.
- Pass 2 implementer-reported passed gates:
  - `pdm run docs-sync`
  - `pdm run format-all` with `923 files unchanged`
  - `pdm run lint-fix`
  - `pdm run typecheck-all` with no issues in 874 source files
  - `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
    with `31 passed`
  - `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_artifacts.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py -q`
    with `17 passed`
  - `pdm run coverage-gate` with `1700 passed`, `6 skipped`, and total
    coverage `95.79%`
  - `pdm run docs-validate`, `pdm run skills-validate`,
    `pdm run handoff-validate`, and `git diff --check`

Reviewer inspection evidence:

- Reviewed route policy, spec validation, create-job admission, runtime replay,
  named artifact manifest/retrieval, primary `/result` and singular `/artifact`
  behavior, OpenAPI component exposure, focused replay tests, formatter artifact
  tests, and governed Story 56 / Task 359 / Task 360 docs.
- Confirmed the replay runtime branch does not call STT, diarization, sidecar,
  alignment, codec, or source-audio execution modules.
- Confirmed the replay primary result manifest is content-safe: no transcript
  text, display names, uploaded JSON, or canonical JSON truth is included in
  the primary `/result` metadata or singular `/artifact` manifest.
- Confirmed named replay artifacts are restricted to `transcript_txt`,
  `transcript_md`, `transcript_vtt`, and `transcript_srt`; named
  `transcript_json` retrieval fails with `transcript_replay_artifact_unavailable`.
- Confirmed existing audio `audio -> transcript_bundle` JSON and formatter
  tests still cover `transcript_json` availability, JSON-only behavior, and
  requested TXT/MD/VTT/SRT formatter artifacts.
- Line-count proof from `wc -l` keeps reviewed production modules below the
  repo limit: `specs_v2.py` 426 lines, `service_routes_v2.py` 358 lines,
  `audio_transcription_options_v2.py` 234 lines,
  `transcript_formatter_replay_runtime.py` 184 lines,
  `audio_transcript_bundle_artifacts.py` 241 lines,
  `http_create_job_routes_v2.py` 476 lines,
  `http_routes_job_artifacts_v2.py` 481 lines, and
  `http_routes_jobs_v2.py` 476 lines.

Reviewer did not rerun the full implementer test matrix before this pass. The
findings above are from code and contract inspection against the current
uncommitted diff.

- Pass 2 reviewer-rerun focused proof:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py tests/sir_convert_a_lot/test_transcript_formatter_replay_strict_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
    passed with `31 passed`.
  - `pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_artifacts.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py -q`
    passed with `17 passed`.

## Review Scope

- Review type: retained ruthless implementation review for Task 359 / Task 360
  current uncommitted Sir Convert-a-Lot diff.
- Reviewer independence: reviewer did not author the production implementation
  or tests under review; this artifact is the only intentional review edit.
- Existing retained-review search:
  `git ls-files docs/backlog/reviews | sort | tail -n 20` confirmed
  `review-44` was the previous review, so this review uses `review-45`.

Required instructions read:

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

Governing authority:

- `docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md`
- `docs/backlog/tasks/task-359-define-transcript-speaker-overlay-formatter-replay-contract.md`
- `docs/backlog/tasks/task-360-implement-transcript-speaker-overlay-formatter-replay-artifacts.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/downstream_integration_contract_v2.md`

Working tree scope reviewed:

- `.codex/handoff.md`
- `.codex/long-term-memory/index.md`
- `.codex/long-term-memory/entries/session-2026-06-13-handoff-trimmed-formula-history.md`
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
- `docs/backlog/INDEX.md`
- `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
- `docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md`
- `docs/backlog/tasks/task-359-define-transcript-speaker-overlay-formatter-replay-contract.md`
- `docs/backlog/tasks/task-360-implement-transcript-speaker-overlay-formatter-replay-artifacts.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `scripts/sir_convert_a_lot/domain/audio_transcription_options_v2.py`
- `scripts/sir_convert_a_lot/domain/service_route_policy_validation_v2.py`
- `scripts/sir_convert_a_lot/domain/service_routes_v2.py`
- `scripts/sir_convert_a_lot/domain/source_format_inference_v2.py`
- `scripts/sir_convert_a_lot/domain/specs_v2.py`
- `scripts/sir_convert_a_lot/domain/transcript_formatter_artifacts.py`
- `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_artifacts.py`
- `scripts/sir_convert_a_lot/infrastructure/transcript_formatter_replay_runtime.py`
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`
- `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_transcript_formatter_replay_request_v2.py`
- `tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
- `tests/sir_convert_a_lot/test_openapi_contract_v2.py`
- `tests/sir_convert_a_lot/test_transcript_formatter_replay_v2.py`

Public surfaces affected:

- Service API v2 route key `transcript_json -> transcript_bundle`.
- `POST /v2/convert/jobs` multipart admission for canonical transcript JSON
  uploads.
- `GET /v2/convert/jobs/{job_id}`, `/result`, singular `/artifact`,
  `/artifacts`, named `/artifacts/{artifact_key}`, and `/cancel` behavior for
  replay jobs.
- OpenAPI `SourceFormatV2`, `OutputFormatV2`, `JobSpecV2`,
  `TranscriptFormatterReplayOptionsV2`,
  `TranscriptFormatterRequestedArtifactV2`, and `SpeakerLabelOverrideV2`.
- Converter and downstream integration docs for replay artifacts.

Compatibility posture:

- This is an additive route key on the v2 job lifecycle, but the replay request
  contract itself is new and should be strict. No compatibility aliases,
  wrapper routes, local downstream formatters, source-audio replay, or Gateway
  response rewrites are governed for this slice.
- Existing `audio -> transcript_bundle` behavior must remain compatible:
  canonical `transcript_json` remains available for audio jobs, formatter
  artifacts remain explicitly requested, and JSON-only audio behavior remains
  valid.

## Decision

`approved`.

Task 359/360 are approved after pass 2. The replay route now rejects
non-contract `pdf_options` / `execution`, replay artifact requests are exact
lowercase enum values, canonical speaker labels are exact case-sensitive
inventory keys, and docs/tests now encode those strict semantics before
downstream clients build against the producer contract.

## Response

No further Task 359/360 code changes are requested by this review.

## Follow-up Actions

1. None required for Task 359/360 approval from this review.

## Completion

Review retained with `changes_requested` on pass 1 and updated to `approved`
after pass 2 on 2026-06-13.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
