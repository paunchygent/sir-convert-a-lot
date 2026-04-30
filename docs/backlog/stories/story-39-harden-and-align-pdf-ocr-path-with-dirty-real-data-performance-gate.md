---
id: story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate
title: Harden and align PDF OCR path with dirty real-data performance gate
type: story
status: proposed
priority: high
created: '2026-04-27'
last_updated: '2026-04-29'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - docs/backlog/tasks/task-71-add-cancel-with-save-and-resume-from-checkpoint-flow.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md
  - docs/backlog/tasks/task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth.md
  - docs/backlog/tasks/task-269-reconcile-pdf-ocr-metadata-contract-across-docs-runtime-and-tests.md
  - docs/backlog/tasks/task-270-add-dirty-pdf-ocr-corpus-manifest-and-benchmark-report-schema.md
  - docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - scripts/sir_convert_a_lot/infrastructure/ocr_preflight_v2.py
  - scripts/sir_convert_a_lot/infrastructure/ocr_resolution_v2.py
labels:
  - ocr
  - pdf
  - checkpoint
  - resume
  - metadata
  - performance
  - dirty-data
  - hemma
---

Implementation slice with acceptance-driven scope.

## Objective

Harden the v2 PDF OCR execution path so checkpoint/resume, metadata, OCR engine
selection, quality checks, and performance evidence describe the same runtime
truth.

The immediate trigger is the 2026-04-27 OCR path review finding: when every PDF
chunk is already present in the checkpoint, finalization can assemble the
artifact without converting any chunk and incorrectly return
`backend_used=None`, `acceleration_used=None`, `ocr_enabled=false`, and empty
OCR metadata/warnings for a job whose checkpointed chunks previously ran OCR.

The broader story goal is to make that class of bug impossible, then prove the
path on hard, dirty, real PDFs before claiming the OCR lane is production-tuned.

## Scope

- Checkpoint and resume metadata truth:
  - Persist or deterministically hydrate per-chunk backend/OCR metadata,
    acceleration evidence, warnings, and phase timings.
  - Terminal finalization must report truthful aggregate metadata even when no
    new chunks are converted during the final run.
  - Mixed jobs must be explicit: if any committed chunk ran OCR, terminal
    metadata must not say OCR was disabled.
- OCR contract alignment:
  - Reconcile v2 API docs, CLI docs, job metadata, checkpoint state, smoke
    reports, and runtime implementation around the exact OCR metadata fields
    that are supported today.
  - Repair the completed Story 21 / Task 77 drift with the selected Outcome B:
    keep the active v2 result contract limited to the fields implemented today
    and mark the old Story 21 / Task 77 claims for `ocr_languages_requested`
    and `ocr_acceleration_used` as deferred or superseded.
  - Do not add `ocr_languages_requested` or `ocr_acceleration_used` in this
    story. A later task may add richer OCR telemetry only if it can distinguish
    request echo, resolved configuration, and observed OCR-stage execution
    without inference.
  - Mixed state is forbidden: the fields must not remain checked off in
    completed docs unless they are backed by runtime code and tests.
  - Preserve canonical v2 job fields; do not introduce Docling-only side
    channels outside `pdf_options` and `execution`.
- Real-data quality and performance gate:
  - Define a hard/dirty PDF corpus manifest and benchmark/report format before
    tuning.
  - Include scanned, mixed scanned/text, low-contrast, rotated/skewed,
    table/form-heavy, Swedish-diacritic, and long-document cases.
  - Synthetic fixtures may cover regressions, but they are not enough to close
    this story.
  - Private or PII-bearing source PDFs must remain untracked; evidence may use
    sanitized summaries, hashes, page counts, and excerpts only when safe.
- Hemma proof:
  - Run the real-data benchmark through the committed Task 74 production Hemma
    command surface, not a local/in-process run and not a one-off benchmark
    path.
  - Bind every executed private PDF to the metadata-only manifest by verifying
    `source_sha256` before generating dirty-corpus benchmark evidence.
  - Prove Task 76 deploy/runtime parity on the exact revision before accepting
    final dirty-corpus benchmark evidence.
  - Record throughput, stage timings, OCR engine/language metadata, GPU runtime
    evidence, retry/warning counts, and failure classification.
  - Honor Task 74's safe matrix and the current safe 2-worker tuning boundary;
    the removed 4-worker ROCm HIP OOM profile must fail closed unless a later
    governed decision explicitly changes Task 74.
  - Keep GPU-first policy fail-closed; no silent CPU fallback is allowed.
- Architecture:
  - Keep modules SRP-focused and under the repo module-size target.
  - If checkpoint schema changes are required, use an explicit schema/version
    decision and retained-state cleanup/proof rather than hidden compatibility
    shims.

Out of scope:

- Adding a new OCR engine family.
- Changing the public async job model.
- Re-opening the general Gateway/auth cutover.
- Exam.net/DigiExam renderer behavior.

## Decision Checkpoints

Before or inside the linked task slices, decide these points explicitly and
record the outcome in the relevant task doc:

1. Checkpoint metadata model:
   - Option A: add aggregate metadata only to the checkpoint root.
   - Option B: add per-chunk metadata and derive terminal aggregate metadata.
   - Recommendation: Option B. It preserves chunk provenance, supports mixed OCR
     outcomes, and keeps resume/finalization auditable.
1. Real-data corpus handling:
   - Option A: commit sanitized PDFs only.
   - Option B: use a private operator corpus with a committed manifest schema
     and sanitized benchmark reports.
   - Recommendation: Option B plus a tiny committed fixture set for unit
     regressions. The production performance claim must come from real dirty
     data without committing private documents.
1. Performance gate placement:
   - Option A: keep this story as a correctness-only blocker and leave all
     performance proof to Task 74.
   - Option B: make dirty real-data performance a hard gate for this story and
     let Task 74 publish the final tuning report from the same evidence.
   - Recommendation: Option B. The OCR path is not aligned until it survives the
     corpus that will actually hurt it.
1. OCR metadata contract drift:
   - Decision: use Task 269 Outcome B.
   - Rationale: `ocr_languages_requested` is request/configuration echo already
     represented by `pdf_options.ocr_languages`, while
     `ocr_acceleration_used` is not currently observed as a separate OCR-stage
     runtime fact. Reporting either field as active result metadata before it is
     backed by runtime evidence would continue the metadata-truth problem this
     story is meant to remove.
   - Follow-up rule: a future task may add richer OCR telemetry only with a
     precise contract for requested input, resolved configuration, and observed
     OCR-stage execution.

## Proposed Task Slices

- `docs/backlog/tasks/task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth.md`:
  fixed checkpoint/resume OCR metadata truth and added regression coverage for
  the all-chunks-already-complete finalization path. Review 08 re-reviewed and
  approved the slice on 2026-04-29.
- `docs/backlog/tasks/task-269-reconcile-pdf-ocr-metadata-contract-across-docs-runtime-and-tests.md`:
  hard-repair the Story 21 / Task 77 OCR metadata drift across API docs, CLI
  docs, runtime metadata, smoke reports, and tests.
- `docs/backlog/tasks/task-270-add-dirty-pdf-ocr-corpus-manifest-and-benchmark-report-schema.md`:
  extend the Task 74 report schema with hard/dirty corpus manifest support,
  local dry-run validation, privacy safeguards, Task 76 parity fields, and
  fail-closed safe profile classification. The generated synthetic scanned
  corpus remains harness smoke input only and cannot satisfy the real-data
  acceptance gate.
- `docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md`:
  run the safe dirty-corpus OCR benchmark against the production service on
  Hemma, publish sanitized evidence, and define rollback/tuning defaults or a
  documented blocker.

## Acceptance Criteria

- [x] The review finding is closed with a deterministic regression test:
  - a PDF OCR job with all chunks already checkpointed finalizes without
    reprocessing,
  - terminal metadata still reports truthful `backend_used`,
    `acceleration_used`, `ocr_enabled`, `ocr_engine_used`,
    `ocr_languages_used`, warnings, and phase timings.
- [x] Checkpoint state can explain terminal OCR metadata:
  - per-chunk or explicitly aggregated metadata is persisted,
  - mixed OCR/non-OCR chunk outcomes are represented without lying,
  - resumed/finalized jobs are byte-identical to the canonical artifact.
- [x] OCR metadata contract is aligned:
  - v2 API docs, CLI docs, result payloads, smoke evidence, and tests agree on
    the same field names and null/empty-list semantics,
  - result `ocr_languages_used` is `[]` for PDF routes where OCR was applicable
    but not executed, and `null` only where OCR is not applicable,
  - completed Story 21 and Task 77 docs no longer publish false guarantees for
    `ocr_languages_requested` or `ocr_acceleration_used`,
  - Task 269 applies selected Outcome B by explicitly deferring or superseding
    both fields everywhere they appear in active/completed contract language.
- [ ] The real-data gate exists and is mandatory:
  - a corpus manifest describes each dirty input class, page count, source
    hash, OCR language expectation, and privacy/sanitization state,
  - at least one benchmark report is generated from hard/dirty real PDFs,
  - the report records `source_hashes_verified=true` and
    `executed_entry_count=entry_count`,
  - story completion is blocked if only synthetic fixtures have been run.
- [ ] Performance requirements are hard gates:
  - accepted benchmark evidence runs against the production service on Hemma
    and includes baseline and candidate/tuned profile,
  - median wall-clock improves by >= 40% versus baseline for the selected
    corpus, or the story remains open with a documented blocker,
  - the operator 150 PDF-page proof target remains visible: \<= 60 minutes on
    the tuned Hemma profile for a manifest-verified dirty corpus with at least
    150 executed PDF pages unless a later governed decision revises it,
  - dirty-corpus benchmarking extends the Task 74 report schema and command
    surface,
  - Task 76 parity evidence is required for the exact revision under benchmark,
  - unsafe profiles, including the removed 4-worker ROCm HIP OOM profile, fail
    closed unless Task 74 is updated by a later governed decision.
- [ ] Quality requirements are hard gates:
  - Swedish diacritics survive OCR in real dirty inputs where expected,
  - low-confidence/sparse output and OCR retry warnings are visible in reports,
  - failures are classified by input quality, engine/runtime availability,
    timeout, GPU/resource pressure, or conversion bug.
- [ ] GPU-first governance holds:
  - GPU-required runs fail closed when ROCm/CUDA evidence is unavailable,
  - no runtime silently changes to CPU OCR for a GPU-required job,
  - any CPU-only local test mode is clearly smoke/schema/regression only and
    cannot masquerade as performance, throughput, tuning, acceptance, or
    production proof,
  - smoke assertions and smoke command stdout do not print or assert p50/p90,
    latency, pages-per-minute, throughput, or improvement percentages.

## Test Requirements

- [x] Unit/contract tests for checkpoint metadata aggregation and resume
  finalization when zero new chunks are converted.
- [ ] API/manifest tests for `conversion_metadata` OCR fields and null/list
  semantics.
- [ ] Focused Docling backend tests for `ocr_mode=auto`, `force`, and `off`
  metadata truth under resolved EasyOCR/Tesseract settings.
- [x] Dirty-corpus harness tests that validate manifest/report schema without
  requiring private PDFs in the repository.
- [ ] Hemma live benchmark command producing deterministic JSON/Markdown report
  artifacts under `build/verification/` or `build/benchmarks/`.
- [ ] Closeout gates:
  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run typecheck-all`
  - focused `pdm run pytest-root <ocr/checkpoint/tests>`
  - `pdm run coverage-gate` when conversion-core coverage applies
  - `pdm run docs-sync`
  - `pdm run docs-validate`
  - `pdm run skills-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

## Done Definition

The v2 PDF OCR path can be restarted, resumed, finalized, inspected, and tuned
without metadata drift. The story is not done until the hard/dirty real-data
benchmark has run on Hemma or a governed blocker explains why it could not run.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
