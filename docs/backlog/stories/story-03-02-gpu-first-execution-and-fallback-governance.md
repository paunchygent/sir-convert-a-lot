---
id: '003b-gpu-first-execution-and-fallback-governance-story'
title: 'GPU-first execution and fallback governance'
type: 'story'
status: 'proposed'
priority: 'critical'
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - 'docs/backlog/epics/epic-03-unified-conversion-service.md'
  - 'docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md'
  - 'docs/converters/pdf_to_md_service_api_v1.md'
labels:
  - 'gpu'
  - 'performance'
  - 'governance'
---
# GPU-first execution and fallback governance

## Objective

Guarantee that initial service behavior validates and uses GPU execution as the default path for heavy PDF conversion workloads, with no silent degradation.

## Scope

- Enforce GPU-required behavior for initial rollout.
- Define benchmark protocol and evidence capture.
- Define explicit change control for enabling CPU fallback later.

## Acceptance Criteria

1. Service rejects GPU-required jobs with explicit `gpu_not_available` when GPU cannot run.
2. No implicit CPU fallback is present in initial rollout paths.
3. Benchmark report exists for agreed corpus with:
  - latency distribution
  - throughput for batch runs
  - resource profile summary
4. Any fallback policy change requires explicit decision update (ADR amendment or new ADR).
5. Conversion result metadata includes `acceleration_used` for auditability.

## Test Requirements

- GPU-available path tests:
  - successful completion on benchmark inputs.
- GPU-unavailable path tests:
  - deterministic failure code and envelope.
- Metadata tests:
  - `acceleration_used` populated and correct.

## Done Definition

- GPU-first behavior proven by tests and benchmark artifacts.
- Governance rule for fallback changes documented and linked from active task docs.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
