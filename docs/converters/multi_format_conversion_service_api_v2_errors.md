---
type: converter
id: CONV-multi-format-conversion-service-api-v2-errors
title: Multi-format Conversion Service API v2 Errors
status: active
created: 2026-03-04
updated: 2026-03-04
owners:
  - platform
tags:
  - api
  - contract
  - v2
  - errors
links:
  - docs/converters/multi_format_conversion_service_api_v2.md
---

## Deterministic Route Errors (Selected)

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
