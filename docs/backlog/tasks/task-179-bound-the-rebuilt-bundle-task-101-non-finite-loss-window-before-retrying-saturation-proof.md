---
id: task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof
title: Bound the rebuilt-bundle Task 101 non-finite loss window before retrying saturation proof
type: task
status: in_progress
priority: high
created: '2026-03-14'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md
  - docs/backlog/tasks/task-174-rebuild-the-task-101-bundle-on-the-t173-contract-and-remove-legacy-bundle-fallbacks-after-stable-throughput-proof.md
  - docs/backlog/tasks/task-175-close-the-remaining-task-101-throughput-truth-gaps-from-the-review-alignment.md
  - docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - training
  - numerical-stability
  - throughput
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Bound the rebuilt-bundle Task 101 non-finite loss window so the next aggressive
throughput proof can produce valid saturation evidence instead of failing
within the first few optimizer steps.

This task exists to turn the current failure from "proof invalid because loss
went `NaN`" into one of two acceptable outcomes:

- the bounded aggressive rebuilt-bundle proof stays numerically finite through
  the first meaningful measurement window, or
- the failure artifact becomes specific enough that the next remediation step
  is data-backed rather than exploratory.

## Why This Exists

The first rebuilt-bundle throughput proof under the `T175` lane failed too
early to support any GPU-saturation claim:

- proof launch: `task175-20260314t-throughput-a2`
- run root:
  `/srv/scratch/sir-convert-a-lot/build/runs/task-175-throughput-proof-20260314a/task175-20260314t-throughput-a2`
- status artifact updated at `2026-03-14T17:34:15Z`
- finite-loss guard triggered after `3` consecutive non-finite optimizer steps
- terminal error:
  `Non-finite loss guard triggered after 3 consecutive optimizer steps (threshold=3, optimizer_step=4, loss=nan).`

The paired single-worker data-path proof completed and proved that persisted
`ref_mel` loading is working and runtime extraction is not the active issue:

- proof launch: `task175-20260314t-datapath-a1`
- persisted `ref_mel` load count: `3`
- runtime `ref_mel` extraction count: `0`
- attribution payload marked `authoritative: true`

That means the next blocker before a fresh saturation retry is not
observability; it is bounding the aggressive rebuilt-bundle lane's numerical
instability.

The code-side remediation tracked by `T180` and `T186` is a prerequisite to
this task's next bounded Hemma repro:

- `T180` fixes accumulation-boundary correctness, failed-run report emission,
  and failed-status counter truth
- `T186` adds deterministic optimizer-boundary replay and the fail-closed guard
  that must prove where corruption starts and stop the lane before weights are
  poisoned
- `T179` then re-runs the bounded rebuilt-bundle proof against those repaired
  surfaces and decides whether the lane is ready for another saturation attempt

## PR Scope

- Add one committed failure-context surface for the rebuilt-bundle aggressive
  proof lane so the first non-finite transition records enough operator truth
  to debug deterministically:
  - optimizer step
  - train iteration
  - phase
  - latest finite loss
  - non-finite loss value
  - active manifest family / launch profile
  - resolved batch occupancy context for the failing window
- Reproduce the current failure on a bounded rebuilt-bundle Hemma proof using
  the same aggressive launch class and canonical detached surface, but only
  after the code-side remediation in `T180` and `T186` lands.
- Land the smallest numerically stabilizing fix needed to keep the rebuilt
  aggressive proof finite through the first acceptance window.
- Preserve the existing `T175` observability and attribution work; do not
  regress occupancy, phase, or worker-truth payloads while fixing the NaN lane.

## Non-Goals

- Do not redesign the Qwen objective or speaker-conditioning architecture.
- Do not broaden this task into a general hyperparameter search.
- Do not retry the long saturation proof until this bounded non-finite-loss
  task has either produced a finite proof window or a deterministic failure
  artifact.

## Deliverables

- [ ] The rebuilt-bundle aggressive proof lane records first-non-finite
  failure context in machine-readable artifacts.
- [ ] One bounded rebuilt-bundle Hemma proof either:
  - remains finite through the first acceptance window, or
  - fails with enough persisted context to attribute the next fix precisely.
- [ ] The chosen stabilizing change is documented and scoped so it can be
  reasoned about independently of broader throughput work.

## Acceptance Criteria

- [ ] A bounded rebuilt-bundle aggressive proof reaches at least the first
  durable checkpoint or `30` optimizer steps without the finite-loss guard
  firing.
- [ ] The proof artifacts preserve truthful occupancy, phase, and data-path
  attribution surfaces while the numerical-stability fix is in place.
- [ ] If a bounded proof still fails, the resulting artifact captures the first
  non-finite window well enough that the next remediation step can be chosen
  from committed evidence instead of live ad hoc probing.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] One bounded rebuilt-bundle Hemma proof under `build/verification/`
  demonstrates a finite early training window or a deterministic non-finite
  failure artifact.

## Current Progress

- The completed `T186` guarded proof isolated the first unsafe optimizer
  boundary at step `1405`, with finite forward losses but non-finite
  `text_embedding.weight.grad` before `optimizer.step()`.
- A runtime-shape audit against the installed upstream Qwen model found that
  the patched trainer, eval, and optimizer-boundary guard were resolving
  `text_projection` from `model.talker.model`, while upstream exposes that
  layer on `model.talker`.
- The text/codec embedding and text-projection access path is now centralized
  under
  `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_runtime.py`, and the
  train, eval, and optimizer-guard surfaces now consume that shared resolver.
- The first projection-enabled replay and the later clean-base restart are now
  recorded as diagnostic experiments, not as the canonical Task 101 training
  graph:
  - the replay `task179-20260315t-textpath-replay-a1` proved the shared talker
    resolver was active and that a projection-enabled resumed lane could fail
    earlier at optimizer step `1239`
  - the later clean-base projection-enabled restart failed immediately at
    optimizer step `1`, which is evidence against projection injection in the
    fine-tuning graph rather than evidence that the preserved no-projection
    lane is worthless
- `state-step-00001238` is therefore back in standing as the canonical
  no-projection RCA checkpoint for the preserved Task 101 lane. It is not
  promoted as "smooth continuation proven," but it is also no longer demoted
  as trash or salvage-only merely because it omitted `text_projection`.
- The runtime contract is now harder to hide:
  - startup/reporting artifacts persist a `talker_runtime` fingerprint that
    records the resolved text embedding, codec embedding, and text projection
    paths plus whether each surface is probeable as an `nn.Module`
  - resolver-matrix tests now cover talker-level projection, nested fallback,
    no-projection, and callable-but-non-module projection cases
- `T193` is now the active follow-on:
  - train and eval were restored to the upstream no-projection fine-tuning
    contract
  - optimizer-boundary probes now split the first bad stage into
    `pre_clip`, `clip_grad_norm`, `post_clip`, and `post_step`
  - the next bounded live proof should mint a fresh diagnostic checkpoint near
    optimizer step `1401` and replay `1401 -> 1406` on the preserved
    no-projection graph

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
