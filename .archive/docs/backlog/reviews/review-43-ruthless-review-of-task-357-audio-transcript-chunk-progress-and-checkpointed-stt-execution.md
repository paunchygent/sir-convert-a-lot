---
id: review-43-ruthless-review-of-task-357-audio-transcript-chunk-progress-and-checkpointed-stt-execution
title: Ruthless review of Task 357 audio transcript chunk progress and checkpointed STT execution
type: review
status: completed
priority: high
created: '2026-06-11'
last_updated: '2026-06-11'
related:
  - docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/tasks/task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json.md
  - docs/backlog/reviews/review-42-ruthless-review-of-task-356-audio-transcript-runtime-json-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
labels:
  - review
  - approved
  - task-357
  - stt
  - audio
  - checkpointing
  - sidecar
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: fixed ruthless implementation review for Task 357 working tree.
- Governing authority:
  - `AGENTS.md`
  - `.codex/rules/030-conversion-workflows.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md`
  - `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
  - `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  - `docs/converters/audio-transcription-service-api-artifact-contract.md`
  - `docs/backlog/reviews/review-42-ruthless-review-of-task-356-audio-transcript-runtime-json-persistence.md`
- Working tree scope reviewed:
  - `docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_alignment.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_artifacts.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_checkpoints.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_chunking.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_merge.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_payloads.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_progress.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_runtime_types.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcript_sidecar_requests.py`
  - `scripts/sir_convert_a_lot/infrastructure/audio_transcription_sidecar_client.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_job_runner_v2.py`
  - `scripts/sir_convert_a_lot/stt_sidecar/app_factory.py`
  - `scripts/sir_convert_a_lot/stt_sidecar/contracts.py`
  - `scripts/sir_convert_a_lot/stt_sidecar/media.py`
  - `scripts/sir_convert_a_lot/stt_sidecar/request_parsing.py`
  - `scripts/sir_convert_a_lot/stt_sidecar/runtime.py`
  - `tests/sir_convert_a_lot/audio_transcript_task357_helpers.py`
  - `tests/sir_convert_a_lot/test_audio_transcript_alignment_v2.py`
  - `tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py`
  - `tests/sir_convert_a_lot/test_audio_transcript_cancellation_v2.py`
  - `tests/sir_convert_a_lot/test_audio_transcript_checkpointing_v2.py`
  - `tests/sir_convert_a_lot/test_audio_transcript_progress_v2.py`
  - `tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py`
  - `tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`
- Public or operational surfaces affected:
  - Service API v2 `audio -> transcript_bundle` execution and polling progress.
  - Internal STT sidecar HTTP contract: `/probe-media`, `/diarize`,
    `/transcribe-chunk`, `/cancel`.
  - Sidecar normalized media scratch retention and cancellation cleanup.
  - Canonical `transcript_json` artifact persistence and checkpoint replay.
- Compatibility posture:
  - Clean Task 357 internal sidecar contract transition is required.
  - The main Service API v2 audio runtime must not preserve or fall back to the
    retired blocking `/transcribe` sidecar route.
  - Legacy-test compatibility is not required and must not be preserved through
    shims or fallback behavior.

## Findings

1. [x] `high` - The new chunk endpoints accept arbitrary normalized-audio
   paths instead of proving the handle was issued by `/probe-media` for the
   same request.

   Evidence:

   - `SttSidecarRuntime.probe_media` stores a normalized file path in
     `_normalized_handles` at
     `scripts/sir_convert_a_lot/stt_sidecar/runtime.py:236`.
   - `SttSidecarRuntime.diarize` and `transcribe_chunk` then resolve
     `normalized_audio_path(request)` directly at
     `scripts/sir_convert_a_lot/stt_sidecar/runtime.py:259` and
     `scripts/sir_convert_a_lot/stt_sidecar/runtime.py:289`.
   - `normalized_audio_path` only checks that the caller-supplied handle is a
     file at `scripts/sir_convert_a_lot/stt_sidecar/request_parsing.py:91`; it
     does not check `_normalized_handles`, the `request_handle`, or the
     provided `normalized_audio.sha256`.
   - The sidecar HTTP contract tests use fakes that accept
     `normalized://job-audio-1`, so they do not exercise the real runtime's
     handle validation or prove that `/diarize` and `/transcribe-chunk` are
     bound to the preceding `/probe-media` result.

   Why it matters:
   Task 357's clean internal sidecar transition depends on
   service-owned probe/chunk/checkpoint state. With the current runtime, an
   internal caller can bypass that state and ask `/diarize` or
   `/transcribe-chunk` to process any file path visible inside the sidecar
   container. That violates the local-upload/probe boundary, makes the
   normalized media hash a passive string instead of an invariant, and weakens
   retry/idempotency proof because chunk work is not cryptographically or
   handle-wise tied to the probed media.

   Required fix:
   Make the normalized handle an owned sidecar capability. Either return an
   opaque handle from `/probe-media`, or validate the returned path through
   `_normalized_handles` by `request_handle`; then verify the normalized audio
   SHA-256 before diarization or chunk transcription. Reject unknown,
   mismatched, or stale handles with a deterministic client-safe error. This
   should be a clean hard break for the internal Task 357 contract; do not keep
   compatibility for caller-supplied arbitrary paths.

   Proof requirement:
   Add sidecar runtime and FastAPI contract tests that:

   - call `/diarize` and `/transcribe-chunk` with a handle not issued by
     `/probe-media` and assert rejection;
   - call them with a mismatched `request_handle` and assert rejection;
   - call them with a mismatched `normalized_audio.sha256` and assert rejection;
   - prove the valid `/probe-media` -> `/diarize` -> `/transcribe-chunk`
     sequence still succeeds.
     Run:
     `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`.

   Re-review disposition on 2026-06-11:
   Resolved. `SttSidecarRuntime` now delegates normalized media capability
   state to `NormalizedAudioStore`; `/probe-media` returns an opaque
   `sir-stt-normalized:...` handle and SHA-256, while `/diarize` and
   `/transcribe-chunk` resolve the handle through the store, require the same
   `request_handle`, verify the recorded SHA against the on-disk normalized
   audio, and reject unknown, wrong-request, wrong-SHA, or finalized handles.
   The proof is in
   `tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`:
   `test_sidecar_runtime_accepts_only_probe_issued_normalized_handles`,
   `test_sidecar_runtime_rejects_unknown_mismatched_or_wrong_sha_handles`, and
   `test_sidecar_runtime_rejects_stale_finalized_handles`.

1. [x] `high` - Sidecar normalized media is not purged on successful or failed
   terminal jobs, so Task 357 leaves retained user media outside the Service API
   artifact lifecycle.

   Evidence:

   - `probe_media` writes normalized audio under
     `/tmp/sir-convert-a-lot-stt-sidecar/.../normalized.wav` and records the
     path at `scripts/sir_convert_a_lot/stt_sidecar/runtime.py:226`.
   - The only runtime cleanup of `_normalized_handles` unlinks the file inside
     `cancel` at `scripts/sir_convert_a_lot/stt_sidecar/runtime.py:350`.
   - The main service success path purges only the checkpoint store at
     `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:219`;
     it does not ask the sidecar to remove the normalized media handle.
   - The main service failure path purges only checkpoints for non-retryable
     `ServiceError`s at
     `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_runtime.py:189`.
   - The Task 357 acceptance criteria require failed or canceled jobs to purge
     incomplete normalized media, sidecar temp chunks, checkpoints, and partial
     transcript state at
     `docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md:169`.

   Why it matters:
   Audio recordings and normalized audio are user content under ADR-0013 and
   the route contract. Persisting normalized WAV files in the sidecar temp root
   after success or failure violates short operational retention and creates a
   hidden artifact surface outside owner-scoped Service API v2 result handling.
   It also means the current cancellation test is too narrow: it proves the
   main-service checkpoint file is purged, not that sidecar normalized media is
   removed for every terminal state.

   Required fix:
   Add an explicit sidecar cleanup/finalize contract or equivalent terminal
   lifecycle hook that removes the normalized handle directory and untracks the
   request on success, non-retryable failure, retry abandonment, and
   cancellation. Cleanup should remove the whole job-scoped sidecar directory,
   not only `normalized.wav`, and should be idempotent.

   Proof requirement:
   Add tests with the real `SttSidecarRuntime` or a file-observing sidecar fake
   that prove normalized media is removed after success, non-retryable failure,
   retryable failure when the job is marked terminal, and cancel. Pair this
   with public lifecycle assertions that terminal failed/canceled jobs expose
   no `transcript_json` artifact. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_cancellation_v2.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`.

   Re-review disposition on 2026-06-11:
   Resolved. The sidecar exposes `/finalize`; `cancel` also finalizes
   internally. The main Service API v2 audio runtime calls sidecar finalize
   before writing a successful terminal artifact, on terminal `ServiceError`
   failure while preserving the original governed error, and during
   cancellation cleanup. `NormalizedAudioStore.finalize` untracks all handles
   for the request and removes the whole job-scoped normalized-media directory.
   The proof is in
   `test_audio_success_finalizes_sidecar_normalized_media`,
   `test_audio_terminal_failure_finalizes_sidecar_normalized_media`,
   `test_cancellation_after_checkpoint_stops_chunks_and_purges_partial_state`,
   and `test_sidecar_runtime_cancel_removes_job_scoped_normalized_media`.

1. [x] `blocker` - Required Task 357 docs and live proof are missing, so the
   task cannot be approved for closure even though focused local tests pass.

   Evidence:

   - Task 357 explicitly requires an update to
     `docs/converters/audio-transcription-service-api-artifact-contract.md` at
     `docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md:133`.
   - That converter contract still describes Task 357 as planned future
     hardening at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:50`.
   - Task 357 requires focused live Hemma proof showing non-null numeric
     progress while the job is still running, followed by successful
     `transcript_json` retrieval, at
     `docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md:147`.
   - The Task 357 stop condition says to stop before deploying or reviewing if
     live proof cannot show non-null numeric progress while running at
     `docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md:235`.
   - Implementer-reported evidence did not include live Hemma proof,
     `coverage-gate`, `docs-sync`, `docs-validate`, `skills-validate`, or
     `handoff-validate`; review-time execution only confirmed the focused
     local suite.

   Why it matters:
   Task 357 changes a contract-bearing runtime surface. Approving without the
   contract doc update and live running-state proof would claim the 120-minute
   progress UX is closed without deployed evidence, and would leave generated
   docs/handoff state stale for downstream Gateway/Skriptoteket consumers.

   Required fix:
   Update the audio transcription converter contract and Task 357 state to
   describe the accepted chunk/checkpoint sidecar contract, progress semantics,
   cleanup semantics, and live-proof evidence. Deploy to Hemma and record a
   bounded proof that polling observes non-null numeric audio progress before
   terminal success and that `transcript_json` retrieval succeeds. Then run the
   repo close-out gates, including docs, handoff, coverage, lint, typecheck,
   and `git diff --check`.

   Proof requirement:
   Run and record:
   `pdm run coverage-gate`,
   `pdm run docs-sync`,
   `pdm run docs-validate`,
   `pdm run skills-validate`,
   `pdm run handoff-validate`,
   `git diff --check`,
   plus the focused live Hemma proof command or retained proof artifact.

   Re-review disposition on 2026-06-11:
   Resolved for Review 43 acceptance. Current `main` is
   `00f9d7ab700ff4dbeea9f8e6da65caa5c49e1cfa`, matching `origin/main`.
   Hemma deploy verification passed with expected, remote, and service
   revisions all equal to that revision in
   `build/verification/hemma-deploy-verify/report.md`. Fresh live tunnel proof
   in `build/verification/task-357-live-progress-proof-00f9d7a/proof.md`
   records service revision `00f9d7ab700ff4dbeea9f8e6da65caa5c49e1cfa`,
   terminal status `succeeded`, running-state audio progress before terminal
   success (`audio_total_media_seconds=675.250667`,
   `audio_processed_media_seconds=600.0`,
   `audio_percent_complete=88.85589149666104`,
   `audio_current_chunk_index=1`, `audio_total_chunks=3`), and successful
   `transcript_json_v1` retrieval with `293` segments. Task 357 records the
   chunk/checkpoint contract and live-proof lane. The stale converter-contract
   wording that still said deploy/live evidence was pending was removed during
   close-out after this re-review.

## Decision

approved

## Response

APPROVED for Task 357 after post-deploy re-review.

Re-review confirms the three original Review 43 findings are resolved in the
current deployed `main` state. The implementation is a clean internal sidecar
contract transition: the main audio runtime calls `/probe-media`, `/diarize`,
`/transcribe-chunk`, `/finalize`, and `/cancel`; no active Service API v2 audio
runtime fallback to the retired blocking `/transcribe` path was found.

Sidecar normalized media is now an opaque, request-bound, SHA-verified
capability; terminal success/failure/cancel paths finalize sidecar media; local
focused tests and full reported quality gates are green; and current deployed
Hemma proof at `00f9d7a` shows running-state non-null numeric audio progress
before successful `transcript_json_v1` retrieval.

## Follow-up Actions

1. No blocking Task 357 follow-up remains for Review 43 acceptance.
1. No non-blocking Task 357 docs cleanup remains after close-out.

## Validation

- Skill/reference workflow used:
  `agent-docs-governance` with the Sir Convert-a-Lot reference, `testing`, and
  `ruthless-code-review` with the forbidden-patterns reference.
- Context7 FastAPI documentation was checked for current `HTTPException` /
  `TestClient` JSON response behavior while reviewing sidecar HTTP contract
  tests.
- Review-time code search:
  `rg -n "\bAny\b|typing\.cast|cast\(|type: ignore|# noqa|/transcribe\b|transcribe\(|transcribe_chunk|transcribe-chunk|probe-media|diarize|cancel\b|fallback|legacy|compat" scripts/sir_convert_a_lot/infrastructure scripts/sir_convert_a_lot/stt_sidecar tests/sir_convert_a_lot/test_audio_transcript* tests/sir_convert_a_lot/test_stt_sidecar*`
  found no active main-service `/transcribe` call in the Task 357 audio
  runtime, but did identify test-only fakes and unrelated historical fallback
  language.
- Review-time focused tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_audio_transcript_progress_v2.py tests/sir_convert_a_lot/test_audio_transcript_checkpointing_v2.py tests/sir_convert_a_lot/test_audio_transcript_cancellation_v2.py tests/sir_convert_a_lot/test_audio_transcript_alignment_v2.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py`
  with `19 passed`.
- Review-artifact docs close-out passed:
  `pdm run docs-sync`,
  `pdm run docs-validate`,
  `pdm run skills-validate`,
  `pdm run handoff-validate`,
  and `git diff --check`.
- Not run before this review decision: `coverage-gate`, live Hemma proof, and
  full implementation close-out gates.
- Re-review pass on 2026-06-11 confirmed current branch state:
  `main...origin/main` clean at
  `00f9d7ab700ff4dbeea9f8e6da65caa5c49e1cfa`.
- Re-review focused tests passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_alignment_v2.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_audio_transcript_progress_v2.py tests/sir_convert_a_lot/test_audio_transcript_checkpointing_v2.py tests/sir_convert_a_lot/test_audio_transcript_cancellation_v2.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_downstream_transcript_coordination_docs_guard.py tests/sir_convert_a_lot/test_runtime_engine_v2.py::test_run_job_returns_when_mark_succeeded_conflicts`
  with `33 passed`.
- Re-review inspected deployed proof:
  `build/verification/hemma-deploy-verify/report.md` and
  `build/verification/task-357-live-progress-proof-00f9d7a/proof.md`.
- Implementer-reported full close-out evidence reviewed:
  `pdm run coverage-gate` passed with `1668 passed`, `6 skipped`, coverage
  `95.61%`; `pdm run format-all` clean; `pdm run lint-fix` all checks passed;
  `pdm run typecheck-all` succeeded for `866` source files;
  `pdm run docs-sync`, `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check` passed.

## Completion

Initial review completed on 2026-06-11 with `changes_requested`.
Post-deploy re-review completed on 2026-06-11 with `approved` after deployed
revision `00f9d7ab700ff4dbeea9f8e6da65caa5c49e1cfa` passed live running-progress
proof and all original findings were resolved.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
