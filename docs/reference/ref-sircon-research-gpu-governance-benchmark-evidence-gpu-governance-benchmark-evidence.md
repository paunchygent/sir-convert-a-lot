---
type: reference
id: REF-SIRCON-RESEARCH-gpu-governance-benchmark-evidence
title: GPU Governance Benchmark Evidence
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: research
retired_ids:
- REF-gpu-governance-benchmark-evidence
summary: GPU Governance Benchmark Evidence
---

## Research Purpose And Boundary

## Evidence And Sources

## Findings And Interpretation

## Evidence Gaps And Follow-Up

## Historical Source Content

### Purpose

Capture benchmark evidence for GPU-first governance, including deterministic local
baseline results and the canonical Hemma execution path for production-profile validation.

### Benchmark Corpus

- Fixture set: `tests/fixtures/benchmark_pdfs/`
- Fixture count: `5` PDFs
- Total input size: `1957` bytes
- Workload type: API contract-level async conversion jobs (`POST /v1/convert/jobs` + polling)

### Stage 1 Result (Local Deterministic Baseline)

Source artifact:

- `build/benchmarks/gpu-governance/benchmark-gpu-governance-local.json`

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

### Stage 2 Path (Hemma GPU Runbook Flow)

Canonical command path:

```bash
pdm run run-hemma -- /bin/bash -lc 'pdm run benchmark:gpu-governance --fixtures-dir tests/fixtures/benchmark_pdfs --output-json build/benchmarks/gpu-governance/benchmark-gpu-governance-hemma.json --stage hemma --data-root build/benchmarks/gpu-governance-hemma'
```

Tunnel validation path:

```bash
ssh hemma -L 28085:127.0.0.1:28085 -N
curl -fsS http://127.0.0.1:28085/healthz
```

Operational requirement:

- Use `docs/runbooks/run-sircon-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot.md` as the source of truth.
- Keep rollout lock active (no env-driven CPU unlock in service startup).
- If policy unlock is ever proposed, record ADR change before rollout.
