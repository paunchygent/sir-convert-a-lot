---
trigger: model_decision
rule_id: RULE-030
title: Conversion Workflows
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - conversion
  - service
scope: repo
---

## Canonical Surfaces

- Service (HTTP): `scripts/sir_convert_a_lot/interfaces/http_api.py`
- Client CLI: `scripts/sir_convert_a_lot/interfaces/cli_app.py`
- Client HTTP adapter: `scripts/sir_convert_a_lot/interfaces/http_client.py`
- Runtime engine: `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`

Compatibility facades remain at package root for stable imports.

## Core Commands

- `pdm run serve:sir-convert-a-lot`
- `pdm run convert-a-lot convert <source> --output-dir <target>`
- `pdm run sir-convert-a-lot convert <source> --output-dir <target>`

## Contract References

- API schema: `docs/converters/pdf_to_md_service_api_v1.md`
- ADR lock: `docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md`
- CLI guide: `docs/converters/sir_convert_a_lot.md`

## Execution Rules

- API is async job-based; no separate sync endpoint in v1.
- `POST /v1/convert/jobs` must enforce idempotency semantics.
- Standard error envelope is mandatory for all non-2xx responses.
- Hemma repo placement invariant for operational workflows:
  - canonical path is `/home/paunchygent/apps/sir-convert-a-lot`
  - do not execute service operations from ad hoc non-`~/apps` clones
- Batch CLI runs must emit deterministic manifest fields:
  - `source_file_path`
  - `job_id`
  - `status`
  - `output_path`
  - `error_code`
