---
trigger: model_decision
rule_id: RULE-035
title: Docling PDF Conversion Guidance
status: active
created: '2026-02-11'
updated: '2026-03-02'
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

- Sir Convert-a-Lot **service API v2** is the canonical conversion surface.
- Runtime enforces GPU-first governance for PDF inputs (Docling is GPU-only by invariant).
- Docling strategy/config behavior must remain contract-compatible (v2 job spec fields).

## Rules

- Keep Docling policy behind canonical v2 job spec fields:
  - `pdf_options.backend_strategy`
  - `pdf_options.ocr_mode`
  - `pdf_options.table_mode`
  - `pdf_options.normalize`
  - `execution.acceleration_policy`
- Never add Docling-only side channels that bypass the v2 contract.
- Any CPU fallback policy change requires explicit ADR update.
- Performance or quality changes must update benchmark/task docs before rollout.
- Hemma ROCm note:
  - Docling documentation does not explicitly name ROCm support; validate on Hemma and record evidence before treating GPU acceleration as guaranteed.
