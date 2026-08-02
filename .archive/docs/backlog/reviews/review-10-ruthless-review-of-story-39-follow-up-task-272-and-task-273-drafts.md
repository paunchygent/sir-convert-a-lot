---
id: review-10-ruthless-review-of-story-39-follow-up-task-272-and-task-273-drafts
title: Ruthless review of Story 39 follow-up Task 272 and Task 273 drafts
type: review
status: completed
priority: high
created: '2026-04-30'
last_updated: '2026-04-30'
related:
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md
  - docs/backlog/tasks/task-273-run-chunk-size-8-production-baseline-tuning-proof-with-warm-up-and-gpu-sampling.md
  - docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py
  - scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py
labels:
  - review
  - story-39
  - task-272
  - task-273
  - ocr
  - pdf
  - artifact-contract
  - performance
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: planning/readiness review of the drafted Story 39 follow-up
  tasks.
- Governing authority:
  - `docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md`
  - `docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md`
  - `docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md`
  - `docs/converters/multi_format_conversion_service_api_v2.md`
- Files reviewed:
  - `docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md`
  - `docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md`
  - `docs/backlog/tasks/task-273-run-chunk-size-8-production-baseline-tuning-proof-with-warm-up-and-gpu-sampling.md`
  - `docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md`
  - `docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`
  - `scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py`
  - `scripts/sir_convert_a_lot/infrastructure/docling_formula_quality.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
- Public surfaces affected:
  - v2 PDF-to-Markdown terminal Markdown artifact.
  - Potential new companion-artifact, bundle, or manifest retrieval surfaces.
  - Retention/privacy behavior for source-derived PDF/image artifacts.
  - Story 39 / Task 74 production-service tuning evidence and defaults.
- Compatibility posture:
  - The primary Markdown artifact must remain retrievable by existing v2 clients.
  - Any new artifact/bundle/manifest surface is public contract work and must be
    documented and tested before implementation.
  - Task 273 may treat the Task 271 production-service result as its comparison
    baseline; the old `>=40%` improvement gate is withdrawn from this review as
    a non-finding after product-owner feedback.
- Evidence reviewed:
  - Current Story 39, Task 271, Task 272, Task 273, Task 74, and Hemma runbook
    wording.
  - Current v2 artifact route surface in
    `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`.
  - Current Docling formula enrichment implementation and heuristics in
    `docling_backend.py`, `docling_formula_fallback.py`, and
    `docling_formula_quality.py`.
  - Context7 lookup for Docling formula/table/image option names:
    `do_formula_enrichment`, `TableFormerMode.ACCURATE`, and
    `generate_picture_images` are plausible upstream surfaces.

## Findings

1. `high` - Task 272 leaves the public artifact contract as an implementation
   decision.

   - Evidence:
     `docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md`
     says to document whether companion artifacts are exposed as a ZIP bundle,
     a manifest plus primary Markdown artifact, or another existing artifact
     surface. The current v2 artifact router exposes only result, primary
     artifact, partial artifact, and checkpoint endpoints in
     `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`.
   - Why it matters:
     ZIP bundle, manifest-plus-primary-artifact, and separate companion-artifact
     routes are different public contracts. They differ in response payload
     shape, content types, authorization checks, retention behavior, client
     compatibility, and checkpoint implications. Leaving this choice to
     implementation means two developers could both satisfy the task while
     producing incompatible v2 surfaces.
   - Required fix:
     Amend Task 272 before implementation to choose the exact v2 artifact shape:
     result payload fields, endpoint paths, content types, manifest schema,
     auth behavior, primary Markdown compatibility rule, and whether checkpoint
     payloads gain any artifact references. If the selected shape is a clean
     public contract expansion, document it in
     `docs/converters/multi_format_conversion_service_api_v2.md` and add API
     contract tests for strict clients.
   - Proof requirement:
     Add API/contract tests for primary Markdown retrieval plus the selected
     manifest or companion-artifact retrieval shape. Run the focused artifact
     route tests, `pdm run docs-sync`, `pdm run docs-validate`,
     `pdm run skills-validate`, `pdm run handoff-validate`, and
     `git diff --check`.

1. `high` - Companion PDF retention lacks privacy and lifecycle semantics.

   - Evidence:
     Task 272 requires a retained PDF companion artifact and extracted
     image/object artifacts, but only forbids committing private PDFs, raw OCR
     excerpts, or PII-bearing source paths to git. It does not define whether
     the retained PDF is the original upload or a generated derivative, how the
     artifact is named, how long it is retained, how retention pinning applies,
     whether it is included in cleanup/deletion behavior, or how auth checks
     apply to each companion artifact.
   - Why it matters:
     This is not just local evidence hygiene. It is runtime data exposure for
     source-derived PDFs and images. A manifest that leaks an original filename,
     source path, or long-lived copy of a private source PDF would violate the
     same privacy boundaries Story 39 enforced for dirty-corpus evidence.
   - Required fix:
     Amend Task 272 to define companion artifact lifecycle semantics before code
     starts:
     original-vs-derived PDF, deterministic sanitized naming, relative paths
     only, no private source roots or original private filenames, retention and
     pinning behavior, cleanup/deletion behavior, auth/ownership checks, and
     safe manifest fields. Tie this to the selected artifact API shape from the
     first finding.
   - Proof requirement:
     Add unit and API tests proving companion-artifact paths are relative and
     stable, private roots and original private filenames are not exposed, and
     artifact retrieval follows the same job-access authorization as the primary
     artifact. Run focused tests plus the docs validators.

1. `medium` - Task 273 promotion and rollback thresholds are too vague.

   - Evidence:
     Task 273 currently says to roll back when placeholder counts regress
     "materially", resource evidence shows "unsafe pressure", or wall-clock
     does not improve enough to justify changing the default. It also asks for
     "credible non-placeholder" GPU/resource values without defining required
     fields or acceptance thresholds.
   - Why it matters:
     Performance-default decisions need machine-checkable thresholds, not prose.
     Otherwise a candidate run can be promoted on a tiny wall-clock improvement,
     ignored quality degradation, or resource samples that are present but too
     sparse to prove safety.
   - Required fix:
     Amend Task 273 with numeric gates:
     minimum wall-clock improvement versus Task 271's `2179.0` seconds,
     maximum allowed `<!-- formula-not-decoded -->` and bare `<!-- image -->`
     deltas, required Swedish-diacritic non-regression rule, required GPU busy
     and memory sample fields/counts, and a fail-closed rule when resource
     sampling is unavailable, all-zero, or placeholder-only.
   - Proof requirement:
     Add regression tests for candidate comparison against an existing Task 271
     baseline artifact, resource-sampler fail-closed behavior, and thresholded
     promotion/rejection decisions. Run the focused benchmark/report tests and
     docs validators.

1. `medium` - Task 272 is larger than one PR-sized execution unit unless its
   internal order is constrained.

   - Evidence:
     Task 272 combines formula final-pass orchestration, image/object
     extraction, companion PDF retention, manifest design, v2 API route changes,
     converter docs, and Hemma quality proof. It also names entry points in the
     already oversized `v2_pdf_checkpointed_executor.py`, which is currently
     over the repository module-size target.
   - Why it matters:
     The task can easily sprawl into checkpoint assembly, artifact routing,
     Docling backend behavior, storage semantics, and public API docs in a
     single patch. That increases the chance of hidden contract drift and makes
     independent review harder.
   - Required fix:
     Either split Task 272 into two governed tasks:
     formula-aware final-pass repair first, then linked artifact/manifest
     contract; or amend Task 272 with a required internal sequence:
     public artifact contract decision, small artifact-manifest module,
     formula-selection/merge module, API route addition, then Hemma quality
     probe. Explicitly forbid adding the new behavior directly into the
     checkpoint executor as a broad catch-all.
   - Proof requirement:
     Update Task 272 docs with the chosen split or internal sequence, then run
     docs validators. During implementation, add focused tests at the new
     module boundaries and keep touched modules under the repo size/SRP target.

## Withdrawn Non-Finding

- The original draft review flagged removal of the old Task 74 `>=40%`
  improvement gate. Product-owner feedback on 2026-04-30 clarified that the
  `>=40%` gate is not useful for this follow-up lane. This review therefore
  does not request restoring that gate. Task 273 should instead use production
  criteria that matter: stable success, no quality regression, credible
  resource sampling, and an explicit conservative wall-clock comparison against
  Task 271.

## Re-review Findings 2026-04-30

No remaining blocking findings for the Story 39 Task 272 / Task 273 drafts.

- The public artifact-contract finding is resolved. Task 272 now selects one v2
  contract: existing primary Markdown retrieval remains unchanged at
  `GET /v2/convert/jobs/{job_id}/artifact`, and the new terminal companion
  surface is `GET /v2/convert/jobs/{job_id}/artifact/bundle` with content type
  `application/zip`, fixed bundle members, result summary fields, and no
  companion references in partial artifacts or checkpoint payloads.
- The companion PDF retention/privacy finding is resolved. Task 272 now states
  that the companion PDF is a full generated OCR PDF deliverable rather than
  the original upload or a Markdown-support preview, forbids original
  filenames/private roots/operator paths in public fields and manifests,
  requires relative deterministic paths, inherits job auth and retention
  behavior, and records safe unavailable reason codes.
- The Task 273 threshold finding is resolved. Task 273 now defines promotion,
  keep-current, and intermediate-result wall-clock thresholds against the Task
  271 `2179.0` second baseline, plus quality non-regression and fail-closed
  resource-sampling gates.
- The Task 272 scope finding is resolved for planning readiness. Task 272 now
  constrains the work with a required internal order and assigns bundle/manifest
  behavior to a dedicated companion-artifact module rather than the checkpoint
  executor.

## Decision

approved

## Response

Amendments have been applied for re-review:

- Task 272 now chooses a single public artifact contract:
  `GET /v2/convert/jobs/{job_id}/artifact` remains Markdown-only, while
  `GET /v2/convert/jobs/{job_id}/artifact/bundle` returns an
  `application/zip` terminal bundle containing `output.md`,
  `artifact-manifest.json`, a full generated OCR PDF companion, and extracted
  image assets with relative links.
- Task 272 now defines companion artifact privacy/lifecycle semantics:
  full generated OCR PDF rather than original upload bytes or a
  Markdown-support preview, deterministic relative paths, no private
  roots/original filenames/OCR excerpts, same auth/ownership as the primary
  artifact, inherited retention/pinning/deletion, no checkpoint or
  partial-artifact exposure before terminal finalization, and safe unavailable
  reason codes.
- Task 272 now constrains implementation order: API docs/tests first, then a
  small companion-artifact module, then formula selection/merge modules, then
  route/result wiring, then Hemma quality probe. The task explicitly forbids
  broad catch-all implementation in `v2_pdf_checkpointed_executor.py`.
- Task 273 now uses numeric gates against the Task 271 baseline:
  promote `chunk_size_pages=8` only at `<=1961.1` seconds with all other gates
  passing, keep `4` above `2070.0` seconds, and treat intermediate results as a
  blocker or authority for one governed candidate such as `6`.
- Task 273 now defines quality/resource gates:
  success rate `1.0`, failed jobs `0`, formula placeholder count `<=168`, bare
  image marker count no higher than the measured Task 271 baseline, longdoc
  Swedish diacritics `>=17684`, warning count `<=4`, no new failure taxonomy
  counts, required timestamped GPU samples and fields, fail-closed
  placeholder/all-zero resource evidence, and GPU memory pressure `<=90%`.

Re-review accepted the amended Task 272 and Task 273 drafts. They remain
proposed execution tasks, but the Review 10 planning/readiness blockers are
resolved.

## Follow-up Actions

1. None for Review 10. Future implementation must still satisfy the task-local
   acceptance criteria and closeout gates.

## Completion

Review 10 is retained as `approved` on 2026-04-30 after re-review of the Task
272 and Task 273 draft amendments.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
