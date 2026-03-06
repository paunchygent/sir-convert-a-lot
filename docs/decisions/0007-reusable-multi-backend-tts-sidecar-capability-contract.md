---
type: decision
id: ADR-0007
title: Reusable Multi-Backend TTS Sidecar Capability Contract
status: accepted
created: 2026-03-06
updated: 2026-03-06
owners:
  - platform
tags:
  - adr
  - tts
  - sidecar
  - capabilities
  - hemma
  - v2
links:
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Purpose

Define the internal sidecar capability contract that lets Sir Convert-a-Lot reuse the same
sidecar integration model across multiple TTS backends without coupling the public v2 API to one
model family or one vendor runtime.

## Status

- Accepted
- Date: 2026-03-06

## 1. Problem and Context

ADR-0006 locked three decisions:

1. TTS is sidecar-only.
1. The public v2 API stays provider-neutral.
1. The main Sir Convert-a-Lot service image must not absorb TTS runtime/model dependencies.

That architecture is sufficient for one benchmarked backend, but not yet for the next phase where
we need to compare and potentially reuse multiple TTS stacks on Hemma:

- OpenVoice V2 as the primary Swedish-probable cloning candidate,
- XTTS-v2 as the comparison cloning backend,
- MMS Swedish as the direct-pronunciation control baseline.

Those backends do not share one native runtime contract. They differ in:

- startup/runtime dependencies,
- cache/storage patterns,
- voice catalogs,
- cloning inputs,
- output-format behavior,
- language-support claims.

Without one Sir-owned internal capability contract, each candidate would force bespoke service
integration logic and make backend replacement expensive.

## 2. Decision

Adopt a **reusable adapter contract** for all TTS sidecars used by Sir Convert-a-Lot.

Key rules:

1. Sir Convert-a-Lot integrates with one **internal adapter contract**, not with backend-native
   APIs directly.
1. Each backend gets its own sidecar image/runtime as needed; we do **not** standardize on one
   universal mega-runtime that must host every TTS stack.
1. Every candidate backend must surface a stable **capability document** that Sir Convert-a-Lot
   can use for validation and routing.
1. Backend-specific concepts are normalized at the sidecar boundary before they reach the main
   service runtime.
1. Benchmarks starting with `T81` must evaluate candidate backends against this adapter contract,
   even if the sidecar uses backend-native libraries internally.

## 3. Sidecar Shape

### 3.1 One backend per sidecar

Each deployable sidecar instance represents exactly one normalized backend profile, for example:

- `openvoice_v2`
- `xtts_v2`
- `mms_tts_swe`

This keeps dependency isolation strong and rollback predictable.

### 3.2 Internal-only exposure

The sidecar remains internal to the Docker network on Hemma. Public clients continue to interact
only with the canonical Sir Convert-a-Lot v2 service lanes.

### 3.3 Public/API separation

The public v2 API remains provider-neutral. Backend identity is runtime-owned and surfaced in
bounded metadata, not chosen directly by public clients through model ids.

## 4. Required Internal Endpoints

Every TTS sidecar adapter must implement these internal endpoints:

### `GET /health`

Purpose:

- liveness/readiness for the adapter as a whole

Required response fields:

- `status`
- `backend_id`
- `backend_version`
- `ready`

### `GET /capabilities`

Purpose:

- machine-readable contract for Sir Convert-a-Lot and benchmark harnesses

Required response shape:

```json
{
  "backend_id": "openvoice_v2",
  "backend_version": "2.x",
  "runtime": {
    "python_version": "3.12.12",
    "gpu_required": true,
    "supports_rocm": true,
    "network_scope": "internal_only"
  },
  "cache": {
    "cache_family": "huggingface",
    "host_root": "/srv/scratch/sir-convert-a-lot/cache/huggingface",
    "container_root": "/cache/huggingface"
  },
  "synthesis": {
    "output_formats": ["wav"],
    "sample_rates_hz": [24000],
    "supports_streaming": false
  },
  "voice": {
    "modes": ["preset", "reference_clone"],
    "reference_transcript_required": true,
    "reference_audio_required": true
  },
  "languages": [
    {
      "code": "sv",
      "support_level": "cross_lingual_claimed"
    }
  ]
}
```

Rules:

- `support_level` must distinguish:
  - `official`
  - `cross_lingual_claimed`
  - `experimental`
  - `unsupported`
- cloning support must be explicit
- cache roots must be explicit
- output formats and sample rates must be explicit

### `GET /voices`

Purpose:

- list preset voices when the backend supports them

Rules:

- cloning-capable backends may still return zero preset voices
- response must be stable and bounded

### `POST /synthesize`

Purpose:

- normalized synthesis call used by Sir Convert-a-Lot

Required request semantics:

- one normalized metadata payload
- optional reference-audio attachment for cloning
- one requested output format
- explicit language intent
- explicit voice mode

Recommended normalized request fields:

```json
{
  "text": "Hej och valkommen.",
  "language": "sv",
  "voice_mode": "reference_clone",
  "preset_voice_id": null,
  "style_instructions": "Read clearly as a teacher.",
  "normalization_profile": "auto",
  "reference_transcript": "Hello and welcome."
}
```

If cloning is requested:

- `reference_audio` is required as an attached binary input
- `reference_transcript` is required when the backend declares it mandatory in `/capabilities`

Required response semantics:

- success returns binary audio plus content type
- failure returns structured JSON with stable error codes

## 5. Cache and Model Storage Policy

The sidecar contract must preserve Hemma's persistent-cache discipline.

### 5.1 Canonical host storage

- No backend may rely on container-local model downloads as its steady-state path.
- Models and runtime caches must live under the canonical Sir Convert-a-Lot cache hierarchy on
  Hemma.

### 5.2 Cache families

- Hugging Face-backed backends must reuse the canonical shared HF cache root:
  - `/srv/scratch/sir-convert-a-lot/cache/huggingface`
- Docker-restricted hosts may expose that canonical cache through the approved home-mount
  compatibility path:
  - `/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface`
- Non-Hugging-Face backends may define another cache family, but they must still declare:
  - canonical host root
  - container mount root
  - reuse strategy

### 5.3 Capability visibility

Every backend must declare its cache family/root in `/capabilities` so runtime truth and benchmark
reports can confirm that cache reuse is working.

## 6. Metadata Normalization Rules

Sir Convert-a-Lot may record bounded backend metadata for completed jobs, but the public contract
must not leak backend-native tuning surfaces.

Recommended normalized conversion metadata keys:

- `backend_used`
- `backend_profile`
- `tts_voice_mode`
- `tts_voice_used`
- `tts_language_used`
- `acceleration_used`

Forbidden public contract patterns:

- raw model ids
- backend-native task names
- backend-native compile/runtime tuning knobs

## 7. Benchmarking Rules for `T81+`

Tasks `T81`, `T82`, and `T83` must benchmark candidate backends through the reusable sidecar
contract, not only through backend-native library calls.

Each benchmark must prove:

- startup on Hemma,
- internal network reachability from Sir Convert-a-Lot,
- cache reuse under the canonical host storage pattern,
- capability reporting via `GET /capabilities`,
- synthesis through `POST /synthesize`,
- artifact capture for listening review.

For cloning-capable backends, each benchmark must also prove:

- reference-audio input handling,
- transcript requirement truth,
- Swedish sample synthesis from a teacher reference clip.

## 8. Consequences

Positive:

- keeps the public v2 API stable while backend experimentation continues
- avoids binding the main service runtime to one vendor API
- makes backend replacement and comparison operationally realistic
- fits Hemma's persistent cache discipline

Tradeoffs:

- requires one thin adapter layer per backend family
- adds one more internal contract to maintain
- pushes capability normalization work earlier into benchmark implementation

## 9. Follow-Up

- `T81` implements the first benchmark against this contract for OpenVoice V2.
- `T82` reuses the same contract for XTTS-v2.
- `T83` uses the same contract for MMS Swedish while marking cloning as unsupported in
  capabilities.
- Later implementation tasks for `md -> wav` should integrate with this contract rather than with
  any backend-native HTTP surface directly.
