---
id: story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech
title: Auxiliary converters parity (image OCR extract + text-to-speech)
type: story
status: proposed
priority: medium
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
labels:
  - ocr
  - tts
  - auxiliary
---

Implementation slice with acceptance-driven scope.

## Objective

Offer the legacy “auxiliary converter” surfaces (image OCR extraction and text-to-speech)
through the canonical Sir Convert-a-Lot CLI, with explicit dependency and credential handling.

## Scope

- Image OCR extraction:
  - support `image -> txt` for common image types,
  - explicitly document system dependencies (Tesseract),
  - deterministic output naming and manifest integration.
- Text-to-speech:
  - support `text/md -> audio` (format(s) to be decided; maintain parity with legacy default),
  - explicit credential handling (no silent network calls without configured API key),
  - deterministic output naming and manifest integration.
- CLI integration:
  - consistent UX with `convert-a-lot` routing (or a dedicated `speak` subcommand),
  - clear error codes for missing dependencies/credentials.

## Acceptance Criteria

- [ ] OCR extraction works for a representative fixture image and emits deterministic text output.
- [ ] TTS command validates configuration before attempting network calls.
- [ ] All routes are documented including required env vars and local system dependencies.
- [ ] Manifest semantics for these routes are documented and deterministic.

## Test Requirements

- [ ] Unit tests for input validation and deterministic output naming.
- [ ] OCR tests are either fixture-based (if Tesseract available) or clearly scoped as optional.
- [ ] TTS tests mock external API calls and verify error codes when API key is missing.

## Done Definition

Auxiliary converters are accessible through Sir Convert-a-Lot with explicit dependency governance,
documented configuration, and regression coverage.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
