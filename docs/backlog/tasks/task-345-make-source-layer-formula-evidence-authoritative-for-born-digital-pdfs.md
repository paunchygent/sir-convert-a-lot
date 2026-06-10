---
id: task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs
title: Make source-layer formula evidence authoritative for born-digital PDFs
type: task
status: in_progress
priority: high
created: '2026-06-05'
last_updated: '2026-06-10'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md
  - docs/backlog/tasks/task-343-investigate-pdf-conversion-decision-logic-and-gpu-cpu-performance-attribution.md
  - docs/backlog/tasks/task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking.md
  - docs/backlog/tasks/task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure.md
  - docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - scripts/sir_convert_a_lot/infrastructure/docling_formula_authority.py
  - scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py
  - scripts/sir_convert_a_lot/infrastructure/docling_formula_quality.py
  - scripts/sir_convert_a_lot/infrastructure/runtime_conversion.py
  - scripts/sir_convert_a_lot/devops/docling_page_window_replay.py
labels:
  - pdf
  - docling
  - formula
  - source-layer
  - born-digital
  - quality
  - cli-progress
  - conversion-decision
---

PR-sized execution unit; may be linked to a story or standalone.

## User Intent and Alignment

The user intent is to fix formula conversion quality and instability at the
root, while preserving the quality-first product contract for `auto`.

This task is the implementation bridge between the concrete Task 344 incident
evidence and the wider conversion-product changes already captured in Tasks 342
and 343:

- Task 342 owns CLI progress, manifest visibility, idempotent replay feedback,
  and user-visible explanations for long or heavy conversion work.
- Task 343 owns the broader conversion decision model and GPU/CPU attribution
  for quality-preserving processing choices.
- Task 344 owns the already-proven Docling/Granite formula VLM stopless
  generation failure and the runtime controls that prevent non-returning
  generation.

Task 345 owns the remaining product-critical quality authority question:
when a born-digital PDF already exposes usable source-layer formula/text
evidence, generative formula VLM output must not be allowed to overwrite that
evidence unless a governed acceptance check proves it is faithful.

This is not a lower-quality profile and not a bypass around Docling. It is a
quality-preserving authority policy inside the approved conversion path.

The larger product invariant is best-effort conversion. PDF-to-Markdown and
PDF-to-other-structured targets cannot promise perfect semantic recovery for
every PDF object, especially formulas and LaTeX-like mathematical notation, but
Sir Convert must make the best recoverable representation as robust as possible
and publish that representation in the conversion artifact. Detection gates are
not a way to drop hard regions back on the user; they are decision points for
choosing the least-lossy available representation and recording why.

## Task Ordering Contract

Task 345 must land the shared formula evidence and authority substrate before
later CLI, conversion-decision, or benchmark work builds on it.

- Task 345 owns the source-layer formula evidence data model, the formula
  authority decision model, the extraction adapter contract, and the policy that
  decides whether generated formula output is skipped, advisory, rejected, or
  committed.
- Task 342 owns presentation only: it consumes Task 345 metadata and renders
  safe CLI/manifest/status feedback. It must not parse PDFs, inspect formula
  crops, classify source-layer evidence, or duplicate formula-authority policy.
- Task 343 owns later conversion-decision and performance-attribution use of
  Task 345 metrics. It must not build a second source-layer formula extractor or
  second formula-authority policy.
- Task 344 owns generation-stability evidence and replay harnesses. It does not
  own output authority for source-backed formulas.
- Task 346 owns pre-infrastructure evaluation of specialist formula/OCR
  candidates such as UniMERNet, PP-FormulaNet, and DeepSeek-OCR-2 on the
  established Task 344 incident pages and crops. It does not own production
  formula authority, artifact representation, CLI presentation, or conversion
  decision policy.
- Task 74/273 benchmark work must consume Task 345's authority outcomes before
  treating formula VLM latency as unavoidable conversion cost.

No later task may reimplement formula source-layer extraction or formula
authority decisions. Later tasks may extend the shared Task 345 model only by
amending this task or creating a governed follow-up that explicitly preserves
the single-owner boundary. No candidate model replacement or formula-lane
infrastructure may be promoted from Task 346 evidence without preserving Task
345's authority and best-effort representation contracts.

## Task 345 Internal Tranche Contract

Task 345 must complete its own implementation in this order. Later tranches may
consume earlier tranche outputs, but they must not reimplement them or jump
ahead by inventing substitute metadata, presentation, or conversion-decision
logic.

1. **Evidence and Authority Substrate**

   Own and implement the shared source-layer formula evidence model, extraction
   adapter, and formula authority decision model. This tranche defines what
   `usable`, `partial_or_unusable`, and `absent` mean for production code.

   Status: initial document-level substrate and Docling fallback-boundary guard
   implemented on 2026-06-06.

1. **Best-Effort Representation Ladder**

   Define and implement the artifact representation choices after authority is
   resolved. This tranche decides what Markdown contains for accepted,
   rejected, partial, unusable, or absent formula evidence. It must preserve the
   best-effort conversion contract: no formula region may disappear merely
   because generated LaTeX was rejected.

   This tranche must be implemented before CLI/manifest presentation or Task
   343 conversion-decision work consumes formula-authority outcomes.

1. **Per-Region/Page-Window Reconciliation**

   Apply the authority and representation decisions at the smallest reliable
   production unit available in the current Docling output path: formula region
   when stable identifiers/coordinates are available, otherwise page-window
   formula batches with explicit limitations. This tranche owns how source
   evidence, generated candidates, and final Markdown are reconciled.

   This tranche may extend the evidence model, but it must not create a second
   extractor or second authority policy.

1. **Runtime Metadata Contract**

   Emit stable formula-authority metadata only after the representation and
   reconciliation decisions exist. Metadata must report what happened
   (`skipped`, `advisory`, `accepted`, `rejected`, or `fallback`) and why,
   without exposing raw prompts, crops, or generated formula internals.

1. **Task 342 Presentation Consumption**

   Task 342 may render the Task 345 metadata in CLI progress, manifests, and
   status output after the metadata contract exists. Task 342 remains
   presentation-only and must not inspect PDFs or make formula-authority
   decisions.

1. **Task 343 Decision/Performance Consumption**

   Task 343 may use Task 345 evidence, authority outcomes, and timings after
   the metadata contract exists. Task 343 owns broader conversion decisioning
   and GPU/CPU performance attribution, not formula extraction or formula
   authority.

1. **Incident Replay and Accepted-Artifact Review**

   Re-run the Task 344 incident pages `13-16` after the representation and
   reconciliation tranches are implemented. The replay must inspect accepted
   Markdown, not only intermediate candidate metrics, for recurrence of known
   hallucination/leakage markers.

## Objective

Make source-layer evidence authoritative for formula output on born-digital
PDFs so Docling's code/formula VLM enrichment cannot commit hallucinated,
malformed, or runaway LaTeX where selectable/vector source evidence is already
available and usable.

The implementation must preserve the Task 344 generation stability fix, feed
Task 343's conversion decision model with source-layer formula evidence, and
surface the resulting formula-authority decisions through the Task 342
CLI/manifest feedback path.

The output objective is not merely to reject bad VLM output. The conversion
must still produce the best-effort artifact:

1. preserve usable source-layer formula/text evidence when available,
1. accept generated LaTeX only when it passes the source-backed or no-source
   quality gate,
1. otherwise emit the least-lossy explicit fallback representation available,
   with safe metadata/warnings, instead of silently omitting the formula region
   or publishing hallucinated markup.

## Evidence Basis

Task 344 produced the governing evidence for this task:

- The failing incident window was localized to Docling's formula/code VLM path,
  specifically Transformers generation through the Granite Docling formula
  mode.
- Forwarding model stop strings and generation controls fixed the stopless
  page-14 loop: target formula calls now complete by stop criteria instead of
  `max_new_tokens`.
- The post-fix pages `13-16` replay still failed output correctness. The
  generated Markdown contained leaked `</formula` fragments and repeated
  hallucinated formula text.
- The pre-remediation full Markdown conversion did not contain the exact
  post-fix leakage markers, but it already contained formula transcription
  hallucinations such as corrupted prose/math tokens. The quality problem
  therefore predates the no-repeat remediation.
- The replay ran with `ocr_enabled=false`. Classic OCR was not the cause:
  Docling formula enrichment is a separate VLM transcription path that can run
  even when OCR is off.
- Source-layer inspection of the incident PDF showed readable born-digital text
  and equation material through PDF text extraction libraries. This evidence is
  not semantic LaTeX, but it is more faithful than the observed Granite
  hallucinations.

Docling and PyMuPDF documentation already reviewed for the preceding
investigation supports the implementation direction:

- Docling formula enrichment is an optional pipeline feature, separate from
  OCR.
- PyMuPDF exposes page text, words, and raw glyph dictionaries with coordinate
  clipping, allowing source-layer evidence to be gathered for formula regions
  in born-digital PDFs.

## Pre-Implementation Scrutiny Gate

Before production implementation starts, prove that the assumptions behind the
source-backed authority policy hold for the incident class and fail safely when
they do not.

The gate must prove all of the following with primary/current library docs and
read-only probes:

- The selected source-layer library supports coordinate-backed page extraction
  for text/words/raw characters or an equivalent structured source-layer
  surface.
- Docling formula enrichment remains an optional enrichment path, so formula
  authority can be decoupled from OCR and table accuracy without route bypass.
- The incident PDF class is genuinely born-digital/source-backed, not merely a
  raster OCR case.
- The affected pages expose enough source-layer text/formula evidence to make
  source preservation a plausible quality authority.
- The implementation does not assume all PDFs, fonts, or extractors are usable.
  The model must represent at least `usable`, `partial_or_unusable`, and
  `absent` evidence states.

Completed 2026-06-06 scrutiny evidence:

- Context7/PyMuPDF docs confirm `page.get_text("text", clip=rect)`,
  `page.get_text("rawdict", clip=rect)`, and word extraction with bounding
  boxes.
- Context7/Docling docs confirm `PdfPipelineOptions.do_formula_enrichment` and
  `CodeFormulaVlmOptions.from_preset(...)` as optional formula-enrichment
  configuration separate from ordinary OCR.
- `pdfinfo build/verification/task-344-md-review-20260605T112725Z/input.pdf`
  reports `Creator: LaTeX with hyperref`, `Producer: pdfTeX-1.40.22`, and
  `Pages: 21`.
- `pdffonts` reports many embedded Type 1 Computer Modern/math fonts with
  Unicode maps, plus some Type 3 fonts without Unicode maps. Therefore source
  evidence is real but must be classified per region; it is not globally
  trustworthy by file type alone.
- `pdftotext -f 13 -l 16 -layout ...` extracts readable formula-heavy source
  text and equations for the affected pages. The local command returned `284`
  layout-text lines containing the affected appendix equations and surrounding
  prose, including `Laplace`, `Bradley-Terry`, `det`, `sigma`, `arg max`,
  `E[...]`, `SummEval`, `TopicalChat`, and `license` contexts.
- The persisted replay report confirms the failure was in the formula
  enrichment path with `backend_used: docling`, `acceleration_used: cuda`,
  ROCm-backed Torch `2.10.0+rocm7.1`, `formula_enrichment: true`,
  `formula_preset_only: granite_docling`, `ocr_enabled: false`, and
  `table_mode: accurate`.
- A read-only PyMuPDF probe on pages `13-16` returned coordinate-backed source
  material with word bounding boxes, raw block counts, raw character counts, and
  clipped text:
  - page `13`: `516` words, `64` raw blocks, `2700` raw characters,
  - page `14`: `561` words, `50` raw blocks, `2664` raw characters,
  - page `15`: `369` words, `37` raw blocks, `2161` raw characters,
  - page `16`: `358` words, `20` raw blocks, `2340` raw characters.
    The first extracted word on every page carried a bounding box, e.g. page `14`
    returned `(70.3435, 71.7245, 99.4286, 84.8707, "Which")`.
- Poppler `pdftotext -bbox` and `-bbox-layout` crash on incident page `14` with
  `std::out_of_range` and return `-1`, so the implementation must not rely on a
  single brittle extractor path or treat coordinate extraction as guaranteed.
- The persisted bad Markdown still contains accepted-output hallucination
  markers such as leaked `</formula`, repeated `\mathbf`, `\mathbmath`, and
  stray words including `looly`. The focused marker counts were `36` leaked
  `</formula`, `2` `\mathbmath` lines, `4` `\mathbf` lines, and `1` `looly`
  line in the persisted affected-window Markdown.

Gate result: **completed, passed in qualified form**.

The source-backed policy survives simple scrutiny only as a classified
authority policy. Source-layer evidence exists for the incident pages and can
be made coordinate-backed with PyMuPDF, but extraction quality varies by font,
region, and extractor. Production implementation may therefore apply
source-layer authority only when the shared evidence model classifies the
region as `usable`. Regions classified as `partial_or_unusable` or `absent`
must remain explicit fallback states and may exercise the governed formula VLM
path with the Task 344 runtime controls.

This gate does not solve the conversion-quality problem by itself. Its purpose
is to prevent a known-bad candidate from becoming authoritative and to force
the implementation to choose an explicit best-effort representation for each
formula region.

## Product Decisions

- `auto` remains quality-first. Quality is not a lever for solving the current
  issue.
- Do not add raw CLI flags for backend/OCR/table/formula internals in this
  slice.
- Do not introduce a `slow` lane.
- Do not use "fast" or "balanced" as the remediation. Future named profiles
  may exist only as separate product work.
- Do not route around the approved conversion path as a fix.
- Always prefer source-layer preservation when it retains quality and output
  parity. This is the quality path for born-digital/source-backed formula
  regions, not a scrape operation.
- Do not use PyMuPDF text extraction as the final formula/LaTeX conversion
  method. Task 346 showed that PyMuPDF source-layer extraction is useful as
  source-backed evidence, localization, contradiction checking, and fallback
  substrate, but it does not preserve enough formula structure to restore
  faithful semantic LaTeX deterministically.
- Do not use toy complexity heuristics. Source-layer authority must be based on
  proven PDF extraction libraries, coordinate-backed evidence, and explicit
  acceptance criteria.
- Generative formula VLM output is advisory for source-backed formula regions
  until proven faithful. It may be authoritative only for regions where source
  evidence is absent or unusable and the candidate passes the formula-quality
  gate.
- The current Docling/Granite formula/LaTeX representation path is not an
  inscrutable invariant. The formula extraction, candidate generation,
  acceptance, merge, and fallback representation stages may be improved,
  replaced, or refactored when evidence shows a better quality-preserving
  method inside the approved conversion product path.
- Candidate model replacement must be evidence-led. Task 346 must run the
  pre-infrastructure evaluation before any UniMERNet, PP-FormulaNet,
  DeepSeek-OCR-2, or similar specialist candidate is promoted into production
  formula-lane design.
- `partial_or_unusable` and `absent` evidence states must never mean "drop the
  region." They mean the artifact builder must choose the best available
  fallback representation and emit safe metadata/warnings.

## Current Implementation Gaps

2026-06-06 implementation checkpoint:

- Added `scripts/sir_convert_a_lot/infrastructure/docling_formula_authority.py`
  with explicit `usable`, `partial_or_unusable`, and `absent` evidence states,
  a PyMuPDF-backed coordinate/raw/text source-layer extraction adapter, and a
  formula authority decision model.
- Wired the initial authority policy into
  `scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py`.
  When source-layer evidence is classified `usable` and the generated formula
  path has already shown structural quality defects, Docling now reruns the
  same conversion pass with `formula_enrichment=false` and emits
  `docling_formula_source_backed_vlm_rejected` instead of committing the VLM
  candidate.
- Preserved the no-source/absent-source behavior: if source-layer evidence is
  `absent`, the existing CodeFormulaV2 -> Granite fallback path remains
  available and may still commit a structurally clean Granite candidate.
- Added red-first and focused tests proving both sides of the boundary:
  `tests/sir_convert_a_lot/test_docling_formula_authority.py` and
  `tests/sir_convert_a_lot/test_docling_backend.py`.
- Scope caveat: this checkpoint is a document-level/source-layer authority
  substrate and Docling fallback-boundary guard. It does not yet implement
  per-region Markdown merge/reconciliation, CLI/manifest metadata, or the
  incident pages `13-16` accepted-output replay.

2026-06-10 formula-hardening checkpoint:

- Split the oversized Task 350 candidate adapter
  `scripts/sir_convert_a_lot/devops/formula_candidate_eval_candidates.py` into
  focused candidate spec, command, output, and execution modules before adding
  any further DeepSeek code.
- Changed source-backed formula authority from post-generation rejection to a
  pre-generation skip for usable source-layer evidence. When PyMuPDF
  coordinate/raw/text evidence is classified `usable`, Docling now runs with
  `formula_enrichment=false` while preserving `table_mode=accurate`; generative
  formula VLM output is not attempted for that page window.
- Preserved the no-source/absent-source ladder: CodeFormulaV2 remains the
  primary formula path, Granite remains the fallback candidate when the primary
  path has placeholders/structural defects, and a runtime-unavailable formula
  lane falls back to non-formula source-layer Markdown with explicit authority
  metadata.
- Added page-window reconciliation for the current production surface by
  appending a deterministic
  `sir-convert-a-lot:formula-authority` marker to accepted Markdown when a
  formula authority decision changes representation. The current stable unit is
  page-window because reliable final Markdown formula-region identifiers are
  not yet available.
- Added structured `formula_authority` metadata to backend results,
  `ConversionMetadata`, and the page-window replay report. The metadata reports
  `scope`, `action`, source evidence state/method/counts, representation,
  `vlm_attempted`, reason, and warning codes; it does not expose prompts, crops,
  or generated formula internals.
- Reran the accepted pages `13-16` Markdown path on Hemma:
  `build/verification/task-345-source-backed-formula-authority-replay/docling-page-window-replay-20260610T055608Z/report.json`.
  The replay succeeded in `15325 ms` parent elapsed / `7880 ms` child payload
  elapsed with `formula_enrichment=false`, `table_mode=accurate`,
  `formula_vlm_batch_count=0`, `transformers_call_count=0`,
  `formula_authority.action=skipped`, and
  `formula_authority.source_evidence_state=usable`.
- Accepted Markdown review found no recurrence of the known bad accepted-output
  markers `</formula`, `\mathbmath`, repeated `\mathbf`, spaced `l o o l y`,
  `<loc_`, `<formula>`, or observed DeepSeek/vLLM repetition markers. The
  accepted artifact still contains explicit `<!-- formula-not-decoded -->`
  placeholders for non-generative formula regions; that is the current
  best-effort source-layer representation instead of hallucinated generated
  LaTeX.

1. Formula enrichment was coupled too broadly to table accuracy.

   - 2026-06-10 status: fixed for usable source-backed page windows. Accurate
     table mode remains active while formula VLM enrichment is skipped.
   - Remaining gap: a later per-region implementation may refine this when
     stable formula-region identifiers exist in the accepted Markdown path.

1. Formula quality checks are candidate-only.

   - Current behavior: structural penalties can reject obvious malformed
     generated text, but they do not compare a candidate against source-layer
     evidence.
   - Gap: a fluent hallucination can pass unless it contains known structural
     defects.
   - Recommendation: add source-backed acceptance checks before committing
     generated formula text.

1. Gating is now connected to page-window artifact representation.

   - 2026-06-10 status: usable source-backed page windows choose
     `source_layer_markdown`; no-source formula paths can still commit a clean
     generated candidate; runtime-unavailable formula paths emit an explicit
     `fallback` metadata decision.
   - Remaining gap: a future governed refinement can replace page-window
     markers with per-region source/candidate merges when stable identifiers
     exist.

1. Runtime metadata explains formula authority at the backend/result boundary.

   - 2026-06-10 status: backend results, conversion metadata, replay reports,
     warnings, and accepted Markdown carry safe formula-authority decisions.
   - Remaining gap: Task 342 still owns CLI/manifest presentation of this
     metadata.

1. Conversion decision logic lacks source-layer formula evidence.

   - Current behavior: Task 343 captures the need for document-aware decision
     features, but the formula-specific authority model is not yet defined.
   - Gap: broad performance tuning could still treat formula VLM latency as
     unavoidable even when source-layer evidence should make it unnecessary for
     some regions.
   - Recommendation: feed Task 343 with page/window formula source-evidence
     metrics and formula VLM invocation reasons.

## PR Scope

- Add a source-layer formula evidence model for born-digital PDFs using a
  proven PDF text extraction library with coordinate-backed page/window/crop
  evidence.
- Add a formula authority policy that decides, for each formula region or
  page-window formula batch, whether VLM formula output may be:
  - skipped,
  - generated only as advisory evidence,
  - rejected after quality/source comparison,
  - committed as authoritative because no usable source evidence exists and the
    quality gate passes.
- Add a best-effort representation policy that decides what the final Markdown
  artifact contains for each formula region after authority is resolved. A
  rejected or unusable candidate must still produce an explicit artifact
  representation and warning.
- Decouple formula-authority decisions from accurate table mode. Accurate
  tables may remain enabled without automatically committing generative formula
  transcriptions over source-backed formulas.
- Extend formula quality validation so source-backed regions cannot accept
  generated output that contradicts or materially degrades the PDF source
  layer.
- Add runtime metadata for formula authority decisions:
  - source evidence present/absent,
  - extraction method,
  - VLM attempted/skipped,
  - candidate accepted/rejected,
  - rejection reason,
  - elapsed time by formula authority path.
- Align CLI and manifest output with Task 342 by surfacing formula-heavy
  progress/reasons without raw backend flags.
- Align conversion decision telemetry with Task 343 by exposing the
  source-layer/formula-evidence features used to avoid unnecessary generative
  work.
- Add an incident replay validation that proves pages `13-16` no longer accept
  known hallucination/leakage markers when source-layer formula evidence is
  usable.

## Out of Scope

- Disabling all formula handling globally.
- Reducing output quality to improve speed.
- Adding raw CLI flags for formula/OCR/table internals.
- Introducing a PyMuPDF-only full-document route as the remediation.
- Replacing Docling as the approved PDF conversion pipeline.
- Solving all remaining Granite/ROCm throughput questions. Residual model
  throughput belongs to Task 343/Task 74 after formula authority is correct.
- Using hand-written complexity heuristics as routing authority.
- Treating Docling/Granite's current formula/LaTeX behavior as untouchable.
  Replacing or improving the formula representation stage is in scope when it
  is evidence-backed and preserves the approved conversion contract.
- Publishing blank, missing, or silently dropped formula regions as an
  acceptable "gated" outcome.

## Deliverables

- [x] Red-first tests for source-backed formula authority.
- [x] Pre-implementation scrutiny evidence recorded before production code.
- [x] Source-layer formula evidence model and extraction adapter, initial
  document-level substrate.
- [x] Formula authority policy integrated with Docling conversion/fallback,
  initial generated-defect rejection guard.
- [x] Best-effort page-window formula representation policy integrated with
  artifact assembly.
- [x] Decoupled table accuracy and formula authority behavior for usable
  source-backed page windows.
- [x] Backend/result/replay metadata for formula-authority decisions and
  reasons.
- [x] Incident replay validation for pages `13-16` with accepted-output review.
- [x] Documentation updates tying the behavior to Tasks 342, 343, and 344.
- [x] Initial Task 342 CLI/manifest/status presentation of formula-authority
  metadata for terminal results.
- [ ] Task 343 conversion-decision consumption of formula-authority metadata.

## Implementation Plan

Follow the **Task 345 Internal Tranche Contract** above as the authoritative
sequencing rule. The plan below gives the implementation actions inside that
order; if a later slice needs to change the order, amend the tranche contract
first.

1. Keep the pre-implementation scrutiny gate above current. If a chosen library
   or incident-class probe contradicts the gate conclusion, stop and update the
   task before writing production code.
1. Consume Task 346's candidate-evaluation result before planning any
   production formula-lane replacement or specialist model integration. If Task
   346 proves a better candidate, create or amend a governed implementation
   task instead of folding throwaway evaluation adapters into this task.
1. Add failing tests first:
   - source-backed formula evidence prevents VLM output from being committed,
   - accurate table mode does not automatically authorize formula VLM commits,
   - raster/no-source formula regions can still exercise the formula VLM path,
   - metadata records formula authority decisions and reasons,
   - rejected/unusable formula candidates still yield a deterministic
     best-effort artifact representation and warning.
1. Introduce a small source-layer evidence module with typed page/window/crop
   results. Keep it separate from backend routing so it cannot become an
   ungoverned bypass.
1. Add a formula authority policy object and wire it into the Docling formula
   fallback/quality path.
1. Add the formula representation ladder and artifact merge behavior so every
   formula region produces the best available Markdown representation, even
   when generated LaTeX is rejected.
1. Add per-region/page-window reconciliation between source evidence, generated
   formula candidates, and accepted Markdown artifact output. Use formula-region
   identifiers/coordinates where stable; otherwise use page-window formula
   batches with explicit metadata limitations.
1. Extend runtime metadata and CLI manifest rendering according to Task 342's
   progress-feedback contract only after representation and reconciliation
   decisions exist.
1. Feed Task 343's conversion-decision model with source-layer formula metrics
   and VLM invocation reasons only after the metadata contract exists.
1. Run the Task 344 incident replay and inspect accepted Markdown for pages
   `13-16`.

## Acceptance Criteria

- [x] Born-digital/source-backed formula regions preserve source-layer evidence
  unless a generated formula candidate passes a source-backed acceptance gate.
- [x] Source-layer authority is applied only after the evidence model classifies
  the region as `usable`; `partial_or_unusable` and `absent` evidence remain
  explicit states with governed fallback behavior.
- [x] Every encountered source-backed formula page window has an explicit
  best-effort artifact representation decision; the accepted terminal Markdown
  uses deterministic `formula-not-decoded` placeholders plus safe authority
  metadata instead of hallucinated generated formula text.
- [x] Accurate table mode can run without automatically committing generative
  formula VLM output.
- [x] No-source/raster formula regions still have a governed formula VLM path
  with the Task 344 stop/compile runtime controls intact.
- [x] Result/replay metadata tells the caller whether formula VLM was skipped,
  advisory, accepted, rejected, or fell back, and why. The initial Task 342
  terminal status/result/manifest presentation slice now surfaces that metadata
  without adding a second authority policy.
- [x] The pages `13-16` incident replay contains no accepted-output recurrence
  of the known leaked `</formula`, `\mathbmath`, repeated `\mathbf`, or
  pre-remediation corrupted formula/prose markers when source-layer evidence is
  usable.
- [x] Any remaining Granite/ROCm latency is explicitly attributed as residual
  model-throughput work for Task 343/Task 74, not mistaken for successful
  formula-authority remediation.
- [ ] Docs index and validation gates pass.

## Checklist

- [x] Red-first tests committed
- [x] Pre-implementation scrutiny gate complete
- [x] Implementation complete
- [x] Best-effort artifact representation behavior complete
- [x] Incident replay validated
- [ ] CLI/manifest alignment complete
- [ ] Conversion-decision alignment complete
- [x] Docs updated
- [x] Validation complete
