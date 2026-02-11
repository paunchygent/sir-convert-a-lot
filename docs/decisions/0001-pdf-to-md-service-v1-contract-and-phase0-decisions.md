---
type: decision
id: ADR-0001
title: PDF-to-MD Service v1 Contract and Phase 0 Decisions
status: accepted
created: 2026-02-11
updated: 2026-02-11
owners:
  - platform
tags:
  - adr
  - api
  - governance
links:
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/backlog/stories/story-03-01-lock-v1-contract-and-no-hassle-local-dev-ux.md
---
# ADR 0001: PDF-to-MD Service v1 Contract and Phase 0 Decisions

## Status

- Accepted
- Date: 2026-02-11

## Context

PDF-to-Markdown conversion is currently split across scripts and repos.  
We need one canonical contract for Hemma-offloaded conversion that is:

- robust for noisy/scanned research PDFs,
- stable for local and remote clients,
- compatible with future queue-worker execution without API breakage.

The governing implementation task is:
- `docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md`

The normative API schema is:
- `docs/converters/pdf_to_md_service_api_v1.md`

## Decision

1. Endpoint model
- v1 uses async job endpoints only:
  - `POST /v1/convert/jobs`
  - `GET /v1/convert/jobs/{job_id}`
  - `GET /v1/convert/jobs/{job_id}/result`
  - `POST /v1/convert/jobs/{job_id}/cancel`
- No separate sync endpoint in v1.
- Small-file convenience is handled by `wait_seconds` on job creation.

2. Auth model
- Hemma service remains internal-network scoped.
- `X-API-Key` is mandatory on every endpoint.

3. Storage model (v1)
- Filesystem backend is canonical in v1.
- Storage adapter boundary is mandatory so object storage can be introduced without API changes.

4. Retention model
- Raw uploads TTL: 24h.
- Artifacts + manifests TTL: 7d.
- Pin/unpin support controls exemption from cleanup.

5. Idempotency
- `Idempotency-Key` is mandatory for `POST /v1/convert/jobs`.
- Same key + same payload fingerprint must return same job identity.
- Same key + different payload fingerprint must fail with `409`.

6. Acceleration policy (mandatory)
- GPU-first is the default objective and default execution policy for initial rollout.
- CPU fallback must not be silently enabled during initial rollout.
- CPU fallback can only be enabled after explicit GPU exploration and benchmark evidence is documented and approved in task/docs updates.

## Consequences

- Clients get one stable API shape now, with no dual sync/async codepath drift.
- Service remains secure for Hemma through network scoping plus API key control.
- v1 implementation speed is improved with filesystem-first storage, while preserving migration flexibility.
- Operational cleanup is predictable via retention defaults.
- GPU capability is intentionally forced as a first-class validation objective before resilience fallback is introduced.

## Follow-up

- Implement v1 endpoints exactly as specified in `docs/converters/pdf_to_md_service_api_v1.md`.
- Add contract tests for:
  - idempotency replay and collision behavior,
  - error model shape and canonical error codes,
  - retention/expiry behavior,
  - GPU-required failure behavior when GPU is unavailable.
- Only after benchmark phase completion, decide whether to enable CPU fallback and record the update in a new ADR (or ADR amendment).
