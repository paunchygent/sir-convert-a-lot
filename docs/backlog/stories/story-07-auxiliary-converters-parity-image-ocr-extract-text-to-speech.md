---
id: story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech
title: Auxiliary converters parity (image OCR extract + text-to-speech)
type: story
status: proposed
priority: medium
created: '2026-02-18'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
labels:
  - ocr
  - tts
  - auxiliary
---

Implementation slice with acceptance-driven scope.

## Objective

Offer the legacy “auxiliary converter” surfaces (image OCR extraction and text-to-speech)
through canonical Sir Convert-a-Lot planning surfaces while preserving a single current TTS path.

Supersession note:

- Image OCR extraction remains in scope for this story.
- TTS planning in this story is superseded by Epic 07 / Story 22 because TTS now requires a
  Hemma sidecar architecture and a v2 service contract rather than a thin local auxiliary command.

## Scope

- Image OCR extraction:
  - support `image -> txt` for common image types,
  - explicitly document system dependencies (Tesseract),
  - deterministic output naming and manifest integration.
- Text-to-speech:
  - superseded by `docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md`,
  - canonical planning path is `docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md`,
  - no local credential-based auxiliary TTS flow is planned from this story.
- CLI integration:
  - image OCR should remain consistent with `convert-a-lot` routing,
  - TTS CLI shape is deferred to Epic 07 after the sidecar-backed v2 contract is implemented.

## Acceptance Criteria

- [ ] OCR extraction works for a representative fixture image and emits deterministic text output.
- [ ] TTS supersession is explicit through links to Epic 07 / Story 22 / ADR-0006.
- [ ] All remaining routes in scope are documented including required env vars and local system
  dependencies.
- [ ] Manifest semantics for these routes are documented and deterministic.

## Test Requirements

- [ ] Unit tests for input validation and deterministic output naming.
- [ ] OCR tests are either fixture-based (if Tesseract available) or clearly scoped as optional.
- [ ] TTS tests mock external API calls and verify error codes when API key is missing.

## Done Definition

This story remains the planning home for legacy image OCR parity only. TTS is governed by Epic 07
and no longer has an ambiguous local auxiliary-converter design path.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
