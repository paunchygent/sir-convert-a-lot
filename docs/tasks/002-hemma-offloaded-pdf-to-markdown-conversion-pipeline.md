---
id: 002-hemma-offloaded-pdf-to-markdown-conversion-pipeline
title: Hemma offloaded PDF-to-Markdown conversion pipeline
type: task
status: proposed
priority: high
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/tasks/003-unified-conversion-service-epic.md
  - .agents/rules/030-conversion-workflows.md
  - .agents/rules/035-docling-pdf-conversion.md
  - scripts/converters/convert_pdf_to_md.py
  - scripts/converters/convert_pdf_to_md_advanced.py
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md
labels:
  - research-ingestion
  - pdf-to-markdown
  - hemma-offload
  - llm-judge
---

## Objective

Build a robust, test-covered PDF-to-Markdown conversion pipeline that can run remotely on Hemma
and be triggered from local development so research-paper ingestion does not saturate the laptop.

## Context

Current conversion utilities are split across repos and are not yet standardized for:

- noisy/scanned research PDFs,
- deterministic quality checks,
- remote execution on Hemma with a stable command/API surface.

Relevant existing assets:

- Existing local converters:
  - `scripts/converters/convert_pdf_to_md.py` (PyMuPDF)
  - `scripts/converters/convert_pdf_to_md_advanced.py` (Docling)
- Existing command aliases:
  - `pdm run convert:pdf-md`
  - `pdm run convert:pdf-md-advanced`

Platform alignment:

- Heavy conversion workloads should run remotely where practical.
- Local ergonomics should remain `pdm run ...` from repo root.

Docling acceleration note (decision-relevant):

- Docling supports accelerator configuration with CPU/CUDA/MPS options.
- ROCm compatibility for Hemma runtime is not assumed and must be validated explicitly.

## Plan

### Phase 0 - Contract and scope freeze (docs-as-code first)

1. Define the governing conversion contract:

- input modes (single PDF, directory, recursive),
- output layout (`.md`, optional sidecar artifacts),
- metadata header schema,
- failure policy (`fail-fast` vs `best-effort` batch),
- asynchronous job state model (`queued`, `running`, `succeeded`, `failed`, `canceled`),
- result and error payload schema.

1. Lock remote architecture target to HTTP API first (not tunnel/SSH-first orchestration).
1. Publish and freeze v1 API schema before implementation:

- `docs/converters/pdf_to_md_service_api_v1.md`
- async-create endpoint with optional bounded wait semantics (no separate sync endpoint),
- authentication and idempotency semantics,
- error model and queue-compatible `JobSpec` / `JobResult`.

1. Add ADR for conversion service boundaries and async API contract before implementation:

- `docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md`
- lock decisions for endpoint shape, auth, storage v1, retention policy.

1. Lock acceleration policy for Phase 0:

- GPU-first is the explicit default objective.
- CPU fallback is disabled until GPU exploration/benchmark gate is completed and documented.

### Phase 1 - Robust local converter foundation

1. Consolidate a single canonical converter entrypoint in this repo with backend strategy:

- backend A: PyMuPDF/PyMuPDF4LLM default path for speed + LLM-oriented markdown,
- backend B: Docling high-fidelity path for complex tables/figures,
- backend fallback when backend initialization fails.

1. Add deterministic cleanup/normalization pipeline for noisy PDFs:

- whitespace normalization,
- heading/section heuristics with bounded rules,
- table and figure handling policy,
- scanned-PDF OCR toggle behavior.

1. Emit stable conversion metadata (source path, backend, timestamp, options fingerprint).

### Phase 2 - Test hardening

1. Build fixture set for representative research PDFs:

- digital-native paper,
- scanned/noisy paper,
- multi-column + tables,
- image-heavy pages.

1. Add unit tests for normalization and heading/table logic.
1. Add integration tests for end-to-end conversion outputs with assertions on:

- non-empty markdown,
- expected section/table presence,
- deterministic metadata header fields.

1. Add regression fixtures for previously failing/noisy documents.
1. Add contract tests for API response schema and job state transitions.

### Phase 3 - Hemma HTTP service deployment (primary path)

1. Package converter core and API server as dedicated container profile for Hemma.
1. Implement async HTTP endpoints:

- `POST /v1/convert/jobs` (create job),
- `GET /v1/convert/jobs/{job_id}` (status),
- `GET /v1/convert/jobs/{job_id}/result` (artifacts/metadata),
- `POST /v1/convert/jobs/{job_id}/cancel` (optional).

1. Persist job metadata/artifacts in a storage layout that is transport-agnostic.
1. Add client command wrappers in this repo that call HTTP endpoints.
1. Record operational limits:

- CPU/memory profile,
- timeout policy,
- expected throughput by document size/class.

1. Validate local->tunnel->Hemma end-to-end conversion flow on sample corpus.

### Phase 3.5 - Queue-ready architecture constraints (future Option 3)

1. Keep conversion core independent from transport and execution engine:

- HTTP handler should only validate request, enqueue/dispatch, and return job IDs.
- Worker entrypoint should consume a job spec and produce standardized artifacts.

1. Define `JobSpec` and `JobResult` as versioned contracts reusable by both:

- in-process async executor (Option 2),
- external queue worker (Option 3).

1. Add idempotency key support for job creation to make future queue retries safe.
1. Add tracing/correlation IDs in all job lifecycle events.

### Phase 4 - GPU decision gate (Docling on Hemma)

1. Validate Docling accelerator behavior on Hemma hardware/runtime.
1. Gate outcomes:

- Start with GPU-first default policy and no silent CPU fallback.
- If GPU path is supported and stable: keep GPU as default.
- Only after explicit benchmark evidence and decision update:
  - allow CPU fallback policy for resilience,
  - document rationale (e.g., runtime mismatch) and impact.

1. Capture benchmark evidence (latency, memory, quality) for CPU vs accelerator mode.

### Phase 5 - Cross-repo local availability

1. Define one canonical local tool surface (`pdf2md` CLI contract) and keep thin repo wrappers.
1. Keep current aliases (`convert:pdf-md`, `convert:pdf-md-advanced`) as compatibility wrappers
   over the canonical entrypoint.
1. Document synchronization strategy to avoid drift between repos.

### Phase 6 - Post-stabilization consolidation and cleanup

1. Define stabilization gate for cleanup:

- async API contract frozen and versioned,
- noisy/scanned regression suite green,
- Hemma deployment validated on representative corpus.

1. Remove redundant converter implementations and repo-local drift:

- deprecate/remove duplicate converter CLI surfaces in `huledu-reboot`,
- keep only thin wrappers that call canonical CLI/API contract.

1. Publish one cohesive and versioned converter surface:

- versioned CLI/API contract (`v1`),
- changelog + migration notes for compatibility aliases and removals.

1. Enforce canonical ownership in docs:

- mark this repo as source of truth for conversion logic,
- keep other repos integration-only for conversion workflows.

## Success Criteria

- A canonical PDF->MD command exists in this repo and is test-covered.
- Conversion pipeline handles noisy/scanned PDFs with documented fallback behavior.
- Hemma HTTP conversion service is operational and callable from local machine.
- Benchmark report exists for backend choices (including Docling accelerator decision gate).
- GPU-first default policy is enforced during initial rollout; any CPU fallback behavior is
  explicitly decision-gated and documented.
- API/transport boundaries support future queue-worker refactor without client contract breakage.
- Cross-repo usage is documented with one canonical CLI/HTTP contract + thin wrappers.
- Redundant converter implementations are removed after stabilization; only canonical CLI/API
  and compatibility wrappers remain.
- Required quality and docs validations pass:
  - `pdm run format`
  - `pdm run lint`
  - `pdm run typecheck`
  - `pdm run test`

## Related

- `.agents/rules/030-conversion-workflows.md`
- `.agents/rules/035-docling-pdf-conversion.md`
- `scripts/converters/convert_pdf_to_md.py`
- `scripts/converters/convert_pdf_to_md_advanced.py`

## Checklist

- [ ] Canonical converter entrypoint implemented
- [ ] Noisy/scanned PDF fixtures added
- [ ] Unit + integration tests added
- [ ] Hemma HTTP service profile added
- [ ] HTTP async job contract implemented
- [ ] Queue-compatible `JobSpec`/`JobResult` contract defined
- [ ] Local client invocation against HTTP endpoint verified
- [ ] Docling accelerator decision gate documented
- [ ] Phase 0 v1 API schema + ADR published and linked
- [ ] GPU-first policy enforced; CPU fallback enabled only after decision gate
- [ ] Post-stabilization cleanup completed (redundant converters removed, canonical surface only)
- [ ] Versioned converter contract + migration notes published
- [ ] Commands documented in repo docs
- [ ] `pdm run format` / `pdm run lint` / `pdm run typecheck` / `pdm run test` executed
