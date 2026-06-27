---
id: task-366-implement-stt-sidecar-lazy-model-load-and-idle-unload
title: Implement STT sidecar lazy model load and idle unload
type: task
status: in_progress
priority: high
created: '2026-06-27'
last_updated: '2026-06-27'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - stt
  - sidecar
  - lazy-load
  - idle-unload
  - task-0814
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the Sir Convert-owned STT sidecar lifecycle slice originating from
HuleEdu TASK-0814: sidecar readiness must mean "can accept STT work" rather
than "heavy FasterWhisper and pyannote models are already resident in GPU
memory."

The sidecar should lazy-load the approved FasterWhisper/CTranslate2 and
pyannote runtime exactly once when real transcription or diarization work
requires it, then unload model references after an idle timeout once no
model-using work is active.

## PR Scope

- Keep the accepted FasterWhisper plus pyannote backend profile from ADR-0013
  and Task 362.
- Change sidecar startup and health/capability truth so `/health`,
  `/capabilities`, and `/probe-media` do not instantiate heavyweight STT or
  diarization pipelines.
- Add typed configuration for the idle unload timeout.
- Add concurrency control so simultaneous model-using requests share one lazy
  load and idle unload cannot run while a model-using request is active.
- Add shutdown cleanup that drops model references.
- Preserve current endpoint compatibility; additive health/capability residency
  fields are allowed.
- Do not implement allocator changes, `malloc_trim`, `MALLOC_ARENA_MAX`,
  quantization, model replacement, concurrency reductions, or new heavy-lane
  routing.

## Deliverables

- [x] Lazy sidecar startup and model-free probe behavior.
- [x] Lazy model lifecycle manager with active-use and idle-unload protection.
- [x] Focused red-first tests for startup/probe, first-use load, active idle
  protection, timeout unload, and shutdown cleanup.
- [x] Generated docs indexes refreshed.

## Acceptance Criteria

- [x] `/health` reports ready when GPU and required secret preconditions are
  satisfied even when STT/diarization models are not resident.
- [x] `/capabilities` preserves existing policy fields and adds bounded model
  residency truth without exposing raw model ids or secrets.
- [x] `/probe-media` can probe/normalize accepted local media without loading
  FasterWhisper or pyannote.
- [x] The first `diarize` or `transcribe-chunk` operation loads both approved
  model pipelines exactly once under concurrency control.
- [x] Idle unload drops model references only after the configured timeout and
  never while model-using work is active.
- [x] Shutdown cleanup drops loaded model references.
- [x] Focused tests include red-first evidence and pass after implementation.

## Red-First Evidence

- Red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py -q`
  failed with `3 failed` before production changes. The failures showed
  `SttSidecarSettings` had no `idle_unload_seconds` configuration and no model
  lifecycle surface yet.
- Reviewer-fix red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py -q`
  failed with `1 failed, 4 passed` before the capability-truth fix. The failing
  test showed an empty Hugging Face cache root reported
  `model_artifacts_present=true`; the added health-triggered idle-unload proof
  already passed before this fix.

## Green Validation Evidence

- Focused sidecar lifecycle, runtime, HTTP, and compose proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_compose_contract.py -q`
  passed with `33 passed`.
- Reviewer-fix focused lazy lifecycle proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py -q`
  passed with `5 passed`.
- Reviewer-fix focused STT/readiness/compose proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py -q`
  passed with `47 passed`.
- `pdm run format-all` passed with `943 files left unchanged`.
- `pdm run typecheck-all` passed with
  `Success: no issues found in 894 source files`.
- `pdm run lint-fix` passed with `All checks passed!`,
  `943 files left unchanged`, `Validated docs=563 rules=11`, and
  `Validated 487 backlog files`.
- `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check` passed.
- `pdm run coverage-gate` reached the coverage threshold
  (`95.37%`, `1730 passed`, `6 skipped`) but exited failed because nine
  unrelated Qwen checkpoint/training tests refused to write durable checkpoints
  with current local free-space headroom
  (`free_bytes` about 28.9 GB versus `required_free_bytes` about 30.1 GB).

## Reviewer Response Notes

- `/capabilities.cache.model_artifacts_present` now checks both configured
  model ids for cached Hugging Face snapshot files without importing or loading
  FasterWhisper or pyannote. A present cache root without those artifacts still
  reports `cache_roots_ready=true` but `model_artifacts_present=false`, so the
  existing main-service readiness policy fails closed with
  `model_artifacts_missing`.
- `runtime.health()` is now directly covered as an idle-unload trigger: the
  regression test loads models, advances a controlled monotonic clock past the
  configured timeout, calls `health()`, and observes `models_resident=false`
  plus the fake CTranslate2 unload counter incrementing once.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
