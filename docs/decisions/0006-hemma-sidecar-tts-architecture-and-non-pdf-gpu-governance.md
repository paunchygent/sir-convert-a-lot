---
type: decision
id: ADR-0006
title: Hemma Sidecar TTS Architecture and Non-PDF GPU Governance
status: accepted
created: '2026-03-06'
updated: '2026-03-06'
owners:
  - platform
tags:
  - adr
  - tts
  - sidecar
  - hemma
  - gpu
  - v2
links:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/tasks/task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-80-publish-md-to-wav-v2-contract-for-sidecar-backed-tts.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/reference/ref-hemma-sidecar-tts-md-to-wav-contract-outline.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Status

- Accepted
- Date: 2026-03-06

## 1. Problem and Context

Sir Convert-a-Lot needs a text-to-speech feature line that works on Hemma without destabilizing the
existing v2 conversion runtime.

The current service runtime is:

- a Python `3.11` image,
- heavily coupled to Docling/Pandoc/WeasyPrint and ROCm torch pinning,
- governed by a GPU-first fail-closed policy for PDF work,
- built around async job creation and artifact retrieval.

Upstream TTS stacks point toward isolated runtimes rather than in-process embedding:

- `qwen-tts` recommends a fresh isolated environment,
- current vLLM-Omni online-serving docs assume a separate Linux/Python runtime and expose an
  OpenAI-like HTTP API.

Additionally, current v2 `execution.acceleration_policy` semantics are PDF-centric; non-PDF routes
do not yet have a fail-closed GPU contract.

## 2. Decision

Adopt the following architecture and contract rules for TTS:

1. TTS is **sidecar-only** from day one.
1. The main Sir Convert-a-Lot service image must not gain TTS model/runtime dependencies.
1. The first TTS delivery route is **`md -> wav`**, not `pdf -> wav`.
1. `pdf -> wav` is a later composition route that builds on:
   - existing checkpointed `pdf -> md`,
   - the sidecar-backed `md -> wav` contract.
1. TTS sidecars run on the **internal Docker network only**; they are not exposed as public
   internet surfaces.
1. Public v2 API fields must remain **provider-neutral**; do not expose model-specific task names
   such as `CustomVoice`, `Base`, or `VoiceDesign`.
1. Phase-1 TTS routes are **GPU-required and fail-closed**.

## 3. Python Runtime Policy

- Preferred policy: use the newest upstream-supported Python version for the sidecar runtime.
- Current proven minimum planning target: **Python `3.12`**.
- Do not standardize on Python `3.14` for this feature until Hemma benchmark evidence confirms
  that the chosen sidecar stack and dependencies support it in practice.

This policy applies to the sidecar runtime, not retroactively to the current main service image.

## 4. Architecture Rules

### 4.1 Main service

- Remains the canonical v2 API surface.
- Owns job creation, idempotency, polling/push status, artifact retention, and artifact download.
- Calls the TTS sidecar over the internal Docker network.

### 4.2 Sidecar

- Owns model/runtime concerns for TTS only.
- Exposes a narrow HTTP interface suitable for internal use.
- Must be replaceable without changing the public Sir Convert-a-Lot v2 contract.

### 4.3 Exposure

- No direct public sidecar ingress.
- Public clients continue to talk only to the canonical Sir Convert-a-Lot service lanes:
  - tunnel: `http://127.0.0.1:28085`
  - Gateway/public lane after the ADR-0009 cutover re-enables the intended
    public edge

## 5. Route Sequencing

### 5.1 Phase 1

- `md -> wav`
- English-first
- Preset voices only

### 5.2 Deferred

- `pdf -> wav`
- voice cloning/reference-audio uploads
- Swedish TTS guarantees
- compressed output as a public-contract requirement

Deferred items may be explored in benchmarks, but they are not part of phase-1 public acceptance.

## 6. Non-PDF GPU Governance

For phase-1 TTS routes:

- `execution` becomes required, even for non-PDF TTS routes.
- Only `execution.acceleration_policy="gpu_required"` is accepted.
- `gpu_prefer` and `cpu_only` are rejected for phase-1 TTS routes.
- If the sidecar is unavailable, misconfigured, or not GPU-capable, the route must fail
  deterministically rather than silently degrading.

This preserves the repository's GPU-first fail-closed philosophy while extending it beyond
PDF-origin routes.

## 7. Public Contract Policy

Phase-1 public contract design must:

- expose a provider-neutral `tts_options` shape,
- express caller intent (voice/language/style/normalization),
- avoid exposing backend-specific model taxonomy or low-level tuning knobs,
- keep chunk sizing and model variant selection runtime-owned.

## 8. Consequences

Positive:

- isolates fast-moving TTS dependencies from the main conversion service,
- makes rollback safer,
- aligns with upstream runtime expectations,
- lets the public v2 contract stay stable if the sidecar implementation changes.

Tradeoffs:

- adds a new runtime component and internal health surface,
- requires explicit benchmark work on Hemma's real GPU/runtime stack,
- requires new non-PDF GPU governance semantics in the v2 contract.

## 9. Follow-Up

- Task 79 validates sidecar compatibility and Python-version reality on Hemma.
- Task 80 publishes the `md -> wav` v2 contract.
- ADR-0007 defines the reusable internal sidecar capability contract for multi-backend TTS work.
- Later implementation tasks may integrate the sidecar and then add `pdf -> wav` composition once
  `md -> wav` is stable.
