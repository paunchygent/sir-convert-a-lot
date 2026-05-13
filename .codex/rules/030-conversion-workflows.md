---
trigger: model_decision
rule_id: RULE-030
title: Conversion Workflows
status: active
created: '2026-02-11'
updated: '2026-05-13'
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
- Client HTTP adapter: `scripts/sir_convert_a_lot/interfaces/http_client_v2.py`
- Runtime engine: `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`

## Core Commands

- `pdm run dev-start`
- `pdm run dev-logs`
- `pdm run convert-a-lot convert <source> --output-dir <target>`
- `pdm run sir-convert-a-lot convert <source> --output-dir <target>`

## Contract References

- API schema (v2): `docs/converters/multi_format_conversion_service_api_v2.md`
- Decision (v2): `docs/decisions/0002-multi-format-service-api-v2.md`
- CLI guide: `docs/converters/sir_convert_a_lot.md`

## Execution Rules

- API is async job-based; no separate sync endpoint in v2.
- Local service integration uses the CPU-only Docker dev service via
  `pdm run dev-start`; do not use host-run `serve:sir-convert-a-lot` as the
  active local integration lane.
- `POST /v2/convert/jobs` must enforce idempotency semantics.
- Standard error envelope is mandatory for all non-2xx responses.
- Artifact bytes are fetched via `GET /v2/convert/jobs/{job_id}/artifact` (not inline).
- Hemma repo placement invariant for operational workflows:
  - canonical path is `/home/paunchygent/apps/sir-convert-a-lot`
  - do not execute service operations from ad hoc non-`~/apps` clones
- Batch CLI runs must emit deterministic manifest fields:
  - `source_file_path`
  - `job_id`
  - `status`
  - `output_path`
  - `error_code`
