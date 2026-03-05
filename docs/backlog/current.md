---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-05'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
  - docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md
  - docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md
  - docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md
  - docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/backlog/tasks/task-59-enforce-90-percent-test-coverage-gate-for-conversion-core.md
  - docs/backlog/tasks/task-60-harden-v2-converter-security-for-ssrf-traversal-and-timeout-enforcement.md
  - docs/backlog/tasks/task-61-enforce-pandoc-sandbox-and-bounded-subprocess-stderr-handling.md
labels:
  - session-log
  - active-work
---

## Context

Epic 05 is complete (v2-only conversion architecture, deterministic markdown ingress routes, and
template-governed DOCX/PDF pathways are delivered and validated).

Active focus is Epic 06: long OCR PDF progress visibility, partial artifact/checkpoint lifecycle,
resume reliability, and throughput scaling.

This file is the canonical long-term memory index for session progress; session handoff summaries
must be archived here when `handoff.md` is pruned.

Current epic entrypoint:

- `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`

Primary implementation stories (active sequence):

- `docs/backlog/stories/story-17-progress-aware-timeout-for-long-running-conversion-jobs.md` (completed)
- `docs/backlog/stories/story-18-page-level-progress-and-stall-telemetry-contract.md` (completed)
- `docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md` (completed)
- `docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md` (active)

## Worklog

- 2026-03-05:

  - Task 73 completed for Story 20 telemetry slice, was reopened after ruthless review findings,
    and is now re-terminalized after remediation.
  - Added canonical v2 phase timing key contract + canonical-only merge enforcement at job
    manifest merge points.
  - Added explicit v2 runtime telemetry sink ownership in app state and injected sink into
    `ServiceRuntimeV2` following the HuleEdu app-owned instrumentation pattern.
  - Added bounded-cardinality metrics for:
    - active/queued/max workers and saturation ratio,
    - terminal job counts with bounded labels,
    - retry category counters,
    - stage duration histograms using canonical timing keys.
  - Enforced no `job_id` metric labels and documented correlation policy (`X-Correlation-ID`,
    lifecycle events, webhook payloads).
  - Validation evidence:
    - `pdm run validate-tasks` (pass: `Validated 106 backlog files`)
    - `pdm run validate-docs` (pass: `Validated docs=132 rules=9`)
    - `pdm run pytest-root tests/sir_convert_a_lot/test_phase_timings_v2.py tests/sir_convert_a_lot/test_api_metrics_v2.py -q` (pass: `4 passed`)
  - Added Task 73 sustained-load evidence runner with explicit non-shim benchmark modes:
    - `pdm run benchmark:task-73-telemetry --total-jobs 40 --max-workers 8 --stub-work-seconds 0.2`
    - artifact: `build/benchmarks/story-20/task-73-telemetry-overhead-local.json`
    - latest run (`2026-03-05`):
      - `overhead_percent.full_vs_sink_disabled=1.3728%`
      - `overhead_percent.full_vs_bypassed=-1.4069%`
      - no `job_id` metrics labels observed.
  - Ruthless review remediation delivered and Task 73 re-terminalized.
  - Removed deprecated benchmark output field (`telemetry_overhead_percent`) in favor of explicit
    `overhead_percent.full_vs_sink_disabled` and `overhead_percent.full_vs_bypassed`.
  - Validation evidence (remediation closeout):
    - `pdm run format-all` (pass)
    - `pdm run lint-fix` (pass)
    - `pdm run typecheck-all` (pass)
    - `pdm run pytest-root tests/sir_convert_a_lot/test_gpu_utilization_snapshot.py tests/sir_convert_a_lot/test_runtime_engine_v2.py tests/sir_convert_a_lot/test_benchmark_story20_telemetry_overhead.py -q` (pass: `29 passed`)
      - Completed Task 76 hardening gate with Hemma deploy-and-verify evidence: `build/verification/task-76-hemma-deploy-verify/report.json` (`status=passed`)
      - Completed Task 77 multilingual OCR hardening with Hemma live evidence: `build/verification/task-76-hemma-deploy-verify/v2-smoke/swedish_ocr_excerpt.txt` (contains `å ä ö`)
      - Changed backlog docs:
        - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
        - `docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md`
        - `docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md`

- 2026-03-04:

  - Planned Epic 06 long PDF conversion reliability/performance slice:
    - new epic/story/task chain under `docs/backlog/` for:
      - progress-aware timeouts,
      - page-level progress/ETA and stall telemetry,
      - checkpointed partial artifacts + cancel-with-save + resume,
      - telemetry-driven parallelization and benchmarked tuning (GPU-first).
  - Completed Task 67 (progress-aware polling timeouts):
    - active-running jobs that exceed the local poll window are classified as
      `error_code=job_poll_window_exceeded`,
    - stalled jobs (stale heartbeat/progress) are classified as `error_code=job_timeout`,
    - added CLI flag `--stall-timeout-seconds` and updated docs/tests.
  - Completed Task 68 (contract-first ADR lock-in):
    - published ADR-0005: `docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md`,
    - linked ADR from `docs/converters/multi_format_conversion_service_api_v2.md` and dependent backlog items.
  - Completed Task 69 (page progress fields + push parity):
    - extended v2 job status payload and async push payloads (SSE + webhooks) with PDF-only
      page progress fields per ADR-0005:
      `total_pages`, `processed_pages`, `failed_pages`, `percent_complete`, `pages_per_minute`,
      `eta_seconds`,
    - webhook callback payloads now include `route` + `progress` for parity with SSE.
  - Completed Task 75 (clean-break enforcement for client surfaces):
    - removed legacy/re-export modules (`interfaces.http_client`, package-level CLI/client facades),
    - updated all in-repo callers to `interfaces.http_client_v2` + `interfaces.cli_app`,
    - kept touched modules below 500 LoC via targeted extraction helpers.
  - Completed Task 70 (chunk checkpoints + partial artifact retrieval):
    - added chunk-level checkpoint persistence + partial markdown assembly for long PDFs,
    - added v2 endpoints for early retrieval:
      - `GET /v2/convert/jobs/{job_id}/artifact/partial`
      - `GET /v2/convert/jobs/{job_id}/checkpoint`
    - kept the main v2 executor lean by extracting dedicated checkpointed PDF + non-PDF modules.
  - Completed Task 71 (cancel-with-save + resume-from-checkpoint):
    - cancel stops long PDF conversion at safe boundaries while preserving checkpoint + partial artifacts,
    - added `POST /v2/convert/jobs/{job_id}/resume` (idempotent per `(api_key, job_id, Idempotency-Key)`),
    - added contract tests that lock deterministic baseline vs resumed final artifact.
  - Validation evidence:
    - `pdm run format-all` (pass)
    - `pdm run lint-fix` (pass)
    - `pdm run typecheck-all` (pass)
    - `pdm run pytest-root tests/sir_convert_a_lot` (pass: `421 passed, 5 skipped`)
    - `pdm run coverage-gate` (pass: total coverage `96.61%`)
    - `pdm run validate-tasks` (pass: `Validated 106 backlog files`)
    - `pdm run validate-docs` (pass: `Validated docs=131 rules=9`)
    - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

- 2026-03-01:

  - Completed Task 61 security follow-up hardening for Pandoc wrappers:
    - added `--sandbox` to all v2 Pandoc conversion wrappers to close unsandboxed
      SSRF/LFI attack surface,
    - introduced shared bounded subprocess helper:
      - `scripts/sir_convert_a_lot/infrastructure/pandoc_subprocess.py`,
    - replaced unbounded `capture_output=True` wrapper execution with bounded
      stderr capture via temp-file strategy and timeout-safe process cleanup.
  - Hardened workdir traversal error echo handling in executor:
    - sanitized user-provided filename echo details in
      `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`.
  - Extended and updated regression tests for sandbox and timeout behavior:
    - `tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py`
    - `tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py`
    - `tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py`
  - Validation evidence for Task 61:
    - `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 157 source files`)
    - `pdm run run-local-pdm coverage-gate` (pass: `392 passed, 5 skipped`; coverage `95.39%`)
    - `pdm run run-local-pdm validate-tasks` (pass: `Validated 86 backlog files`)
    - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=108 rules=9`)
  - Task 61 moved to `completed` with checklist/evidence synchronized.
  - Scaffolded the next downstream-GUI enabling slice (proposed) via ADR-0004 and Story 16.
  - Proposed execution order: Task 64 -> Task 65 -> Task 66.
  - Completed Task 64 (ADR-0004 contract alignment) and Task 65 (v2 PDF layout presets):
    - added `conversion.pdf_layout` to v2 JobSpec and applied it to PDF outputs via deterministic
      generated CSS (`pdf_layout_presets_v2.py`),
    - added unit and executor tests; executor tests re-split to keep modules \<500 LoC,
    - coverage gate remained >=90% (pass: `95.87%`).
  - Completed Task 66 (`docx -> pdf` v2 route):
    - added sandboxed Pandoc DOCX->HTML wrapper with extracted media under workdir,
    - added executor branch `pipeline_used="docx_to_pdf_v2"` and CLI route registry entry,
    - updated v2 converter docs and downstream integration contract to mark `docx -> pdf` implemented.

- 2026-02-28:

  - Epic 05 was fully executed and terminalized in strict order:
    - clean-break v2-only removal (`T04-T05`, `S01`),
    - DOCX template governance and endpoints (`T06-T07`, `S02`),
    - Markdown ingress routes (`T08-T09`),
    - downstream contract + runtime/docs cleanup (`T10-T12`, `S03-S04`),
    - async push ADR/contract/implementation (`T02-T03`, `T13-T16`, `S05`).
  - Key milestones from the day:
    - v1 conversion surfaces removed; v2 route registry and contracts hardened,
    - `docx -> md` and `html -> md` routes implemented with deterministic validation and tests,
    - eval container/runtime removed; topology simplified to single runtime,
    - async push stack completed (SSE replay + webhook onboarding + signed retry/DLQ delivery),
    - Task 60 security hardening delivered (WeasyPrint SSRF/LFI guard + traversal + timeout parity).
  - Validation trend remained above target throughout:
    - coverage gates across slices ranged from `93.03%` to `96.14%`,
    - docs/task validators and typecheck remained passing.
  - Canonical detailed evidence is preserved in:
    - `docs/backlog/tasks/task-44-*.md` through `task-60-*.md`,
    - `.agents/session/handoff.md` dated entries for 2026-02-28.

- 2026-02-18:

  - Epic 04 delivered service API v2 multi-format runtime and CLI remote-only pivot
    for non-PDF->MD routes.
  - Follow-up hardening tasks 40-42 completed (tests, zip-hardening, cancellation CAS).

## Next Actions

- Continue Epic 06 execution sequence under Story 20:
  - execute `T72` -> `T74`.
- Keep docs/task status synchronization strict as tasks terminalize:
  - task status terminal before epic/story checkboxes are checked.
- After `T74`, publish benchmark evidence and lock runbook defaults/guardrails for parallel OCR.
