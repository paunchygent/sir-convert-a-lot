---
id: 'task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma'
title: 'Benchmark OpenVoice V2 Swedish-probable cloning sidecar on Hemma'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - benchmark
  - tts
  - sidecar
  - hemma
  - swedish
  - cloning
  - openvoice
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Prove whether OpenVoice V2 is the strongest next Hemma sidecar candidate for Swedish-capable
teacher voice cloning, using live R9700 evidence rather than upstream claims alone.

## PR Scope

- Add a committed benchmark/smoke command surface for an OpenVoice V2 sidecar on Hemma.
- Implement the benchmark against the reusable internal sidecar capability contract from
  ADR-0007 (`/health`, `/capabilities`, `/voices`, `/synthesize`).
- Reuse the canonical Hemma persistent model-cache discipline so reruns do not redownload model
  weights.
- Exercise a cloning flow with one approved teacher reference voice clip plus transcript.
- Exercise Swedish probe text generation and capture sample artifacts for listening review.
- Record runtime truth:
  - Python version,
  - backend package/runtime versions,
  - GPU identity and peak utilization,
  - whether the sidecar remains reachable from Sir Convert-a-Lot over the internal Docker network.

## Deliverables

- [ ] Committed `benchmark:task-81` command surface (or equivalent named wrapper).
- [ ] Deterministic Hemma evidence under `build/verification/task-81-openvoice-v2-hemma/`.
- [ ] Swedish sample artifacts generated from a cloning flow.
- [ ] Explicit recommendation on whether OpenVoice V2 becomes the primary cloning-capable backend
  candidate for the next implementation slice.

## Acceptance Criteria

- [ ] OpenVoice V2 sidecar boots on Hemma and is reachable from the Sir Convert-a-Lot service
  container over the internal Docker network only.
- [ ] The sidecar exposes the normalized capability contract from ADR-0007 rather than a
  benchmark-only backend-native surface.
- [ ] The benchmark proves model-cache reuse via the canonical host storage pattern rather than
  repeated runtime downloads.
- [ ] One cloning flow succeeds with the approved teacher reference clip and Swedish probe text.
- [ ] Evidence clearly separates:
  - official upstream support claims,
  - live Hemma runtime truth,
  - subjective listening notes.
- [ ] The task records whether OpenVoice V2 is sufficiently credible to be the default Swedish-
  probable cloning backend for follow-on implementation work.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
