---
id: task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion
title: Run the Hemma pilot full-finetune for Swedish Qwen3-TTS language expansion
type: task
status: active
priority: high
created: '2026-03-08'
last_updated: '2026-03-12'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
  - docs/backlog/tasks/task-141-define-frozen-qwen-pilot-dataset-use-for-finetuning.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/tasks/task-143-harden-qwen-pilot-training-eval-and-bundle-preflight-contracts.md
  - docs/backlog/tasks/task-144-harden-task-101-bundle-against-unreadable-frozen-freeze-summary.md
  - docs/backlog/tasks/task-145-repair-hemma-kernel-package-drift-and-disable-auto-applied-tailscale-updates.md
  - docs/backlog/tasks/task-146-normalize-frozen-qwen-pilot-root-permissions-for-bundle-reads.md
  - docs/backlog/tasks/task-147-fail-closed-task101-pilot-bundle-builds-on-insufficient-scratch-capacity.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - hemma
  - pilot
  - swedish
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the first bounded Hemma pilot full-finetune for Swedish language expansion
on `Qwen/Qwen3-TTS-12Hz-1.7B-Base` from the frozen pilot-owned dataset bundle
and capture deterministic runtime and memory evidence.

## PR Scope

- Use the committed Hemma runtime from Task 100 plus the deterministic pilot
  training bundle materialized from the frozen pilot root owned by `T140`.
- Materialize that deterministic bundle with:
  - `pdm run run-hemma -- pdm run task-101-pilot-bundle build`
  - treat the frozen `--source-root` as immutable input; the builder writes
    only to the new output root and can fall back to the canonical readable
    ownership ledgers when the freeze summary file itself is unreadable
  - the builder now fails closed before writing any partial output when the
    target filesystem does not have enough free space for the retained bundle
    payload plus safety headroom
  - the canonical `build` surface is now internally staged:
    - `copy` retained spool/audio
    - `finalize-batch` in bounded family batches
    - `assemble` final manifests/report only after validated batch shards exist
  - bounded `finalize-batch` execution now runs inside the governed Qwen
    Task 100/101 image rather than the host PDM environment
  - the canonical governed batch-finalization runtime is now also explicitly
    GPU-backed for `audio_codes` generation
    - `Qwen3TTSTokenizer` is initialized on `cuda:0`
    - governed dtype is `bfloat16`
    - governed attention posture is `flash_attention_2`
    - the canonical Task 101 batch runtime now fails closed instead of
      silently continuing on CPU when that tokenizer posture cannot be
      established
  - that batch runtime reuses the canonical fixed in-container HF cache
    contract:
    - `HF_HOME=/cache/huggingface`
    - `HUGGINGFACE_HUB_CACHE=/cache/huggingface/hub`
    - `TORCH_HOME=/cache/huggingface/torch`
  - the selected bundle output root is mounted back into the container at the
    same host-visible path so progress/status/report artifacts remain
    host-rooted
  - operator-visible progress artifacts now live under `reports/`:
    - `task101_pilot_bundle_plan.json`
    - `task101_pilot_bundle_events.jsonl`
    - `task101_pilot_bundle_status.json`
    - `task101_pilot_bundle_runtime.json`
    - `task101_pilot_bundle_audio_codes_runtime.json`
    - `reports/batches/<family>/batch-xxxxx.runtime.json`
  - validated batch reuse now fails closed on legacy host-generated shards
    that do not carry the governed runtime fingerprint
- Use the detached committed Task 101 runner surface:
  - `pdm run run-hemma -- pdm run task-101-pilot launch`
- Treat the generic promoted Task 103 corpus view as insufficient for this run.
  The pilot must launch only from a deterministic bundle that contains:
  - `swedish_pilot_train.prepared.jsonl`
  - `swedish_checkpoint_dev.prepared.jsonl`
  - stable per-speaker `refs/`
  - machine-readable bundle metadata describing the frozen source root
- Carry the held-out eval family through detached launch, status, and report
  metadata for the pilot contract while being explicit that the current
  upstream Qwen trainer remains train-only and does not perform in-training
  held-out scoring.
- The canonical frozen pilot ownership source is:
  - `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`
- Accepted bounded-pilot input for the next canonical Task 101 launch:
  - current frozen `swedish_pilot_train`
  - `8445` high-trust train rows
  - `29` speakers
  - about `54.996` hours total
  - held-out `swedish_checkpoint_dev=8` rows
  - this is intentionally accepted as the current bounded pilot even though it
    exceeds the original `24` to `36` hour planning target
- Capture:
  - clean idle GPU baseline,
  - startup/runtime metadata,
  - successful optimizer-step evidence,
  - peak VRAM/GPU usage,
  - checkpoint/output locations,
  - failure notes if the run does not complete.
- Keep the lane focused on pilot proof, not maximal dataset hours.
- Do not launch Task 101 against ad hoc row subsets or a manually edited
  manifest. `T142` must materialize the deterministic pilot bundle first.
- Do not claim that Swedish quality is proven from the current held-out split
  alone. The current `8 + 8 + 8` eval/control rows remain enough for smoke and
  contract checks, not for a confident “Swedish works” conclusion.

## Deliverables

- [ ] Hemma pilot evidence under `build/verification/`.
- [ ] Detached launch and status metadata for the pilot lane.
- [ ] Machine-readable report for memory/runtime truth.
- [ ] Linked task/runbook updates with the exact command used.

## Acceptance Criteria

- [ ] The pilot uses the `1.7B` base model, not the `0.6B` lane.
- [ ] The run reaches a real Swedish full-finetune optimizer step with `AdamW`.
- [ ] The run consumes the deterministic pilot bundle projected from the frozen
  pilot root rather than the generic promoted preprocessing root.
- [ ] The evidence records actual VRAM usage and headroom on the R9700.
- [ ] The task explicitly states whether Hemma is good enough for the bounded
  pilot and what should move to Colab H100 for scale.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
