---
id: task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2
title: Register audio transcript bundle route admission in Service API v2
type: task
status: in_progress
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md
  - docs/backlog/reviews/review-40-ruthless-review-of-stt-sidecar-hiprtc-live-proof.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
labels:
  - stt
  - audio
  - v2
  - route-admission
  - transcript-json
  - diarization
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Register the governed `audio -> transcript_bundle` Service API v2 route at the
admission boundary now that Story 51's route policy and Task 352/354's live
Hemma sidecar proof have been accepted. This task lets authenticated,
owner-scoped callers submit valid audio transcript jobs through the canonical
v2 request contract and receive deterministic admission failures for invalid or
temporarily unavailable audio routes.

This task intentionally stops before sidecar execution, progress streaming,
canonical `transcript_json` persistence, formatter generation, Gateway
downstream UI work, or durable Skriptoteket save semantics. Those remain in
later Story 53 and Story 55 tasks after the route admission contract is green.

## PR Scope

- Remove the stale Story 53 blocked-state text and record that Task 352/354 plus
  Review 40 and human transcript review accepted the selected FasterWhisper ROCm
  plus pyannote sidecar profile.
- Extend Service API v2 job-spec validation so `source=audio` and
  `target=transcript_bundle` is a recognized route only for authenticated,
  owner-scoped requests.
- Wire Story 51's audio transcription policy into route admission for:
  - uploaded local media only;
  - accepted public options for Swedish/English auto-detection and optional
    diarization controls;
  - exact speaker count and min/max speaker range validation;
  - route-local concurrency/admission caps;
  - GPU-required create-job policy;
  - rejected `retention.pin=true`.
- Preserve existing idempotency behavior: same owner plus same accepted payload
  can replay, while same idempotency key with a different audio payload or
  options remains a deterministic conflict.
- Preserve owner-scoped status, result, artifact, and cancel access behavior
  through the existing `InternalIdentityContextV1` boundary.
- Return deterministic public error codes for admission-only failures, including
  route disabled, capacity exceeded, invalid options, and unsupported audio
  request shape.
- Keep sidecar invocation, media probing, normalization, transcription,
  diarization alignment, `transcript_json` persistence, route-specific progress
  fields, retention cleanup, and cancellation propagation out of this task
  unless the existing route architecture requires a thin placeholder state to
  preserve API correctness. Sidecar health/capability readiness remains the
  next Story 53 execution-slice gate and is not polled by Task 355.

## Deliverables

- [x] Purpose-named route validation tests for accepted and rejected
  `audio -> transcript_bundle` request shapes.
- [x] Focused idempotency tests for replay and different-payload conflict on
  the audio route.
- [x] Owner-scoped route access tests for Gateway/user-originated
  `InternalIdentityContextV1` requests.
- [x] Admission-cap failure tests using Story 51's accepted route policy.
- [x] Runtime route/spec implementation with no STT dependencies added to the
  main service image.
- [x] OpenAPI/converter docs synchronized for the newly admitted route without
  claiming sidecar execution or transcript persistence is complete.
- [ ] Retained ruthless review artifact that accepts this admission slice or
  records concrete changes requested.

## Acceptance Criteria

- [x] `audio -> transcript_bundle` is recognized by the Service API v2 create
  job boundary when and only when the request satisfies Story 51 admission
  policy and authenticated owner-scoped access.
- [x] Invalid source/target combinations, remote or URL media, unsupported
  diarization options, invalid speaker hints, non-GPU create-job policy,
  exhausted admission caps, and `retention.pin=true` fail with deterministic
  public error codes.
- [x] Accepted admission does not imply transcription success: jobs must remain
  in a clear pending or fail-closed state until a later execution task wires the
  STT sidecar and `transcript_json` artifact persistence.
- [x] Existing PDF, DOCX, Markdown, HTML, and image route behavior is unchanged.
- [x] No raw backend model ids, GPU device knobs, Hugging Face tokens, private
  cache paths, transcript text, uploaded media, or generated verification
  artifacts are persisted in governed docs or committed files.
- [x] Route implementation remains compatible with Gateway `/sir-convert` and
  local tunnel access through the existing Service API v2 boundary.
- [ ] The retained review artifact is accepted before this task is marked
  completed.

## Test Requirements

- [x] Red-first route validation test for an otherwise valid
  `audio -> transcript_bundle` create-job request that failed before this task
  because the route was unregistered.
- [x] Red-first tests for invalid diarization modes, invalid exact speaker
  count, invalid min/max speaker range, remote inputs, retention pin rejection,
  and capacity exhaustion.
- [x] Red-first idempotency replay/conflict test covering audio request options
  in the idempotency payload.
- [x] Red-first owner-scope test proving the audio route cannot bypass
  `InternalIdentityContextV1`.
- [x] Focused regression tests proving existing non-audio routes still validate.
- [x] Validation commands: focused pytest for the changed route tests,
  `pdm run format-all`, `pdm run lint-fix`, `pdm run typecheck-all`,
  applicable focused pytest suites, `pdm run docs-sync`,
  `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.

## Implementation Evidence

- Red-first command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py`
  failed with `32 failed, 44 passed`. Failures showed
  `source.format=audio` and `output_format=transcript_bundle` were not enum
  members, `audio_transcription_options` was forbidden, the route registry did
  not include `audio -> transcript_bundle`, audio/video-with-audio filename
  extensions inferred as unsupported, and HTTP create-job requests returned
  `415` before route admission.
- Admission identity rationale: audio create admission preserves Epic 12
  local/operator tunnel access by admitting API-key-only requests under the
  existing `service-api-key` owner scope. Requests that include any
  `InternalIdentityContextV1` headers are treated as Gateway/user-originated
  calls and must verify the signed identity plus `sir-convert:jobs:create`;
  accepted jobs then use the identity-derived owner scope.
- Implementation keeps Task 355 admission-only by registering an audio create
  handler that validates request shape and companion uploads without calling an
  STT sidecar, probing media, normalizing audio, or persisting
  `transcript_json`. Submitted audio jobs stay queued even when
  `run_jobs_on_submit=true` until a later Story 53 execution task wires the
  sidecar.
- Follow-up red-first command for the API-key/operator and capacity audit:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py`
  failed with `2 failed, 30 passed`. The API-key-only audio operator test
  received `401` instead of `202`, and the third active queued audio job
  received `202` instead of `429 audio_route_capacity_exceeded`.
- Green focused command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
  passed with `83 passed`.
- Follow-up focused admission command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py`
  passed with `32 passed`.
- Quality gates run during implementation: `pdm run format-all` passed,
  `pdm run lint-fix` passed, and `pdm run typecheck-all` passed with
  `Success: no issues found in 837 source files`.
- Parent overseer focused regression command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_transcript_formatter_blocked_state.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_profile_proof.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  passed with `118 passed`.
- Parent quality gates passed: `pdm run format-all`, `pdm run lint-fix`,
  `pdm run typecheck-all`, and `pdm run coverage-gate`. The coverage gate
  passed with `1631 passed, 6 skipped`, `95.41%` total coverage.
- Parent docs gates passed after `pdm run docs-sync`: `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.
- Deployed live smoke against revision
  `f7af68535a73b4cdecdd3ea0fdbd75f87fc0b046` admitted
  `audio -> transcript_bundle` through `http://127.0.0.1:28085` with
  `create_status=202`, then exposed a pre-review admission-only defect: the
  production supervisor immediately claimed the queued audio job and returned
  `status=running`. The smoke job `jobv2_587a64cfbd5d4a7f97ab324ce4` was
  canceled through the same owner scope with `cancel_status=202`.
- Supervisor regression red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_runtime_supervision_v2.py`
  failed with `1 failed, 1 passed` because the supervisor started
  `job_audio_queued` before the executable document job.
- Supervisor fix green command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_runtime_supervision_v2.py`
  passed with `2 passed` after route policy gained a shared
  runtime-dispatch flag and `RuntimeSupervisorV2` skipped admission-only audio
  jobs.
- Post-fix focused command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
  passed with `92 passed`.
- Post-fix quality gates passed: `pdm run lint-fix`, `pdm run typecheck-all`,
  and `git diff --check`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
