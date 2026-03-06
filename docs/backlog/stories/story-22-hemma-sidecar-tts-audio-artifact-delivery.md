---
id: story-22-hemma-sidecar-tts-audio-artifact-delivery
title: Hemma sidecar TTS audio artifact delivery
type: story
status: in_progress
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech.md
  - docs/backlog/tasks/task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-80-publish-md-to-wav-v2-contract-for-sidecar-backed-tts.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/reference/ref-hemma-sidecar-tts-md-to-wav-contract-outline.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - tts
  - sidecar
  - audio
  - hemma
  - v2
---
Implementation slice with acceptance-driven scope.

## Objective

Lock the next Sir Convert-a-Lot audio feature around a Hemma sidecar TTS architecture and publish
the first implementation slice as a provider-neutral `md -> wav` v2 job contract.

## Scope

- Sidecar-only architecture:
  - the main Sir Convert-a-Lot service remains free of TTS model/runtime dependencies,
  - TTS is served through an internal Docker-network sidecar on Hemma,
  - no public direct sidecar exposure.
- Contract-first sequence:
  - publish ADR and route policy before implementation,
  - benchmark compatibility on the real Hemma R9700/gfx1201 host,
  - publish `md -> wav` request/response semantics before code changes.
- Product boundary for phase 1:
  - English-first,
  - preset voices only,
  - `wav` contract first,
  - `pdf -> wav` deferred to a follow-up composition slice after `md -> wav` is stable.
- Governance:
  - fail-closed GPU behavior for TTS routes,
  - Python runtime policy of "newest supported upstream version" with Python `3.12` as the
    current proven floor until Task 79 verifies a newer target,
  - provider-neutral public contract (no Qwen-specific task taxonomy in v2).

## Tasks (Ordered)

1. `docs/backlog/tasks/task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy.md`
1. `docs/backlog/tasks/task-80-publish-md-to-wav-v2-contract-for-sidecar-backed-tts.md`
1. `docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md`

## Acceptance Criteria

- [x] ADR-0006 is accepted and explicitly forbids in-process TTS in the main service image.
- [ ] Hemma benchmark scope is concrete enough to prove sidecar viability on the live R9700 host.
- [x] `md -> wav` is the first documented implementation route and includes:
  - request/response contract,
  - output content type,
  - TTS options shape,
  - fail-closed acceleration policy behavior,
  - phase-1 language/voice limits.
- [x] Story links make it clear that Story 07's old auxiliary-converter framing is not the
  canonical architecture for TTS delivery anymore.

## Test Requirements

- [x] Docs validations pass for epic/story/task/ADR/reference additions.
- [ ] The benchmark task defines deterministic Hemma evidence artifacts and command surfaces.
- [ ] The contract task defines required API contract tests for create-job validation, result
  payloads, and artifact content type before implementation starts.

## Done Definition

The team can start implementation without reopening the architecture choice, route ordering, or
public contract shape for phase-1 TTS delivery on Hemma.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [x] Docs synchronized
