---
id: 'task-138-canonicalize-qwen-pilot-ownership-and-salvage-the-remaining-colab-slice'
title: 'Canonicalize qwen pilot ownership and salvage the remaining colab slice'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-134-deduplicate-live-colab-remainder-and-enforce-unique-slice-allocation-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-137-implement-canonical-qwen-processed-root-dedupe-and-immutable-shard-allocation.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - canonical-root
  - colab
  - hemma
  - pilot
  - recovery
---

## Objective

Restore one orderly pilot ownership model after the `task116`/`task129`
overlap incident by:

1. materializing one canonical processed root for the current pilot-owned work,
2. measuring the exact unique pilot set from that canonical root, and
3. replacing the live Colab input manifest with a remaining-unique slice so it
   only processes rows not already owned by the canonical pilot root.

## PR Scope

- Use the committed canonical processed-root builder to combine:
  - Hemma `task116-rowproc-5x2-20260309c`
  - the synced Colab backup snapshot for
    `task129-colab-scale-rowproc-1-of-2-20260311a`
- Emit one pilot ownership report from the resulting canonical root.
- Use the original Hemma `task129` slice root as the source manifest for one
  remaining-unique recovery slice.
- Produce one repo-owned Colab recovery bundle for the unique remainder.
- Update the active docs/session surfaces with the exact canonical and
  remaining counts plus the new recovery instructions.

## Deliverables

- [x] One canonical pilot processed root exists on Hemma and is recorded in the
      task/docs state.
- [x] One exact ownership summary exists for:
      - Hemma-completed rows
      - Colab-completed rows
      - unique pilot rows
      - remaining rows in the original `task129` slice
- [x] One deduplicated remaining Colab bundle exists for the current
      `task129` recovery path.
- [x] Canonical docs and session state reflect the new owned root and recovery
      bundle.

## Acceptance Criteria

- [x] The canonical pilot root is materialized on Hemma and its retained rows
      are measured exactly.
- [x] The Colab recovery bundle contains only rows not already owned by the
      canonical pilot root.
- [x] The live Colab lane can resume from the same run root against the
      recovery bundle instead of the original overlapping `18000`-row slice.
- [x] Docs clearly state the canonical owned root and the remaining recovery
      bundle for the current campaign.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Outcome

Materialized canonical pilot root:

- `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task138-qwen-pilot-owned-20260311b`

Exact current ownership result:

- Hemma completed rows: `10024`
- Colab completed rows: `7970`
- current Colab duplicate rows against Hemma: `2158`
- current Colab novel rows: `5812`
- canonical retained unique pilot rows: `15748`
- quarantined same-row conflicts: `88`
- dropped identical duplicates: `2070`

Current Colab salvage result:

- original `task129` slice rows: `18000`
- rows already owned by completed Hemma or completed Colab work: `10813`
- remaining unique recovery rows: `7187`
- recovery bundle:
  - `colab_ml_training/proof_inputs/task138-task129-remaining-unique-20260311a-bundle.tar.gz`
  - `sha256=6b260245a5daf208310489c4b4ba59eab4284c45ef4e4fb401519948a1e70d6b`

Important nuance:

- the retained canonical root is the safe unique pilot set
- the `88` conflicts remain quarantined and must not be silently reissued
- for this incident, the shipped Colab recovery bundle is the correct
  remaining-work artifact
