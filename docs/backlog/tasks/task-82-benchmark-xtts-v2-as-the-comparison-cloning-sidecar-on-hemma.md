---
id: task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma
title: Benchmark XTTS-v2 as the comparison cloning sidecar on Hemma
type: task
status: proposed
priority: high
created: '2026-03-06'
last_updated: '2026-03-07'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
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
  - xtts
---

PR-sized execution unit; may be linked to a story or standalone.

Planning note (2026-03-07):

- Story 23 no longer treats `T82` as the immediate next benchmark lane.
- The active next comparison benchmark moved to `T85` for F5-TTS after the OpenVoice
  quality decision and explicit user direction.
- Keep this task as a deferred follow-up candidate if F5-TTS does not produce a credible Swedish
  teacher-voice result.

## Objective

Benchmark XTTS-v2 as the comparison cloning backend so OpenVoice V2 is judged against a credible
alternative rather than in isolation.

## PR Scope

- Add a committed benchmark/smoke command surface for an XTTS-v2 sidecar on Hemma.
- Implement the benchmark against the reusable internal sidecar capability contract from
  ADR-0007 (`/health`, `/capabilities`, `/voices`, `/synthesize`).
- Reuse the same teacher reference voice clip, Swedish probe text, and evidence layout used for
  Task 81 so comparisons stay fair.
- Capture runtime fit on Hemma:
  - startup profile,
  - cache reuse behavior,
  - GPU usage,
  - cloning success/failure,
  - Swedish sample artifacts.
- Document the operational differences from Task 81, including Python/runtime/dependency pressure.

## Deliverables

- [ ] Committed `benchmark:task-82` command surface (or equivalent named wrapper).
- [ ] Deterministic Hemma evidence under `build/verification/task-82-xtts-v2-hemma/`.
- [ ] Swedish cloning sample artifacts using the shared evaluation input set.
- [ ] Explicit comparison notes versus OpenVoice V2.

## Acceptance Criteria

- [ ] XTTS-v2 sidecar boots on Hemma and stays isolated from the main Sir Convert-a-Lot runtime.
- [ ] The sidecar exposes the normalized capability contract from ADR-0007 rather than a
  benchmark-only backend-native surface.
- [ ] The benchmark proves whether XTTS-v2 can complete a cloning flow with Swedish probe text on
  the real R9700 host.
- [ ] Evidence records where XTTS-v2 is stronger or weaker than OpenVoice V2:
  - cloning workflow ergonomics,
  - Swedish output credibility,
  - runtime/dependency complexity,
  - Hemma operational fit.
- [ ] The task ends with a clear recommendation on whether XTTS-v2 remains a serious candidate or
  drops behind OpenVoice V2.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
