---
id: epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab
title: Qwen3-TTS Swedish language expansion fine-tuning on Hemma and Colab
type: epic
status: in_progress
priority: high
created: '2026-03-08'
last_updated: '2026-03-13'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-98-add-qwen-english-reference-clone-lane-to-hemma-benchmark.md
  - docs/backlog/tasks/task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md
  - docs/backlog/tasks/task-105-build-qwen3-tts-swedish-finetuning-research-repomix-package.md
  - docs/backlog/tasks/task-116-expand-rixvox-staging-and-run-a-sustained-detached-row-processing-window-for-the-bounded-hemma-pilot.md
  - docs/backlog/tasks/task-119-stream-rixvox-source-selection-and-make-preflight-status-truthful.md
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-123-add-resumable-row-processing-for-qwen-preprocessing-runs.md
  - docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md
  - docs/backlog/tasks/task-129-prepare-large-portable-colab-slice-for-multi-session-qwen-row-processing.md
  - docs/backlog/tasks/task-131-add-backward-compatible-resume-index-for-drive-backed-qwen-row-processing.md
  - docs/backlog/tasks/task-134-deduplicate-live-colab-remainder-and-enforce-unique-slice-allocation-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-135-plan-canonical-dedupe-of-qwen-preprocessing-storage-backups.md
  - docs/backlog/tasks/task-136-define-immutable-qwen-shard-registry-and-enforced-unique-work-allocation.md
  - docs/backlog/tasks/task-137-implement-canonical-qwen-processed-root-dedupe-and-immutable-shard-allocation.md
  - docs/backlog/tasks/task-138-canonicalize-qwen-pilot-ownership-and-salvage-the-remaining-colab-slice.md
  - docs/backlog/tasks/task-139-synchronize-qwen-shard-governance-across-story-24-epic-08-and-runbook.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
  - docs/backlog/tasks/task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md
  - docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md
  - docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-research-map-2026-03-08.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - tts
  - finetuning
  - swedish
  - hemma
  - colab
---

Major capability increment managed through linked stories.

## Goal

Plan and prove a Sir-owned `Qwen/Qwen3-TTS-12Hz-1.7B-Base` fine-tuning lane that
adds general Swedish language support through a multi-speaker dataset strategy,
while preserving the existing Sir Convert-a-Lot public TTS contract and Hemma
container/runtime discipline.

This epic is complete only when:

- the training/runtime lane is documented as a separate concern from Epic 07
  sidecar delivery,
- the Hemma `32.06 GB` ROCm host has a reproducible containerized full-finetune
  baseline for the `1.7B` model,
- the Swedish corpus curation and preprocessing path is explicit and reviewable,
- a Hemma pilot run is documented and the optional Colab fallback lane is
  decisioned explicitly,
- and the resulting model-delivery path still fits ADR-0006 and ADR-0007.

## In Scope

- A new model-training lane parallel to Epic 07, not embedded inside the
  current public `md -> wav` delivery scope.
- Containerized GPU-first runtime work for Qwen `1.7B` on Hemma as the default
  lane, with Colab documented only as an optional fallback/comparison lane.
- Re-enabling Triton flash attention for the existing Qwen Hemma benchmark lane
  so the serving/runtime baseline matches the now-understood ROCm container
  path on `AMD Radeon AI PRO R9700`.
- Multi-speaker Swedish corpus planning built from:
  - `KBLab/rixvox`,
  - `google/fleurs` Swedish (`sv_se`),
  - `KTH/waxholm`.
- Preprocessing/manifests that adapt the official Qwen `prepare_data.py` flow
  to Swedish full-finetune inputs and persistent cache discipline.
- Hemma pilot evidence for a real full-finetune step with `AdamW` on the
  `1.7B` model.
- Optional Colab H100 fallback guidance if Hemma later proves insufficient on
  stability or wall time.
- Evaluation planning focused on language support, pronunciation, prosody,
  held-out speakers, and operational fit for a future sidecar candidate.

## Out of Scope

- Changing the current public v2 API away from the provider-neutral ADR-0006
  / ADR-0007 contract.
- Collapsing model training into the main Sir Convert-a-Lot service image.
- Raw host or `systemd` training flows on Hemma.
- Treating single-speaker cloning or custom-voice adaptation as the end goal.
- Shipping a production default backend decision in this epic alone.

## Current Story 26 Throughput Reality (2026-03-13)

Latest bounded evidence from `T161` and `T162`:

- `T161` cache-off steady-state train median GPU busy: `26%`
- `T161` cache-on steady-state train median GPU busy: `8%`
- `T162` profiling steady-state train median GPU busy: `3%`
- all three runs reported effectively dead runtime cache stats:
  `cache_hits=0`, `cache_misses=0`, `cache_size=0`
- `T162` ROCm attribution:
  - HIP API `98.74s`
  - kernels `102.08s`
  - memory copy `1.73s`
  - top HIP API calls:
    `hipLaunchKernel=44.18s`, `hipMemcpyWithStream=21.52s`,
    `hipEventSynchronize=17.89s`

Epic-level interpretation:

- the current Task 101 lane remains host-orchestration/synchronization bound
- runtime `ref_mel` cache is not currently lifting saturation on this lane
- persistent `NaN` loss must be treated as a quality blocker before saturation
  evidence is considered trustworthy

## Stories

1. `docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md`
1. `docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md`
1. `docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md`
1. `docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md`

## Tasks (Ordered Planning and Execution Checklist)

1. `docs/backlog/tasks/task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark.md`
1. `docs/backlog/tasks/task-105-build-qwen3-tts-swedish-finetuning-research-repomix-package.md`
1. `docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md`
1. `docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md`
1. `docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md`
1. `docs/backlog/tasks/task-116-expand-rixvox-staging-and-run-a-sustained-detached-row-processing-window-for-the-bounded-hemma-pilot.md`
1. `docs/backlog/tasks/task-119-stream-rixvox-source-selection-and-make-preflight-status-truthful.md`
1. `docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md`
1. `docs/backlog/tasks/task-123-add-resumable-row-processing-for-qwen-preprocessing-runs.md`
1. `docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md`
1. `docs/backlog/tasks/task-129-prepare-large-portable-colab-slice-for-multi-session-qwen-row-processing.md`
1. `docs/backlog/tasks/task-131-add-backward-compatible-resume-index-for-drive-backed-qwen-row-processing.md`
1. `docs/backlog/tasks/task-134-deduplicate-live-colab-remainder-and-enforce-unique-slice-allocation-for-qwen-preprocessing.md`
1. `docs/backlog/tasks/task-135-plan-canonical-dedupe-of-qwen-preprocessing-storage-backups.md`
1. `docs/backlog/tasks/task-136-define-immutable-qwen-shard-registry-and-enforced-unique-work-allocation.md`
1. `docs/backlog/tasks/task-137-implement-canonical-qwen-processed-root-dedupe-and-immutable-shard-allocation.md`
1. `docs/backlog/tasks/task-138-canonicalize-qwen-pilot-ownership-and-salvage-the-remaining-colab-slice.md`
1. `docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md`
1. `docs/backlog/tasks/task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma.md`
1. `docs/backlog/tasks/task-156-activate-first-class-mlflow-and-accelerate-tracking-for-task-101-qwen-training.md`
1. `docs/backlog/tasks/task-157-add-truthful-live-heartbeat-and-phase-accounting-to-the-task-101-qwen-pilot-runtime.md`
1. `docs/backlog/tasks/task-158-make-high-resolution-hemma-resource-monitoring-default-for-long-task-101-qwen-runs.md`
1. `docs/backlog/tasks/task-159-correct-task-101-checkpoint-cadence-and-step-semantics-for-throughput-oriented-qwen-runs.md`
1. `docs/backlog/tasks/task-160-tune-the-task-101-qwen-dataloader-and-device-transfer-path-for-gpu-saturation.md`
1. `docs/backlog/tasks/task-161-add-ref-mel-caching-and-a-promotion-decision-for-precomputed-task-101-qwen-reference-mels.md`
1. `docs/backlog/tasks/task-162-add-bounded-pytorch-and-rocm-profiling-surfaces-for-task-101-qwen-bottleneck-attribution.md`
1. `docs/backlog/tasks/task-163-define-saturation-oriented-task-101-qwen-launch-profiles-and-acceptance-gates-on-hemma.md`
1. `docs/backlog/tasks/task-164-persist-precomputed-task-101-qwen-reference-mels-in-the-pilot-bundle-and-training-manifest-contract.md`
1. `docs/backlog/tasks/task-165-triage-and-remediate-miopen-workspace-warnings-in-the-task-101-rocm-qwen-training-lane.md`
1. `docs/backlog/tasks/task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md`
1. `docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md`
1. `docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md`
1. `docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md`
1. `docs/backlog/tasks/task-139-synchronize-qwen-shard-governance-across-story-24-epic-08-and-runbook.md`
1. `docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md`

## Acceptance Criteria

- [ ] Epic 08 remains explicitly separate from Epic 07 so model training does
  not distort the current sidecar-delivery scope.
- [ ] The Hemma runbook and the dedicated Qwen finetuning runbook both describe
  a containerized ROCm path with Triton flash attention enabled by default for
  the current Qwen benchmark lane.
- [ ] A committed backlog path exists for corpus curation, preprocessing,
  Hemma pilot execution, robust resumable checkpointing, and optional Colab
  fallback work.
- [x] The canonical preprocessing allocation model is visible from the epic
  entrypoint: future work issuance must go through immutable shard ids, while
  `plan-remaining-unique` is incident-recovery-only for already-issued
  manifests.
- [x] The frozen pilot canonical root and its conflict-row manifest are part
  of the future allocation contract, so shard issuance excludes both owned and
  quarantined rows.
- [ ] The planning record captures the real Hemma evidence already established:
  clean idle baseline around `0.06 GB`, real official Waxholm full-finetune
  step around `20.19 GB`, and remaining headroom around `11.87 GB` on the
  `32.06 GB` card.
- [ ] Epic 08 now includes one explicit follow-on story that treats truthful
  monitoring and `>= 90%` steady-state GPU-busy saturation evidence as a
  first-class acceptance target for the Hemma training lane.
- [ ] The epic defines general Swedish language support as a multi-speaker
  outcome rather than a single-voice adaptation shortcut.
- [ ] All future delivery candidates from this epic remain downstream of
  ADR-0006 and ADR-0007 instead of inventing a parallel public contract.

## Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
