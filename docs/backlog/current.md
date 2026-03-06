---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-06'
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

- 2026-03-06:

  - Completed Task 72 for Story 20 bounded parallel PDF chunk execution.
  - Added deterministic Task 72 benchmark evidence via `pdm run benchmark:task-72` at
    `build/benchmarks/story-20/task-72-parallel-throughput-local.json`
    (`comparison.p50_wall_clock_improvement_percent=73.274`, `comparison.byte_identical_to_serial=true`).
  - Updated runbook/reference/task docs and checked the Epic 06 `T72` tracker box.
  - Planned the next feature line as Epic 07 sidecar-backed TTS: added Epic 07 / Story 22 /
    Tasks 78-80, accepted ADR-0006, published the approved `md -> wav` contract draft, and marked
    legacy Story 07 TTS planning as superseded by Epic 07.
  - Added the follow-on Swedish cloning benchmark slice under Epic 07 as Story 23 with
    `T81` OpenVoice V2, `T82` XTTS-v2, and `T83` MMS Swedish.
  - Drafted and accepted ADR-0007 to define the reusable internal multi-backend sidecar
    capability contract before `T81` starts.
  - Started `T81` implementation against ADR-0007:
    - added the reusable normalized sidecar contract plus the first OpenVoice V2 adapter app,
    - added the dedicated OpenVoice benchmark image/build surface and `benchmark:task-81`,
    - added Task 81 unit coverage plus runbook/task/story status updates.
  - Ran the first live Hemma `T81` benchmark successfully from a runtime standpoint:
    - OpenVoice sidecar booted on the R9700 host,
    - canonical caches were reused,
    - Swedish cloned output was generated from the approved teacher reference clip.
  - Manual listening review rejected the current `T81` sample:
    - timbre not close enough to the teacher voice,
    - audible artifacts,
    - uneven pacing.
  - Current `T81` conclusion:
    - the pipeline is technically working,
    - the current model setup is bad,
    - `T81` stays open for setup remediation before we treat OpenVoice as credible.
  - Planned the initial `T81` remediation around three concrete fixes: sample-rate boundaries,
    intended reference preprocessing, and paired processed-reference/base/cloned artifacts.
  - Implemented the local `T81` remediation slice:
    - split the oversized OpenVoice adapter support into a dedicated helper module,
    - replaced the upstream `openvoice.se_extractor` import with a committed local VAD-only
      reference-preprocessing helper,
    - removed the broken `faster-whisper` / PyAV dependency chain from the sidecar image so Hemma
      can rebuild on Python 3.12,
    - preserved the sidecar-only boundary so the main service image remains untouched.
  - Ran the corrected Hemma rerun far enough to replace the old blocker: the sidecar image now
    builds and boots past the old `faster-whisper` / PyAV failure, and the next live failure was
    narrowed to the VAD dependency path inside `/synthesize`.
  - Took the ruthless review as binding and implemented the evidence-discipline correction slice:
    - `T81` / `T84` now record machine-readable `benchmark_status`, `evidence_status`,
      `blocking_step`, and failure metadata,
    - the benchmark now declares Torch Hub cache roots under the canonical HF cache tree and
      records reference-audio SHA256,
    - local tests now cover partial-run report writing and Torch Hub cache declaration.
  - Ran the updated current-head Hemma rerun on `beac775f1f6c021946105adef0f007cf06b908d3` without
    `--skip-build`:
    - one atomic partial evidence bundle now exists for `run_id=20260306T220740Z`,
    - the earlier export failure did not reproduce,
    - current blocker is now synthesize-stage Torch Hub / Silero repo-path mismatch,
    - `/synthesize` returns `500` because `whisper-timestamped` still asserts
      `/root/.cache/torch/hub/snakers4_silero-vad_master`,
    - corrected setup quality still cannot be judged because no processed-reference/base artifacts
      are emitted before that failure.
  - Removed `whisper-timestamped` from the active Task 81 reference-preprocessing path and
    switched the sidecar to direct local Silero VAD loading from the canonical Torch cache.
  - Ran the rebuilt current-head Hemma rerun on `e1d5901879c64a21f256a88352f407e6ce2ae45d`:
    - one new atomic partial evidence bundle now exists for `run_id=20260306T222647Z`,
    - `/synthesize` now succeeds with `200 OK` and writes `artifacts/sample_sv.wav`,
    - the current blocker has moved to `collect_setup_artifacts`,
    - processed-reference, base-output, and converter-input artifacts are still missing, so the
      corrected setup is still not ready for listening review.

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
  - Completed Task 76 deploy-and-verify evidence plus Task 77 multilingual OCR hardening;
    canonical backlog updates landed in the linked Epic 06 / Story 20 / Task 76 docs.

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
  - Validation evidence remained green across the Epic 06 March 4 delivery slice; canonical
    detailed results stay in the linked task docs and tests.

## Next Actions

- Current local execution focus is Epic 07 Story 23 with `T81 -> T84`, then `T82 -> T83`.
- Other devs are closing Epic 06 `T74`; sync backlog terminal states once their Hemma evidence lands.
- Immediate `T81` remediation goal after the failed listening review: correct the OpenVoice setup,
  preserve the failed baseline, rerun with Swedish base vs cloned comparison artifacts, then decide whether OpenVoice remains viable before moving to `T82`.
- `T84` is now the explicit root-cause remediation lane and is review-bound to five concrete fixes:
  atomic rerun evidence, declared Torch/Silero cache truth, current-head export diagnosis,
  machine-readable benchmark status, preserved reference/setup artifacts, and a current-head Hemma rerun.
- Current `T81` blocker after the latest current-head rerun: recover setup-artifact collection so
  the corrected rerun preserves processed-reference, base-output, and converter-input artifacts, then rerun before any further listening review.
- Follow-on cleanup queue after the active TTS benchmark lane remains: `T62`, `T25` + `T26`, `T12`, `T08`.
