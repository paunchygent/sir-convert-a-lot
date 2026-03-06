---
id: task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy
title: ADR for Hemma sidecar TTS architecture and route policy
type: task
status: completed
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - adr
  - tts
  - sidecar
  - gpu-governance
  - hemma
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish an accepted ADR that locks TTS to a Hemma sidecar architecture and defines the route-policy
rules for the first audio artifact slice.

## PR Scope

- Add `ADR-0006` with:
  - sidecar-only TTS decision,
  - prohibition on adding TTS runtime/model dependencies to the main service image,
  - internal Docker-network-only exposure policy,
  - `md -> wav` first and `pdf -> wav` later as composition,
  - provider-neutral public contract guidance,
  - fail-closed GPU semantics for non-PDF TTS routes.
- Record Python runtime policy:
  - use the newest upstream-supported version,
  - treat Python `3.12` as the current proven minimum until benchmark evidence confirms newer.
- Link ADR from the new epic/story/tasks and from the v2 API/runbook surfaces that will depend on it.

## Deliverables

- [x] `docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md`
- [x] Epic/story/task cross-links synchronized.
- [x] Sidecar-only route-policy language captured in canonical docs.

## Acceptance Criteria

- [x] ADR is `accepted`, not merely proposed.
- [x] ADR explicitly rejects in-process TTS for this feature line.
- [x] ADR defines how `execution.acceleration_policy` behaves for TTS routes in phase 1.
- [x] ADR defines phase-1 exclusions: voice cloning, Swedish guarantee, public sidecar exposure.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Published ADR-0006 and linked it from Epic 07, Story 22, the first TTS tasks, and the
  sidecar-backed `md -> wav` contract outline.
- Locked the planning decision that TTS is sidecar-only from day one and that phase-1 TTS routes
  are `gpu_required` and fail-closed.

## Validation Evidence (2026-03-06)

- `pdm run validate-tasks` (pass: `Validated 114 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=144 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
