---
id: epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling
title: Long PDF conversion reliability progress and throughput scaling
type: epic
status: in_progress
priority: high
created: '2026-03-04'
last_updated: '2026-03-06'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/stories/story-17-progress-aware-timeout-for-long-running-conversion-jobs.md
  - docs/backlog/stories/story-18-page-level-progress-and-stall-telemetry-contract.md
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md
  - docs/backlog/tasks/task-67-detect-stalled-conversions-separately-from-active-long-running-jobs.md
  - docs/backlog/tasks/task-68-publish-adr-for-progress-checkpoint-and-resume-contract.md
  - docs/backlog/tasks/task-69-add-page-level-progress-fields-to-v2-jobs-api.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - docs/backlog/tasks/task-71-add-cancel-with-save-and-resume-from-checkpoint-flow.md
  - docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md
  - docs/backlog/tasks/task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - long-pdf
  - progress-tracking
  - partial-results
  - resume
  - performance
  - parallelization
---

Major capability increment managed through linked stories.

## Goal

Turn long PDF OCR conversions from opaque all-or-nothing jobs into a resilient, observable, and
high-throughput pipeline with:

- page-level progress visibility,
- partial artifacts/checkpoints,
- cancel-with-save and resume semantics,
- explicit stall detection,
- parallel execution tuned for Hemma GPU/CPU resources.

## In Scope

- Progress contract and telemetry:
  - page-aware status fields (`total_pages`, `processed_pages`, `failed_pages`, `percent_complete`),
  - page throughput and ETA (`pages_per_minute`, `eta_seconds`),
  - deterministic stall classification (active vs stale/blocked jobs).
- Partial-result architecture:
  - checkpointed conversion chunks for long PDFs,
  - recoverable partial markdown artifacts and metadata while job is still running,
  - idempotent cancel-with-save behavior.
- Resume architecture:
  - resume from checkpoint without reprocessing completed chunks/pages,
  - deterministic merge/finalization of partial outputs into canonical markdown artifact.
- Performance and bottleneck removal:
  - bounded parallel worker pool model for OCR/conversion chunks,
  - stage-level timing and bottleneck observability (OCR, layout, normalization, persist),
  - benchmark-driven tuning and published runbook guidance.

## Out of Scope

- New conversion domains unrelated to long PDF OCR throughput/reliability.
- Re-architecting the whole API versioning strategy.
- UI frontend implementation work outside required API/CLI/manifest contract changes.

## Stories (Ordered)

- [x] `S00` `docs/backlog/stories/story-17-progress-aware-timeout-for-long-running-conversion-jobs.md`
  (requires `T67`)
- [x] `S01` `docs/backlog/stories/story-18-page-level-progress-and-stall-telemetry-contract.md`
  (requires `T68-T69`)
- [x] `S02` `docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md`
  (requires `T70-T71`)
- [ ] `S03` `docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md`
  (requires `T72-T74` plus `T76` preflight hardening gate)
- [x] `S04` `docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md`
  (requires `T77` and should land before `T74` benchmark/report)

## Tasks (Ordered)

- [x] `T67` `docs/backlog/tasks/task-67-detect-stalled-conversions-separately-from-active-long-running-jobs.md`
- [x] `T68` `docs/backlog/tasks/task-68-publish-adr-for-progress-checkpoint-and-resume-contract.md`
- [x] `T69` `docs/backlog/tasks/task-69-add-page-level-progress-fields-to-v2-jobs-api.md`
- [x] `T70` `docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md`
- [x] `T71` `docs/backlog/tasks/task-71-add-cancel-with-save-and-resume-from-checkpoint-flow.md`
- [x] `T73` `docs/backlog/tasks/task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics.md`
- [x] `T76` `docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md`
- [x] `T72` `docs/backlog/tasks/task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools.md`
- [x] `T77` `docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md`
- [ ] `T74` `docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md`

## Execution Plan (Implementation Order)

This epic is intentionally ordered to reduce risk and prevent wasted work.

1. `T67` (client semantics first):
   - make “timeout” progress-aware using heartbeat-only fallback,
   - ensures long jobs do not look failed while they are still active.
1. `T68` (ADR locks contract):
   - unblocks implementation without contract drift,
   - locks page progress fields + partial/checkpoint + cancel-with-save + resume semantics.
1. `T69` (contract + API surfaces):
   - add page-level progress fields to polling payloads and async push channels (SSE/webhooks).
1. `T70` (checkpoints + partial artifacts):
   - incremental persistence + partial artifact retrieval, with bounded retention/cleanup.
1. `T71` (cancel-with-save + resume):
   - resume creates a new job id; preserved provenance from source job/checkpoint.
1. `T73` (telemetry before tuning):
   - stage timings + queue/worker saturation + GPU evidence for real bottleneck diagnosis.
1. `T76` (deploy/verification hardening gate):
   - enforce deploy parity and stable live-verification workflow before throughput tuning.
1. `T72` (parallelization with caps):
   - introduce bounded worker pools and GPU concurrency caps after telemetry exists.
1. `T74` (benchmark/report):
   - run baseline vs tuned profiles and publish operational defaults + rollback criteria.

## Per-Task Closeout Checklist (Mandatory)

When completing any task in this epic, keep status and checkboxes synchronized in strict order and
always include verification evidence.

- [ ] Run quality gates (minimum):
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
- [ ] Run docs-as-code gates:
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Update the task doc:
  - set `status: completed`,
  - add “Validation Evidence” command outputs (or explicit notes if not run).
- [ ] Only after task status is terminal:
  - check the corresponding `T##` checkbox in this epic and any story trackers.
- [ ] For major slices (after `T69`, `T71`, `T74`):
  - update `.codex/handoff.md`,
  - archive into `docs/backlog/current.md` (keep within RULE-090 limits).

## Acceptance Criteria

- [ ] A running long PDF job exposes page-aware progress and ETA fields in v2 job status.
- [ ] `job_timeout` semantics are reserved for stalled jobs; active heartbeating jobs are not
  misclassified as failed timeouts.
- [ ] Partial markdown/checkpoint artifacts are accessible while conversion is still running.
- [ ] Canceling a long job preserves completed work and exposes a deterministic partial artifact.
- [ ] Resuming from checkpoint avoids full re-OCR of already completed chunks/pages.
- [ ] Partial/checkpoint storage is bounded (explicit retention/cleanup policy; no unbounded disk
  growth under repeated long conversions).
- [ ] GPU-first governance remains invariant:
  - acceleration-policy requests are honored (no silent CPU fallback when GPU is requested/required),
  - any fallback behavior is explicit in job metadata and client/manifest messaging.
- [ ] Throughput target is met and documented:
  - baseline configuration and dataset are explicitly defined and versioned in the benchmark report,
  - median wall-clock for representative long OCR PDFs improves by >= 40% versus that baseline,
  - bottleneck evidence includes stage timings and queue/worker saturation metrics,
  - GPU utilization evidence is captured (or ROCm equivalent) in benchmark report artifacts.
- [ ] Required quality and docs gates pass:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
