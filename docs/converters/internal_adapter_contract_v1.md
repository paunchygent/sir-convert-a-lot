---
type: converter
id: CONV-internal-adapter-contract-v1
title: Internal Adapter Contract v1
status: active
created: 2026-02-11
updated: 2026-02-11
owners:
  - platform
tags:
  - integration
  - adapter
  - contract
  - internal
links:
  - docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md
  - docs/backlog/tasks/task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/reference/ref-story-003c-consumer-integration-handoff.md
  - scripts/sir_convert_a_lot/integrations/adapter_profiles.py
---

## Purpose

Define normative requirements for thin internal consumer adapters (HuleEdu and
Skriptoteket) that submit conversion jobs to Sir Convert-a-Lot without contract
drift or business-logic forks.

## Scope

- Applies to internal integration layers only.
- Public HTTP contract remains defined by `CONV-pdf-to-md-service-api-v1`.
- This contract governs adapter behavior, not service runtime policy internals.

## Mandatory Adapter Requirements

1. Thin adapter only

- Adapter code must orchestrate transport concerns only:
  - Canonical `JobSpec` construction
  - Deterministic header generation
  - Delegation to canonical client
- Adapter code must not implement conversion business logic or policy forks.

2. Canonical `JobSpec` mapping

- Adapters must submit canonical v1 `JobSpec` shape only.
- Consumer profile must not mutate schema shape or contract fields.
- Required defaults for Story 003c slice:
  - `api_version: "v1"`
  - `source.kind: "upload"`
  - `conversion.output_format: "md"`
  - `execution.acceleration_policy: "gpu_required"` (unless explicit caller override)
  - `retention.pin: false`

3. Correlation header policy

- Request `X-Correlation-ID` handling:
  - If caller-provided correlation ID is present and non-empty, preserve exactly.
  - If missing, generate deterministic fallback:
    - `corr_<consumer>_<sha16>`
    - `<sha16>` is first 16 hex chars of SHA256 over adapter `source_label`.

4. Idempotency header policy

- `Idempotency-Key` must be deterministic:
  - `idem_<consumer>_<sha48>`
  - `<sha48>` is first 48 hex chars of SHA256 over:
    - normalized `job_spec` JSON (`sort_keys=true`, compact separators), and
    - uploaded file SHA256
- Same payload and file must produce same key.
- Payload or file changes must produce a different key.

5. Error propagation behavior

- Adapter must not remap service errors into consumer-specific codes.
- Status codes and `error.code` values from canonical client/service are preserved.
- Timeouts and retryable failures remain canonical (`job_timeout`, etc.).

6. Submission interface

- Adapter submission path must delegate to:
  - `scripts.sir_convert_a_lot.interfaces.http_client.SirConvertALotClient`
- Adapter helper surface for Story 003c reference implementation:
  - `prepare_submission(...)`
  - `submit_pdf_for_profile(...)`

## Conformance Gate (Primary)

The acceptance gate for this contract is automated conformance tests in:

- `tests/sir_convert_a_lot/test_integration_adapter_conformance.py`

Required scenario coverage:

- Canonical `JobSpec` equivalence across `huledu` and `skriptoteket`.
- Deterministic idempotency key behavior.
- Correlation pass-through plus deterministic fallback generation.
- Non-mutating error propagation (auth/validation/timeout).
- End-to-end adapter smoke path through canonical API app.

## Tunnel and Operational Expectations

- Local/internal consumers use internal HTTP endpoint plus `X-API-Key`.
- Tunnel-first local development follows:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
- No consumer-specific service forks may be introduced to bypass tunnel/API flow.

## Change Control

- Any consumer-specific exception to this contract requires Story/ADR update before
  implementation to prevent adapter drift.
