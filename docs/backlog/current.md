---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-07'
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
  - Ran the first live Hemma `T81` benchmark successfully from a runtime standpoint, but manual
    listening review rejected the sample (timbre mismatch, artifacts, uneven pacing), so `T81`
    stayed open for setup remediation.
  - Planned the initial `T81` remediation around three concrete fixes: sample-rate boundaries,
    intended reference preprocessing, and paired processed-reference/base/cloned artifacts.
  - Implemented the local `T81` remediation slice:
    - split the oversized OpenVoice adapter support into a dedicated helper module,
    - replaced the upstream `openvoice.se_extractor` import with a committed local VAD-only
      reference-preprocessing helper,
    - removed the broken `faster-whisper` / PyAV dependency chain from the sidecar image so Hemma
      can rebuild on Python 3.12,
    - preserved the sidecar-only boundary so the main service image remains untouched.
  - Ran the corrected Hemma rerun far enough to replace the old `faster-whisper` / PyAV blocker
    with a narrower VAD dependency failure inside `/synthesize`.
  - Took the ruthless review as binding and implemented the evidence-discipline correction slice:
    - `T81` / `T84` now record machine-readable `benchmark_status`, `evidence_status`,
      `blocking_step`, and failure metadata,
    - the benchmark now declares Torch Hub cache roots under the canonical HF cache tree and
      records reference-audio SHA256,
    - local tests now cover partial-run report writing and Torch Hub cache declaration.
  - Ran the updated current-head Hemma rerun on `beac775f1f6c021946105adef0f007cf06b908d3`
    without `--skip-build`; it produced an atomic partial bundle and narrowed the next blocker to
    the synthesize-stage Torch Hub / Silero mismatch from `whisper-timestamped`.
  - Removed `whisper-timestamped` from the active Task 81 reference-preprocessing path and
    switched the sidecar to direct local Silero VAD loading from the canonical Torch cache.
  - Ran the rebuilt current-head Hemma rerun on `e1d5901879c64a21f256a88352f407e6ce2ae45d`:
    - one new atomic partial evidence bundle now exists for `run_id=20260306T222647Z`,
    - `/synthesize` now succeeds with `200 OK` and writes `artifacts/sample_sv.wav`,
    - the current blocker has moved to `collect_setup_artifacts`,
    - processed-reference, base-output, and converter-input artifacts are still missing, so the
      corrected setup is still not ready for listening review.
  - Fixed the remaining `collect_setup_artifacts` blocker without introducing legacy cache paths:
    - replaced unreliable `docker cp` evidence export with streamed `docker exec tar` extraction,
    - reran `T81` on Hemma and produced one atomic complete evidence bundle for
      `run_id=20260306T224057Z` on `61b263cab56118677dc47810b615daaf0adbe463`,
    - preserved `processed_reference`, `base_sv.wav`, `base_sv_converter_input.wav`, and
      `sample_sv.wav` under `build/verification/task-81-openvoice-v2-hemma/artifacts/`; `T84`
      is complete and `T81` is now blocked only on the qualitative recommendation decision.
  - Recorded the qualitative `T81` decision:
    - the Swedish base artifact is very unnatural with pitch, tone, and phrasing issues,
    - the cloned artifact is somewhat better but still sub-par,
    - OpenVoice is technically feasible on Hemma but not the lead Swedish teacher-voice
      candidate, so Story 23 now advances to `T82`.

- 2026-03-07:

  - Redirected Story 23 from deferred XTTS comparison to the active `T85`
    F5-TTS lane, prepared deterministic F5 reference evidence, and recorded a
    technically successful but qualitatively rejected Hemma benchmark under
    `build/verification/task-85-f5-tts-hemma/`.
  - Implemented and verified `T86` Chatterbox on Hemma, including the dedicated
    sidecar image, runtime, reporting, and deterministic evidence under
    `build/verification/task-86-chatterbox-hemma/`; runtime truth is now fixed
    to the live ROCm stack on `AMD Radeon AI PRO R9700`.
  - Completed `T87` as the first documented Chatterbox tuning sweep and opened
    `T88` / `T89` for the bounded eSpeak preprocessing experiment.
  - Completed `T89` on live Hemma:
    - baseline and eSpeak-preprocessed lanes both synthesized successfully,
    - deterministic evidence now exists under
      `build/verification/task-89-chatterbox-espeak-hemma/`,
    - the run also forced one deterministic Chatterbox image fix:
      prefetch `spacy_pkuseg` assets during image build so startup no longer
      depends on a live model download.
  - Recorded the next explicit Chatterbox quality requirement:
    - the current path is still single-pass with no sentence splitting,
      prosodic-boundary detection, chunk batching, or stitching/cross-fade,
    - `T90` is now the follow-on implementation task for that missing quality
      layer.

- 2026-03-05:

  - Re-terminalized Task 73 after ruthless review remediation:
    - canonical phase timing keys and app-owned telemetry sink wiring landed,
    - bounded-cardinality worker/job/retry/duration metrics replaced the older shape,
    - sustained-load evidence was recorded in
      `build/benchmarks/story-20/task-73-telemetry-overhead-local.json`,
    - remediation validations passed (`format-all`, `lint-fix`, `typecheck-all`, targeted pytest).
  - Completed Task 76 deploy-and-verify evidence plus Task 77 multilingual OCR hardening; full
    detail remains in the linked Epic 06 / Story 20 / Task 76 docs.

- 2026-03-04:

  - Planned Epic 06 long PDF reliability/performance work under the new progress, checkpoint,
    resume, and throughput stories.
  - Completed Tasks 67-71 and 75 in the first Epic 06 delivery slice:
    - progress-aware timeout classification,
    - ADR-0005 lock-in for long-job progress/checkpoint/cancel/resume,
    - page progress fields plus SSE/webhook parity,
    - chunk checkpoints plus partial artifact retrieval,
    - cancel-with-save plus resume,
    - clean-break v2 client-surface enforcement.
  - Validation evidence remained green across that delivery slice; detailed results stay in the
    linked task docs and tests.

## Next Actions

- Current local execution focus is Epic 07 Story 23 `T90`
  segmentation/stitching quality work for Chatterbox, then `T83`, with `T82`
  kept deferred.
- Other devs are closing Epic 06 `T74`; sync backlog terminal states once their Hemma evidence lands.
- `T81` is complete with a negative recommendation: OpenVoice is technically feasible but not the
  lead Swedish teacher-voice candidate.
- Immediate Story 23 focus is now `T90` segmentation/stitching quality work
  after the completed `T89` eSpeak experiment, then listening review and
  recommendation capture, with `T83` kept as the Swedish pronunciation control
  and `T82` remaining deferred.
- Follow-on cleanup queue after the active TTS benchmark lane remains: `T62`, `T25` + `T26`, `T12`, `T08`.
