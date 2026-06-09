---
id: task-343-investigate-pdf-conversion-decision-logic-and-gpu-cpu-performance-attribution
title: Investigate PDF conversion decision logic and GPU CPU performance attribution
type: task
status: in_progress
priority: high
created: '2026-06-04'
last_updated: '2026-06-05'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-273-run-chunk-size-8-production-baseline-tuning-proof-with-warm-up-and-gpu-sampling.md
  - docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md
  - docs/backlog/tasks/task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking.md
  - docs/backlog/tasks/task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs.md
  - docs/backlog/tasks/task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure.md
  - docs/converters/sir_convert_a_lot.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/runbooks/runbook-hemma-conversion-benchmarks.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - scripts/sir_convert_a_lot/infrastructure/backend_routing.py
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpoint_chunk_runner.py
  - scripts/sir_convert_a_lot/benchmarking/story20_throughput_cli.py
labels:
  - performance
  - gpu
  - cpu
  - docling
  - easyocr
  - processing-decisions
  - benchmark
  - decision-logic
---

PR-sized execution unit; may be linked to a story or standalone.

## User Intent and Goal Alignment

The user intent is to stop treating GPU-backed conversion as a black box. Very
long GPU-lane conversion times must be explained by evidence about the current
code, library settings, runtime configuration, and Hemma hardware behavior.

The implementation and investigation must answer these product questions:

- Is the CLI/runtime choosing the right processing settings for the actual
  document inside the approved quality pipeline?
- Is the GPU genuinely busy on useful work, or are CPU work, small batches,
  page/chunk serialization, model initialization, synchronization, or library
  defaults dominating wall-clock time?
- Which settings materially affect processing efficiency while preserving
  output quality and parity?
- Which input features should drive quality-preserving processing decisions and
  user-visible explanations inside the approved pipeline?
- What evidence should be shown to users/operators when heavy processing is
  required and therefore expected to take longer?

The first remediation path is to diagnose and tune the current pipeline itself.
Do not treat the current Docling/OCR/chunk execution path as an optimized
invariant. The existing pipeline is mutable: pipeline options, batch sizing,
threading, OCR worker behavior, converter/model reuse, chunk/page-window
execution, warm-up, CPU thread pressure, ROCm/PyTorch interaction, and
instrumentation are all in scope when evidence points there.

No trial-and-error tuning is allowed. Every tuning change must be tied to a
specific low-level hypothesis, a controlled measurement, and parity-preserving
acceptance evidence.

## Objective

Investigate and harden PDF conversion decision logic and GPU/CPU performance
attribution for the current Hemma production service. The outcome must be an
evidence-backed recommendation for current-pipeline tuning, settings,
profiling, and benchmark next steps before changing production defaults. Routing
around the current quality pipeline is not an acceptable remediation outcome.

## Current Implementation Gaps

1. Processing decisions are strategy-based, not document-aware.

   - Current behavior: `backend_strategy="auto"` selects Docling; `pymupdf`
     is used only when explicitly requested and is blocked for GPU/OCR modes.
   - Gap: no decision model considers selectable text density, scanned-page
     ratio, page count, layout complexity, tables/forms, formula density, image
     density, OCR language needs, or expected parity-preserving processing path.
   - Recommendation: introduce a preflight classification surface that records
     input features and produces typed processing-setting decisions and reasons
     within the approved quality pipeline. Do not use this as route-bypass
     authority.

1. Current pipeline tuning is under-specified.

   - Current behavior: the service has a working Docling/OCR/checkpoint path,
     but the repo does not prove that its low-level settings match Hemma's
     actual CPU/GPU behavior.
   - Gap: current code and settings are too easily treated as fixed instead of
     the first object of diagnosis.
   - Recommendation: inspect and tune the current pipeline first, including
     Docling pipeline class/options, OCR/layout batch sizes, EasyOCR worker and
     model reuse behavior, chunk scheduling, CPU thread pressure, warm-up,
     ROCm/PyTorch profiler traces, and GPU memory/busy sampling.

1. "GPU accelerated" does not prove efficient GPU utilization.

   - Current behavior: GPU availability is probed and Docling is configured
     with an accelerator device, but previous benchmarks show long wall-clock
     times and limited improvement from safe parallel profiles.
   - Gap: benchmark evidence does not yet isolate CPU time, GPU kernel time,
     GPU busy gaps, memory pressure, model initialization, batch sizes, and
     per-stage bottlenecks.
   - Recommendation: add an attribution benchmark/profiling lane that captures
     CPU/GPU stage timings, ROCm sampling, and PyTorch profiler evidence for
     bounded representative runs.

1. Docling performance knobs are not explicit in the runtime profile.

   - Current code uses `PdfPipelineOptions` and sets device, OCR, table
     structure, formula enrichment, and layout model.
   - Current Docling docs expose `ThreadedPdfPipelineOptions` with
     `ocr_batch_size`, `layout_batch_size`, and `table_batch_size` for GPU
     performance tuning.
   - Gap: current production settings do not document or expose these batch
     controls as governed profile fields.
   - Recommendation: benchmark current `PdfPipelineOptions` against a bounded
     `ThreadedPdfPipelineOptions` candidate matrix before adopting any default.

1. OCR batching and EasyOCR behavior are opaque.

   - EasyOCR supports GPU mode, model storage, `batch_size`, `workers`, and
     batched inference surfaces.
   - Gap: current service evidence does not show whether Docling/EasyOCR is
     reusing OCR models efficiently, batching page/box recognition, or
     serializing tiny OCR calls that underfeed the GPU.
   - Recommendation: capture OCR-stage profiling and compare quality-preserving
     OCR settings only inside the approved pipeline. Do not introduce
     selectable-text or PyMuPDF bypass routing as a remediation path.

1. Formula/table/layout quality features may be expensive but are always tied
   to broad presets.

   - Current behavior: accurate table mode enables formula enrichment; ordering
     quality gates can trigger layout fallback attempts; `auto` OCR can run a
     no-OCR pass followed by full OCR retry.
   - Gap: the user cannot see whether time is spent on formula fallback,
     ordering fallback, no-OCR retry, OCR retry, layout detection, table
     structure, or artifact persistence.
   - Recommendation: preserve these quality features, but attribute their cost
     explicitly and use input-aware decisioning for when each is required.

1. Source-layer formula evidence is not part of conversion decisioning.

   - Current behavior: formula VLM enrichment can run on born-digital PDFs even
     when OCR is disabled and the PDF source layer exposes usable formula/text
     evidence.
   - Gap: broad GPU/performance attribution can misclassify formula VLM latency
     as unavoidable quality work, and candidate-only quality checks can still
     accept hallucinated formulas.
   - Recommendation: Task 345 must feed this task with source-layer formula
     evidence metrics and formula-authority decisions so the conversion
     decision model distinguishes necessary VLM work from source-backed regions
     where generative output should be skipped, advisory, or rejected. Task 343
     must consume the shared Task 345 evidence/authority model and must not
     reimplement formula source-layer extraction or formula-authority policy.

1. Specialist formula/OCR candidate evidence is not yet separated from
   infrastructure choices.

   - Current behavior: the conversion lane has concrete Granite/Docling
     incident evidence, but no small, controlled comparison against
     formula-specialist alternatives on the same pages/crops.
   - Gap: production integration, dependency, or infrastructure choices could
     be made before proving whether UniMERNet, PP-FormulaNet, DeepSeek-OCR-2,
     or a current baseline actually improves the incident-class output.
   - Recommendation: consume Task 346's pre-infrastructure evaluation report as
     the candidate-quality and candidate-timing input. Task 343 may use those
     measurements for later decision policy, but must not duplicate the Task
     346 evaluation harness or Task 345 formula-authority policy.

1. Benchmark tasks are close but not enough for root-cause attribution.

   - Task 74 and Task 273 define throughput and chunk-size tuning evidence.
   - Gap: they do not yet require library-level profiling or conversion
     decision-policy analysis.
   - Recommendation: Task 343 should feed Task 74/273 with profiler-backed
     hypotheses and candidate profile dimensions.

## PR Scope

- Inventory the current production PDF path from CLI job spec through backend
  selection, OCR resolution, Docling options, chunk execution, progress updates,
  and benchmark reporting.
- Diagnose and tune the current Docling/OCR/checkpoint pipeline. Route bypass
  or selectable-text bypass is forbidden as a remediation fix, regardless of
  what low-level inspection finds.
- Produce a low-level attribution map for the existing pipeline:
  - CPU time,
  - GPU kernel/busy time,
  - launch/synchronization gaps,
  - model initialization/warm-up cost,
  - OCR/layout/table/formula timing,
  - chunk extraction and checkpoint/artifact persistence,
  - worker queue/saturation behavior.
- Capture current Hemma runtime facts without changing active jobs:
  - CPU model/core pressure,
  - GPU runtime kind,
  - GPU busy and memory sampling,
  - worker/chunk saturation,
  - service env profile,
  - Docling/EasyOCR/PyTorch/ROCm versions.
- Define a document preflight feature model for conversion decisioning.
- Include formula-specific source-layer evidence in the decision model so
  born-digital/source-backed formula regions do not require generative VLM work
  merely because accurate tables or broad formula enrichment are enabled.
- Consume Task 346 candidate-evaluation measurements before adding specialist
  formula/OCR model choices to the decision matrix.
- Define a decision matrix for allowed processing choices inside the current
  quality pipeline:
  - Docling quality-first,
  - Docling parity-preserving tuned profile,
  - OCR-off/auto/force variants when they preserve parity inside the approved
    pipeline,
  - table/formula accurate variants where heavy processing is actually needed.
- Add or amend benchmark/profiling commands only after red-first tests and
  docs authority are in place.
- Record findings in a sanitized report with recommended product defaults,
  open risks, and next implementation tasks.

## Out of Scope

- Changing production defaults without benchmark/profiler evidence.
- Treating current pipeline code/settings as already optimized or off-limits.
- Implementing or recommending route bypass, selectable-text bypass, or routing
  around the current quality pipeline as remediation, even if low-level
  inspection identifies bottlenecks.
- Silently routing GPU-required work to CPU-only paths.
- Removing quality features such as formula/table/layout handling without an
  explicit product decision and quality gate.
- Using quality reduction, scraping-style extraction, or "fast" conversion as a
  solution to the current performance issue.
- Adding toy heuristics for processing decisions. Any simpler processing
  setting must use proven, high-quality implementation methods or libraries and
  must demonstrate output parity inside the approved pipeline.
- Running destructive Hemma operations, canceling active conversions, or
  pruning artifacts.

## Investigation Hypotheses

- Current Docling pipeline options may not be using GPU-friendly batch sizes,
  causing low GPU occupancy despite GPU availability.
- Current Docling pipeline class and option wiring may be leaving supported
  library-level GPU batching/threading controls unused.
- Chunk size/page-window execution may be too small or too serialized to keep
  layout/OCR GPU stages saturated.
- `ocr_mode=auto` may double-run expensive pages: first no-OCR, then full OCR
  retry.
- Formula enrichment, ordering fallback, and accurate table structure may be
  dominating runtime for academic PDFs where heavy processing may or may not be
  required to preserve parity.
- EasyOCR model/cache initialization or OCR worker settings may be adding
  repeated CPU/GPU overhead.
- ROCm utilization sampling may be too coarse or wrong-lane, producing
  misleading all-zero or low-signal evidence.

## 2026-06-04 Runtime Evidence

Read-only Hemma inspection captured these production facts without canceling,
restarting, or mutating active jobs:

- Service revision: `fe195ba440c727ad081dee58a9a5d3525f7fe022`.
- Worker profile:
  - `SIR_CONVERT_A_LOT_MAX_WORKERS=1`
  - `SIR_CONVERT_A_LOT_ENABLE_PARALLEL_PDF_CHUNKS=1`
  - `SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS=2`
  - `SIR_CONVERT_A_LOT_PDF_CHUNK_SIZE_PAGES=4`
  - `SIR_CONVERT_A_LOT_GPU_STAGE_MAX_CONCURRENCY` unset, so the runtime
    effective GPU-stage limit was `1`.
- Runtime libraries in the GPU worker:
  - Docling `2.73.1`
  - EasyOCR `1.7.2`
  - PyTorch `2.10.0+rocm7.1`
- Current Docling docs and installed runtime both expose
  `ThreadedPdfPipelineOptions` and batch fields (`ocr_batch_size`,
  `layout_batch_size`, `table_batch_size`), but the current backend constructs
  `PdfPipelineOptions` and does not expose governed batch controls.
- Current code uses a thread-local converter cache. With chunk workers, model
  reuse may be per worker thread rather than global; this needs measurement
  before tuning.
- Current terminal GPU snapshots are insufficient for attribution because they
  sample after completion and do not explain GPU busy gaps during long chunks.

The incident jobs separated queue wait from conversion time:

- `jobv2_9daddbc98ee8457ba7e0034dd5` was queued for about 47 minutes but
  converted in about 6 seconds.
- `jobv2_63a3d3533e154af1887a61f31d` converted 21 pages in about 64 minutes.
  Its chunk commits showed highly uneven chunk durations, including a roughly
  35-minute chunk gap for pages 13-16.

## 2026-06-04 Attribution Defects Fixed

Two telemetry defects blocked trustworthy performance diagnosis:

- Chunk checkpoint records wrote `started_at` and `completed_at` at commit time,
  after conversion had finished. Long-running chunk chronology was therefore
  misleading.
- Runtime conversion emitted `backend_convert_ms` and `normalize_ms`, but v2
  canonical timing normalization dropped those keys. At the same time, accurate
  Docling conversion labeled the whole Docling attempt as
  `formula_enrichment_ms`, so production progress made the entire backend call
  look like formula-only time.

Implemented first attribution slice:

- Chunk conversion outcomes now carry worker-boundary `started_at` and
  `completed_at` timestamps into checkpoint records.
- Runtime conversion keeps legacy timing names for old consumers while also
  emitting canonical `ocr_layout_extract_ms` and `markdown_normalize_ms`.
- Docling accurate-table guarded conversion now reports whole Docling attempt
  time under the broader canonical extraction timing instead of the misleading
  formula-only label.

This is not yet a production tuning claim. It gives the next Hemma exercise a
trustworthy timing baseline; profiler-backed GPU/CPU attribution and Docling
threaded/batch-size tuning remain open.

## Deliverables

- [ ] Current-state codepath map from CLI options to backend/library settings.
- [ ] Current-state production runtime inventory for Hemma GPU worker.
- [ ] Current-pipeline low-level attribution report with measured bottlenecks
  and concrete tuning candidates.
- [ ] Evidence-backed tuning plan for the existing Docling/OCR/checkpoint path
  with route-bypass explicitly excluded as remediation.
- [ ] Sanitized profiler/benchmark plan for CPU/GPU attribution.
- [ ] Conversion decision feature model and parity-preserving processing-setting
  decision matrix.
- [ ] Recommendation on whether to implement a preflight decision engine before
  additional benchmark sweeps.
- [ ] Recommendation on Docling/EasyOCR/PyTorch profiling and tuning candidates.
- [ ] Updated Task 74/273 follow-up guidance if their benchmark matrix should
  change.

## Acceptance Criteria

- [ ] The investigation identifies every major stage that can plausibly dominate
  wall-clock: preflight, PDF splitting, Docling layout, OCR, table structure,
  formula enrichment, ordering fallback, normalization, checkpoint/artifact
  persistence, and queue/worker wait.
- [ ] The report distinguishes GPU availability from GPU utilization and
  includes CPU/GPU attribution methods.
- [ ] The current pipeline is explicitly inspected and tuned where evidence
  supports it; the investigation must not declare route selection or bypass as a
  solution at any point.
- [ ] Every tuning proposal is linked to a measured bottleneck and includes a
  parity-preserving validation gate. Random sweeps or undocumented trial-and-error
  parameter changes do not satisfy this task.
- [ ] The conversion decision model records input features, selected
  processing settings, decision reasons, parity evidence, and user-visible
  explanation when heavy processing is required.
- [ ] Recommendations are evidence-backed and conservative: no production
  default changes without passing Task 76 parity plus benchmark/profiler gates.
- [ ] Product decision questions are explicitly closed or carried forward as
  blockers before implementation.

## Closed Product Decisions

1. The first solution path is low-level tuning of the current pipeline.

   - The current Docling/OCR/chunk/checkpoint path is not an optimized invariant.
   - Diagnose and tune the current implementation. Route bypass,
     selectable-text bypass, or routing around the current quality pipeline is a
     forbidden remediation outcome.
   - Tuning must be hypothesis-driven and measurement-backed, not trial and
     error.

1. `auto` is quality-first.

   - Performance must not be solved by lowering output quality.
   - Adaptive processing decisions may tune settings only inside the approved
     quality pipeline, and only when quality and output parity are preserved.

1. Product profiles are a good direction, but not a shortcut for this task.

   - Normal users should get profiles instead of raw backend/OCR/table flags in
     a later product slice.
   - Do not introduce `balanced` or `fast` profiles as a remediation for the
     current issue.
   - Raw flags remain available only when explicitly requested by operators.

1. No quality loss is acceptable for this remediation.

   - Sir Convert is not running a scrape operation. Faster processing is valid
     only when it preserves quality and output parity.

1. Selectable-text PDFs should avoid unnecessary heavy processing only inside
   the approved quality pipeline when heavy stages are not needed.

   - This is required to preserve quality and output parity without wasting
     GPU-heavy processing.
   - This must not use toy heuristics or hand-drawn rules from memory.
   - The implementation must use proven, high-quality methods or libraries and
     must be validated against parity evidence.
   - This does not permit PyMuPDF bypass, selectable-text bypass, or any route
     around the current quality pipeline as remediation.

1. The benchmark matrix should include Docling threaded/batch-size profiles.

   - Include them only after a profiler-backed candidate matrix proves the
     settings are valid on Hemma ROCm.

1. Do not frame this as a "slow lane."

   - The user-facing explanation should say why heavy processing is required,
     what evidence led to that decision, and what progress/runtime signals are
     available. It must not imply quality can be traded away for speed.

## Remaining Product Question

1. Which proven PDF analysis library or library combination should be the
   canonical preflight implementation for parity-preserving processing-setting
   decisions?
   - Recommendation: decide only after primary-doc/library research and a small
     evidence spike. No hand-written heuristic implementation is acceptable.

## Validation Commands

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Implementation follow-up must also run:
  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run typecheck-all`
  - focused `pdm run pytest-root <tests>`
  - `pdm run coverage-gate` when conversion-core behavior changes

## Checklist

- [ ] Implementation complete
- [x] Validation complete for first attribution-correction slice
- [x] Docs updated for first attribution-correction slice
