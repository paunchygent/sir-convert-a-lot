---
id: review-08-ruthless-review-of-task-268-pdf-ocr-checkpoint-metadata-truth
title: Ruthless review of Task 268 PDF OCR checkpoint metadata truth
type: review
status: completed
priority: high
created: '2026-04-28'
last_updated: '2026-04-29'
related:
  - docs/backlog/tasks/task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - docs/backlog/tasks/task-71-add-cancel-with-save-and-resume-from-checkpoint-flow.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py
  - scripts/sir_convert_a_lot/infrastructure/pdf_checkpoints_v2.py
  - scripts/sir_convert_a_lot/infrastructure/pdf_checkpoint_metadata_v2.py
  - tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py
labels:
  - review
  - task-268
  - ocr
  - pdf
  - checkpoint
  - resume
  - metadata
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: post-implementation retained review of
  `docs/backlog/tasks/task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth.md`.
- Governing authority:
  - `docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md`
  - `docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md`
  - `docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md`
  - `docs/backlog/tasks/task-71-add-cancel-with-save-and-resume-from-checkpoint-flow.md`
  - `docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
- Files reviewed:
  - `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`
  - `scripts/sir_convert_a_lot/infrastructure/pdf_checkpoints_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/pdf_checkpoint_metadata_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/conversion_backend.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_conversion.py`
  - `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`
  - `tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py`
  - `tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py`
  - `tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py`
  - `docs/backlog/tasks/task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
- Public surfaces affected:
  - v2 PDF terminal result `conversion_metadata`.
  - `GET /v2/convert/jobs/{job_id}/checkpoint` checkpoint JSON payload.
  - Durable PDF checkpoint schema/version and retained-state resume behavior.
- Compatibility posture:
  - Task 268 explicitly selected a clean fail-closed break for v1 checkpoint
    payloads without a backwards-compatibility bridge.
  - That posture is acceptable, but the new v2 shape and failure semantics must
    be contract-documented because `/checkpoint` returns the raw checkpoint
    payload.
- Evidence reviewed:
  - Task 268 records successful local validation for format, lint, typecheck,
    focused checkpoint/OCR tests, and coverage.
  - This review reran the narrow Task 268 checkpoint tests:
    `pdm run pytest-root tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py -q`.
    The command failed with one Task 268 regression-test failure and four
    passing tests.

## Findings

1. `high` - The focused Task 268 regression suite is not deterministic under
   the parallel executor it enables.

   - Evidence:
     `tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py:161`
     uses `_task268_config`, which enables parallel PDF chunks with
     `max_chunk_workers=2`, then line 169 asserts `conversion_calls == [(1,), (2,)]`. On this review run, the same focused command listed in Task 268
     failed because the executor legitimately converted page 2 before page 1:
     `assert [(2,), (1,)] == [(1,), (2,)]`.
   - Why it matters:
     Task 268 claims validation passed, but the core regression test can fail
     solely because worker scheduling is nondeterministic. That makes the
     retained evidence unreliable and can mask or create false regressions in
     the checkpoint path.
   - Required fix:
     Keep the artifact ordering assertions strict, but make the conversion-call
     assertion order-insensitive for parallel execution, or force serial mode
     only for the part of the test that needs ordered call evidence. The test
     should prove all expected chunks ran on the first pass and no chunks ran
     on the zero-new-chunk pass without depending on thread scheduling order.
   - Proof requirement:
     Rerun
     `pdm run pytest-root tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py -q`
     repeatedly enough to show the focused proof is stable.

1. `high` - Missing checkpoint chunk artifacts are silently skipped, so a
   resumed job can still succeed with incomplete markdown while publishing
   truthful-looking terminal metadata.

   - Evidence:
     `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py:342`
     iterates succeeded checkpoint records, but lines 343-345 skip a missing
     `artifact_relpath` and continue. Finalization then validates only metadata
     at lines 814-822 and returns the assembled markdown at lines 823-831.
     Task 268 requires resumed jobs to preserve byte-identical final artifacts
     and fail closed when terminal metadata cannot be truthfully derived at
     `docs/backlog/tasks/task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth.md:59`
     and lines 63-65.
   - Why it matters:
     A retained checkpoint can claim every chunk succeeded while the chunk
     file is missing or pruned. The current finalizer would omit that chunk,
     return success if any other chunk exists, and publish aggregate
     backend/OCR metadata from checkpoint records for an artifact that no
     longer matches the checkpoint. That violates the byte-identical resume
     contract and turns retained-state corruption into a successful conversion.
   - Required fix:
     Make final assembly fail closed when any succeeded chunk artifact is
     missing, unreadable, size-mismatched, checksum-mismatched, duplicated, or
     leaves the expected page/chunk coverage incomplete. Keep this check in the
     checkpoint assembly/finalization boundary, not in an API route shim.
   - Proof requirement:
     Add a deterministic Task 268 regression that creates a valid v2 checkpoint
     with two succeeded chunks, removes or corrupts one chunk artifact, reruns
     zero-new-chunk finalization, and asserts a non-retryable checkpoint error
     rather than a successful truncated artifact. Run:
     `pdm run pytest-root tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py -q`.

1. `high` - `ocr_engine_used` and `ocr_languages_used` are persisted from the
   resolved request/configuration, not from backend-observed chunk output.

   - Evidence:
     `scripts/sir_convert_a_lot/infrastructure/conversion_backend.py:38`
     defines `ConversionResultData` with `backend_used`, `acceleration_used`,
     and `ocr_enabled`, but no observed OCR engine/language fields. The v1
     conversion wrapper builds `ConversionMetadata` from only those fields at
     `scripts/sir_convert_a_lot/infrastructure/runtime_conversion.py:97`.
     Task 268 nevertheless writes checkpoint `ocr_engine_used` and
     `ocr_languages_used` from `resolved_ocr_engine` / `resolved_ocr_languages`
     in
     `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py:740`
     and lines 744-745. The focused Task 268 test discards the OCR arguments
     in `tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py:125`
     through line 134 and then asserts config-derived values at lines 197-198.
   - Why it matters:
     Task 268's acceptance criteria require truthful per-chunk
     `ocr_engine_used` and `ocr_languages_used`, and the new aggregation module
     says it must avoid inferring facts from request options. Today the
     checkpoint stores "used" values even though the backend result has no way
     to prove them. If Docling `auto`, EasyOCR/Tesseract mapping, fallback, or
     future backend behavior diverges from the resolved request, retained
     checkpoints will preserve configuration echo as runtime truth.
   - Required fix:
     Either extend the backend result contract so Docling reports observed OCR
     engine/language metadata for OCR-enabled attempts, then persist those
     observed values, or rename/document these fields as resolved configuration
     in the governing contract and Task 269 before using them as terminal
     `*_used` metadata. Under the current Task 268 wording, the clean fix is to
     make observed backend metadata available and fail closed when an OCR chunk
     cannot provide it.
   - Proof requirement:
     Add a regression where the stub/backend receives one requested OCR
     configuration but returns a different observed OCR engine/language set,
     then assert the checkpoint and terminal result use the observed values or
     fail closed. Run:
     `pdm run pytest-root tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py -q`
     plus `pdm run typecheck-all`.

1. `medium` - The public checkpoint endpoint now exposes a new raw schema, but
   the API contract docs and endpoint tests do not specify that schema.

   - Evidence:
     `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
     returns `checkpoint.model_dump(mode="json")` directly from
     `GET /v2/convert/jobs/{job_id}/checkpoint`. Task 268 changed the durable
     checkpoint version to `v2_pdf_checkpoint_v2` and added required per-chunk
     metadata fields. The v2 API docs still say only "returns checkpoint JSON
     payload" at
     `docs/converters/multi_format_conversion_service_api_v2.md:657`, with no
     `schema_version`, chunk record field, null/list, or clean-break failure
     semantics. The endpoint contract test only asserts `job_id` and
     `processed_pages`, so the exposed shape can drift again unnoticed.
   - Why it matters:
     `/checkpoint` is a public v2 surface even if the terminal async job model
     is unchanged. Strict clients, operators, and resume tooling now see a
     different schema, and v1 checkpoint payloads fail with
     `checkpoint_invalid`. Without a documented v2 checkpoint payload contract,
     Task 268's "Docs updated" checkbox is overstated and future changes can
     accidentally reintroduce metadata drift.
   - Required fix:
     Document the v2 checkpoint payload shape in
     `docs/converters/multi_format_conversion_service_api_v2.md` or a linked
     converter/reference doc: `schema_version`, root counters, chunk identity,
     artifact integrity fields, backend/OCR metadata, warning/timing semantics,
     and the explicit v1 fail-closed behavior. Extend the HTTP contract test to
     assert at least the version and new per-chunk metadata fields.
   - Proof requirement:
     Run `pdm run docs-sync`, `pdm run docs-validate`,
     `pdm run skills-validate`, `pdm run handoff-validate`, and
     `git diff --check` after the docs/test correction.

## Decision

`changes_requested`

Task 268 is not approval-ready. The focused regression suite failed during this
review, the retained-state boundary still permits a successful incomplete
artifact, the OCR engine/language fields are not yet observed runtime facts,
and the externally visible checkpoint schema is not documented or
contract-tested.

## Response

The implementation should stay in Task 268 rather than spawning a separate
follow-up for these findings. The task is already the governed authority for
checkpoint metadata truth, retained-state fail-closed behavior, schema version
selection, and byte-identical resume finalization.

## Follow-up Actions

1. Fix the four findings above inside Task 268 before marking the task
   independently approved.
1. Rerun the Task 268 focused tests, `pdm run typecheck-all`, and the docs
   closeout gates after correction.

## Implementation Response

2026-04-28 Task 268 follow-up response:

- Finding 1 fixed by making the parallel conversion-call assertion
  order-insensitive while keeping artifact byte-order assertions strict.
- Finding 2 fixed by making terminal assembly fail closed when succeeded chunk
  artifacts are missing, unreadable, size-mismatched, checksum-mismatched,
  duplicated, or do not cover the full page range.
- Finding 3 fixed by promoting observed `ocr_engine_used` and
  `ocr_languages_used` through `ConversionResultData` and `ConversionMetadata`;
  checkpoint records now persist observed backend result metadata and fail
  closed when an OCR chunk lacks observed OCR metadata.
- Finding 4 fixed by documenting `v2_pdf_checkpoint_v2` in
  `docs/converters/multi_format_conversion_service_api_v2.md` and extending the
  checkpoint endpoint contract test to assert schema version plus per-chunk
  metadata fields.
- Focused proof after fixes:
  `pdm run pytest-root tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py tests/sir_convert_a_lot/test_task72_parallel_execution_contracts.py -q`
  passed with `20 passed`.
- `pdm run typecheck-all` passed with
  `Success: no issues found in 574 source files`.

## Re-review 2026-04-29

Decision: `approved`

The four retained findings are resolved in the current checkout.

Disposition:

1. Finding 1 resolved. The zero-new-chunk resume test now asserts
   `sorted(conversion_calls) == [(1,), (2,)]`, so the proof no longer depends
   on parallel worker completion order while preserving strict artifact digest
   and byte equality assertions.
1. Finding 2 resolved. Terminal checkpoint assembly now verifies full page
   coverage, duplicate chunk identities, chunk artifact existence, byte length,
   SHA-256, and UTF-8 readability before publishing final markdown. Integrity
   failures map to non-retryable `checkpoint_artifact_invalid`.
1. Finding 3 resolved for the Task 268 boundary. Backend conversion results now
   carry `ocr_engine_used` and `ocr_languages_used`; checkpoint persistence
   uses those result fields and fails closed when an OCR chunk lacks them. The
   focused test proves the persisted terminal result can differ from the
   resolved request configuration.
1. Finding 4 resolved. The v2 converter API doc now documents
   `v2_pdf_checkpoint_v2`, root fields, chunk fields, v1 fail-closed behavior,
   and artifact-integrity finalization semantics; the endpoint contract test
   asserts the exposed schema version and per-chunk metadata fields.

Verification run during re-review:

- `pdm run pytest-root tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py tests/sir_convert_a_lot/test_task72_parallel_execution_contracts.py -q`
  passed with `20 passed`.
- `pdm run typecheck-all` passed with
  `Success: no issues found in 574 source files`.

Residual note:

- Docling itself exposes OCR behavior primarily through configured
  `PdfPipelineOptions` / OCR option classes. The Task 268 contract boundary now
  requires adapters to publish OCR metadata through the backend result contract
  rather than letting checkpoint persistence infer it from the request.

## Completion

Review retained in this document on 2026-04-28. Re-reviewed on 2026-04-29 and
approved after verifying the retained findings against code, docs, and focused
tests.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
