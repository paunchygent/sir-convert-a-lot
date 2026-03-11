---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot.md
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

This file is the canonical long-term memory index for session progress; session handoff summaries must be archived here when `handoff.md` is pruned. Current epic entrypoint:
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
  - Opened `T107` so `task-103-preprocess` could move from repo fixtures to
    staged Hemma public corpora while keeping the deterministic corpus bundle
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
  - Detached `T108` proof then established the exact failure mode: Hemma
    kernel logs recorded a real Python OOM kill inside the detached Docker
    scope at `2026-03-08 21:41:24`, after `88` `audio_24k` files, `10` refs,
    and `51` curated `swedish_smoke_train` rows had already been emitted but
    before final manifests/reports existed.
  - Opened `T110` and `T111` as the next hardening slices:
    `T110` for disk-backed row/finalization split and `T111` for optional
    provenance-safe ASR relabeling.
  - Implemented the first `T110` slice on `main`: the Task 103 preprocessing
    monolith is now split into stage modules with durable spool rows,
    spool-driven finalization, and explicit row/GPU plus chunk-size controls.
  - Ran the first bounded detached `T108` proof after the run-root and
    scratch-mount fixes with `3` row workers and `3` GPU ASR workers; the
    scratch-backed run root now preserves real partial artifacts (`inventory`,
    `run.json`, `status.json`, `5` `audio_24k` files), and the blocker has
    narrowed to a clean meta-tensor runtime error rather than OOM, detach
    loss, or artifact-loss drift.
  - Ran the first detached post-`T110` `T108` proof with
    `row-worker-count=10`, `gpu-asr-worker-count=5`, and
    `audio-codes-chunk-size=4`; it exited `139`, the kernel log pinned the
    crash to `libaotriton_v2.so.0.11.1`, and root-disk pressure was confirmed
    as a separate operational problem.
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
    finalized successfully in fresh stage-isolated containers, and then
    promoted via a separate `reports` stage. Final counts: `smoke=52`,
    `pilot=52`, `scaleup=58`, `checkpoint_dev=8`, `final_test=8`,
    `waxholm_control=8`.
  - Completed the remaining `T114` cleanup/alignment pass: the public
    `task-103-preprocess-public-corpus` command now points at the detached
    Task 114 orchestrator, `Task 103` rejects non-canonical `stage=all`
    execution by default, `status.json` preserves row and finalization
    heartbeat fields across stage completion, and reports-stage promotion is
    now the only canonical promotion path.

- 2026-03-10:
  - Completed `T124-T128`: portable Colab slices now support repo-owned localization, archive/timing progress logs, the canonical repo URL, and GPU preflight while the notebook stays a thin Task 103 orchestrator.
  - Completed live localized Colab proof `task121-colab-proof-rowproc-20260310a`: `256/256` rows finished with `256` spool rows and `256` `audio_24k` files at about `11.2` rows/minute end to end and `12-13` rows/minute in steady state.
  - Completed `T129-T130`: the notebook now defaults to `task129-scale-slice-1-of-2-20260311a`, a stable `RUN_ID`, persistent Google Drive storage for cross-session resume safety, the next `10:2` Colab worker mix, and a forced refresh of any existing Colab repo checkout before bundle lookup.

- 2026-03-11:
  - Completed `T131` to harden Drive-backed Task 103 resume performance after the persistent Colab `task129` run exposed a real bottleneck: row-processing now maintains `spool/completed_row_keys.jsonl`, resume prefers that sequential index, older run roots rebuild it from canonical spool JSON, stale crash tails self-heal by skipping rows whose spool artifact already exists, and the committed `task103_qwen_resume_index.py` helper can rebuild or validate historical run roots explicitly.
  - Completed `T132` to make the next Task 103 production refactors safer and more honest: the old `tests/sir_convert_a_lot/test_task103_qwen_preprocessing.py` monolith was removed, shared builders moved into `tests/sir_convert_a_lot/task103_test_support.py`, and the Task 103 test surface is now split into focused runner, processing, source-adapter, and ASR modules.
  - Completed `T133` as the first Task 103 production follow-on after `T132`: Task 103 run-status lifecycle and heartbeat orchestration now live in `task103_qwen_runner_status.py`, the public runner delegates to that helper instead of inlining nested callback/status logic, and the new direct helper tests make the run-status seam independently testable.
  - Tightened the decomposed Task 103 processing tests so they stub both `WhisperStrictScorer.ensure_loaded()` and `transcribe()` through shared test support, preserving row-processing/resume/finalization coverage while avoiding unnecessary local CPU ASR pipeline startup during focused test runs.
  - Completed `T134` to contain the `task116`/`task129` overlap incident: Task 121 now exposes repo-owned `plan-remaining-unique` and `dedupe-selected-source-records` commands, the portable-slice reference/runbook now require guarded allocation against completed run roots and already-issued selected-source manifests, and the live `task129` slice currently has `7347` rows still unique after subtracting both Hemma-completed and Colab-completed ownership.
  - Completed `T137` to turn overlap containment into the first durable allocation model: Task 103 now builds one canonical deduplicated processed root from ordered run roots, Task 121 now cuts the remaining universe into immutable `~5000`-row shards plus an append-only shard-assignment ledger, and the public Task 121 CLI has been reduced to a thin canonical surface over planning, localization, shard registry, and shard assignment modules.
  - Completed `T138` to restore order to the live pilot campaign: the canonical pilot root at `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task138-qwen-pilot-owned-20260311b` now retains `15748` safe unique rows, quarantines `88` same-row conflicts, confirms `2158` of the current `7970` completed Colab rows are duplicates of Hemma work, and ships the repo-owned Colab recovery bundle `colab_ml_training/proof_inputs/task138-task129-remaining-unique-20260311a-bundle.tar.gz` with `7187` remaining unique rows.
  - Completed `T139` to close the remaining governance drift after `T137`: Story 24, Epic 08, `T137`, and the Qwen Hemma/Colab runbook now all state the same normative rule that future preprocessing work issuance must go through shard ids, while `plan-remaining-unique` is restricted to incident recovery for already-issued manifests.
  - Completed `T140` to freeze the canonical pilot dataset and make conflict exclusions enforceable: canonical processed roots now emit owned-row, conflict-row, and freeze-summary artifacts, the frozen pilot root now lives at `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`, Task 121 exclusion flows now accept explicit `--exclude-row-keys-path` manifests, and the first post-pilot shard registry at `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-shards/task140-task129-post-pilot-remaining-20260311a` already excludes the frozen owned rows, frozen conflict rows, and the still-assigned `task138` Colab recovery manifest.
  - Completed `T141`: Task 101, Story 25, the Qwen runbook, the finetuning guide, and the relevant skills now require the frozen pilot root plus one deterministic Task 101 training bundle with `swedish_pilot_train`, `swedish_checkpoint_dev`, stable `refs/`, and machine-readable bundle metadata before launch.
  - Opened `T142`: materialize that deterministic Task 101 pilot bundle from the frozen pilot root and retarget the Task 101 runner away from the generic promoted Task 103 corpus view.

## Next Actions

- Current local execution focus is Epic 08 canonical ownership hardening: the first canonical pilot root now exists, and the next allocation move should use it plus the future shard registry/assignment ledger instead of fresh overlapping slice math.
- Current pilot-training follow-on is `T142`: materialize the deterministic Task 101 pilot bundle from the frozen pilot root before any new bounded Hemma fine-tune launch is treated as canonical.
- Immediate operational follow-on is to reload Colab against `task138-task129-remaining-unique-20260311a-bundle.tar.gz` while keeping the same persistent `task129-colab-scale-rowproc-1-of-2-20260311a` run root so only the `7187` remaining unique rows are processed.
- Current reliability hardening follow-on is to validate the new `T131` resume index on the live persistent Colab run and capture the before/after restart latency once the next real resume is performed.
- Current preprocessing-quality follow-on is to use the decomposed `T132` test surface as the guardrail for the next Task 103 production refactors, starting with runner/orchestration responsibility review and any further domain extraction inside the Task 103 runtime.
- Current ownership-governance follow-on is to use the existing `task140-task129-post-pilot-remaining-20260311a` shard registry as the only future allocation surface for that bounded `task129` universe once the in-flight Colab recovery run is finished.
- Current Task 103 production follow-on after `T133` is source-resolution and run-metadata orchestration now that run-status lifecycle ownership has been extracted from the public runner.
- Parallel planning focus is Epic 08: `T100`, `T103`, `T106`, `T107`, `T108`, `T109`, `T115`, `T131`, `T132`, `T133`, `T134`, and `T137` are complete; bounded source-selection, persistent Colab resume, overlap containment, canonical processed-root dedupe, and immutable shard allocation are in place for the next preprocessing campaign.
- Historical corpus-expansion note: `T116` Hemma row-processing is now complete and has been folded into the `T138` canonical pilot ownership set.
- Follow-on hardening after the first detached `T108` repro is now in place: `T110`, `T112`, `T113`, and `T114` are complete; `T111` remains the later provenance-safe ASR relabel candidate task.
- `T115` evidence under `build/verification/task-115-qwen-training-resume-proof/task115-20260309t155615z/` proves durable checkpoint, intentional stop, detached resume, and successful completion.
