---
type: story
id: ST-SIRCON-02-02
title: Auxiliary converters parity (image OCR extract + text-to-speech)
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-02
links:
  decisions: []
acceptance_criteria:
- OCR extraction works for a representative fixture image and emits deterministic
  text output.
- TTS supersession is explicit through links to Epic 07, Story 22, and ADR-0006.
- All remaining routes in scope are documented, including required environment variables
  and local system dependencies.
- Manifest semantics for these routes are documented and deterministic.
retired_ids:
- story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech
---

## Context

## Epic Contract Slice

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review

## Historical Source Content

Implementation slice with acceptance-driven scope.

### Objective

Offer the legacy “auxiliary converter” surfaces (image OCR extraction and text-to-speech)
through canonical Sir Convert-a-Lot planning surfaces while preserving a single current TTS path.

Supersession note:

- Image OCR extraction remains in scope for this story.
- TTS planning in this story is superseded by Epic 07 / Story 22 because TTS now requires a
  Hemma sidecar architecture and a v2 service contract rather than a thin local auxiliary command.

### Scope

- Image OCR extraction:
  - support `image -> txt` for common image types,
  - explicitly document system dependencies (Tesseract),
  - deterministic output naming and manifest integration.
- Text-to-speech:
  - superseded by `docs/backlog/epics/epic-sircon-04-hemma-sidecar-tts-audio-artifact-delivery.md`,
  - canonical planning path is `docs/backlog/stories/st-sircon-04-01-hemma-sidecar-tts-audio-artifact-delivery.md`,
  - no local credential-based auxiliary TTS flow is planned from this story.
- CLI integration:
  - image OCR should remain consistent with `convert-a-lot` routing,
  - TTS CLI shape is deferred to Epic 07 after the sidecar-backed v2 contract is implemented.

### Acceptance Criteria

- [ ] OCR extraction works for a representative fixture image and emits deterministic text output.
- [ ] TTS supersession is explicit through links to Epic 07 / Story 22 / ADR-0006.
- [ ] All remaining routes in scope are documented including required env vars and local system
  dependencies.
- [ ] Manifest semantics for these routes are documented and deterministic.

### Test Requirements

- [ ] Unit tests for input validation and deterministic output naming.
- [ ] OCR tests are either fixture-based (if Tesseract available) or clearly scoped as optional.
- [ ] TTS tests mock external API calls and verify error codes when API key is missing.

### Done Definition

This story remains the planning home for legacy image OCR parity only. TTS is governed by Epic 07
and no longer has an ambiguous local auxiliary-converter design path.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
