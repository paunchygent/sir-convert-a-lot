---
id: task-112-move-qwen-hemma-generated-output-to-data-and-clean-root-disk
title: Move Qwen Hemma hot output to SSD scratch, move raw corpus to HDD storage, and clean root disk
type: task
status: active
priority: high
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma.md
  - docs/backlog/tasks/task-110-split-qwen-preprocessing-into-disk-backed-row-processing-and-finalization.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - hemma
  - storage
  - docker
  - remediation
  - scratch
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Correct the Hemma storage contract for the Qwen preprocessing lane so:

- hot generated preprocessing artifacts and detached-proof evidence persist on
  the SSD scratch tier
- raw Swedish corpus assets persist on the HDD storage tier
- root-disk pressure is reduced by moving repo output and reclaiming non-active
  Docker leftovers

## Why This Exists

The earlier repo contract blurred Hemma's storage tiers and left generated
output under the root-backed repo `build/` tree.

Confirmed `2026-03-09` evidence:

- Hemma root (`/`) has about `1.3 GB` free
- SSD scratch (`/srv/scratch`) has about `398 GB` free
- HDD storage (`/srv/storage`) has about `3.6 TB` available
- repo-root Qwen `build/` output is only about `438 MB`
- the dominant OS-disk bloat is Docker state:
  - dangling Qwen images around `15 GB` each
  - BuildKit cache around `43.78 GB`

So three remediations are required:

1. future hot/generated Qwen output must persist on SSD scratch
2. raw Swedish corpus assets must persist on HDD storage
3. root-disk Docker bloat must be cleaned intentionally

## PR Scope

- Move the existing Hemma Qwen preprocessing/generated output from repo-root
  `build/` into an SSD-scratch-backed `build/` root while preserving the documented
  subtree structure.
- Move the existing Hemma raw Swedish corpus root from SSD scratch onto the HDD
  storage tier and preserve a compatibility path for existing adapters/runners.
- Update the canonical Hemma Qwen preprocessing and detached-proof runners so
  hot output uses SSD scratch and raw corpus storage uses HDD storage.
- Preserve the logical artifact structure:
  - `build/reference/qwen3-tts-swedish-corpus/`
  - `build/verification/task-108-qwen-detached-proof/`
  - `build/verification/task-109-qwen-containerized-preprocessing/`
- Keep local-workstation behavior reasonable, but treat Hemma as
  SSD-scratch-first for generated artifacts and HDD-storage-first for raw
  corpus data.
- After migration, reclaim root-disk space from:
  - dangling Docker images
  - stale BuildKit cache
  - old stopped detached Qwen proof/debug containers when safe

## Non-Goals

- Do not move the whole repo onto SSD scratch or HDD storage.
- Do not prune active images or containers needed by running services.
- Do not treat preprocessing output as the main source of root-disk bloat when
  the measured culprit is Docker state.

## Deliverables

- [ ] One committed SSD-scratch output-root contract for Hemma Qwen
  preprocessing/proof runs.
- [ ] One committed Hemma migration surface that moves existing Qwen `build/`
  outputs from repo-root storage onto SSD scratch.
- [ ] One committed Hemma migration surface that moves existing raw Swedish
  corpus data from SSD scratch onto HDD storage.
- [ ] One committed cleanup surface that removes dangling Docker bloat after
  migration.
- [ ] One updated runbook/reference contract documenting the new storage rule.

## Acceptance Criteria

- [ ] Future Hemma Qwen preprocessing output defaults to SSD scratch.
- [ ] Existing Qwen preprocessing/proof artifacts are moved off the Hemma root
  disk without changing their logical subtree structure.
- [ ] Existing raw Swedish corpus assets are moved onto the HDD storage tier
  and the canonical raw-corpus root is updated accordingly.
- [ ] The docs clearly state that large generated Qwen preprocessing artifacts
  on Hemma belong on SSD scratch, while raw corpus assets belong on HDD
  storage.
- [ ] Root-disk cleanup removes dangling Docker leftovers and build cache based
  on measured evidence, not guesswork.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
