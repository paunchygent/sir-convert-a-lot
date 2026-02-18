---
type: decision
id: ADR-0002
title: Multi-format Conversion Service API v2
status: proposed
created: 2026-02-18
updated: 2026-02-18
owners:
  - platform
tags:
  - adr
  - api
  - v2
  - multi-format
links:
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
---

## Purpose

Record the decision to introduce a versioned multi-format **service API v2** on Hemma so that all
in-scope conversion pipelines run server-side (dockerized runtime), while preserving the locked
PDF-to-Markdown **service API v1** contract.

## Status

- Proposed
- Date: 2026-02-18

## Context

Sir Convert-a-Lot started with a locked v1 service contract focused on GPU-governed PDF-to-Markdown
conversion (`pdf -> md`). Converter-suite parity work initially introduced CLI-local Pandoc/WeasyPrint
pipelines to unblock layout-controlled exports.

However, the platform objective is:

- all conversions executed on Hemma in a controlled docker runtime,
- the CLI as a thin submit/poll/download client (no laptop-local Pandoc/WeasyPrint dependency),
- versioned HTTP contracts for expansion (no silent v1 drift).

## Decision

1. Introduce multi-format service API v2

- Add `/v2/convert/jobs` endpoints for multi-format conversion jobs as specified in:
  - `docs/converters/multi_format_conversion_service_api_v2.md`
- Keep v1 endpoints and semantics unchanged.

2. Add binary artifact retrieval

- v2 must support binary artifacts (PDF/DOCX).
- v2 exposes a dedicated artifact download endpoint:
  - `GET /v2/convert/jobs/{job_id}/artifact`

3. Support resources bundles for deterministic rendering

- v2 job creation supports an optional `resources` zip upload so Markdown/HTML conversions can
  resolve images/fonts/stylesheets inside the service runtime.

4. Runtime dependencies are service-owned

- Pandoc and WeasyPrint dependencies are treated as **service runtime dependencies** and must be
  installed in the Hemma docker image(s).
- Missing runtime dependencies must still surface deterministic error codes (diagnosability), but
  are considered deployment misconfiguration rather than a client responsibility.

## Consequences

- The CLI route taxonomy shifts from “local/hybrid execution” to “service v1 or service v2”.
- Service storage and job persistence must support non-Markdown artifacts (PDF/DOCX).
- Additional service-level validation and deterministic error mapping is required for v2 routes
  (unsupported route combinations, missing resources, missing Pandoc/WeasyPrint runtime).

## Follow-up

- Implement the v2 contract and runtime primitives (job store/runtime + router) under Epic 04.
- Pivot the canonical CLI to use v2 for `md/html/pdf -> pdf/docx` routes, retaining v1 only for
  `pdf -> md`.
