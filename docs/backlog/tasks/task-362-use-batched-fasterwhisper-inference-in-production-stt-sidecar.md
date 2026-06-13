---
id: task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar
title: Use batched FasterWhisper inference in production STT sidecar
type: task
status: completed
priority: high
created: '2026-06-13'
last_updated: '2026-06-13'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md
  - docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - stt
  - faster-whisper
  - batch-inference
  - sidecar
  - hemma
  - production-remediation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remediate the production STT sidecar so the accepted FasterWhisper ROCm profile
uses `BatchedInferencePipeline` with explicit `batch_size=8`, and make that
runtime truth visible through sanitized capabilities and production compose
contracts.

RCA: the observed 34-second first-response latency was not solved by widening
Gateway timeout alone. The deployed sidecar profile used FasterWhisper and
pyannote on ROCm, but the runtime still called plain
`WhisperModel.transcribe(..., beam_size=5)` with no batched pipeline and no
batch-size configuration or capability evidence. Production must therefore use
batched inference with `batch_size=8` as part of the runtime contract.

## PR Scope

- Add typed sidecar settings for `SIR_STT_SIDECAR_BATCH_SIZE`, defaulting to
  `8` and rejecting non-positive values at configuration load.
- Require `faster_whisper.BatchedInferencePipeline` during sidecar startup and
  fail clearly if the installed faster-whisper package does not provide it.
- Wrap the loaded `WhisperModel` with the batched pipeline and pass
  `batch_size=settings.batch_size` plus the existing `beam_size` and
  `word_timestamps` options during chunk transcription.
- Expose sanitized `/capabilities` transcription truth with
  `backend_family=faster_whisper` and `batch_size=8`.
- Pin the Hemma production sidecar compose environment to
  `SIR_STT_SIDECAR_BATCH_SIZE=8` and keep compose contract tests fail-closed on
  drift.
- Do not change public STT API request fields, add CPU fallback, expose raw
  model ids or secrets, or deploy from this implementation slice.

## Deliverables

- [x] Sidecar settings include typed batch-size configuration.
- [x] Production runtime uses `BatchedInferencePipeline` and passes
  `batch_size=8` to transcription.
- [x] Sanitized capability output exposes FasterWhisper backend family and
  batch size.
- [x] Production compose declares `SIR_STT_SIDECAR_BATCH_SIZE=8`.
- [x] Focused tests fail if chunk transcription omits `batch_size`, startup
  skips the batched wrapper, or prod compose omits the batch-size env.

## Acceptance Criteria

- [x] The production sidecar startup path wraps the loaded FasterWhisper model
  in `BatchedInferencePipeline`; missing pipeline support fails with a clear
  startup error rather than silently using unbatched inference.
- [x] Chunk transcription passes `batch_size=8`, preserves `beam_size=5`, keeps
  word timestamps enabled, and preserves language override behavior.
- [x] `/capabilities` reports bounded transcription runtime truth without
  secrets or raw model identifiers, including
  `backend_family=faster_whisper` and `batch_size=8`.
- [x] `compose.yaml` explicitly sets `SIR_STT_SIDECAR_BATCH_SIZE=8` on
  `sir_convert_a_lot_stt_sidecar`.
- [x] Focused tests, docs validation, skills validation, handoff validation,
  and whitespace diff checks pass.

## Red-First Evidence

- Red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_compose_contract.py -q`
  failed with `9 failed, 17 passed` before production changes. Failures showed
  `SttSidecarSettings` had no `batch_size` field and prod compose omitted
  `SIR_STT_SIDECAR_BATCH_SIZE`.

## Green Validation Evidence

- Focused runtime/compose proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_compose_contract.py -q`
  passed with `27 passed`.
- `pdm run format-all` passed with `928 files left unchanged`.
- `pdm run typecheck-all` passed with `Success: no issues found in 879 source files`.
- `pdm run lint-fix` passed after `pdm run docs-sync` refreshed generated
  indexes; final lint/docs output reported `Validated docs=554 rules=11` and
  `Validated 479 backlog files`.
- Final docs, skills, handoff, and whitespace gates passed after task status
  completion.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
