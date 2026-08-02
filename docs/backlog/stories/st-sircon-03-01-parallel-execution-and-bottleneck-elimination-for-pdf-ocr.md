---
type: story
id: ST-SIRCON-03-01
title: Parallel execution and bottleneck elimination for PDF OCR
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
epic: EPIC-SIRCON-03
links:
  decisions: []
acceptance_criteria:
- Throughput improvements are measurable and reproducible on the benchmark corpus.
- Median wall-clock for long scanned OCR jobs improves by at least 40 percent from
  baseline.
- Telemetry identifies top bottlenecks with stage-level timings and utilization evidence.
- Parallelization does not regress output determinism or API contract behavior.
- GPU-first governance remains enforced under parallel mode, with no silent CPU fallback
  and explicit concurrency caps for GPU-backed stages.
retired_ids:
- story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr
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

Reduce wall-clock conversion time and increase predictability for long OCR jobs by introducing
bounded parallel execution and evidence-driven bottleneck removal.

### Scope

- Implement bounded parallel worker pools for chunk/page processing where safe.
- Add scheduling controls to avoid GPU/CPU over-subscription and memory contention.
- Instrument stage timings and resource telemetry for OCR/layout/normalization/persist phases.
- Produce benchmark baselines and tuned profiles for long scanned PDFs on Hemma hardware.
- Publish runbook recommendations for worker counts, chunk sizes, and fallback strategy.

Guardrails:

- Hemma deploy-parity + live verification hardening (`T76`) must be completed before tuning work
  in `T72`/`T74`.
- Parallelization is opt-in behind config defaults until benchmark evidence exists.
- GPU-backed stages must have explicit concurrency caps to avoid OOM and thrash.
- Any backend-specific limitations (Docling vs PyMuPDF) must be captured in the benchmark report.

### Acceptance Criteria

- [ ] Throughput improvements are measurable and reproducible on benchmark corpus.
- [ ] Median wall-clock for long scanned OCR jobs improves by >= 40% from baseline.
- [ ] Telemetry identifies top bottlenecks with stage-level timings and utilization evidence.
- [ ] Parallelization does not regress output determinism or API contract behavior.
- [ ] GPU-first governance remains enforced under parallel mode (no silent CPU fallback, explicit
  concurrency caps for GPU-backed stages).

### Test Requirements

- [ ] Concurrency safety tests for worker pool execution and checkpoint writes.
- [ ] Regression tests for deterministic markdown output under parallel mode.
- [ ] Benchmark harness test run producing machine-readable report artifacts.
- [ ] Load tests validating stability under multiple long-running jobs.

### Done Definition

Long PDF OCR conversion performance is tuned with clear bottleneck evidence, robust parallel
execution controls, and documented operational defaults for production use.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
