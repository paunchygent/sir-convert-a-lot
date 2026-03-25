---
type: converter
id: CONV-internal-adapter-contract-v2
title: Internal Adapter Contract v2
status: active
created: 2026-03-04
updated: 2026-03-25
owners:
  - platform
tags:
  - integration
  - adapter
  - contract
  - internal
links:
  - docs/converters/multi_format_conversion_service_api_v2.md
  - scripts/sir_convert_a_lot/integrations/adapter_profiles.py
  - tests/sir_convert_a_lot/test_integration_adapter_conformance.py
---

## Purpose

Define normative requirements for thin internal consumer adapters (HuleEdu and Skriptoteket) that
submit conversion jobs to Sir Convert-a-Lot **service API v2** without contract drift or
business-logic forks.

This contract is consumer-facing: it governs adapter behavior (job spec construction, deterministic
headers, and error propagation), not service runtime policy internals.

## Scope

- Applies to internal integration layers only.
- All submissions must target `/v2/convert/jobs*` endpoints (no legacy version lanes).
- Adapter helpers must remain transport-only; conversion policy and orchestration live in this repo.

## Mandatory Adapter Requirements

### 1. Thin adapter only

- Adapter code must orchestrate transport concerns only:
  - canonical v2 `JobSpec` construction,
  - deterministic header generation (correlation + idempotency),
  - delegation to canonical v2 client.
- Adapter code must not implement conversion business logic or consumer-specific policy forks.

### 2. Canonical `JobSpec` mapping (v2)

- Adapters must submit the canonical v2 job spec shape.
- Consumer profile must not mutate schema shape or omit required defaults.
- For internal “PDF -> Markdown” ingestion, required defaults are:
  - `api_version: "v2"`
  - `source.kind: "upload"`
  - `source.format: "pdf"`
  - `conversion.output_format: "md"`
  - `execution.acceleration_policy: "gpu_required"` (unless explicit caller override)
  - `retention.pin: false`

Canonical reference implementation:

- `scripts/sir_convert_a_lot.integrations.adapter_profiles.build_job_spec_for_profile(...)`

### 3. Correlation header policy

- `X-Correlation-ID` handling:
  - if caller-provided correlation ID is present and non-empty, preserve exactly,
  - if missing, generate deterministic fallback:
    - `corr_<consumer>_<sha16>`
    - `<sha16>` is first 16 hex chars of SHA256 over adapter `source_label`.

Canonical reference implementation:

- `scripts/sir_convert_a_lot.integrations.adapter_profiles.build_correlation_id(...)`

### 4. Idempotency header policy

- `Idempotency-Key` must be deterministic:
  - `idem_<consumer>_<sha48>`
  - `<sha48>` is first 48 hex chars of SHA256 over:
    - normalized `job_spec` JSON (`sort_keys=true`, compact separators), and
    - uploaded file SHA256.
- Same payload and file must produce the same key.
- Payload or file changes must produce a different key.

Canonical reference implementation:

- `scripts/sir_convert_a_lot.integrations.adapter_profiles.build_idempotency_key(...)`

### 5. Error propagation behavior

- Adapter must not remap service/client errors into consumer-specific codes.
- Status codes and `error.code` values from canonical client/service are preserved.
- Timeout classifications remain canonical (for example `job_poll_window_exceeded`, `job_timeout`).

### 6. Submission interface

- Adapter submission path must delegate to:
  - `scripts.sir_convert_a_lot.interfaces.http_client_v2.SirConvertALotClientV2`
- Adapter helper surface for consumer code:
  - `prepare_submission(...)`
  - `submit_pdf_for_profile(...)`

### 7. Trusted HTML bundle policy

- Internal adapters may opt into `conversion.input_trust_mode="trusted_app_bundle"` only for
  app-owned `html -> pdf` bundles that the consumer renderer generates itself.
- Trusted HTML bundle submissions must use the internal adapter API key lane
  (`SIR_CONVERT_A_LOT_INTERNAL_API_KEY`), not the public service key.
- Adapters must not silently elevate ordinary HTML uploads into trusted mode.
- Bundled assets must still remain job-local resources; adapters must not rely on external
  network URLs or arbitrary host filesystem reads.

## Conformance Gate (Primary)

The acceptance gate for this contract is automated conformance tests in:

- `tests/sir_convert_a_lot/test_integration_adapter_conformance.py`

Required scenario coverage includes:

- Canonical `JobSpec` equivalence across `huledu` and `skriptoteket`.
- Deterministic idempotency key behavior.
- Correlation pass-through plus deterministic fallback generation.
- Non-mutating error propagation (auth/validation/timeout).
- End-to-end adapter smoke path through canonical API app.

## Tunnel and Operational Expectations

- Local/internal consumers use the internal HTTP endpoint plus `X-API-Key`.
- Consumers that use `trusted_app_bundle` must authenticate with the internal adapter key lane.
- Tunnel-first local development follows:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Change Control

- Any consumer-specific exception to this contract requires Story/ADR update before
  implementation to prevent adapter drift.
