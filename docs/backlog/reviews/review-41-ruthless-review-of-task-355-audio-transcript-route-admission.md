---
id: review-41-ruthless-review-of-task-355-audio-transcript-route-admission
title: Ruthless review of Task 355 audio transcript route admission
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - review
  - approved
  - task-355
  - stt
  - audio
  - route-admission
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: fixed ruthless post-deploy implementation review for Task 355.
- Governing authority:
  - `AGENTS.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md`
  - `docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md`
  - `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
- Commits reviewed:
  - `216ae2fe85d0cf029593b3a96018906ade1131fd`
  - `f7af68535a73b4cdecdd3ea0fdbd75f87fc0b046`
  - `de5ec5be0b9008dec57f808511b57e8ec5e79795`
- Re-review pass 2 commit reviewed:
  - `9859b4a51dc94e9a6083a9fd7985b746cd75c380`
- Deployed proof reviewed:
  - `pdm run hemma-deploy-and-verify --expected-revision de5ec5be0b9008dec57f808511b57e8ec5e79795 --lane host`
    passed with expected, remote, and service revision all equal to
    `de5ec5be0b9008dec57f808511b57e8ec5e79795`.
  - Live tunnel smoke admitted `audio -> transcript_bundle` with
    `create_status=202`, job `jobv2_2071141bbff84285a94ec138c1`,
    `status=queued`, and cancel returned `cancel_status=202` with
    `status=canceled`.
  - Earlier deployed smoke against `f7af68535a73b4cdecdd3ea0fdbd75f87fc0b046`
    exposed `status=running`; the supervisor fix in
    `de5ec5be0b9008dec57f808511b57e8ec5e79795` added shared route-policy
    dispatch blocking for admission-only audio jobs.
  - Re-review pass 2 deployment ran
    `pdm run hemma-deploy-and-verify --expected-revision 9859b4a51dc94e9a6083a9fd7985b746cd75c380 --lane host`
    and passed. The report at `build/verification/hemma-deploy-verify/report.md`
    recorded expected, remote, and service revision all equal to
    `9859b4a51dc94e9a6083a9fd7985b746cd75c380`, lane `host`, service URL
    `http://127.0.0.1:28085`, env-backed API key, and passing structured LLM,
    metrics, and public-edge checks.
  - Re-review pass 2 live tunnel smoke against
    `http://127.0.0.1:28085/v2/convert/jobs` admitted
    `audio -> transcript_bundle` with `create_status=202`, job
    `jobv2_7d6c801106cb458199364f78c5`, `status=queued`,
    `source_format=audio`, and `output_format=transcript_bundle`; cancel
    returned `cancel_status=202` and the same job `status=canceled`.
- Files reviewed in the commit range:
  - `.codex/handoff.md`
  - `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
  - `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
  - `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
  - `docs/backlog/stories/story-55-gateway-and-downstream-transcript-delivery-coordination.md`
  - `docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/converters/downstream_integration_contract_v2.md`
  - `docs/converters/internal_adapter_contract_v2.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_contracts.py`
  - `scripts/sir_convert_a_lot/domain/audio_transcription_policy.py`
  - `scripts/sir_convert_a_lot/domain/service_routes_v2.py`
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_supervision_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_auth_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_route_policy.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py`
  - `tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
  - `tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py`
  - `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
  - `tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  - `tests/sir_convert_a_lot/test_runtime_supervision_v2.py`
  - `tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py`
- Public or operational surfaces affected:
  - Service API v2 `POST /v2/convert/jobs` admission for
    `audio -> transcript_bundle`.
  - Service API v2 OpenAPI source/output enums and `JobSpecV2` schema.
  - Gateway/user-originated `InternalIdentityContextV1` create-job ownership
    behavior for the audio route.
  - Local/operator API-key tunnel admission for the audio route.
  - Runtime supervisor dispatch eligibility for queued v2 jobs.
- Compatibility posture:
  - Additive v2 route registration.
  - No legacy route, alias, shim, fallback, or wrapper is introduced.
  - The route is intentionally admission-only and must not imply sidecar
    execution or `transcript_json` availability before later Story 53 tasks.

## Evidence Reviewed

- Code inspection confirmed the audio route policy requires
  `audio_transcription_options`, `execution.acceleration_policy=gpu_required`,
  `retention.pin=false`, and sets `dispatches_runtime_jobs=False`.
- Code inspection confirmed `http_routes_jobs_v2` uses optional signed identity
  only when HuleEdu identity headers are present, otherwise preserving the
  local/operator API-key owner scope.
- Code inspection confirmed `RuntimeSupervisorV2` skips queued jobs whose route
  policy does not dispatch runtime work.
- Code inspection found no `Any`, `typing.cast`, `# type: ignore`, lint-ignore
  bypass, compatibility shim, alias, or wrapper in the reviewed code paths.
- Test-file naming is purpose-based. The stale
  `test_audio_transcription_route_registration_gating.py` file was removed;
  no active test/helper file is named for Task 355.
- Generated live-smoke artifacts under `build/verification/` are not tracked.
- Focused review validation passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  passed with `38 passed`.
- `git diff --check` passed before this review artifact was written.
- Re-review pass 2 code inspection confirmed the audio contract example no
  longer contains `conversion.artifact_language`, and `JobSpecV2` accepts the
  documented initial request shape.
- Re-review pass 2 code inspection confirmed `RoutePolicyV2` now carries
  `uses_route_specific_primary_upload_limit` and `required_execution_message`;
  the audio route enables both while document routes keep the generic upload
  gate and existing PDF execution diagnostic.
- Re-review pass 2 code inspection confirmed `http_routes_jobs_v2` resolves the
  validated route before reading the primary upload and applies
  `runtime.config.max_upload_bytes` only when the route does not use a
  route-specific primary-upload limit. Audio uploads therefore reach the audio
  admission handler, which enforces `MAX_AUDIO_UPLOAD_BYTES` and emits
  `audio_upload_size_exceeded`.
- Re-review pass 2 shortcut search found no `Any`, `typing.cast`,
  `# type: ignore`, `noqa`, shim, alias, wrapper, story-named, or task-named
  active code/test additions in the reviewed fix paths.
- Re-review pass 2 generated live-smoke artifacts under
  `build/verification/task-355-live-audio-route-smoke-review41/` are ignored
  and untracked.
- Red-first evidence reviewed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  failed with `4 failed, 39 passed` before the fixes. The failures matched the
  three retained findings: the published contract example was rejected, an
  audio upload above the generic cap was rejected before route admission,
  oversize audio returned generic `payload_too_large`, and the docs guard
  rejected the contract example.
- Green evidence reviewed from implementation:
  - Same command passed with `43 passed`.
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
    passed with `65 passed`.
  - `pdm run pytest-root tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_specs_v2.py`
    passed with `129 passed`.
  - `pdm run format-all`, `pdm run lint-fix`, `pdm run typecheck-all`,
    `pdm run coverage-gate`, `pdm run docs-sync`, `pdm run docs-validate`,
    `pdm run skills-validate`, `pdm run handoff-validate`, and
    `git diff --check` all passed. Coverage gate reported `1637 passed,
    6 skipped`, total coverage `95.40%`.
- Focused validation run during this re-review passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
  passed with `72 passed`.

## Findings

1. [x] `high` - The published audio request shape still includes
   `conversion.artifact_language`, but the implemented route rejects that field.

   Evidence:

   - The audio converter contract's initial request example includes
     `"artifact_language": "auto"` under `conversion` at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:95`.
   - The implemented route policy only enables `artifact_language` for exam
     migration routes. `_validate_exam_migration_options` rejects any
     `conversion.artifact_language` when `policy.allows_artifact_language` is
     false at `scripts/sir_convert_a_lot/domain/service_routes_v2.py:378`.
   - The new positive audio route fixture omits `artifact_language` at
     `tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py:427`,
     so the focused tests do not prove the published contract example is
     admissible.

   Why it matters:
   Gateway/Skriptoteket clients use the converter contract as the product-facing
   request authority. A client that sends the documented example receives a
   `422 validation_error` instead of admitted `202 queued`, which breaks the
   Task 355 claim that OpenAPI/converter docs are synchronized for the newly
   admitted route.

   Required fix:
   Make the public contract and validator agree. Given Task 355 routes language
   through `audio_transcription_options.language`, the smallest clean fix is to
   remove `conversion.artifact_language` from the audio request example and any
   active audio guidance that implies it is accepted. If the product contract
   intentionally wants `conversion.artifact_language` for audio, then add a
   governed route-policy allowance and define how it interacts with
   `audio_transcription_options.language`; do not leave two contradictory
   authorities.

   Proof requirement:
   Add a red-first behavioral test that posts the published audio contract
   request shape through `POST /v2/convert/jobs` and expects the intended
   outcome. If docs remove `artifact_language`, add a docs guard proving the
   audio contract example stays aligned with the admissible request shape. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`,
   then the docs gates.

   Re-review pass 2 disposition:
   Resolved. The audio converter contract initial request example removes
   `conversion.artifact_language` and uses the currently admissible
   `document_timeout_seconds=7200`. The contract example is now parsed and
   admitted through the HTTP create-job boundary by
   `test_audio_contract_initial_request_shape_is_admitted`, and the docs guard
   validates the same example with `JobSpecV2` in
   `test_audio_contract_initial_request_shape_is_admissible`.

1. [x] `high` - The audio route's 500 MiB upload cap is shadowed by the generic
   50 MiB Service API upload gate and returns the wrong public error code.

   Evidence:

   - ADR-0013 requires a route-specific default maximum upload size of
     `500 MiB` at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:166`.
   - The audio converter contract repeats the same limit and public failure
     code `audio_upload_size_exceeded` at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:158`.
   - `ServiceConfig.max_upload_bytes` still defaults to `50 * 1024 * 1024` at
     `scripts/sir_convert_a_lot/infrastructure/runtime_models.py:49`.
   - `service_config_from_env` does not populate `max_upload_bytes` at
     `scripts/sir_convert_a_lot/infrastructure/runtime_config.py:400`, so the
     default remains 50 MiB unless a test constructs `ServiceConfig` manually.
   - `POST /v2/convert/jobs` rejects the primary upload against
     `runtime.config.max_upload_bytes` before route-specific audio preparation
     at `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:155`.
   - The audio-specific `MAX_AUDIO_UPLOAD_BYTES` check and
     `audio_upload_size_exceeded` error are only reached later inside
     `AudioTranscriptionAdmissionCreateJobRouteHandlerV2.prepare` at
     `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py:240`.

   Why it matters:
   Valid audio uploads between 50 MiB and 500 MiB are rejected before the audio
   route policy can run, and clients see the generic `payload_too_large` error
   rather than the governed `audio_upload_size_exceeded` code. That undermines
   120-minute recording admission and means the deployed tiny-file smoke does
   not prove the route admits realistic day-one audio media.

   Required fix:
   Make primary-upload size admission route-aware. The document routes should
   keep the existing generic `payload_too_large` behavior, while
   `audio -> transcript_bundle` must enforce `MAX_AUDIO_UPLOAD_BYTES` and emit
   `audio_upload_size_exceeded`. Do not solve this with a hidden global default
   bump that silently changes document-route limits unless the governing docs
   intentionally authorize that broader contract change.

   Proof requirement:
   Add red-first HTTP tests proving:

   - an audio upload larger than `ServiceConfig.max_upload_bytes` but within
     the audio route cap reaches audio admission instead of generic
     `payload_too_large`;
   - an audio upload over the audio cap fails with
     `413 audio_upload_size_exceeded`;
   - existing document-route oversized uploads still fail with
     `413 payload_too_large`.
     Use a small configured document cap and a bounded/monkeypatched audio cap or
     a route-handler test so the suite does not allocate hundreds of MiB. Run:
     `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`.

   Re-review pass 2 disposition:
   Resolved. `RoutePolicyV2` now marks audio as using a route-specific primary
   upload limit, and `http_routes_jobs_v2` bypasses the generic
   `runtime.config.max_upload_bytes` check only for such routes. The audio
   handler now owns audio size enforcement and returns
   `audio_upload_size_exceeded`. The tests prove both an audio payload above
   the generic cap but below the audio cap is admitted, and an audio payload
   above the audio cap returns the governed audio error while existing document
   route oversized uploads still return generic `payload_too_large`.

1. [x] `medium` - Missing execution on the audio route reports a PDF-specific
   validation message.

   Evidence:

   - The audio route policy sets `requires_execution=True` at
     `scripts/sir_convert_a_lot/domain/service_routes_v2.py:217`.
   - The shared execution-required check raises
     `"execution is required when source.format is 'pdf'"` at
     `scripts/sir_convert_a_lot/domain/service_routes_v2.py:355`, even when the
     route is `audio -> transcript_bundle`.

   Why it matters:
   Task 355 requires deterministic public admission failures for invalid audio
   request shape. A PDF-specific message on an audio request is not a stable
   audio route diagnostic and will mislead Gateway/downstream client debugging.

   Required fix:
   Split the execution-required validation so PDF and audio routes emit
   route-accurate messages or typed audio error details. Keep non-audio route
   behavior unchanged.

   Proof requirement:
   Add a red-first request validation test for an audio create job with missing
   `execution`, asserting the corrected audio-specific diagnostic. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py`.

   Re-review pass 2 disposition:
   Resolved. The audio route policy now carries
   `required_execution_message="execution is required for audio transcription routes"`.
   `test_job_spec_requires_audio_execution_with_route_message` proves the
   corrected diagnostic is present and the PDF-specific text is absent.

## Decision

approved

## Response

ACCEPTED for Task 355.

Re-review pass 2 confirms the deployed revision
`9859b4a51dc94e9a6083a9fd7985b746cd75c380` resolves all three original Review
41 findings. The route remains admission-only, preserves API-key tunnel and
Gateway signed-identity ownership behavior, keeps audio jobs queued rather than
dispatching STT execution, and now aligns the published request contract,
route-specific upload cap, and audio execution diagnostic.

## Follow-up Actions

- No blocking follow-up actions remain for the Task 355 route-admission slice.
- Later Story 53 tasks still own sidecar execution, media probing,
  normalization, progress, cancellation cleanup, retry, short-retention cleanup,
  and canonical `transcript_json` persistence.
- Non-blocking maintainability note: before adding more audio-admission cases,
  split `tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py`
  into narrower purpose-based files. It is currently 550 lines; this did not
  block approval because the added tests truthfully prove the reviewed public
  behavior, but the file should not continue to grow.

## Completion

Initial review completed on 2026-06-10 with `changes_requested`. Re-review pass
2 completed on 2026-06-10 after deployed live proof for
`9859b4a51dc94e9a6083a9fd7985b746cd75c380`; final decision is `approved`.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
