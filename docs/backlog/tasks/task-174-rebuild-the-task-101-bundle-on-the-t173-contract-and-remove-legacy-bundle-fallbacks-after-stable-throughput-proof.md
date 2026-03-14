---
id: task-174-rebuild-the-task-101-bundle-on-the-t173-contract-and-remove-legacy-bundle-fallbacks-after-stable-throughput-proof
title: Rebuild the Task 101 bundle on the T173 contract and remove legacy-bundle fallbacks after stable throughput proof
type: task
status: in_progress
priority: high
created: '2026-03-14'
last_updated: '2026-03-14'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md
  - docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - training
  - throughput
  - bundle
  - cleanup
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Rebuild the canonical Task 101 bundle on the persisted `T173` precomputed-ref
input contract and then remove the temporary legacy-bundle compatibility trees
that were kept only to unblock live `T172` throughput validation.

## Why This Exists

The current training lane contains temporary legacy-bundle fallback logic so we
could validate `T171` and `T172` against the already-materialized Hemma bundle
without paying an immediate training reset cost. That fallback must not become
permanent architecture.

This task has two phases:

1. rebuild the canonical bundle now on the governed `T173` contract
1. remove the temporary legacy fallback trees only after the rebuilt-bundle
   lane has proven stable throughput gain on Hemma

## Current Progress

- The public `task-101-pilot-bundle` surface is being restored to the governed
  service/container runtime so bundle batch finalization no longer executes in
  host Python.
- Hemma scratch-capacity remediation is in progress:
  - failed `2026-03-14` bundle roots were removed from `/srv/scratch`
  - the old canonical `20260312h` bundle root was backed up to
    `/srv/storage/sir-convert-a-lot/backups/reference/`
  - exited containers, stale Qwen image lineage, and unused BuildKit cache
    were pruned to recover rebuild headroom
- The task is intentionally still open because the rebuilt canonical bundle,
  the fallback-removal step, and the one-day rebuilt-bundle throughput proof
  are not complete yet.

## Entry Criteria

- The governed bundle build/runtime surface is restored and launchable on
  Hemma.
- Hemma scratch/storage capacity is sufficient for a fresh canonical rebuild.
- The repo is ready to write the rebuilt bundle under the `T173` contract.

The following do **not** gate task start; they gate fallback removal and task
closeout:

- real Hemma throughput improvement versus the pre-`T172` baseline
- at least `24` hours of stable rebuilt-bundle training evidence
- final selection of the canonical post-`T172` launch profile from evidence

## PR Scope

- Rebuild the canonical Task 101 bundle on Hemma with the `T173` persisted
  precomputed-reference-input contract.
- Verify the rebuilt bundle exposes canonical
  `training_bundle_report.json` metadata and per-row
  `precomputed_ref_input_*` fields.
- Normalize the upstream frozen-row reference contract so bundle-building no
  longer has to repair empty `reference_audio_24k_paths` maps from row
  artifacts; either make row-processing persist deterministic per-family
  reference paths or move that field out of the pre-finalization row contract.
- Remove the temporary legacy-bundle launch and dataset fallback branches that
  allow old bundles without `T173` metadata to launch, but only after the
  rebuilt-bundle lane has demonstrated stable throughput gain.
- Remove any temporary legacy-oriented `if` trees that only exist to bridge the
  old bundle contract.
- Update runbooks and backlog docs so operators rebuild the bundle before new
  long-run training launches.

## Non-Goals

- Do not retune throughput profiles in this task.
- Do not change the chosen post-`T172` default profile unless the rebuild
  itself exposes a regression.
- Do not accept cleanup-only completion without a real rebuilt Hemma bundle.

## Deliverables

- [ ] One rebuilt canonical Task 101 bundle exists on Hemma under the `T173`
  contract.
- [ ] Upstream row artifacts expose one uniform, explicit reference-audio
  contract instead of ambiguous empty `reference_audio_24k_paths` payloads.
- [ ] Legacy-bundle fallback branches are removed from the training launch and
  dataset path after rebuilt-bundle throughput proof.
- [ ] Docs and operator surfaces point to the rebuilt-bundle path only.

## Acceptance Criteria

- [ ] A real Hemma run launched from the rebuilt bundle succeeds without any
  legacy-bundle fallback logic.
- [ ] The rebuilt-bundle run preserves the post-`T172` throughput gain for at
  least `24` hours of observed training.
- [ ] Bundle-building no longer depends on a fallback from empty
  `reference_audio_24k_paths` to row audio because the upstream row contract is
  uniform and explicit.
- [ ] The repo no longer contains temporary legacy-bundle compatibility trees
  introduced only to bridge pre-`T173` bundles.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root <focused-paths>`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Real Hemma rebuilt-bundle evidence is written under `build/verification/`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
