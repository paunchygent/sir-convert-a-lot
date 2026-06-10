---
id: review-42-ruthless-review-of-task-356-audio-transcript-runtime-json-persistence
title: Ruthless review of Task 356 audio transcript runtime JSON persistence
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md
  - docs/backlog/reviews/review-40-ruthless-review-of-stt-sidecar-hiprtc-live-proof.md
  - docs/backlog/reviews/review-41-ruthless-review-of-task-355-audio-transcript-route-admission.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
labels:
  - review
  - approved
  - task-356
  - stt
  - audio
  - transcript-json
  - diarization
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: fixed ruthless post-deploy implementation review for Task 356.
- Governing authority:
  - `AGENTS.md`
  - `.codex/rules/030-conversion-workflows.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json.md`
  - `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
  - `docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md`
  - `docs/backlog/reviews/review-40-ruthless-review-of-stt-sidecar-hiprtc-live-proof.md`
  - `docs/backlog/reviews/review-41-ruthless-review-of-task-355-audio-transcript-route-admission.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/downstream_integration_contract_v2.md`
  - `docs/converters/internal_adapter_contract_v2.md`
- Commits reviewed:
  - `a8ab0d1211fa4a0fb8e0d1efe5fd6a40d982e4ac` - Execute audio transcript bundle jobs.
  - `9edbddafbc58c8d5bf6171546bfdd417e8b19c5e` - Record live audio transcript proof.
- Re-review pass 2 commits reviewed:
  - `d036271155d0dde005e12a9a228ca0f6a13dd848` - Fix audio transcript runtime failure handling.
  - `c8e6621` - Record audio transcript remediation proof.
- Public or operational surfaces affected:
  - Service API v2 `audio -> transcript_bundle` runtime dispatch.
  - Internal STT sidecar HTTP contract: `/health`, `/capabilities`, `/transcribe`, `/cancel`.
  - Service API v2 status/result/artifact/named-artifact/cancel behavior.
  - Audio route progress fields and job-store manifest persistence.
  - Hemma compose/runtime sidecar wiring.
- Compatibility posture:
  - Additive v2 runtime execution for an already accepted route.
  - No legacy route or anonymous lane is introduced.
  - The public route must remain provider-neutral, GPU-required, diarization
    fail-closed, and formatter artifacts must remain explicitly unavailable.

## Evidence Reviewed

- Code inspection covered the implementation/proof commit range and the governed
  authority listed above.
- Live deployment evidence reviewed from Task 356:
  - `pdm run hemma-deploy-and-verify --expected-revision a8ab0d1211fa4a0fb8e0d1efe5fd6a40d982e4ac --lane host`
    passed with expected, remote, and service revisions all equal to
    `a8ab0d1211fa4a0fb8e0d1efe5fd6a40d982e4ac`.
  - Deployed sidecar proof returned healthy/ready with
    `adapter_contract_version=stt-sidecar-v1`,
    `backend_profile_id=stt_sv_en_primary`, `gpu_required=true`,
    `acceleration_family=rocm`, `acceleration_ready=true`,
    `backend_family=faster_whisper`, required diarization, and `HF_TOKEN`
    present by name only.
  - English two-speaker tunnel proof against `http://127.0.0.1:28085`
    succeeded for `jobv2_26d3dbc95c9342ec931e45c116`, detected language `en`,
    diarization `succeeded`, 231 segments, speaker labels `SPEAKER_00` and
    `SPEAKER_01`, transcript SHA-256
    `f9ca1b3121345ebc40fa067b3f44ce80e5baac310161726b6fb685185218aa0d`.
  - Swedish speaker-range tunnel proof succeeded for
    `jobv2_21eeb0d974404d9f82f81e9cc7`, detected language `sv`,
    diarization `succeeded`, 4 segments, speaker label `SPEAKER_00`,
    transcript SHA-256
    `c3fc7e70c40a50aacf6fb40092b286bb2eb5114e111459953b8cc486a6aa02a3`.
  - Ignored proof artifacts are referenced under
    `build/verification/audio-transcript-live-api-proof/a8ab0d1/` and are not
    committed.
- Focused validation during this review passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py -q`
  passed with `6 passed`.
- Docs/proof inspection found no committed transcript text, token values, raw
  model ids in transcript proof, or private cache paths in retained proof docs.
  Contract examples name required secret names and example cache labels only.
- Re-review pass 2 focused validation passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py -q`
  with `17 passed`.
- Re-review pass 2 deployed proof reviewed from Task 356:
  - `pdm run hemma-deploy-and-verify --expected-revision d036271155d0dde005e12a9a228ca0f6a13dd848 --lane host`
    passed with expected, remote, and service revisions all equal to
    `d036271155d0dde005e12a9a228ca0f6a13dd848`.
  - Fresh live tunnel proof against `http://127.0.0.1:28085` succeeded for
    English two-speaker job `jobv2_796bead89df64c679afb373ebf`: detected
    language `en`, diarization `succeeded`, 231 segments, speaker labels
    `SPEAKER_00` and `SPEAKER_01`, transcript SHA-256
    `9b5c8c8e0a3c27c6a94d066b73214379eafaca0ed03b7b044fc63143767815dd`.
  - Fresh live tunnel proof succeeded for Swedish speaker-range job
    `jobv2_646a9ce564b4498989c2040ebe`: detected language `sv`,
    diarization `succeeded`, 4 segments, speaker label `SPEAKER_00`,
    transcript SHA-256
    `5962a1ce927a5cf106539638fba8180c62f12ff2b5ef060a1ccc34a63b216450`.
  - Ignored proof root:
    `build/verification/audio-transcript-live-api-proof/d036271/`.

## Findings

1. [x] `high` - Real sidecar HTTP failures collapse into
   `audio_sidecar_unavailable`, so governed codec, diarization, model, and
   alignment errors do not survive the main-service boundary.

   Evidence:

   - The sidecar HTTP factory returns structured client-safe error payloads
     with the backend code, for example `{"code": exc.code}` at
     `scripts/sir_convert_a_lot/stt_sidecar/app_factory.py:49`.
   - `HttpAudioTranscriptionSidecarClient._post_json` calls
     `response.raise_for_status()` and maps every HTTP status error to
     `_sidecar_unavailable("sidecar_http_status", ...)` at
     `scripts/sir_convert_a_lot/infrastructure/audio_transcription_sidecar_client.py:106`.
   - `_sidecar_unavailable` always raises Service API error
     `audio_sidecar_unavailable` at
     `scripts/sir_convert_a_lot/infrastructure/audio_transcription_sidecar_client.py:148`.
   - The current tests prove the sidecar endpoint can emit
     `unsupported_audio_codec`, but they do not pass that response through the
     real `HttpAudioTranscriptionSidecarClient` into a v2 job failure; the main
     runtime tests use an in-memory fake sidecar that bypasses HTTP error
     translation.

   Why it matters:
   Task 356 and the audio contract require deterministic v2 audio errors for
   media probe/normalization, transcription, diarization, GPU/cache/model
   access, alignment, and cancellation failures. With the deployed HTTP client,
   a real `audio_diarization_failed`, `unsupported_audio_codec`,
   `audio_model_access_denied`, `audio_normalization_failed`, or
   `audio_sidecar_canceled` response is reported to clients and operators as
   `audio_sidecar_unavailable`. That hides fail-closed cause, breaks retry
   semantics, and makes downstream/Gateway handling unreliable.

   Required fix:
   Parse structured non-2xx sidecar JSON at the HTTP adapter boundary and map
   recognized `AudioTranscriptionErrorCode` values into `ServiceError` with the
   governed code, appropriate status/retryability, and bounded details. Keep
   transport failures, non-JSON responses, and unrecognized sidecar payloads as
   `audio_sidecar_unavailable`; do not expose backend messages that contain
   private paths, model ids, transcript text, or secrets.

   Proof requirement:
   Add red-first tests that run the real HTTP client against a sidecar test app
   whose `/transcribe` returns at least `unsupported_audio_codec`,
   `audio_diarization_failed`, `audio_model_access_denied`, and
   `audio_sidecar_canceled`, then assert the stored v2 job error preserves the
   governed code and retryability. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py -q`.

   Re-review pass 2 disposition:
   Resolved. `HttpAudioTranscriptionSidecarClient` now parses recognized
   structured non-2xx sidecar responses through `_recognized_sidecar_error`
   before falling back to transport-level `audio_sidecar_unavailable`. The
   mapped `ServiceError` preserves the governed audio code, uses sanitized
   messages/details only, and keeps unknown/non-JSON payloads fail-closed as
   sidecar unavailable. The real HTTP adapter path is covered by
   `test_real_http_sidecar_error_codes_are_preserved_in_stored_job_failure`,
   including `unsupported_audio_codec`, `audio_diarization_failed`,
   `audio_model_access_denied`, and `audio_sidecar_canceled`, with assertions
   that private paths, raw model ids, token-like values, and transcript text do
   not leak into stored failure details.

1. [x] `high` - Runtime media duration and codec timeout enforcement does not
   match the accepted audio ingestion contract.

   Evidence:

   - The sidecar request carries `options.max_duration_seconds` from the public
     job at `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:189`.
   - The production sidecar probes duration at
     `scripts/sir_convert_a_lot/stt_sidecar/runtime.py:228`, but no code
     compares that probed duration with `options.max_duration_seconds` or the
     route maximum before transcription and diarization continue at
     `scripts/sir_convert_a_lot/stt_sidecar/runtime.py:229`.
   - The media helper uses one fixed `120.0` second subprocess timeout for both
     FFmpeg normalization and ffprobe duration probing at
     `scripts/sir_convert_a_lot/stt_sidecar/media.py:74`.
   - A timeout raises the same code that the caller passed for the operation at
     `scripts/sir_convert_a_lot/stt_sidecar/media.py:83`, so probe timeout maps
     to `audio_probe_failed` and normalization timeout maps to
     `audio_normalization_failed` rather than the governed
     `audio_probe_timeout` and `audio_normalization_timeout` codes.

   Why it matters:
   ADR-0013 and the route contract require uploaded media over 7200 seconds to
   fail deterministically with `audio_duration_exceeded`, probe timeout to be
   30 seconds, and normalization timeout to be duration-derived and capped at
   1800 seconds. The current runtime can run over-limit media through the GPU
   transcription path and misclassifies timeout failures. That is an
   operational safety issue for 120-minute recordings and a client-visible
   contract drift from the required error policy.

   Required fix:
   Enforce probed duration immediately after codec probing and before
   transcription. Split probe and normalization timeout codes so timeout paths
   return `audio_probe_timeout` or `audio_normalization_timeout`, while
   non-timeout subprocess failures keep `audio_probe_failed` or
   `audio_normalization_failed`. Use the contract timeout values: 30 seconds
   for probe and `max(300, 2 * media_duration_seconds + 120)` capped at 1800
   seconds for normalization.

   Proof requirement:
   Add red-first sidecar/runtime tests that simulate a duration above
   `max_duration_seconds` and assert the v2 job fails with
   `audio_duration_exceeded` without invoking transcription or diarization.
   Add media-helper tests for probe timeout and normalization timeout code
   mapping without sleeping. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py -q`.

   Re-review pass 2 disposition:
   Resolved. The sidecar now probes duration from the source upload before
   normalization or model work, enforces the smaller of the request duration
   limit and the route maximum, and raises `audio_duration_exceeded` before
   transcription/diarization. Media helpers now use a 30-second probe timeout,
   duration-derived normalization timeout capped at 1800 seconds, and separate
   timeout error codes for probe and normalization. The behavioral proof is in
   `test_sidecar_runtime_rejects_over_limit_duration_before_model_work`,
   `test_duration_probe_timeout_maps_to_probe_timeout`, and
   `test_normalization_timeout_uses_duration_based_contract`.

1. [x] `high` - Cancellation is only observed before and after the blocking
   `/transcribe` call, so in-flight sidecar work is not canceled promptly.

   Evidence:

   - The main runtime checks cancellation before calling `sidecar.transcribe`
     and after it returns at
     `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:122`.
   - The actual sidecar call is synchronous and may block for the configured
     read timeout at
     `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:125`.
   - The default sidecar read timeout is 7200 seconds at
     `scripts/sir_convert_a_lot/infrastructure/runtime_models.py:70` and is
     loaded from `SIR_CONVERT_A_LOT_STT_SIDECAR_TIMEOUT_SECONDS` at
     `scripts/sir_convert_a_lot/infrastructure/runtime_config.py:424`.
   - The HTTP cancel endpoint marks the v2 job canceled at
     `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py:417`, but
     it does not call `audio_transcription_sidecar.cancel(job_id)`. The only
     sidecar cancel call is inside `_raise_if_canceled`, which is not reached
     while the blocking `/transcribe` request is still running.
   - The current cancellation test covers only a pre-transcribe cancellation
     where `is_cancel_requested` is already true at
     `tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py:226`;
     it does not prove mid-flight cancellation of active sidecar work.

   Why it matters:
   Task 356 requires clean cancellation: no stale sidecar scheduling after
   cancellation, cancellation propagation to sidecar/chunk work, and purging of
   incomplete normalized audio/chunks/partial transcript state. In the current
   deployed shape, a user can receive `202 canceled` while FasterWhisper and
   pyannote continue consuming the GPU until `/transcribe` completes or times
   out. That violates the GPU-required operational invariant and can starve the
   route's single GPU/sidecar slot.

   Required fix:
   Make v2 cancel propagate to the active STT sidecar request when the job is
   `audio -> transcript_bundle`, or restructure sidecar execution so the main
   service can interrupt active work promptly. The sidecar should stop further
   codec/model work and return `audio_sidecar_canceled`; the main service must
   keep the job canceled and must not persist a terminal transcript artifact.

   Proof requirement:
   Add a red-first public lifecycle test with a blocking fake sidecar that
   starts `/transcribe`, then calls `POST /v2/convert/jobs/{job_id}/cancel`.
   Assert the sidecar receives cancel before the transcribe call is released,
   the job remains `canceled`, `/result` and named artifact endpoints return
   `409 job_not_succeeded`, and no transcript artifact file remains. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py -q`.

   Re-review pass 2 disposition:
   Resolved. `ServiceRuntimeV2.cancel_job` now calls
   `audio_transcription_sidecar.cancel(job_id)` for running or queued
   `audio -> transcript_bundle` jobs after the v2 job is marked canceled.
   `test_canceling_running_audio_job_propagates_to_sidecar_and_keeps_no_artifact`
   proves an in-flight sidecar receives cancel before the blocking transcribe
   call is released, the job remains `canceled`, `/result` and
   `/artifacts/transcript_json` return `409 job_not_succeeded`, and no
   transcript artifact file is exposed.

## Decision

approved

## Response

ACCEPTED for Task 356.

Re-review pass 2 confirms the deployed remediation revision
`d036271155d0dde005e12a9a228ca0f6a13dd848` resolves all three original Review
42 findings. Structured sidecar HTTP error codes now survive the real adapter
boundary without unsafe payload leakage, duration and timeout enforcement match
the ADR-0013 route contract before model work, and v2 cancellation propagates
to active audio sidecar requests while terminal canceled jobs expose no
transcript artifact.

## Follow-up Actions

- No blocking follow-up actions remain for Task 356.
- Formatter artifacts, downstream durable transcript save semantics, and
  UI/storage work remain separate governed downstream tasks.

## Validation

- Review-time focused tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py -q`
  with `6 passed`.
- Re-review pass 2 focused tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py -q`
  with `17 passed`.
- Required docs validation for the re-review artifact is recorded after this
  file is updated: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and `git diff --check`.

## Completion

Initial review completed on 2026-06-10 with `changes_requested`. Re-review is
pass 2 completed on 2026-06-10 after remediation, focused red/green proof,
Hemma deploy verification, and live tunnel proof for
`d036271155d0dde005e12a9a228ca0f6a13dd848`; final decision is `approved`.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
