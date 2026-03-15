---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-15'
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
  - docs/backlog/stories/story-27-transition-to-domain-centric-ml-pipeline-structure.md (completed)
  - docs/backlog/tasks/task-166-establish-domain-centric-directory-structure-and-shared-common-logic.md (completed)
  - docs/backlog/tasks/task-167-migrate-qwen-preprocessing-logic-to-domain-centric-modules.md (completed)
  - docs/backlog/tasks/task-168-migrate-qwen-training-and-detached-orchestration-to-domain-centric-modules.md (completed)
  - docs/backlog/tasks/task-169-rebuild-ml-cli-entrypoints-as-thin-domain-centric-wrappers.md (completed)
  - docs/backlog/tasks/task-170-align-dockerfiles-runbooks-and-backlog-to-domain-centric-structure.md (completed)
  - docs/backlog/tasks/task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md (proposed)
  - docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md (proposed)
  - docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md (proposed)
labels:
  - session-log
  - active-work
---

## Context

Epic 05 is complete (v2-only conversion architecture, deterministic markdown ingress routes, and template-governed DOCX/PDF pathways are delivered and validated).
Active focus is Epic 08: Qwen3-TTS Swedish language expansion, the live Hemma
Task 101 run, and Story 26 throughput/observability hardening toward the new
`>= 90%` steady-state GPU-busy target.
This file is the canonical long-term memory index for session progress; session handoff summaries must be archived here when `handoff.md` is pruned. Current epic entrypoint:

- `docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md`
  Primary implementation story (active sequence): Story 26 is now the explicit
  Task 101 follow-on optimization story:
  `docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md`
  Story 25 remains the baseline/runtime-contract story that the current live
  Hemma run still depends on:
  `docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md`

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
    parquet files onto the HDD storage tier with revision-pinned evidence in
    `build/reference/qwen3-tts-swedish-corpus/acquisition/report.json`.
  - Opened `T107` so `task-103-preprocess` could move from repo fixtures to
    staged Hemma public corpora while keeping the deterministic corpus bundle
    contract stable.
  - Completed the first live Hemma `T107` staged public-corpus preprocessing
    pass with the bounded `task-103-preprocess-public-corpus` surface:
    `fleurs` dev/test were capped to `8` rows each, labeled `waxholm` ran end
    to end, staged `rixvox` metadata was included, and the live result produced
    `inventory_rows=16841`, `curated_rows=24`, `admitted_rows=23`, and `prepared_rows=23`.
  - Opened `T108` as the next blocker before `T101`: `rixvox` still lacks
    committed audio materialization and train-family mapping, so the current
    preprocessing bundle is useful for eval/control corpora but not yet sufficient for the bounded Hemma fine-tune.
  - Completed `T109` and corrected the runtime-model drift introduced during
    `T103` / `T107`: `task-103-preprocess-public-corpus` now runs through the
    Task 100-style Qwen container on Hemma, with canonical DATA/HF cache
    mounts and the reproduced public-corpus result (`inventory_rows=16841`,
    `curated_rows=24`, `admitted_rows=23`, `prepared_rows=23`).
  - Began live `T108` bounded `rixvox` train-family proof work with
    `train_metadata.parquet` plus `train_0.tar.gz` staged on Hemma DATA and a
    bounded `--rixvox-max-rows-per-split 64` containerized preprocessing run.
  - Recorded the Hemma long-job execution rule: detached only; the earlier
    attached `137` from `T109` is not treated as canonical `T108` evidence.
  - Detached `T108` proof then established the exact failure mode: Hemma
    kernel logs recorded a real Python OOM kill inside the detached Docker
    scope at `2026-03-08 21:41:24`, after `88` `audio_24k` files, `10` refs,
    and `51` curated `swedish_smoke_train` rows but before final manifests/reports existed.
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
    execution by default, `status.json` preserves row and finalization heartbeat fields
    across stage completion, and reports-stage promotion is now the only canonical promotion path.
- 2026-03-10:
  - Completed `T124-T128`: portable Colab slices now support repo-owned localization, archive/timing progress logs, the canonical repo URL, and GPU preflight while the notebook stays a thin Task 103 orchestrator.
  - Completed live localized Colab proof `task121-colab-proof-rowproc-20260310a`: `256/256` rows finished with `256` spool rows and `256` `audio_24k` files at about `11.2` rows/minute end to end and `12-13` rows/minute in steady state.
  - Completed `T129-T130`: the notebook now defaults to `task129-scale-slice-1-of-2-20260311a`, a stable `RUN_ID`, persistent Google Drive storage for cross-session resume safety, the next `10:2` Colab worker mix, and a forced refresh of any existing Colab repo checkout before bundle lookup.
- 2026-03-11:
  - Completed `T131-T143` preprocessing/resume/governance hardening for Story 24, including canonical dedupe and immutable shard issuance, frozen pilot ownership enforcement, deterministic Task 101 pilot-bundle governance, and relocation-safe launch/report contracts.
  - Completed `T117` signal-safe Task 101 training behavior (final durable checkpoint on stop, partial HF-cache sync fallback, and explicit BuildKit cold-build warnings).
- 2026-03-12:
  - Completed `T148-T149`: Task 101 pilot-bundle materialization now stages copy, bounded `finalize-batch`, and final `assemble`, persists `task101_pilot_bundle_plan.json`, `task101_pilot_bundle_events.jsonl`, and `task101_pilot_bundle_status.json`, and finalization now runs inside the governed Task 100/101 Qwen image with the fixed in-container HF cache contract (`/cache/huggingface`) instead of the host PDM environment. Follow-up added runtime provenance, preserved host-visible bundle/report paths, and kept direct `finalize-batch` plus `build` under the same governed runtime contract.
  - Completed `T150` as the immediate throughput correction after the live Hemma Task 101 bundle run showed the governed runtime was still CPU-bound during `audio_codes` generation. The active host-runtime bundle build at `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h` was intentionally stopped after `swedish_pilot_train:batch-00012` completed and `batch-00013` had started so the resumable bundle root can be retried under the new GPU-backed tokenizer posture. The governed Task 101 batch runtime now loads `Qwen3TTSTokenizer` onto `cuda:0` with `bfloat16` plus `flash_attention_2`, writes `reports/task101_pilot_bundle_audio_codes_runtime.json`, and fails closed instead of silently continuing on CPU. Same-day follow-up `T151` repaired the remaining Task 101 `/srv/...` output-root bind gap by reusing the shared home-backed Docker mount fallback.
  - Completed `T152`: the governed Task 101 audio-code path now preloads waveform arrays with `soundfile`, runs batch containers as the host uid/gid plus GPU device groups, and keeps `chunk_size=64` as the stable Hemma default. Evidence: `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312e-hostuser/preload-chunk64-span1` produced `7m 07s` for `swedish_pilot_train:batch-00000`; `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1` produced `duration_seconds=481.3638345239997` and `rows_per_minute=15.954667652991478`; requested `chunk_size=128` repeatedly OOMed; and model encode still dominates chunk-64 runtime (`audio_codes_model_encode_seconds=424.4988881419995` out of `audio_codes_chunk_total_seconds=425.61176394299764`).
- 2026-03-13:
  - Completed Story 26 `T156-T160` first-five sequence and implemented `T161/T162` code surfaces with full local gates.
  - Captured bounded Hemma evidence: `task161-20260313t212725z-cache-off` median `26%`, `task161-20260313t212725z-cache-on` median `8%`, `task162-20260313t220644z-profile` median `3%`; runtime cache stats were `0/0/0` across all three runs.
  - Recorded `T162` ROCm attribution: HIP API `98.74s`, kernels `102.08s`, memory copy `1.73s`; top API calls were `hipLaunchKernel=44.18s`, `hipMemcpyWithStream=21.52s`, `hipEventSynchronize=17.89s`.
  - Synced Story 26, Epic 08, the Qwen runbook, and the Task 101 reference analysis to one root-cause posture: host-orchestration/synchronization bound lane with persistent `NaN` quality risk.
  - Opened follow-on hard-fix tasks `T171`, `T173`, and `T172`.
  - Completed Story 27 and Tasks 166-170 (domain-centric ML structure, CLI rebuild, Docker/runbook alignment).
- 2026-03-15:
  - Completed `T184`: schedule-driven resume now advances the latest-launch pointer, schedule preflight fails closed for launch-derived checkpoint/eval/bundle paths, and checkpoint persistence proves retention `3`.
  - Opened `T185`: the legacy `1236`-step run can relaunch without manual JSON edits and can override a stale bundle root, but the first probe exposed stale reused-run artifacts and an impossible saved `next_step_in_epoch` that did not fail closed against the replacement bundle `dataloader_length`. Follow-up landed stale-artifact filtering, a trainer-side resume-cursor guard, and a standalone eval baseline for the original `1236` checkpoint (`eval_loss=6.440637648105621` over `8` eval batches). The next relaunch decision should now be based on that baseline rather than blind resume.

## Next Actions

- Story 26 follow-on: execute `T171`, `T173`, and `T172` in order, then rerun acceptance evidence until the lane can prove `>= 90%` steady-state median GPU busy on a finite-loss window.
- Story 27 follow-on: finish remaining moved-test import refactor under `tests/sir_convert_a_lot/ml/qwen/`, then run the focused Qwen test lane for status synchronization.
- Task 185 follow-on: finish incompatible-resume-cursor remediation, pull the stale-artifact status fix onto Hemma after the active container stops, run standalone eval against the preserved legacy checkpoint, then consider the next detached relaunch.
