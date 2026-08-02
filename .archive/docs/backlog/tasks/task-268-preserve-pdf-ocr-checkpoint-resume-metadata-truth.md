---
id: task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth
title: Preserve PDF OCR checkpoint resume metadata truth
type: task
status: completed
priority: high
created: '2026-04-27'
last_updated: '2026-04-29'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - docs/backlog/tasks/task-71-add-cancel-with-save-and-resume-from-checkpoint-flow.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py
  - scripts/sir_convert_a_lot/infrastructure/pdf_checkpoints_v2.py
  - scripts/sir_convert_a_lot/infrastructure/pdf_checkpoint_metadata_v2.py
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/infrastructure/job_store_v2.py
  - tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py
  - tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py
  - tests/sir_convert_a_lot/test_pdf_checkpoint_metadata_resume.py
labels:
  - ocr
  - pdf
  - checkpoint
  - resume
  - metadata
  - regression
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close the P1 OCR review finding where a resumed/finalized PDF job can skip all
already-checkpointed chunks and publish false terminal metadata
(`backend_used=None`, `acceleration_used=None`, `ocr_enabled=false`, empty OCR
engine/language/warning data) even though the checkpointed chunks previously ran
OCR.

## PR Scope

- Extend checkpoint persistence so terminal OCR metadata can be derived without
  reprocessing completed chunks.
- Prefer per-chunk metadata over root-only metadata:
  - `backend_used`,
  - `acceleration_used`,
  - `ocr_enabled`,
  - `ocr_engine_used`,
  - `ocr_languages_used`,
  - warnings,
  - normalized phase timings.
- Update finalization in
  `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`
  so it hydrates aggregate metadata from existing succeeded chunk records when
  `pending_chunks` is empty or only partially populated.
- Preserve byte-identical final artifacts for resumed jobs.
- If checkpoint schema changes are required, make the schema/version decision
  explicit in `pdf_checkpoints_v2.py` and the tests. Do not hide retained-state
  behavior behind an ungoverned compatibility shim.
- Selected retained-state decision: fail closed when terminal metadata cannot
  be truthfully derived. No backwards-compatibility bridge is allowed for old
  checkpoint payloads that lack per-chunk terminal metadata.
- Do not change the public async job model or introduce Docling-only request
  side channels.

## Entry Points

- `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`
- `scripts/sir_convert_a_lot/infrastructure/pdf_checkpoints_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/job_store_manifest_v2.py`
- `tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py`
- Add a focused regression test module if keeping this out of the PDF parallel throughput suite
  makes the proof clearer.

## Deliverables

- [x] Checkpoint chunk records or equivalent persisted checkpoint state can
  represent backend/OCR metadata for each succeeded chunk.
- [x] Finalization aggregates checkpointed chunk metadata when no new chunks
  are converted.
- [x] Regression test proves the all-chunks-already-complete path reports
  truthful terminal metadata.
- [x] Resume/finalization remains byte-identical to the canonical artifact.

## Acceptance Criteria

- [x] Reproduce the reviewed failure before the fix, then lock the fixed
  behavior in a deterministic test.
- [x] A job with all chunks already checkpointed finalizes without reprocessing
  and still returns:
  - `backend_used="docling"` or the real backend used by the chunks,
  - truthful `acceleration_used`,
  - `ocr_enabled=true` when any completed chunk ran OCR,
  - truthful `ocr_engine_used` and `ocr_languages_used`,
  - retained warnings such as `docling_auto_ocr_retry_applied`,
  - retained phase timings.
- [x] Mixed OCR/non-OCR chunk outcomes do not collapse to a false
  `ocr_enabled=false`.
- [x] Existing serial/parallel/cancel/resume tests remain green.
- [x] No compatibility bridge is added without an explicit checkpoint schema
  version and retained-state proof.

## Test Requirements

- [x] Focused unit/contract test for zero-new-chunk resume finalization.
- [x] Resume artifact digest proof remains byte-identical to the baseline.
- [x] Existing PDF parallel throughput parallel/cancel/resume regression suite remains green.
- [x] Focused command:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py -q`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- `PdfChunkRecordV2` now persists backend/OCR metadata, warnings, and canonical
  phase timings for each succeeded chunk.
- `PdfCheckpointV2.schema_version` is now `v2_pdf_checkpoint_v2`; v1 payloads
  are rejected instead of bridged or inferred.
- `pdf_checkpoint_metadata_v2.py` derives terminal metadata from sorted
  succeeded chunk records and fails closed when records are missing, mixed, or
  internally inconsistent for single-value terminal fields.
- Zero-new-chunk finalization now returns checkpoint-derived metadata and does
  not call the conversion backend for already-complete chunks.
- Review 08 follow-up made the parallel regression order-insensitive, made
  final assembly fail closed for missing/corrupt/duplicate/incomplete chunk
  artifacts, promoted observed OCR engine/language values through the backend
  result contract, and documented the public checkpoint v2 payload shape.
- Review 08 was re-reviewed on 2026-04-29 and approved. The original retained
  findings remain in the review record as history, and the current accepted
  state is the 2026-04-29 approval section in
  `docs/backlog/reviews/review-08-ruthless-review-of-task-268-pdf-ocr-checkpoint-metadata-truth.md`.

## Validation Evidence

- `pdm run format-all` passed.
- `pdm run lint-fix` passed.
- `pdm run typecheck-all` passed: `Success: no issues found in 574 source files`.
- Review 08 follow-up focused regression command passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py -q`
  (`20 passed`).
- 2026-04-29 Review 08 re-review focused command passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py -q`
  (`20 passed`).
- 2026-04-29 Review 08 re-review typecheck passed:
  `pdm run typecheck-all` (`Success: no issues found in 574 source files`).
- `pdm run coverage-gate` passed: `1065 passed, 5 skipped`, total coverage
  `95.47%`.

## Closeout

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- focused `pdm run pytest-root <ocr/checkpoint/tests>`
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
