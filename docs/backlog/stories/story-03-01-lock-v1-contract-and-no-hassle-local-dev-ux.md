---
id: '003a-conversion-service-v1-contract-and-dev-experience-story'
title: 'Lock v1 contract and no-hassle local dev UX'
type: 'story'
status: 'completed'
priority: 'critical'
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - 'docs/backlog/epics/epic-03-unified-conversion-service.md'
  - 'docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md'
  - 'docs/converters/pdf_to_md_service_api_v1.md'
labels:
  - 'contract'
  - 'developer-experience'
  - 'api'
---
# Lock v1 contract and no-hassle local dev UX

## Objective

Ensure local developers and coding assistants can use one predictable command path to submit conversion jobs and retrieve results through internal HTTP/tunnel without contract ambiguity.

## Scope

- Finalize and enforce v1 API schema.
- Define canonical `convert-a-lot` local UX contract for:
  - single file,
  - directory batch,
  - output directory targeting,
  - batch summary manifest.
- Ensure idempotency and error model behavior are deterministic and documented.

## Acceptance Criteria

1. `docs/converters/pdf_to_md_service_api_v1.md` is treated as normative and referenced by implementation/test docs.
2. `convert-a-lot` usage docs exist with canonical examples for local tunnel workflow.
3. Batch run emits deterministic manifest containing:
  - source file path
  - job id
  - status
  - output path
  - error code (if failed)
4. Re-running same input with same idempotency key must not create duplicate jobs.
5. All API failures follow standard error envelope with canonical error codes.

## Test Requirements

- Contract tests for schema conformance on all endpoints.
- Idempotency tests:
  - replay with same payload,
  - collision with different payload.
- CLI integration tests:
  - folder with 10 files,
  - mixed success/failure handling,
  - output manifest assertions.

## Done Definition

- Acceptance criteria met.
- Test suite green for contract + CLI integration behavior.
- Docs updated in repo start points (README_FIRST/HANDOFF/CURRENT_TASK links where needed).

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized

## Implementation Notes (2026-02-11)

- Implemented v1 HTTP surface in `scripts/sir_convert_a_lot/service.py`:
  - `POST /v1/convert/jobs`
  - `GET /v1/convert/jobs/{job_id}`
  - `GET /v1/convert/jobs/{job_id}/result`
  - `POST /v1/convert/jobs/{job_id}/cancel`
- Added canonical local CLI in `scripts/sir_convert_a_lot/cli.py` with deterministic manifest output.
- Added client module in `scripts/sir_convert_a_lot/client.py` for HTTP/tunnel workflows.
- Added usage docs in `docs/converters/sir_convert_a_lot.md`.
- Added contract + CLI tests:
  - `tests/sir_convert_a_lot/test_api_contract_v1.py`
  - `tests/sir_convert_a_lot/test_convert_a_lot_cli.py`
- Added PDM scripts:
  - `pdm run serve:sir-convert-a-lot`
  - `pdm run convert-a-lot`
  - `pdm run sir-convert-a-lot`
- Refactored implementation into DDD-oriented layers:
  - `scripts/sir_convert_a_lot/domain/`
  - `scripts/sir_convert_a_lot/application/`
  - `scripts/sir_convert_a_lot/infrastructure/`
  - `scripts/sir_convert_a_lot/interfaces/`
  - root modules (`service.py`, `client.py`, `cli.py`, `models.py`, `runtime.py`)
    retained as compatibility facades.
