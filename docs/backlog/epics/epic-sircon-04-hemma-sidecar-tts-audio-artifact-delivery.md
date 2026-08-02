---
type: epic
id: EPIC-SIRCON-04
title: Hemma sidecar TTS audio artifact delivery
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
links:
  decisions: []
outcome: Hemma sidecar TTS audio artifact delivery
retired_ids:
- epic-07-hemma-sidecar-tts-audio-artifact-delivery
---

## Scope

## Epic Contract

## ADR Coverage

## Contract Inputs

## Stories

## Epic Verification Plan

## Exceptions And Follow-Ups

## Risks

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Epic Closeout Review

## Historical Source Content

Major capability increment managed through linked stories.

### Goal

Deliver sidecar-backed text-to-speech on Hemma through the canonical v2 async job contract,
starting with `md -> wav` and explicitly forbidding in-process TTS dependencies in the main
Sir Convert-a-Lot service image.

This epic is complete only when:

- the sidecar-only architecture is decision-locked in an accepted ADR,
- Hemma compatibility and output-format evidence is captured on the real R9700/gfx1201 host,
- the `md -> wav` v2 contract is published with fail-closed GPU semantics for TTS routes,
- implementation tasks are sequenced so `pdf -> wav` composes on top of `md -> wav`
  rather than becoming the first delivery slice.

### In Scope

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
- Parallel upstream model work:
  - keep Sir-owned Qwen Swedish fine-tuning under Epic 08 as a separate
    training/model-lifecycle lane,
  - treat that lane as an upstream model-candidate source for future sidecar
    evaluation rather than as a replacement for Epic 07 scope.
- Delivery sequencing:
  - `md -> wav` first,
  - `pdf -> wav` later as a composition route over the existing checkpointed PDF-to-Markdown stage.

### Out of Scope

- In-process TTS inside the existing Python 3.11 service runtime.
- Direct public exposure of the TTS sidecar.
- Voice cloning, voice-reference uploads, or teacher-voice persistence in phase 1.
- Swedish TTS quality guarantees in phase 1.
- Sir-owned Qwen Swedish fine-tuning lifecycle work, which now lives in Epic 08.
- Reusing Story 07's legacy auxiliary-converter assumptions as the canonical design surface.

### Stories

1. `docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md`
1. `docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md`

### Tasks (Ordered Planning and Execution Checklist)

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

### Acceptance Criteria

- [x] Accepted ADR records sidecar-only TTS, non-PDF GPU governance, and the Python runtime policy.
- [x] Accepted follow-on ADR records the reusable internal sidecar capability contract for
  OpenVoice V2, F5-TTS, and MMS Swedish benchmark work.
- [ ] Hemma benchmark task records sidecar startup/runtime evidence on the R9700 and captures
  `wav` output plus compressed-format availability.
- [x] `md -> wav` contract outline is published and linked from the epic/story/task chain.
- [x] Epic sequencing explicitly makes `md -> wav` the first implementation route and
  `pdf -> wav` a later composition step.

### Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
