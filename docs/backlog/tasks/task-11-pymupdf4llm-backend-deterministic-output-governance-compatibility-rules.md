---
id: task-11-pymupdf4llm-backend-deterministic-output-governance-compatibility-rules
title: 'PyMuPDF4LLM backend: deterministic output + governance compatibility rules'
type: task
status: completed
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

## Execution Plan (2026-02-14 locked)

### Locked decisions

- Task sequencing:
  - Task 10 stabilization checkpoint runs before Task 11 implementation.
- Backend routing:
  - `conversion.backend_strategy="auto"` remains Docling-first.
  - PyMuPDF backend is explicit-only (`conversion.backend_strategy="pymupdf"`).
- Dependency pin:
  - `pymupdf4llm==0.3.4` (exact pin).
- PyMuPDF compatibility behavior:
  - Only `conversion.ocr_mode="off"` is allowed.
  - `conversion.ocr_mode in {"auto","force"}` is rejected with deterministic `422 validation_error`.
- Deterministic table strategy mapping:
  - `table_mode="fast"` -> `table_strategy="lines"`
  - `table_mode="accurate"` -> `table_strategy="lines_strict"`

### Implementation steps

1. Stabilize pending Task 10 hardening updates and confirm a clean implementation boundary.
1. Add `pymupdf4llm==0.3.4` and update lockfile.
1. Add `scripts/sir_convert_a_lot/infrastructure/pymupdf_backend.py`:
   - implement `PyMuPdfConversionBackend` using `pymupdf4llm.to_markdown` with `pymupdf.open`.
   - classify backend failures into:
     - `BackendInputError` for unreadable/invalid documents,
     - `BackendExecutionError` for runtime failures.
1. Refactor `runtime_engine.py` backend orchestration:
   - keep `auto -> docling`,
   - route explicit `pymupdf` requests to new backend,
   - enforce deterministic compatibility validation:
     - `backend_strategy="pymupdf"` + `acceleration_policy in {"gpu_required","gpu_prefer"}` -> `422 validation_error` with
       `{"field":"conversion.backend_strategy","reason":"backend_incompatible_with_gpu_policy"}`.
     - `backend_strategy="pymupdf"` + `ocr_mode in {"auto","force"}` -> `422 validation_error` with
       `{"field":"conversion.ocr_mode","reason":"backend_option_incompatible","backend":"pymupdf","supported":["off"]}`.
1. Keep existing GPU rollout lock behavior unchanged (`cpu_only` remains test-gated unless explicit override config is used).
1. Update docs:
   - `docs/converters/pdf_to_md_service_api_v1.md`
   - `docs/converters/sir_convert_a_lot.md`
   - `scripts/sir_convert_a_lot/README.md`
   - `.agents/session/handoff.md`
   - `docs/backlog/current.md`

### Test implementation plan

1. Add backend unit tests in `tests/sir_convert_a_lot/test_pymupdf_backend.py`:
   - success with real fixture PDF,
   - deterministic output for identical input,
   - metadata truth (`backend_used="pymupdf"`, `acceleration_used="cpu"`, `ocr_enabled=false`),
   - table-mode mapping assertions.
1. Update API tests in `tests/sir_convert_a_lot/test_api_contract_v1.py`:
   - `pymupdf + gpu_required` -> deterministic `422` incompatible-policy details,
   - `pymupdf + gpu_prefer` -> deterministic `422` incompatible-policy details,
   - `pymupdf + ocr_mode=force|auto` -> deterministic `422` OCR-incompatible details,
   - `pymupdf + cpu_only` success under explicit test config enabling CPU path.
1. Update runtime failure/routing tests in `tests/sir_convert_a_lot/test_runtime_engine_conversion_failures.py`.
1. Keep Docling and normalization suites green (no regressions).

### Validation gates

1. `pdm run run-local-pdm format-all`
1. `pdm run run-local-pdm lint-fix`
1. `pdm run run-local-pdm typecheck-all`
1. `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
1. `pdm run run-local-pdm validate-tasks`
1. `pdm run run-local-pdm validate-docs`
1. `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Post-merge Hemma smoke

1. `pdm run run-hemma -- pwd`
1. `pdm run run-hemma --shell 'cd /home/paunchygent/apps/sir-convert-a-lot && pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v1.py -q'`

## Deliverables

- [x] PyMuPDF4LLM backend implementation behind canonical v1 job spec fields.
- [x] Request-validation guardrails for GPU-first governance compatibility.
- [x] Tests for determinism and the `422` rejection behavior/details payload.

## Acceptance Criteria

- [x] `conversion.backend_strategy="pymupdf"` succeeds only when execution policy allows CPU use
  in the current rollout lock model.
- [x] Rejection is deterministic and contract-compatible (`422` + standard error envelope).
- [x] Successful jobs report `acceleration_used="cpu"` for PyMuPDF4LLM and never claim GPU usage.
- [x] Quality gates pass (format/lint/typecheck/tests + docs validators and backlog index).

## Validation Evidence

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
