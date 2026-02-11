---
type: reference
id: REF-story-003b-gpu-governance-benchmark-evidence
title: Story 003b GPU Governance Benchmark Evidence
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - benchmark
  - gpu
  - governance
links:
  - docs/backlog/tasks/task-05-enforce-gpu-first-lock-and-benchmark-evidence-for-story-003b.md
  - docs/backlog/stories/story-03-02-gpu-first-execution-and-fallback-governance.md
  - docs/reference/benchmark-story-003b-gpu-governance-local.json
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Purpose

Capture benchmark evidence for Story 003b GPU-first governance, including deterministic local
baseline results and the canonical Hemma execution path for production-profile validation.

## Benchmark Corpus

- Fixture set: `tests/fixtures/benchmark_pdfs/`
- Fixture count: `5` PDFs
- Total input size: `1957` bytes
- Workload type: API contract-level async conversion jobs (`POST /v1/convert/jobs` + polling)

## Stage 1 Result (Local Deterministic Baseline)

Source artifact:

- `docs/reference/benchmark-story-003b-gpu-governance-local.json`

Runtime config:

- `acceleration_policy`: `gpu_required`
- `gpu_available`: `true`
- `allow_cpu_only`: `false`
- `allow_cpu_fallback`: `false`
- `processing_delay_seconds`: `0.05`

Summary metrics:

- `total_jobs`: `5`
- `succeeded_jobs`: `5`
- `failed_jobs`: `0`
- `success_rate`: `1.0`
- `throughput_jobs_per_minute`: `920.224581`
- `latency_seconds.min`: `0.056769`
- `latency_seconds.p50`: `0.060003`
- `latency_seconds.p95`: `0.077069`
- `latency_seconds.max`: `0.081294`
- `latency_seconds.mean`: `0.063249`

Resource profile summary:

- `acceleration_observed`: `["cuda"]`
- `backend_observed`: `["docling"]`
- `fixtures_count`: `5`
- `fixtures_total_bytes`: `1957`

## Stage 2 Path (Hemma GPU Runbook Flow)

Canonical command path:

```bash
pdm run run-hemma -- /bin/bash -lc 'pdm run benchmark:story-003b --fixtures-dir tests/fixtures/benchmark_pdfs --output-json docs/reference/benchmark-story-003b-gpu-governance-hemma.json --stage hemma --data-root build/benchmarks/story-003b-hemma'
```

Tunnel validation path:

```bash
ssh hemma -L 28085:127.0.0.1:28085 -N
curl -fsS http://127.0.0.1:28085/healthz
```

Operational requirement:

- Use `docs/runbooks/runbook-hemma-devops-and-gpu.md` as the source of truth.
- Keep rollout lock active (no env-driven CPU unlock in service startup).
- If policy unlock is ever proposed, record ADR change before rollout.
