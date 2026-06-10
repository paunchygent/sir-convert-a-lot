---
id: task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json
title: Execute audio transcript jobs and persist canonical transcript JSON
type: task
status: proposed
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

- [ ] Purpose-named domain/application/infrastructure modules for transcript
  bundle execution, sidecar client contracts, chunk checkpoints, and artifact
  packaging.
- [ ] Red-first behavior tests for successful `transcript_json` persistence and
  named artifact retrieval.
- [ ] Red-first tests for sidecar unavailable, GPU unavailable, model/cache
  unavailable, transcription failure, diarization failure, alignment failure,
  media probe/normalization failures, retry-safe checkpoint behavior,
  cancellation cleanup, and owner-scoped access.
- [ ] OpenAPI/converter/downstream docs synchronized to show JSON execution is
  live while formatter artifacts remain blocked.
- [ ] Hemma deploy and live tunnel proof that an English two-speaker fixture and
  Swedish one-speaker fixture complete through the public v2 job lifecycle with
  `transcript_json` available for human review.
- [ ] Retained ruthless review artifact accepted after deployed live proof.

## Acceptance Criteria

- [ ] Valid admitted audio jobs are dispatchable by the v2 runtime only when
  the accepted STT sidecar health/capability contract is ready and
  GPU-required execution is available. No CPU fallback is permitted.
- [ ] Successful jobs persist a `transcript_json` artifact containing schema
  version, ordered timestamped segments, speaker labels, language evidence,
  warnings, bounded runtime metadata, source/normalized media hashes in
  artifact metadata, and no raw model ids, token values, private cache paths,
  backend-native tuning knobs, unbounded stderr, or sidecar trust secrets.
- [ ] Diarization is fail-closed: no successful artifact may contain placeholder
  speakers, missing speakers, or `diarization_unavailable`.
- [ ] Segment alignment validates before artifact persistence; alignment
  failure returns `audio_segment_alignment_failed` and exposes no terminal
  transcript artifact.
- [ ] Audio progress is monotonic and uses `audio_total_media_seconds`,
  `audio_processed_media_seconds`, `audio_percent_complete`,
  `audio_current_chunk_index`, and `audio_total_chunks`; PDF page counters stay
  `null` for audio jobs.
- [ ] Cancellation propagates to pending sidecar/chunk work and purges
  incomplete normalized audio, sidecar temp chunks, checkpoints, and partial
  transcript state. Canceled or failed jobs do not expose partial transcript
  artifacts.
- [ ] Transient retry is idempotent under the v2 job fingerprint and does not
  duplicate transcript segments, diarization windows, checkpoints, or named
  artifacts.
- [ ] `GET /v2/convert/jobs/{job_id}/result`, `/artifact`, `/artifacts`, and
  `/artifacts/transcript_json` behave consistently for successful, pending,
  failed, and canceled audio jobs.
- [ ] Existing PDF, DOCX, Markdown, HTML, DigiExam, and admission-only
  validation behavior is unchanged except where shared artifact-bundle routing
  must become route-aware for `transcript_bundle`.
- [ ] Live proof on Hemma demonstrates the accepted FasterWhisper ROCm plus
  pyannote profile, FFmpeg/ffprobe boundary, exact and min/max speaker hints,
  no CPU fallback, and human-reviewable `transcript_json` output through the
  tunnel.

## Test Requirements

- [ ] Red-first tests must fail on the current Task 355 state because audio
  jobs remain queued and no `transcript_json` artifact exists.
- [ ] Tests must exercise the public HTTP lifecycle where owner scope,
  status/result/artifact/cancel behavior is the contract.
- [ ] Domain tests must cover transcript JSON schema, segment ordering,
  speaker-label presence, language evidence, bounded runtime metadata, and
  content-safety exclusions.
- [ ] Infrastructure tests must use a fake sidecar adapter at the internal
  boundary, not mocks of helper internals, so failures prove behavior the
  production service owns.
- [ ] Live Hemma proof must be captured as ignored artifacts under
  `build/verification/` and only bounded paths/statuses may be retained in
  governed docs.

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

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
