---
id: task-11-pymupdf4llm-backend-deterministic-output-governance-compatibility-rules
title: 'PyMuPDF4LLM backend: deterministic output + governance compatibility rules'
type: task
status: proposed
priority: high
created: '2026-02-14'
last_updated: '2026-02-14'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine.py
labels:
  - pymupdf
  - pdf-to-md
  - governance
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement a CPU-only PyMuPDF4LLM backend as a fast, deterministic PDF-to-Markdown path and enforce
GPU-first governance compatibility rules at request-validation time (no falsified acceleration metadata).

## PR Scope

- Add `pymupdf4llm` dependency and implement backend strategy `pymupdf`.
- Ensure output determinism for the same PDF/job spec inputs.
- Enforce policy/backends compatibility:
  - when `execution.acceleration_policy` is `gpu_required` or `gpu_prefer`, reject
    `conversion.backend_strategy="pymupdf"` with a `422 validation_error` including stable details:
    `{"field":"conversion.backend_strategy","reason":"backend_incompatible_with_gpu_policy"}`
- Ensure conversion metadata truth:
  - `conversion_metadata.backend_used="pymupdf"`
  - `conversion_metadata.acceleration_used="cpu"`

## Deliverables

- [ ] PyMuPDF4LLM backend implementation behind canonical v1 job spec fields.
- [ ] Request-validation guardrails for GPU-first governance compatibility.
- [ ] Tests for determinism and the `422` rejection behavior/details payload.

## Acceptance Criteria

- [ ] `conversion.backend_strategy="pymupdf"` succeeds only when execution policy allows CPU use
  in the current rollout lock model.
- [ ] Rejection is deterministic and contract-compatible (`422` + standard error envelope).
- [ ] Successful jobs report `acceleration_used="cpu"` for PyMuPDF4LLM and never claim GPU usage.
- [ ] Quality gates pass (format/lint/typecheck/tests + docs validators and backlog index).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
