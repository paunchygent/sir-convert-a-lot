---
id: 'task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma'
title: 'Benchmark MMS Swedish as the direct-pronunciation control on Hemma'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - benchmark
  - tts
  - sidecar
  - hemma
  - swedish
  - control
  - mms
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Benchmark MMS Swedish as the direct-pronunciation control so we can separate Swedish language
quality from cloning capability when evaluating backend candidates.

## PR Scope

- Add a committed benchmark/smoke command surface for an MMS Swedish sidecar on Hemma.
- Implement the benchmark against the reusable internal sidecar capability contract from
  ADR-0007 (`/health`, `/capabilities`, `/voices`, `/synthesize`).
- Exercise Swedish synthesis using the same probe text family as Tasks 81 and 82.
- Capture runtime truth and audio artifacts for pronunciation/naturalness review.
- Explicitly document that this task is a control baseline, not a candidate for default backend
  selection when cloning remains a hard requirement.

## Deliverables

- [ ] Committed `benchmark:task-83` command surface (or equivalent named wrapper).
- [ ] Deterministic Hemma evidence under `build/verification/task-83-mms-swedish-hemma/`.
- [ ] Swedish control sample artifacts.
- [ ] Comparison notes that isolate language quality from cloning support.

## Acceptance Criteria

- [ ] MMS Swedish sidecar boots on Hemma and synthesizes Swedish sample text deterministically.
- [ ] The sidecar exposes the normalized capability contract from ADR-0007 and explicitly reports
  cloning as unsupported in `/capabilities`.
- [ ] Evidence records runtime/dependency reality, cache/storage layout, and sample artifacts.
- [ ] Report explicitly states that lack of cloning keeps MMS Swedish out of primary backend
  consideration even if pronunciation quality is strong.
- [ ] The task produces a control baseline that helps compare OpenVoice V2 and XTTS-v2 against
  direct Swedish narration quality.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
