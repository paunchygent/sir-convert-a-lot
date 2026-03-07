---
id: epic-07-hemma-sidecar-tts-audio-artifact-delivery
title: Hemma sidecar TTS audio artifact delivery
type: epic
status: in_progress
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-80-publish-md-to-wav-v2-contract-for-sidecar-backed-tts.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md
  - docs/backlog/tasks/task-92-promote-chatterbox-sidecar-to-hemma-production-candidate-and-mark-experimental-sidecars-explicitly.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
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

Major capability increment managed through linked stories.

## Goal

Deliver sidecar-backed text-to-speech on Hemma through the canonical v2 async job contract,
starting with `md -> wav` and explicitly forbidding in-process TTS dependencies in the main
Sir Convert-a-Lot service image.

This epic is complete only when:

- the sidecar-only architecture is decision-locked in an accepted ADR,
- Hemma compatibility and output-format evidence is captured on the real R9700/gfx1201 host,
- the `md -> wav` v2 contract is published with fail-closed GPU semantics for TTS routes,
- implementation tasks are sequenced so `pdf -> wav` composes on top of `md -> wav`
  rather than becoming the first delivery slice.

## In Scope

- Architecture and governance:
  - accepted ADR for sidecar-only TTS,
  - explicit prohibition on adding model/runtime TTS dependencies to the main service image,
  - sidecar runs on the internal Docker network only.
- Hemma runtime validation:
  - benchmark and smoke evidence on the actual AMD Radeon AI PRO R9700 (`gfx1201`) host,
  - Python runtime policy of "newest supported upstream version"; treat Python `3.12` as the
    current minimum proven target until benchmark evidence confirms a newer version.
- Backend selection for cloning-enabled follow-on work:
  - benchmark OpenVoice V2 as the Swedish-probable cloning candidate,
  - benchmark F5-TTS as the active comparison cloning backend,
  - keep XTTS-v2 as a documented deferred follow-up candidate,
  - benchmark MMS Swedish as the pronunciation-only control baseline.
- Contract-first API design:
  - publish provider-neutral `md -> wav` v2 request/response semantics,
  - define fail-closed acceleration policy behavior for non-PDF TTS routes,
  - define output artifact/content-type semantics and stage markers.
- Internal multi-backend reuse:
  - standardize one internal sidecar capability contract before cloning-capable backend benchmarks
    begin,
  - keep backend-native runtime differences behind adapter-specific sidecar images.
- Delivery sequencing:
  - `md -> wav` first,
  - `pdf -> wav` later as a composition route over the existing checkpointed PDF-to-Markdown stage.

## Out of Scope

- In-process TTS inside the existing Python 3.11 service runtime.
- Direct public exposure of the TTS sidecar.
- Voice cloning, voice-reference uploads, or teacher-voice persistence in phase 1.
- Swedish TTS quality guarantees in phase 1.
- Reusing Story 07's legacy auxiliary-converter assumptions as the canonical design surface.

## Stories

1. `docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md`
1. `docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md`

## Tasks (Ordered Planning and Execution Checklist)

Execution rule:

- Publish the architecture decision first.
- Publish the provider-neutral `md -> wav` contract next.
- Benchmark the chosen sidecar stack on Hemma before implementation defaults are locked.

1. `docs/backlog/tasks/task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy.md`
1. `docs/backlog/tasks/task-80-publish-md-to-wav-v2-contract-for-sidecar-backed-tts.md`
1. `docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md`
1. `docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md`
1. `docs/backlog/tasks/task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md`
1. `docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md`
1. `docs/backlog/tasks/task-92-promote-chatterbox-sidecar-to-hemma-production-candidate-and-mark-experimental-sidecars-explicitly.md`

Deferred follow-up:

1. `docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md`

## Acceptance Criteria

- [x] Accepted ADR records sidecar-only TTS, non-PDF GPU governance, and the Python runtime policy.
- [x] Accepted follow-on ADR records the reusable internal sidecar capability contract for
  OpenVoice V2, F5-TTS, and MMS Swedish benchmark work.
- [ ] Hemma benchmark task records sidecar startup/runtime evidence on the R9700 and captures
  `wav` output plus compressed-format availability.
- [x] `md -> wav` contract outline is published and linked from the epic/story/task chain.
- [x] Epic sequencing explicitly makes `md -> wav` the first implementation route and
  `pdf -> wav` a later composition step.

## Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
