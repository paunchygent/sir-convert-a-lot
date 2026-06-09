---
type: converter
id: CONV-internal-adapter-contract-v2
title: Internal Adapter Contract v2
status: active
created: 2026-03-04
updated: 2026-06-09
owners:
  - platform
tags:
  - integration
  - adapter
  - contract
  - internal
links:
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
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
- Route-specific adapters, including DigiExam migration for Skriptoteket, must
  follow the route-specific converter contract without embedding conversion
  policy in the consumer app.
- Planned route-specific adapters, including audio transcription, must remain
  transport-only until their route contract, OpenAPI update, and implementation
  tasks register the runtime route.
- Internal adapters currently use the v2 service API key as a transport
  credential. Under ADR-0009, user-originated adapter calls must also preserve
  HuleEdu `InternalIdentityContextV1` with audience `sir-convert-a-lot` so job
  and artifact authorization is not reduced to global service-key ownership.
- There is no separate Sir-specific signed identity transport.

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
- For Skriptoteket DigiExam migration, required defaults are owned by
  `docs/converters/digiexam-migration-service-api-artifact-contract.md` and
  include:
  - `api_version: "v2"`
  - `source.kind: "upload"`
  - `source.format: "digiexam_dxe"`
  - `conversion.output_format: "examnet_migration_bundle"`
  - `retention.pin: false`
- For future audio transcription, required defaults are owned by
  `docs/converters/audio-transcription-service-api-artifact-contract.md` and
  begin with:
  - `api_version: "v2"`
  - `source.kind: "upload"`
  - `source.format: "audio"`
  - `conversion.output_format: "transcript_bundle"`
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
    - uploaded file SHA256,
    - plus route-specific companion file SHA256 values when present.
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

### 7. Curated app-owned PDF boundary

- Internal adapters should not route app-owned curated-app PDF artifacts through
  Sir Convert when the owning product already has the renderer and artifact
  model locally.
- Klassrumskartan is the current explicit example of that rule.
- Adapters must keep using Sir Convert for general conversion and parsing
  workloads rather than for renderer-owned teacher artifacts.

### 8. DigiExam migration adapter boundary

- Skriptoteket may submit `.dxe` files and optional governed companion PDFs
  through the DigiExam migration contract.
- The adapter must remain transport-only: it builds headers and job specs,
  uploads declared parts, polls status/result, lists named artifacts, downloads
  artifacts, and passes artifact metadata to Skriptoteket user-file storage.
- The adapter must not parse `.dxe`, parse graded-result PDFs, infer answer
  keys, hide manual-follow-up states, rewrite target warnings, or inspect Sir
  Convert work directories.

### 9. Audio transcription adapter boundary

- Skriptoteket and HuleEdu adapters may submit governed audio transcription
  jobs only after the route-specific contract and runtime implementation tasks
  land.
- The adapter must remain transport-only: it builds headers and job specs,
  uploads the declared source file, polls status/result, lists named artifacts,
  downloads transcript artifacts, and passes artifact metadata to product-owned
  persistence.
- The adapter must not perform local transcription, diarization, source media
  probing, chunking, transcript formatting policy, retention decisions, or
  sidecar/backend selection.
- The first stable product artifact is the canonical transcript JSON bundle.
  Plain text, Markdown, VTT, and SRT must be requested or consumed as
  downstream formatter artifacts once Sir Convert exposes them.

## Conformance Gate (Primary)

The acceptance gate for this contract is automated conformance tests in:

- `tests/sir_convert_a_lot/test_integration_adapter_conformance.py`

Required scenario coverage includes:

- Canonical `JobSpec` equivalence across HuleEdu and Skriptoteket callers.
- Deterministic idempotency key behavior.
- Correlation pass-through plus deterministic fallback generation.
- Non-mutating error propagation (auth/validation/timeout).
- End-to-end adapter smoke path through canonical API app.
- DigiExam migration conformance must cover route-specific idempotency over
  `.dxe` plus companion digests and named artifact bundle handling when the
  runtime route is implemented.
- Audio transcription conformance must cover route-specific idempotency over
  uploaded media, optional diarization settings, canonical transcript JSON
  artifact handling, and no adapter-side transcription or diarization policy.

## Tunnel and Operational Expectations

- Local/internal consumers use the internal HTTP endpoint plus `X-API-Key`.
- After the Gateway/internal identity cutover, user-originated internal calls
  also carry verified `InternalIdentityContextV1` according to
  `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.
- Tunnel-first local development follows:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Change Control

- Any consumer-specific exception to this contract requires Story/ADR update before
  implementation to prevent adapter drift.
