---
id: review-27-ruthless-review-of-story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection
title: Ruthless review of Story 52 Hemma STT and diarization backend benchmark profile selection
type: review
status: completed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - review
  - approved
  - story-52
  - stt
  - diarization
  - benchmark
  - hemma
  - gpu
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless implementation review of Story 52.
- Decision frame: Story 52 is acceptable only as a governed rejection outcome.
  It must not present a local-only selector or fake evidence bundle as
  production STT/diarization readiness.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/030-conversion-workflows.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/_meta/docs-contract.yaml`
  - `docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md`
  - `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
- Files reviewed:
  - `scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  - `docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md`
  - `docs/backlog/INDEX.md`
- Working-tree and untracked-file inspection:
  - `git status --short --untracked-files=all` was inspected directly.
  - Story 52 code/test files are untracked additions and the story/index docs
    are modified.
  - Two unrelated untracked input artifacts were present under `inputs/`;
    `file -- ...` identified them as a zip archive and a 9-page PDF. They are
    outside this review scope and are not approved for commit by this review.
- Public or operational surfaces affected:
  - No live Service API v2 route is registered.
  - No OpenAPI route publication is introduced.
  - No sidecar Compose service, Docker image, host port, or direct backend call
    is introduced.
  - New code is a domain-only benchmark evidence and profile-selection
    contract used before route registration.
- Compatibility posture:
  - The audio transcription route remains draft/runtime-disabled.
  - The local selected-profile path is acceptable only as typed contract proof
    for complete evidence, not as production readiness.
  - The completed story records production `stt_profile` and
    `diarization_profile` as rejected because Hemma lacks the sidecar image,
    FFmpeg/ffprobe boundary, STT/diarization packages, gated model-access
    readiness, governed fixtures, speaker-hint execution, and 120-minute
    harness.

## Review Evidence

- Existing retained reviews were searched with
  `rg -n "story-52|Story 52|audio transcription profile|benchmark profile" docs/backlog/reviews`;
  no prior Story 52 review artifact existed.
- The actual working-tree diff and untracked files were inspected directly.
- Runtime route exposure was checked with
  `rg -n "source\\.format.*audio|transcript_bundle|audio_transcription_options" scripts/sir_convert_a_lot`;
  the only runtime-code hit is the Story 51 domain policy docstring stating the
  route remains unregistered.
- Focused Story 52 tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  -> `7 passed`.
- Focused lint passed:
  `pdm run ruff check scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`.
- Focused mypy passed:
  `pdm run mypy scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`.
- Forbidden typing shortcut search found no `Any`, `cast`, `type: ignore`, or
  lint bypasses in the reviewed code/tests.
- Docs validation passed after this retained review was created:
  `pdm run docs-sync`;
  `pdm run docs-validate` -> `Validated 447 backlog files`,
  `Validated docs=522 rules=11`;
  `pdm run skills-validate` -> `skills-validate: ok`;
  `pdm run handoff-validate` -> `handoff-validate: ok`;
  `git diff --check`.

## Test Truthfulness Audit

- The red-first evidence is credible for this slice: the focused test file
  initially failed during collection with `ModuleNotFoundError` for the missing
  `audio_transcription_benchmark_profiles` module, then the same focused Story
  52 tests passed after the implementation.
- Local tests prove the intended domain behavior:
  - bounded profile labels are selected only when all evidence gates are
    complete;
  - silent CPU fallback rejects the profile decision;
  - missing model-access failure evidence rejects the decision;
  - unexercised speaker-range hints reject the decision;
  - incomplete 120-minute proof shape rejects the decision;
  - public benchmark reports omit transcript samples, raw model identifiers,
    secret values, and private cache paths.
- The tests do not claim to execute live STT, live diarization, FFmpeg/ffprobe,
  Hugging Face downloads, or a Hemma sidecar. That is the right boundary for a
  governed rejection story.

## Content-Safety Audit

- The committed Story 52 docs record bounded command outcomes only. They do
  not include transcript text, secret values, raw private model identifiers,
  private cache paths, generated audio artifacts, generated model artifacts, or
  fixture media.
- The tests use synthetic sentinel strings to prove report redaction. Those
  sentinel values are asserted absent from the public report projection and do
  not represent live Hemma secrets, live model identifiers, or real transcript
  evidence.
- The unrelated untracked `inputs/` zip/PDF artifacts remain outside this
  review scope and must not be swept into a Story 52 commit by accident.

## Findings

- [x] No blocking findings.

## Decision

approved

Story 52 is accepted in full as a governed rejection outcome. The implementation
does not make Sir Convert production-ready for audio transcription and does not
authorize Story 53 route registration. It correctly records that production
`stt_profile` and `diarization_profile` are rejected until a later governed STT
sidecar benchmark image/runner proves FFmpeg/ffprobe, backend dependencies,
token/cache readiness, Swedish/English fixtures, diarization speaker hints, and
120-minute lifecycle behavior on Hemma.

## Response

Implementation agents for Story 52 can be closed after the overseer records
this accepted review. The next production-enabling slice must be governed by a
separate Story 53 task or predecessor benchmark-runner task and must not reuse
the local Story 52 selector as proof of live route readiness.

## Follow-up Actions

1. No new non-blocking follow-up is required by this review.

## Completion

Review artifact created and decision recorded on 2026-06-09. Docs validation
was run after this retained review was created.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
