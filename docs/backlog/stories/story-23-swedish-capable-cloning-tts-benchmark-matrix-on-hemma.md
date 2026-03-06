---
id: story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma
title: Swedish-capable cloning TTS benchmark matrix on Hemma
type: story
status: in_progress
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/reference/ref-hemma-sidecar-tts-md-to-wav-contract-outline.md
labels:
  - tts
  - sidecar
  - benchmark
  - swedish
  - cloning
---

Implementation slice with acceptance-driven scope.

## Objective

Define the benchmark matrix that will choose the most credible cloning-capable Swedish TTS backend
for Hemma before we commit implementation defaults for teacher-voice audio delivery.

## Scope

- Benchmark OpenVoice V2 as the primary Swedish-probable cloning candidate based on official
  cross-lingual voice-cloning claims.
- Benchmark XTTS-v2 as the comparison cloning backend using the same Hemma sidecar discipline and
  evidence structure.
- Benchmark MMS Swedish as a direct-pronunciation control to separate language quality from
  cloning capability.
- Keep the main Sir Convert-a-Lot public API and provider-neutral `tts_options` contract stable
  while the sidecar backend choice remains open.
- Require candidate benchmarks to target the reusable internal sidecar capability contract from
  ADR-0007 rather than backend-native APIs directly.
- Reuse the Hemma model-cache discipline:
  - canonical persistent host cache/storage,
  - no repeated redownloads between runs,
  - no ad hoc container-local model storage.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md`
1. `docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md`
1. `docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md`

## Acceptance Criteria

- [ ] Task 81 defines deterministic Hemma evidence for OpenVoice V2 startup, cache reuse,
  cloning flow, and Swedish-text synthesis with a teacher reference voice sample.
- [ ] Task 82 defines parallel evidence for XTTS-v2 so we can compare cloning quality, runtime
  fit, and operational complexity against OpenVoice V2.
- [ ] Task 83 defines a Swedish pronunciation control benchmark whose result is explicitly
  non-canonical for backend selection because cloning is absent.
- [ ] Story outputs are strong enough to recommend:
  - one primary cloning-capable backend candidate,
  - one comparison backend,
  - one pronunciation control baseline,
    without reopening ADR-0006 or the public v2 contract shape.
  - and without inventing a backend-specific service integration path outside ADR-0007.

## Test Requirements

- [ ] Each task writes deterministic Hemma evidence under `build/verification/` with:
  - `report.json`,
  - `report.md`,
  - sidecar logs,
  - at least one synthesized Swedish sample artifact.
- [ ] OpenVoice V2 and XTTS-v2 tasks require an explicit cloning workflow using one approved
  teacher reference clip.
- [ ] Each task records Python/runtime truth, model cache path, and whether the sidecar remains
  internal-network only.

## Done Definition

The team has enough live Hemma evidence to choose the next cloning-capable Swedish TTS backend
without guessing from upstream docs alone.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [x] Docs synchronized
