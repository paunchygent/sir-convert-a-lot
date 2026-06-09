---
id: task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence
title: Run safe Hemma dirty PDF OCR benchmark and publish tuning evidence
type: task
status: completed
priority: high
created: '2026-04-27'
last_updated: '2026-05-13'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/backlog/tasks/task-270-add-dirty-pdf-ocr-corpus-manifest-and-benchmark-report-schema.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/pdf_throughput_benchmark_report.py
  - scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py
labels:
  - ocr
  - benchmark
  - dirty-data
  - hemma
  - performance
  - gpu
  - safety
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the dirty real-data OCR benchmark against the production service on Hemma
through the safe Task 74 command surface, publish sanitized tuning evidence,
and block Story 39 closeout on unsafe or non-representative performance proof.

## PR Scope

- Use the manifest/report schema from Task 270.
- Re-run Task 76 deploy/runtime parity on the current pushed revision before
  any final benchmark evidence is accepted.
- Accept no local, in-process, synthetic-corpus, or smoke-run metrics as
  performance proof; local surfaces may validate only schema, command wiring,
  manifest privacy, and fail-closed profile classification.
- Provide the private Hemma source root alongside the metadata-only manifest so
  the benchmark runner can hash executed PDFs, verify them against manifest
  `source_sha256` values, and copy only sanitized `source_id.pdf` names into the
  execution corpus.
- Run only Task 74-approved safe profiles:
  - final production-service proof records the single deployed service profile
    as `production_service_current`,
  - in-process/local profile sweeps may still compare `serial_baseline`,
    `parallel_conservative`, or bounded 2-worker variants, but those sweeps are
    command-surface or tuning exploration only and cannot satisfy final proof.
- Treat the removed 4-worker ROCm HIP OOM profile as forbidden unless a new
  governed decision explicitly reopens it.
- Capture sanitized benchmark JSON/Markdown evidence with:
  - corpus manifest summary,
  - page counts and hashes,
  - OCR engine/language metadata,
  - throughput and wall-clock,
  - stage timings,
  - GPU runtime/utilization evidence,
  - metrics safety,
  - warning/failure taxonomy,
  - determinism/non-regression evidence.
- Publish recommended tuning defaults and rollback criteria, or leave the story
  open with a concrete blocker when the target is not met.

## Deliverables

- [x] Task 76 parity evidence for the exact revision under benchmark.
- [x] Dirty-corpus benchmark JSON and Markdown report.
- [x] Safe-profile compliance proof.
- [x] Runbook/defaults update or explicit blocker explaining why defaults must
  stay unchanged.
- [x] Story 39 / Task 74 evidence links updated.

## Acceptance Criteria

- [x] Final evidence is captured against the production service on Hemma,
  GPU-backed, and tied to the pushed revision under review.
- [x] Runtime parity is proven through Task 76 before the benchmark result is
  accepted.
- [x] No local, in-process, synthetic-corpus, or smoke output is used as
  performance, throughput, tuning, acceptance, or production default evidence.
- [x] Smoke assertions and smoke command stdout remain schema/safety-only and
  do not print or assert p50/p90, latency, pages-per-minute, throughput, or
  improvement percentages.
- [x] The dirty-corpus run uses the Task 74 report schema and command surface.
- [x] The Hemma command fails closed unless `runtime_surface.mode` is
  `production_service`; final Task 271 evidence must not dispatch through the
  in-process FastAPI `TestClient` profile runner.
- [x] The dirty-corpus report records `source_hashes_verified=true`,
  `executed_entry_count=entry_count`, and `real_data_gate_satisfied=true`;
  manifest-only validation cannot satisfy this gate.
- [x] Sanitized JSON/Markdown evidence omits the manifest path, private source
  root, and private PDF filenames.
- [x] Unsafe profiles fail closed:
  - no 4-worker OOM-profile rerun as acceptance evidence,
  - no profile outside the safe 2-worker boundary unless a new governed
    decision updates Task 74 first.
- [x] Recommended profile records `success_rate=1.0`; lower success blocks
  closeout.
- [x] The former `>=40%` median wall-clock gate is not claimed by Task 271:
  the production-service current-profile report records
  `p50_improvement_percent=0.0`, Story 39 remains open for follow-up
  optimization, and Review 10 withdraws the old toy improvement gate in favor
  of Task 273's production-service thresholds.
- [x] The operator 150 PDF-page proof target is evaluated from measured
  evidence:
  - report field `dirty_corpus.task271_proof.meets_150_page_target=true`,
  - report fields include `target_executed_pages=150`,
    `target_wall_clock_seconds=3600`, `tuned_total_pages`,
    `tuned_wall_clock_seconds`, and `production_service_runtime=true`,
  - \<= 60 minutes on tuned Hemma profile for a manifest-verified dirty corpus
    with at least 150 executed PDF pages, or
  - a governed blocker keeps the target open.
- [x] Metrics safety records `contains_job_id_label=false`.
- [x] Reports include OCR quality evidence for Swedish diacritics where
  expected and classify failures by input quality, engine/runtime availability,
  timeout, GPU/resource pressure, or conversion bug.

## Entry Points

- `pdm run run-hemma -- pdm run benchmark:pdf-throughput-hemma --expected-revision <sha>`
- `pdm run run-hemma -- pdm run benchmark:pdf-throughput-hemma --expected-revision <sha> --dirty-corpus-manifest <metadata-only-manifest.json> --dirty-corpus-source-root <private-pdf-root>`
- `pdm run run-hemma -- pdm run benchmark:pdf-throughput-two-worker-sweep-hemma --expected-revision <sha>` remains a safe exploration command only unless the service is redeployed per governed profile and the resulting evidence is tied to the production-service lane.
- `scripts/sir_convert_a_lot/pdf_throughput_benchmark_report.py`
- `scripts/sir_convert_a_lot/benchmarking/pdf_throughput_report.py`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Test Requirements

- [x] No new benchmark profile can be accepted without Task 76 parity evidence.
- [x] The report marks unsafe profile requests as hard failures.
- [x] Regression tests prove the Hemma command sends
  `--runtime-mode production_service` and the production-service benchmark path
  cannot dispatch through the in-process `TestClient` runner.
- [x] Regression tests prove 1-page and 149-page dirty corpora cannot set
  `meets_150_page_target=true`, even with verified source hashes.
- [x] The evidence bundle includes stable input/output checks appropriate for
  the single deployed `production_service_current` baseline: manifest
  `source_sha256` verification, sanitized `source_id.pdf` execution copies,
  deterministic report fields, and counts-only OCR quality evidence. Task 273
  owns tuned-vs-baseline comparison against this Task 271 baseline.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Kickoff Evidence (2026-04-30)

- Local dirty-corpus operator folder is ignored by git via `.gitignore`.
- Pilot dirty-corpus manifest was generated from 9 local PDFs with stable
  `source_id` values, SHA-256 hashes, page counts, and private privacy state.
- The pilot corpus is staged on Hemma under the ignored operator folder and the
  Hemma checkout is fast-forwarded to revision
  `a8197a0a82b4cedd78eb603c52ac47a00d7c0d67`.
- Hemma manifest validation passes as schema/privacy proof only.
- Hemma source-root verification matched 9 manifest entries to 9 PDFs and 9
  total pages without launching a benchmark.
- This pilot corpus is not final Task 271 acceptance evidence: every PDF is
  currently one page, so the manifest still reports missing `long_document` and
  cannot satisfy the full dirty-corpus real-data gate or 150 PDF-page proof
  target.
- The Syntes long-document corpus update added `dirty-pdf-ocr-longdoc-001`
  with 148 observed PDF pages. Together with the 9 one-page pilot PDFs, the
  operator manifest now has 10 entries and 157 total PDF pages; Hemma
  source-root verification matched all 10 entries and all 157 pages without
  launching OCR.
- Initial Hemma pilot exposed a ROCm/MIOpen EasyOCR failure mode during repeated
  PDF OCR:
  - default MIOpen execution emitted `IsEnoughWorkspace` warnings for
    `GemmFwdRest` with required scratch sizes around 343-405 MiB while the
    selected path reported `provided ptr: 0 size: 0`,
  - a 9-PDF in-process diagnostic without explicit MIOpen settings reproduced
    `miopenStatusUnknownError` / HIP unspecified launch failure after several
    successes,
  - a controlled rerun with `MIOPEN_FIND_MODE=FAST`,
    `MIOPEN_USER_DB_PATH=/srv/scratch/sir-convert-a-lot/cache/miopen/user-db`,
    and
    `MIOPEN_CUSTOM_CACHE_DIR=/srv/scratch/sir-convert-a-lot/cache/miopen/kernel-cache`
    completed all 9 pilot PDFs successfully and did not emit the MIOpen
    workspace warnings.
- The successful diagnostic tree has been copied locally under
  `build/benchmarks/story-39/local-copies/miopen-fast-diagnostic/` for operator
  inspection. This remains diagnostic runtime evidence only, not Task 271
  performance proof.
- Follow-up implementation in this task makes the MIOpen cache/scratch settings
  repeatable for production compose and the host-side Task 74 Hemma runner, and
  removes Docling's deprecated EasyOCR `use_gpu` option in favor of
  `pipeline_options.accelerator_options.device`.
- Revision `9abbb29bd22f7aadfc3bff870b6b25d80cea1f48` was pushed, pulled on
  Hemma, and deployed through Task 76 parity:
  - report: `build/verification/task-76-hemma-deploy-verify/report.md`,
  - status: `passed`,
  - remote revision and service revision both matched
    `9abbb29bd22f7aadfc3bff870b6b25d80cea1f48`.
- Live production container probe confirmed:
  - `MIOPEN_FIND_MODE=FAST`,
  - `MIOPEN_USER_DB_PATH=/srv/scratch/sir-convert-a-lot/cache/miopen/user-db`,
  - `MIOPEN_CUSTOM_CACHE_DIR=/srv/scratch/sir-convert-a-lot/cache/miopen/kernel-cache`,
  - the container bind mount is read-write from
    `/home/paunchygent/.data/sir-convert-a-lot/cache/miopen` to
    `/srv/scratch/sir-convert-a-lot/cache/miopen`.
- Production-service diagnostic OCR probe against `http://127.0.0.1:28085`
  converted the same 9 pilot PDFs with `ocr_mode=force`, `ocr_engine=easyocr`,
  and `sv,en` languages:
  - output root:
    `build/verification/task-271-miopen-prod-service-probe/`,
  - manifest: `sir_convert_a_lot_manifest.json`,
  - 9 entries, all `status=succeeded`,
  - no recent container-log matches for `MIOpen`, `IsEnoughWorkspace`,
    `miopenStatus`, `HIP error`, `unspecified launch failure`, or the Docling
    deprecated `use_gpu` warning.
- Production-service probe outputs were copied locally under
  `build/verification/local-copies/task-271-miopen-prod-service-probe/`.
  This is production-runtime health evidence only, not throughput,
  performance, tuning, acceptance, or 150 PDF-page proof evidence.

## Final 150-Page Proof Evidence (2026-04-30)

- Implementation revision:
  `405cddc59d02974f43eaf03556bad92cdd1c2341`.
- Hemma deploy/runtime parity for that exact revision passed before the
  benchmark:
  - deploy report:
    `build/verification/task-76-hemma-deploy-verify-task271-profile/report.md`,
  - remote revision and service revision both matched
    `405cddc59d02974f43eaf03556bad92cdd1c2341`,
  - live smoke, metrics scan, public edge, TLS, and reserved default-host checks
    passed.
- The benchmark was launched through the committed detached Hemma command
  surface:
  - detached log:
    `.artifacts/hemma-command-task271-dirty-proof-20260430T103413Z.log`,
  - command surface:
    `pdm run benchmark:pdf-throughput-hemma --expected-revision 405cddc59d02974f43eaf03556bad92cdd1c2341 --dirty-corpus-manifest inputs/dirty_pdf_to_ocr/dirty_pdf_ocr_manifest.json --dirty-corpus-source-root inputs/dirty_pdf_to_ocr`.
- Benchmark artifacts were written on Hemma and copied locally for operator
  inspection under ignored `build/` paths:
  - remote JSON:
    `build/benchmarks/story-39/task-271-dirty-pdf-ocr-benchmark-hemma.json`,
  - remote Markdown:
    `build/benchmarks/story-39/task-271-dirty-pdf-ocr-benchmark-report-hemma.md`,
  - local copies:
    `build/benchmarks/story-39/local-copies/task-271-dirty-pdf-ocr-proof/`.
- Raw artifacts remain untracked because `build/` is ignored and the raw
  report includes the sanitized execution-corpus location. The committed
  evidence below intentionally records only sanitized facts, stable source ids,
  hashes/page counts, and artifact locations; it does not commit private PDFs,
  private source roots, original PDF filenames, or OCR excerpts.
- Production-service proof summary:
  - `runtime_surface.mode=production_service`,
  - `runtime_surface.host=hemma`,
  - profile `production_service_current`,
  - `source_hashes_verified=true`,
  - `executed_entry_count=10`,
  - `entry_count=10`,
  - `real_data_gate_satisfied=true`,
  - `total_pages=157`,
  - `target_executed_pages=150`,
  - `target_wall_clock_seconds=3600`,
  - `tuned_total_pages=157`,
  - `tuned_wall_clock_seconds=2179.0`,
  - `production_service_runtime=true`,
  - `meets_150_page_target=true`,
  - `success_rate=1.0`,
  - `failed_jobs=0`,
  - `resource_evidence.contains_job_id_label=false`.
- OCR/backend metadata summary:
  - OCR enabled jobs: `10`,
  - OCR engine used: `easyocr`,
  - OCR languages used: `en, sv`,
  - backend used: `docling`,
  - acceleration used: `cuda`.
- Failure and warning taxonomy:
  - failed jobs: `0`,
  - warnings: `4`,
  - input-quality warnings: `0`,
  - engine/runtime failures: `0`,
  - timeout failures: `0`,
  - GPU/resource failures: `0`,
  - conversion-bug failures: `0`,
  - recent production container log scan during and after the run found `0`
    matches for `MIOpen`, `ERROR`, `WARNING`, `Traceback`, or `Exception`.
- Counts-only Swedish-diacritic evidence from downloaded Markdown artifacts:
  - 10 OCR artifacts were scanned without storing excerpts in git,
  - 1 artifact contained Swedish diacritic code points,
  - total Swedish diacritic code points observed: `18615`,
  - the long-document source id accounted for those counts:
    `å=4981`, `ä=8718`, `ö=4728`, `Å=8`, `Ä=108`, `Ö=72`.
- The production-service current-profile report intentionally records
  `p50_improvement_percent=0.0` and `meets_target=false` because a fixed
  deployed service profile cannot truthfully compare itself against a separate
  production-service baseline. Do not use this run to claim the Story 39
  `>=40%` baseline-vs-tuned improvement gate. That gate needs either a governed
  service-backed baseline/tuned A/B proof or an explicit Story 39/Task 74
  blocker decision.

## Governance Reconciliation (2026-05-13)

- Task 271 is closed as `completed` because its own production-service
  dirty-corpus benchmark, Task 76 parity, 150-page proof, safety checks, and
  sanitized evidence requirements are satisfied by the final proof above.
- Story 39 remains `in_progress`: formula/image quality repair and
  chunk-size-8 production tuning are intentionally carried by Task 272 and
  Task 273.
- The Task 271 result is the current production-service optimization baseline
  for Task 273. Do not rerun a serial baseline unless a later governed decision
  changes that policy.

## Closeout

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Include any code/test gates required by the benchmark harness changes made
  in this task.
