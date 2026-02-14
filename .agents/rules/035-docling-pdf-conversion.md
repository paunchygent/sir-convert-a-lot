---
trigger: model_decision
rule_id: RULE-035
title: Docling PDF Conversion Guidance
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - pdf
  - docling
scope: repo
---

## Purpose

Use Docling-oriented settings when high-fidelity PDF understanding is required
(complex layout, tables, citations, technical structures).

## Current Platform Context

- Sir Convert-a-Lot v1 contract is the canonical surface.
- Runtime currently enforces GPU-first governance policy from ADR 0001.
- Docling strategy/config behavior must remain contract-compatible.

## Rules

- Keep Docling policy behind canonical job spec fields (`backend_strategy`, `ocr_mode`, `table_mode`).
- Never add Docling-only side channels that bypass the v1 contract.
- Any CPU fallback policy change requires explicit ADR update.
- Performance or quality changes must update benchmark/task docs before rollout.
- Hemma ROCm note:
  - Docling documentation does not explicitly name ROCm support; validate on Hemma and record evidence before treating GPU acceleration as guaranteed.
