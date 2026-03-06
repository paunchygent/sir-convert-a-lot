---
id: task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700
title: Benchmark Hemma TTS sidecar compatibility and audio formats on R9700
type: task
status: proposed
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/tasks/task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - benchmark
  - tts
  - sidecar
  - hemma
  - rocm
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Prove that the chosen sidecar stack can run on the real Hemma AMD Radeon AI PRO R9700
(`gfx1201`) host and record audio-format evidence before the service contract is implemented.

## PR Scope

- Add a committed benchmark/smoke surface that:
  - starts the TTS sidecar in an isolated Linux container/runtime,
  - targets Python `3.12` or newer when upstream dependencies support it,
  - verifies sidecar readiness and internal-network accessibility from Sir Convert-a-Lot,
  - exercises `/v1/audio/speech` and `/v1/audio/voices`,
  - captures `wav` output and records compressed-format availability (`mp3` and/or equivalent).
- Capture deterministic evidence under `build/verification/` or `build/benchmarks/`.
- Update the Hemma runbook with the canonical benchmark command and rollback notes.

## Deliverables

- [ ] Committed benchmark/smoke command surface.
- [ ] Deterministic Hemma evidence artifacts for startup/runtime/output-format checks.
- [ ] Runbook guidance for the sidecar benchmark flow.

## Acceptance Criteria

- [ ] Sidecar boots on Hemma with documented Python/runtime versions.
- [ ] Hemma evidence records the live GPU identity (`R9700`, `gfx1201`) and runtime truth.
- [ ] `/v1/audio/speech` succeeds with `wav`.
- [ ] Benchmark output explicitly records whether compressed audio formats are supported on Hemma.
- [ ] The task makes an explicit recommendation on the highest supported Python version observed
  in practice; if `3.14` is unsupported, the evidence records why.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
