---
type: reference
id: REF-SIRCON-GENERAL-multi-format-conversion-service-api-v2-errors
title: Multi-format Conversion Service API v2 Errors
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: general
retired_ids:
- CONV-multi-format-conversion-service-api-v2-errors
summary: Multi-format Conversion Service API v2 Errors
---

## Overview

State the subject, why it is useful, and the boundary of the retained context.

## Facts And Semantics

Define terms and record durable facts, ownership, relationships, and evidence
interpretation. Distinguish confirmed facts from mutable interpretation. Link
to a runbook for ordered execution and to backlog items for work state.

## Decisions And Interpretation

Record current interpretation and its practical consequences. Route accepted
architecture or governance rationale to an ADR, material planning choices to a
`decisions` reference, and implementation authority to the backlog.

## Historical Source Content

## Deterministic Route Errors (Selected)

- `pdf -> md` OCR engine missing/unavailable:
  - `503 Service Unavailable`
  - `error.code = "ocr_engine_unavailable"`
  - `error.retryable = false`
- `pdf -> md` OCR language pack missing (preflight):
  - `503 Service Unavailable`
  - `error.code = "ocr_language_unavailable"`
  - `error.retryable = false`
- `pdf -> md` OCR language tags invalid/unsupported for engine:
  - `422 Unprocessable Entity`
  - `error.code = "validation_error"`
- `docx -> md` unreadable/corrupt DOCX:
  - `422 Unprocessable Entity`
  - `error.code = "docx_unreadable"`
- `docx -> md` converter dependency missing:
  - `503 Service Unavailable`
  - `error.code = "pandoc_not_installed"`
  - `error.retryable = true`
- `docx -> md` converter execution failure:
  - `500 Internal Server Error`
  - `error.code = "docx_to_markdown_failed"`
  - `error.retryable = false`
- `html -> md` missing local resources:
  - `422 Unprocessable Entity`
  - `error.code = "html_resource_not_found"`
  - `error.details = {"missing_resources":[...]}`
- `html -> md` invalid local resource references:
  - `422 Unprocessable Entity`
  - `error.code = "html_resource_invalid"`
  - `error.details = {"invalid_resources":[...]}`
- `html -> md` converter dependency missing:
  - `503 Service Unavailable`
  - `error.code = "pandoc_not_installed"`
  - `error.retryable = true`
- `html -> md` converter execution failure:
  - `500 Internal Server Error`
  - `error.code = "html_to_markdown_failed"`
  - `error.retryable = false`

DigiExam migration route errors are governed by
`docs/converters/digiexam-migration-service-api-artifact-contract.md` because
that route has source-validation, companion-evidence, privacy, and named
artifact-bundle semantics beyond the generic v2 routes.

## Error Envelope (v2)

All non-2xx responses return a standard error envelope:

```json
{
  "api_version": "v2",
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "retryable": false,
    "details": {
      "errors": []
    },
    "correlation_id": "corr_..."
  }
}
```

The error model is intentionally compatible with v1, with `api_version` set to `v2`.
