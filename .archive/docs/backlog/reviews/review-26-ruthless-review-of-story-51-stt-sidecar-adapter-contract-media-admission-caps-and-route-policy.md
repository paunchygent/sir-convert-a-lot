---
id: review-26-ruthless-review-of-story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy
title: Ruthless review of Story 51 STT sidecar adapter contract media admission caps and route policy
type: review
status: completed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
labels:
  - review
  - approved
  - story-51
  - stt
  - audio
  - sidecar
  - admission-control
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless implementation review of Story 51.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/030-conversion-workflows.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/_meta/docs-contract.yaml`
  - `docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md`
  - `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
- Files reviewed:
  - `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_policy.py`
  - `tests/sir_convert_a_lot/audio_transcription_test_support.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_route_policy.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`
  - `docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `.codex/handoff.md`
- Public or operational surfaces affected:
  - Future Service API v2 `audio -> transcript_bundle` route contract.
  - Internal Story 51 domain policy for audio route admission.
  - Internal STT sidecar health/capability readiness parser.
  - Deterministic public error-code authority for later HTTP mapping.
- Compatibility posture:
  - This story does not register a runtime route, publish OpenAPI fields, add a
    public browser route, or introduce a live Compose STT service.
  - The planned route remains draft/runtime-disabled until later governed
    implementation stories land.
  - Clean contract tightening is appropriate before any consumer or runtime
    compatibility burden exists.
- Review evidence:
  - Existing retained reviews were searched before creating this artifact; no
    Story 51 retained review existed.
  - Working-tree diff and untracked Story 51 files were inspected directly.
  - Focused tests passed:
    `pdm run pytest-root tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py`
    -> `24 passed`.
  - Focused lint passed:
    `pdm run ruff check scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py scripts/sir_convert_a_lot/domain/audio_transcription_policy.py tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py`.
  - Focused mypy passed:
    `pdm run mypy --no-incremental --config-file pyproject.toml scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py scripts/sir_convert_a_lot/domain/audio_transcription_policy.py tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py`.
  - Docs sync and validation passed after this retained review was created:
    `pdm run docs-sync`;
    `pdm run docs-validate` -> `Validated 446 backlog files`,
    `Validated docs=521 rules=11`;
    `pdm run skills-validate` -> `skills-validate: ok`;
    `pdm run handoff-validate` -> `handoff-validate: ok`;
    `git diff --check`.
  - Runtime exposure search found no live STT Compose service or registered
    runtime `audio -> transcript_bundle` route outside Story 51 docs/tests/domain
    policy.

### Re-Review Pass 2 Evidence

- Date: 2026-06-09.
- Scope: remediation for the three Review 26 findings.
- Files reviewed after remediation:
  - `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_policy.py`
  - `tests/sir_convert_a_lot/audio_transcription_test_support.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_route_policy.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`
  - `docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md`
- Focused tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`
  -> `35 passed`.
- Focused lint passed:
  `pdm run ruff check scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py scripts/sir_convert_a_lot/domain/audio_transcription_policy.py tests/sir_convert_a_lot/audio_transcription_test_support.py tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`.
- Focused mypy passed:
  `pdm run mypy --no-incremental --config-file pyproject.toml scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py scripts/sir_convert_a_lot/domain/audio_transcription_policy.py tests/sir_convert_a_lot/audio_transcription_test_support.py tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`.
- Forbidden typing shortcut search found no `Any`, `cast`, `type: ignore`, or
  lint bypasses in the reviewed code/tests.
- Runtime exposure search still found no live STT Compose service or registered
  runtime `audio -> transcript_bundle` route outside Story 51 docs/tests/domain
  policy.
- Retained review validation after approval passed:
  `pdm run docs-sync`;
  `pdm run docs-validate` -> `Validated 446 backlog files`,
  `Validated docs=521 rules=11`;
  `pdm run skills-validate` -> `skills-validate: ok`;
  `pdm run handoff-validate` -> `handoff-validate: ok`;
  `git diff --check`.

## Findings

1. [x] `high` - Sidecar readiness accepts a capability payload that omits the
   required normalized-audio contract.

   Evidence:

   - The converter contract requires the sidecar capability payload to include
     `media.normalized_audio` with `container = "wav"`,
     `sample_rate_hz = 16000`, `channels = 1`, and `sample_format = "s16"` at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:246`.
   - The readiness parser's media capability check validates upload size,
     duration, accepted containers, and input protocols, then returns success
     without inspecting `normalized_audio` at
     `scripts/sir_convert_a_lot/domain/audio_transcription_policy.py:245`.
   - The positive test fixture does not include `normalized_audio`, so
     `test_sidecar_readiness_accepts_internal_gpu_ready_provider_neutral_profile`
     currently proves the parser accepts an incomplete capability payload at
     `tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py:231`.

   Why it matters:
   Story 51 is supposed to lock the internal STT sidecar capability contract
   before runtime registration. If the main service marks a sidecar ready
   without normalized-audio truth, a later sidecar can drift into stereo,
   non-16 kHz, non-PCM, or undocumented normalized outputs while still passing
   admission. That undermines the FFmpeg/normalization boundary and turns a
   required contract field into optional documentation.

   Required fix:
   Extend the domain readiness parser to require `media.normalized_audio` and
   fail closed unless it reports the governed initial format: container `wav`,
   `sample_rate_hz` `16000`, `channels` `1`, and `sample_format` `s16`. Keep the
   failure deterministic under the Story 51 sidecar-unavailable/model-readiness
   error policy; do not introduce backend-native knobs or fallback acceptance.

   Proof requirement:
   Add red-first behavioral tests that fail with the current implementation for
   missing `normalized_audio`, wrong sample rate, wrong channel count, and wrong
   sample format, then make them green. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py`,
   focused ruff, focused mypy, and the docs gates after updating evidence.

   Re-review pass 2 disposition:
   Resolved. `scripts/sir_convert_a_lot/domain/audio_transcription_policy.py`
   now requires `media.normalized_audio` and fails closed unless it reports
   mono 16 kHz `s16` WAV. The positive readiness fixture now includes the
   normalized-audio contract, and
   `tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`
   covers missing normalized audio, wrong container, wrong sample rate, wrong
   channel count, and wrong sample format.

1. [x] `high` - Public `max_duration_seconds` is not enforced as a request
   guardrail against probed media.

   Evidence:

   - The request contract exposes `audio_transcription_options.max_duration_seconds`
     at `docs/converters/audio-transcription-service-api-artifact-contract.md:104`,
     and public options are allowed to express duration guardrails at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:367`.
   - `AudioTranscriptionPublicOptions.validation_failure` rejects only values
     above the route maximum and accepts `0` or negative values at
     `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py:283`.
   - `evaluate_audio_transcription_route_policy` compares probed media duration
     only to the global route limit, not the caller's requested
     `max_duration_seconds`, at
     `scripts/sir_convert_a_lot/domain/audio_transcription_policy.py:111`.

   Why it matters:
   A caller can ask for a short duration guardrail, or accidentally send an
   invalid non-positive guardrail, and the domain policy will still accept any
   media up to the global 120-minute cap. That is a fail-open admission policy:
   the public request shape claims a bounded duration control, but the route
   policy ignores it when deciding whether to spend probe/normalization/sidecar
   capacity.

   Required fix:
   Validate `max_duration_seconds` as a positive integer no greater than the
   route maximum. After probing, reject media whose `probe.duration_seconds`
   exceeds `request.public_options.max_duration_seconds` with
   `audio_duration_exceeded` and stable details that identify the effective
   limit without leaking source content.

   Proof requirement:
   Add red-first behavioral tests that fail with the current implementation for
   `max_duration_seconds = 0`, `max_duration_seconds < 0`, and a probed duration
   greater than the caller-supplied max but below the global route cap. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py`,
   focused ruff, focused mypy, and docs gates.

   Re-review pass 2 disposition:
   Resolved. `AudioTranscriptionPublicOptions.validation_failure` now rejects
   non-positive duration guardrails, and
   `evaluate_audio_transcription_route_policy` rejects probed media duration
   above the caller's public duration limit. The route policy tests cover
   `0`, negative values, and media over the public guardrail but below the
   route maximum.

1. [x] `medium` - Admission tests do not prove every concrete Story 51 cap
   fails closed.

   Evidence:

   - The contract names four concrete admission caps and reject-only queue
     behavior at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:177`.
   - The implementation has separate branches for active STT jobs, active
     probe/normalization workers, active sidecar transcription requests, and GPU
     slots at `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py:178`.
   - The test suite asserts the cap constants at
     `tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py:43`,
     but route-admission rejection is exercised only for `active_stt_jobs = 2`
     at `tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py:96`.

   Why it matters:
   A regression that stops rejecting exhausted probe workers, sidecar requests,
   or GPU slots would still pass the current tests. Story 51's central purpose
   is route-level admission, so the tests need to prove the actual rejection
   behavior for each cap rather than only the presence of constant values.

   Required fix:
   Parameterize the admission-cap rejection test across all four exhausted
   capacity snapshots. Assert `audio_route_capacity_exceeded` and the stable
   exhausted-cap detail for each branch. Keep the route-unregistered test
   unchanged.

   Proof requirement:
   Add the cap cases red-first or tighten the existing test so it fails if any
   cap branch is removed. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_story51_audio_transcription_policy.py`.

   Re-review pass 2 disposition:
   Resolved. `test_route_policy_rejects_each_exhausted_audio_capacity_cap`
   covers active STT jobs, active probe/normalization workers, active sidecar
   transcription requests, and GPU slot exhaustion, and asserts the stable
   `exhausted_cap` detail for each branch.

## Decision

approved

## Response

Re-review pass 2 accepts the remediation in full. Story 51 is accepted as the
task-ready sidecar/admission policy slice, with no runtime audio route
registered.

## Follow-up Actions

1. No blocking follow-up remains for Story 51.
1. Later runtime stories must still prove the implementation-gate items in the
   audio converter contract before registering the live route.

## Completion

Review completed and approved. Story 51 is accepted in full, and the
implementation agent can be closed.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
