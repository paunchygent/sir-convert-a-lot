---
id: task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json
title: Execute audio transcript jobs and persist canonical transcript JSON
type: task
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/stories/story-51-stt-sidecar-adapter-contract-media-admission-caps-and-route-policy.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md
  - docs/backlog/tasks/task-355-register-audio-transcript-bundle-route-admission-in-service-api-v2.md
  - docs/backlog/reviews/review-40-ruthless-review-of-stt-sidecar-hiprtc-live-proof.md
  - docs/backlog/reviews/review-41-ruthless-review-of-task-355-audio-transcript-route-admission.md
  - docs/backlog/reviews/review-42-ruthless-review-of-task-356-audio-transcript-runtime-json-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
labels:
  - stt
  - audio
  - v2
  - sidecar-execution
  - transcript-json
  - diarization
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Execute admitted `audio -> transcript_bundle` Service API v2 jobs through the
accepted FasterWhisper ROCm plus pyannote sidecar profile and persist the first
canonical owner-scoped `transcript_json` artifact.

This task starts after Task 352/354 live Hemma proof and Task 355 route
admission are accepted. It is the first Story 53 runtime-execution slice and
must turn a valid queued audio job into a succeeded job only when codec
probing, normalization, transcription, diarization, segment alignment,
artifact packaging, and retention cleanup all satisfy the accepted
route-specific contract.

Formatter artifacts (`txt`, `md`, `vtt`, `srt`), Skriptoteket durable save
semantics, and HuleEdu/Skriptoteket UI work remain out of scope until the JSON
core is accepted.

## PR Scope

- Wire `audio -> transcript_bundle` jobs into runtime dispatch without adding
  STT, diarization, or broad codec dependencies to the main service image.
- Add a Sir-owned internal sidecar client/adapter boundary for health,
  capability, transcription, deterministic error mapping, and cancellation. The
  main service must not call backend-native FasterWhisper or pyannote APIs.
- Probe uploaded audio/video media through the sidecar codec boundary, enforce
  route duration and codec errors, normalize to the accepted audio contract, and
  keep source/normalized/chunk scratch under job-scoped roots.
- Execute deterministic duration-based audio chunks with retry-safe checkpoint
  metadata sufficient to prevent duplicate segment, diarization window, or
  artifact persistence.
- Map sidecar transcription, diarization, GPU, cache, model-access,
  normalization, alignment, and cancellation failures to the governed v2 audio
  error codes.
- Persist a canonical `transcript_json` artifact only after all chunks complete
  and transcription/diarization alignment validates across chunk boundaries.
- Expose named artifact bundle retrieval for `transcript_json`; keep future
  formatter artifacts explicitly unavailable/not implemented rather than
  silently pretending they exist.
- Project route-specific audio progress fields while keeping PDF page counters
  `null` for audio jobs.
- Preserve owner-scoped job/result/artifact/cancel access for both local
  API-key tunnel calls and Gateway `InternalIdentityContextV1` calls.
- Prove clean idempotent cancellation: no terminal partial transcript artifact,
  no stale sidecar scheduling after cancellation, and incomplete scratch state
  is purged according to the route retention policy.
- Deploy to Hemma and prove the full live pipeline through the tunnel before
  requesting retained review.

## Deliverables

- [x] Purpose-named domain/application/infrastructure modules for transcript
  bundle execution, sidecar client contracts, chunk checkpoints, and artifact
  packaging.
- [x] Red-first behavior tests for successful `transcript_json` persistence and
  named artifact retrieval.
- [x] Red-first tests for sidecar unavailable, GPU unavailable, model/cache
  unavailable, transcription failure, diarization failure, alignment failure,
  media probe/normalization failures, retry-safe checkpoint behavior,
  cancellation cleanup, and owner-scoped access.
- [x] OpenAPI/converter/downstream docs synchronized to show JSON execution is
  live while formatter artifacts remain blocked.
- [x] Hemma deploy and live tunnel proof that an English two-speaker fixture and
  Swedish one-speaker fixture complete through the public v2 job lifecycle with
  `transcript_json` available for human review.
- [x] Retained ruthless review artifact accepted after deployed live proof.

## Acceptance Criteria

- [x] Valid admitted audio jobs are dispatchable by the v2 runtime only when
  the accepted STT sidecar health/capability contract is ready and
  GPU-required execution is available. No CPU fallback is permitted.
- [x] Successful jobs persist a `transcript_json` artifact containing schema
  version, ordered timestamped segments, speaker labels, language evidence,
  warnings, bounded runtime metadata, source/normalized media hashes in
  artifact metadata, and no raw model ids, token values, private cache paths,
  backend-native tuning knobs, unbounded stderr, or sidecar trust secrets.
- [x] Diarization is fail-closed: no successful artifact may contain placeholder
  speakers, missing speakers, or `diarization_unavailable`.
- [x] Segment alignment validates before artifact persistence; alignment
  failure returns `audio_segment_alignment_failed` and exposes no terminal
  transcript artifact.
- [x] Audio progress is monotonic and uses `audio_total_media_seconds`,
  `audio_processed_media_seconds`, `audio_percent_complete`,
  `audio_current_chunk_index`, and `audio_total_chunks`; PDF page counters stay
  `null` for audio jobs.
- [x] Cancellation propagates to pending sidecar/chunk work and purges
  incomplete normalized audio, sidecar temp chunks, checkpoints, and partial
  transcript state. Canceled or failed jobs do not expose partial transcript
  artifacts.
- [x] Transient retry is idempotent under the v2 job fingerprint and does not
  duplicate transcript segments, diarization windows, checkpoints, or named
  artifacts.
- [x] `GET /v2/convert/jobs/{job_id}/result`, `/artifact`, `/artifacts`, and
  `/artifacts/transcript_json` behave consistently for successful, pending,
  failed, and canceled audio jobs.
- [x] Existing PDF, DOCX, Markdown, HTML, DigiExam, and admission-only
  validation behavior is unchanged except where shared artifact-bundle routing
  must become route-aware for `transcript_bundle`.
- [x] Live proof on Hemma demonstrates the accepted FasterWhisper ROCm plus
  pyannote profile, FFmpeg/ffprobe boundary, exact and min/max speaker hints,
  no CPU fallback, and human-reviewable `transcript_json` output through the
  tunnel.

## Test Requirements

- [x] Red-first tests must fail on the current Task 355 state because audio
  jobs remain queued and no `transcript_json` artifact exists.
- [x] Tests must exercise the public HTTP lifecycle where owner scope,
  status/result/artifact/cancel behavior is the contract.
- [x] Domain tests must cover transcript JSON schema, segment ordering,
  speaker-label presence, language evidence, bounded runtime metadata, and
  content-safety exclusions.
- [x] Infrastructure tests must use a fake sidecar adapter at the internal
  boundary, not mocks of helper internals, so failures prove behavior the
  production service owns.
- [x] Live Hemma proof must be captured as ignored artifacts under
  `build/verification/` and only bounded paths/statuses may be retained in
  governed docs.

## Implementation Evidence

- Implementation commit:
  `a8ab0d1211fa4a0fb8e0d1efe5fd6a40d982e4ac`.
- The runtime now dispatches `audio -> transcript_bundle` jobs only when the
  internal STT sidecar health/capability contract is ready, with GPU-required
  execution and no CPU fallback.
- The main service owns the v2 job lifecycle, owner scope, progress, result,
  artifact, cancellation, and retention semantics. The sidecar owns only
  media probing, normalization, transcription, diarization, and bounded
  transcript payload production behind the internal adapter contract.
- Successful audio jobs expose the canonical `transcript_json` artifact through
  `/result`, `/artifact`, `/artifacts`, and `/artifacts/transcript_json`.
  Formatter artifacts remain unavailable until later Story 54 formatter
  strategies are accepted.
- Focused sidecar/runtime command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py -q`
  passed with `28 passed`.
- Broader focused regression command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_policy.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_webhook_delivery_v2.py -q`
  passed with `141 passed, 3 skipped`.
- Post-healthcheck focused regression command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py -q`
  passed with `23 passed`.
- Quality gates passed: `pdm run format-all`, `pdm run lint-fix`,
  `pdm run typecheck-all`, and `pdm run coverage-gate`. The coverage gate
  passed with `1645 passed, 6 skipped`, `95.51%` total coverage.
- Contract/documentation gates passed after `pdm run openapi-export-v2` and
  `pdm run docs-sync`: `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.

## Deployed Live Proof

- Hemma deploy verification passed:
  `pdm run hemma-deploy-and-verify --expected-revision a8ab0d1211fa4a0fb8e0d1efe5fd6a40d982e4ac --lane host`.
  The report recorded expected, remote, and service revisions all equal to
  `a8ab0d1211fa4a0fb8e0d1efe5fd6a40d982e4ac` on lane `host`.
- The internal STT sidecar was live and healthy after deploy, with
  `adapter_contract_version=stt-sidecar-v1`, `backend_profile_id=stt_sv_en_primary`,
  `gpu_required=true`, `acceleration_family=rocm`, `acceleration_ready=true`,
  `backend_family=faster_whisper`, and required diarization.
- Live tunnel proof artifacts are ignored under
  `build/verification/audio-transcript-live-api-proof/a8ab0d1/`.
- English two-speaker proof:
  - job id: `jobv2_26d3dbc95c9342ec931e45c116`
  - status: `succeeded`
  - detected language: `en`
  - diarization status: `succeeded`
  - segment count: `231`
  - speaker labels: `SPEAKER_00`, `SPEAKER_01`
  - transcript artifact:
    `build/verification/audio-transcript-live-api-proof/a8ab0d1/english_dialogue_two_speakers/transcript_json.json`
  - transcript SHA-256:
    `f9ca1b3121345ebc40fa067b3f44ce80e5baac310161726b6fb685185218aa0d`
- Swedish speaker-range proof:
  - job id: `jobv2_21eeb0d974404d9f82f81e9cc7`
  - status: `succeeded`
  - detected language: `sv`
  - diarization status: `succeeded`
  - segment count: `4`
  - speaker labels: `SPEAKER_00`
  - transcript artifact:
    `build/verification/audio-transcript-live-api-proof/a8ab0d1/swedish_monologue_speaker_range/transcript_json.json`
  - transcript SHA-256:
    `c3fc7e70c40a50aacf6fb40092b286bb2eb5114e111459953b8cc486a6aa02a3`
- Live proof summary:
  `build/verification/audio-transcript-live-api-proof/a8ab0d1/live-proof-summary.md`.

## Review 42 Remediation Evidence

- Remediation commit:
  `d036271155d0dde005e12a9a228ca0f6a13dd848`.
- Review 42 fixes preserve structured sidecar HTTP error codes across the real
  HTTP adapter boundary, enforce duration and timeout contract values before
  model work, and propagate v2 cancellation to active STT sidecar requests.
- Red-first remediation command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py -q`
  failed with `8 failed, 3 passed`.
- Green focused command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py -q`
  passed with `17 passed`.
- Review 42 remediation quality gates passed: `pdm run format-all`,
  `pdm run lint-fix`, `pdm run typecheck-all`, and `pdm run coverage-gate`.
  The coverage gate passed with `1653 passed, 6 skipped`, `95.54%` total
  coverage. Docs gates passed after `pdm run docs-sync`.
- Hemma deploy verification passed:
  `pdm run hemma-deploy-and-verify --expected-revision d036271155d0dde005e12a9a228ca0f6a13dd848 --lane host`.
  The report recorded expected, remote, and service revisions all equal to
  `d036271155d0dde005e12a9a228ca0f6a13dd848` on lane `host`.
- Fresh live tunnel proof artifacts are ignored under
  `build/verification/audio-transcript-live-api-proof/d036271/`.
- English two-speaker proof after remediation:
  - job id: `jobv2_796bead89df64c679afb373ebf`
  - status: `succeeded`
  - detected language: `en`
  - diarization status: `succeeded`
  - segment count: `231`
  - speaker labels: `SPEAKER_00`, `SPEAKER_01`
  - transcript SHA-256:
    `9b5c8c8e0a3c27c6a94d066b73214379eafaca0ed03b7b044fc63143767815dd`
- Swedish speaker-range proof after remediation:
  - job id: `jobv2_646a9ce564b4498989c2040ebe`
  - status: `succeeded`
  - detected language: `sv`
  - diarization status: `succeeded`
  - segment count: `4`
  - speaker labels: `SPEAKER_00`
  - transcript SHA-256:
    `5962a1ce927a5cf106539638fba8180c62f12ff2b5ef060a1ccc34a63b216450`

## Validation Plan

- Focused red/green pytest for audio runtime execution and artifact routes.
- Focused regression pytest for Task 355 admission, runtime supervision, v2
  artifact routes, OpenAPI contract, and formatter-blocked-state guards.
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Hemma deploy and verify with
  `pdm run hemma-deploy-and-verify --expected-revision <sha> --lane host`
- Live tunnel create/status/result/artifact/cancel proof for
  `audio -> transcript_bundle` before retained review.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
