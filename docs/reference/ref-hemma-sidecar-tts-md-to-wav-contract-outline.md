---
type: reference
id: REF-hemma-sidecar-tts-md-to-wav-contract-outline
title: Hemma Sidecar TTS md to wav Contract Outline
status: active
created: '2026-03-06'
updated: '2026-03-06'
owners:
  - platform
tags:
  - reference
  - tts
  - contract
  - md-to-wav
  - sidecar
links:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/tasks/task-80-publish-md-to-wav-v2-contract-for-sidecar-backed-tts.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/converters/multi_format_conversion_service_api_v2.md
---

## Purpose

Capture the recommended phase-1 `md -> wav` v2 contract shape before implementation work begins,
so the team can review field boundaries and GPU-governance semantics without jumping straight into
code changes.

## Recommended Route

- `source.format = "md"`
- `conversion.output_format = "wav"`
- sidecar-backed TTS only

`pdf -> wav` is intentionally deferred until `md -> wav` exists and can be composed over the
existing checkpointed `pdf -> md` pipeline.

## Recommended Request Shape

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "lesson.md",
    "format": "md"
  },
  "conversion": {
    "output_format": "wav",
    "css_filenames": [],
    "pdf_layout": null,
    "template": null,
    "reference_docx_filename": null
  },
  "tts_options": {
    "voice": "teacher-clear-01",
    "language": "en",
    "style_instructions": "Read clearly as a teacher with a moderate pace.",
    "normalize_for_speech": "auto"
  },
  "execution": {
    "acceleration_policy": "gpu_required",
    "priority": "normal",
    "document_timeout_seconds": 1800
  },
  "retention": {
    "pin": false
  }
}
```

## Recommended `tts_options` Fields

Phase 1 fields:

- `voice`:
  - required string
  - provider-neutral preset voice identifier
- `language`:
  - required string
  - caller intent only; runtime validates against the configured sidecar/profile
- `style_instructions`:
  - optional string
  - bounded length
- `normalize_for_speech`:
  - enum: `auto | strict`
  - `auto`: service-owned speech cleanup rules
  - `strict`: more aggressive suppression of tables/URLs/noise

Fields intentionally excluded from phase 1:

- model ids or model sizes
- provider-specific task names
- chunk-size tuning knobs
- reference-audio / voice-clone inputs
- pronunciation lexicon uploads

## Execution Policy

For phase-1 TTS routes:

- `execution` is required
- only `acceleration_policy="gpu_required"` is accepted
- `gpu_prefer` and `cpu_only` are rejected

This keeps TTS aligned with the repository's fail-closed GPU policy.

## Success Result Expectations

Artifact:

- filename suffix: `.wav`
- content type: `audio/wav`

Recommended additions to `result.conversion_metadata`:

- `backend_used`:
  - stable bounded value such as `tts_sidecar`
- `acceleration_used`:
  - `cuda` when sidecar GPU execution succeeds
- `tts_voice_used`
- `tts_language_used`

The public contract should avoid exposing sidecar vendor internals.

## Progress Semantics

Phase 1 should avoid introducing new numeric progress fields prematurely.

Recommended stage markers:

- `queued`
- `starting`
- `normalizing`
- `synthesizing`
- `packaging`
- `succeeded`
- `failed`
- `canceled`

Existing PDF-only page counters remain `null` for `md -> wav`.

## Error Policy

Recommended deterministic failures:

- TTS route requested while sidecar feature is disabled
- sidecar unavailable or unhealthy
- unsupported language for the configured sidecar/profile
- unsupported acceleration policy
- invalid `tts_options`

## Phase-1 Exclusions

- voice cloning
- Swedish quality guarantee
- public compressed-format contract
- direct public sidecar access

These may be revisited after Hemma benchmark evidence exists.
