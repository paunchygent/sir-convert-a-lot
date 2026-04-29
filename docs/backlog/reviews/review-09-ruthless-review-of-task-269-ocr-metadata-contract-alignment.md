---
id: review-09-ruthless-review-of-task-269-ocr-metadata-contract-alignment
title: Ruthless review of Task 269 OCR metadata contract alignment
type: review
status: completed
priority: high
created: '2026-04-29'
last_updated: '2026-04-29'
related:
  - docs/backlog/tasks/task-269-reconcile-pdf-ocr-metadata-contract-across-docs-runtime-and-tests.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md
  - docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - scripts/sir_convert_a_lot/application/contracts_v2.py
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - scripts/sir_convert_a_lot/infrastructure/pdf_checkpoint_metadata_v2.py
  - scripts/sir_convert_a_lot/infrastructure/job_store_v2.py
  - tests/sir_convert_a_lot/test_task269_ocr_metadata_contract.py
  - tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py
labels:
  - review
  - task-269
  - ocr
  - contract
  - metadata
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: post-implementation retained review of
  `docs/backlog/tasks/task-269-reconcile-pdf-ocr-metadata-contract-across-docs-runtime-and-tests.md`.
- Governing authority:
  - `docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md`
  - `docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md`
  - `docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/sir_convert_a_lot.md`
- Files reviewed:
  - `docs/backlog/tasks/task-269-reconcile-pdf-ocr-metadata-contract-across-docs-runtime-and-tests.md`
  - `docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md`
  - `docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md`
  - `docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `scripts/sir_convert_a_lot/application/contracts_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`
  - `scripts/sir_convert_a_lot/infrastructure/pdf_checkpoint_metadata_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py`
  - `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py`
  - `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions_helpers.py`
  - `tests/sir_convert_a_lot/test_task269_ocr_metadata_contract.py`
  - `tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
- Public surfaces affected:
  - Service API v2 terminal result `result.conversion_metadata`.
  - PDF checkpoint metadata that hydrates terminal PDF OCR metadata.
  - Hemma v2 smoke report OCR metadata fields.
- Compatibility posture:
  - Task 269 selected Outcome B: keep the active v2 result metadata contract
    limited to `ocr_enabled`, `ocr_engine_used`, and `ocr_languages_used`.
  - The old `ocr_languages_requested` and `ocr_acceleration_used` result fields
    remain superseded/deferred, not compatibility-shimmed.
- Evidence reviewed:
  - `rg "ocr_languages_requested|ocr_acceleration_used" docs scripts tests`
  - `pdm run pytest-root tests/sir_convert_a_lot/test_task269_ocr_metadata_contract.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py -q`
  - `pdm run docs-validate`
  - `pdm run skills-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

## Findings

1. `high` - The checked-off null/list semantics still drift for no-OCR PDF
   results, and the focused Task 269 tests do not cover that path.

   - Evidence:
     `docs/backlog/tasks/task-269-reconcile-pdf-ocr-metadata-contract-across-docs-runtime-and-tests.md:103`
     marks `ConversionMetadataV2`, job-store persistence, API docs, CLI docs,
     smoke evidence, and tests as agreeing on OCR metadata null/list semantics.
     The API docs define `ocr_languages_used` as `list[string] | null` and say
     it is `null` when OCR is not executed at
     `docs/converters/multi_format_conversion_service_api_v2.md:591`.
     The PDF runtime instead emits an empty list for that same no-OCR PDF case:
     Docling returns `ocr_languages_used=[]` when OCR is disabled at
     `scripts/sir_convert_a_lot/infrastructure/docling_backend.py:215`, and
     checkpoint terminal aggregation does the same at
     `scripts/sir_convert_a_lot/infrastructure/pdf_checkpoint_metadata_v2.py:121`.
     Job-store persistence preserves whichever list value it receives at
     `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py:256`.
   - Why it matters:
     Task 269 is specifically a metadata-truth repair. A strict v2 client can
     read the API docs and expect `null` for no-OCR PDF results, while the
     runtime can legally publish `[]`. That leaves the exact drift class this
     task was created to remove, just in null/list semantics rather than field
     names.
   - Required fix:
     Pick one public semantic and make the docs, runtime, persistence, smoke
     evidence, and tests match it. If PDF no-OCR should mean `[]`, update the
     v2 API docs and Task 269/Story 39 wording to state that `null` is reserved
     for non-PDF/not-applicable routes and `[]` means PDF route with OCR not
     executed. If `null` is the intended no-OCR result value, normalize the PDF
     terminal path before persistence/serialization instead of preserving
     empty lists.
   - Proof requirement:
     Add or update a v2 API contract test for a PDF-to-Markdown result with
     OCR disabled/not-needed and assert the chosen `ocr_enabled`,
     `ocr_engine_used`, and `ocr_languages_used` values. Rerun
     `pdm run pytest-root tests/sir_convert_a_lot/test_task269_ocr_metadata_contract.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py <new-or-updated-no-ocr-test> -q`
     plus the docs validators.

## Decision

approved

## Response

Task 269 now removes the two unsupported result fields from the active
contract, aligns the no-OCR PDF null/list semantics across docs and runtime,
and includes focused API coverage for the branch that previously lacked proof.

## Implementation Response

The Review 09 follow-up is implemented locally:

- selected public semantic: `ocr_languages_used=[]` for PDF routes where OCR
  was applicable but not executed, and `ocr_languages_used=null` only for routes
  where OCR is not applicable,
- updated the v2 API docs and Story 39 / Task 269 wording to state that split,
- added a PDF-to-Markdown no-OCR API contract test that asserts
  `ocr_enabled=false`, `ocr_engine_used=null`, and `ocr_languages_used=[]`,
- reran the focused Task 269 contract suite and docs/governance validators.

Validation evidence for the local response:

- `pdm run pytest-root tests/sir_convert_a_lot/test_task269_ocr_metadata_contract.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py -q`
  passed with `5 passed`.
- `pdm run format-all` passed.
- `pdm run lint-fix` passed.
- `pdm run typecheck-all` passed with `Success: no issues found in 575 source files`.
- `pdm run docs-sync` passed.
- `pdm run docs-validate` passed.
- `pdm run validate-tasks` passed.
- `pdm run skills-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.

## Follow-up Actions

1. None. The retained finding is resolved.

## Completion

Retained review closed as `approved` on 2026-04-29 after the no-OCR PDF
metadata semantics were aligned and verified.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
