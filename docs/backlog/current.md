---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-09'
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

Primary implementation stories (active sequence): Stories 17-19 are completed; Story 20 remains
active: `docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md`

## Worklog

- 2026-03-06:

  - Completed `T72`, opened Epic 07 / Story 23, remediated `T81`, closed
    `T84`, and advanced Story 23 to `T82`.

- 2026-03-07:

  - Redirected Story 23 to `T85`, completed `T86-T93`, and established
    Chatterbox as the production-candidate Swedish TTS sidecar lane on Hemma.

- 2026-03-08:

  - Completed `T95` and `T97` follow-up work on the F5 Swedish lane:
    `T95` exposed the remaining tuning controls and exact voice-tag syntax,
    and `T97` replaced the old local `10` second reference cap with a bounded
    `12.0` second maximum.
  - Ran the corrected live Hemma Christian Hedlund rerun for `T97` under
    `build/verification/task-97-f5-reference-12s-hemma/`; the `11.5` second
    reference clip now remained intact and output duration increased to
    `18.538` seconds from the earlier `16.266` second `T95` run.
  - Implemented and ran the new segmented F5 benchmark lane under
    `build/verification/task-97-f5-segmented-hemma/`; deterministic
    `segment-debug/` evidence now exists, the segmented lane emitted `4`
    chunks and a final duration of `18.362` seconds, and the current
    recommendation is to keep segmented F5 as a comparison/debug lane rather
    than making it the default path.
  - Opened Epic 08 as a separate Qwen Swedish fine-tuning lane with Stories
    24-25, Tasks 99-104, the dedicated finetuning runbook/skill, and the
    measured Hemma `1.7B` memory proof recorded as planning input.
  - Re-enabled Triton flash attention as the default in the current Qwen Hemma
    benchmark lane and updated the benchmark/reporting docs so future evidence
    records whether Triton was enabled.
  - Added `T105` as the research-handoff slice for Epic 08 so the first
    multi-speaker experiment is preceded by a tracked repomix package, research
    brief, and source map instead of freeform external searching.
  - Completed the hardened Task 100 runtime bring-up on live Hemma:
    the dedicated ROCm training image now builds through a container-local
    virtualenv, uses `HF_HOME` and `dtype=`, and the smoke report under
    `build/verification/task-100-qwen-finetune-smoke/` confirms
    `flash_attn==2.8.3` with successful `flash_attention_2` model init on the
    `AMD Radeon AI PRO R9700`.
  - Completed the first committed Task 103 preprocessing slice:
    `pdm install -G qwen-preprocessing` plus `pdm run task-103-preprocess`
    now emits the deterministic artifact bundle under
    `build/reference/qwen3-tts-swedish-corpus/`, including inventory, curated,
    raw, prepared, and summary-report layers; the first bundle produced
    `2` admitted Swedish smoke rows and `2` prepared Qwen rows.
  - Opened and began `T106` as the script-free public-corpus extension lane:
    the Task 103 core is now adapter-shaped, `fleurs` / labeled `waxholm` /
    `rixvox` parquet adapters exist, and the new Hemma-only
    `task-106-acquire` surface stages targeted revision-pinned raw assets onto
    `/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus/` instead of
    downloading large corpora locally.
  - Completed the first live Hemma `T106` acquisition pass on `main`:
    `task-106-acquire --waxholm-max-files 8 --request-pause-seconds 0.5`
    staged `4` `fleurs` files, `17` bounded `waxholm` files, and `2` `rixvox`
    parquet files onto the HDD storage tier, with revision-pinned evidence written to
    `build/reference/qwen3-tts-swedish-corpus/acquisition/report.json` on
    Hemma.
  - Opened `T107` as the next active Epic 08 slice so `task-103-preprocess`
    can run against the staged Hemma public corpora rather than repo fixtures,
    while keeping the deterministic `build/reference/qwen3-tts-swedish-corpus/`
    contract stable.
  - Completed the first live Hemma `T107` staged public-corpus preprocessing
    pass with the bounded `task-103-preprocess-public-corpus` surface:
    `fleurs` dev/test were capped to `8` rows each, labeled `waxholm` ran end
    to end, and staged `rixvox` metadata was included in inventory. The live
    result produced `inventory_rows=16841`, `curated_rows=24`,
    `admitted_rows=23`, and `prepared_rows=23`.
  - Opened `T108` as the next blocker before `T101`: `rixvox` still lacks
    committed audio materialization and train-family mapping, so the current
    preprocessing bundle is real and useful for eval/control corpora but not
    yet sufficient for the bounded Hemma fine-tune.
  - Completed `T109` and corrected the runtime-model drift introduced during
    `T103` / `T107`: `task-103-preprocess-public-corpus` now runs through the
    Task 100-style Qwen container on Hemma, and the live remediation evidence
    under `build/verification/task-109-qwen-containerized-preprocessing/`
    records the canonical DATA/HF cache mounts plus the reproduced
    public-corpus preprocessing result (`inventory_rows=16841`,
    `curated_rows=24`, `admitted_rows=23`, `prepared_rows=23`).
  - Began live `T108` bounded `rixvox` train-family proof work with
    `train_metadata.parquet` plus `train_0.tar.gz` staged on Hemma DATA and a
    bounded `--rixvox-max-rows-per-split 64` containerized preprocessing run.
  - Recorded the Hemma long-job execution rule: detached only; the earlier
    attached `137` from `T109` is not treated as canonical `T108` evidence.
  - Detached `T108` proof then established the exact failure mode:
    Hemma kernel logs recorded a real Python OOM kill inside the detached
    Docker scope at `2026-03-08 21:41:24`, after `88` `audio_24k` files,
    `10` refs, and `51` curated `swedish_smoke_train` rows had already been
    emitted but before final manifests/reports existed.
  - Opened `T110` and `T111` as the next docs-as-code hardening slices for the
    preprocessing lane: `T110` will split row preprocessing from finalization
    with disk-backed row results, and `T111` will define an optional
    provenance-safe ASR relabeling lane without silently replacing source
    transcripts.
  - Implemented the first `T110` slice on `main`: the Task 103 preprocessing
    monolith is now split into stage modules, row-processing persists durable
    spool rows, finalization rebuilds canonical refs from the spool, and the
    runtime now exposes explicit row/GPU concurrency plus chunked
    `audio_codes` controls for the next detached `T108` proof.
  - Ran the first bounded detached `T108` proof after the run-root and
    scratch-mount fixes with `3` row workers and `3` GPU ASR workers; the
    scratch-backed run root now preserves real partial artifacts (`inventory`,
    `run.json`, `status.json`, `5` `audio_24k` files), and the blocker has
    narrowed to a clean meta-tensor runtime error rather than OOM, detach
    loss, or artifact-loss drift.
  - Ran the first detached post-`T110` `T108` proof with
    `row-worker-count=10`, `gpu-asr-worker-count=5`, and
    `audio-codes-chunk-size=4`; the container exited `139`, the kernel log
    pinned the crash to `libaotriton_v2.so.0.11.1`, and Hemma root-disk
    pressure is now confirmed as a separate operational problem because `/`
    has only about `1.3 GB` free while DATA still has ample space.
  - Completed `T112` and `T113`: Hemma Qwen hot output now persists on SSD
    scratch, raw Swedish corpora persist on HDD storage, Docker root is back on
    the canonical snap path `/var/snap/docker/common/var-lib-docker` while
    physically bind-mounted from `/srv/scratch/docker/data-root`, and the old
    home-path Docker root entry was removed from `/etc/fstab`.
  - Recovered the preserved detached `4`-worker `T108` run root after the hard
    power cycle and confirmed the host wedge happened during
    `swedish_scaleup_train` finalization, after complete `swedish_smoke_train`
    and `swedish_pilot_train` outputs had already been written.
  - Opened `T114` to hard-isolate row-processing and finalization on Hemma:
    the canonical path is now detached row-processing first, then detached
    fresh-process finalization, then reports/promotion, never one GPU-backed
    `stage=all` run.
  - Completed the recovered `T108` proof on Hemma after `T114` hardening:
    the preserved crashed run root was resumed without rerunning row-processing,
    `swedish_scaleup_train` finalized successfully in one fresh container,
    the remaining eval/control families finalized in a second
    fresh container, and a third fresh `reports` stage promoted the canonical
    corpus view to the successful run root. Final counts: `smoke=52`,
    `pilot=52`, `scaleup=58`, `checkpoint_dev=8`, `final_test=8`,
    `waxholm_control=8`.

- 2026-03-05:
  - Re-terminalized `T73` with sustained-load evidence and completed `T76-T77`;
    see the linked Epic 06 / Story 20 task docs for detail.
- 2026-03-04:
  - Planned Epic 06 long PDF reliability/performance work and completed
    `T67-T71` plus `T75`; detail remains in the linked task docs and tests.
## Next Actions

- Current local execution focus is Epic 07 Story 23 listening review on
  `T91`, then `T93`, then `T83`, with `T82` kept deferred.
- Parallel planning focus is Epic 08: `T100`, `T103`, `T106`, `T107`,
  `T108`, and `T109` are complete. The recovered `T108` run root is now the
  canonical promoted corpus view on Hemma, so the next functional step before
  broader scale-up is `T101`.
- Follow-on hardening after the first detached `T108` repro is now partly in
  place: `T110` has delivered the staged spool/finalization split plus explicit
  row/GPU concurrency controls, and `T112` / `T113` have closed the Hemma
  storage-model blocker. `T114` has now proven the isolated-stage recovery
  model end to end; the remaining open `T114` work is richer stage/family/chunk
  heartbeat detail in `status.json`. `T111` remains the later provenance-safe
  ASR relabel candidate task.
- Other devs are closing Epic 06 `T74`; sync backlog terminal states once
  their Hemma evidence lands.
- Follow-on cleanup queue after the active TTS benchmark lane remains: `T62`, `T25` + `T26`, `T12`, `T08`.
