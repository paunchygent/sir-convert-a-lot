---
id: task-204-restore-story-29-scratch-headroom-and-establish-cold-artifact-demotion-policy-on-hemma
title: Restore Story 29 scratch headroom and establish cold-artifact demotion policy on Hemma
type: task
status: in_progress
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/backlog/tasks/task-112-move-qwen-hemma-generated-output-to-data-and-clean-root-disk.md
  - docs/backlog/tasks/task-113-migrate-hemma-docker-storage-root-to-data-backed-disk.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - hemma
  - qwen
  - storage
  - scratch
  - story-29
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Recover enough `/srv/scratch` headroom for the blocked Story 29 accumulation-`2`
rerun, and replace the current ad hoc cleanup habit with one committed
hot-versus-cold artifact policy for recurring high-churn Qwen proof lanes on
Hemma.

## Why This Exists

The first `T198` accumulation-`2` replay proved something useful and something
operationally broken:

- it cleared the old optimizer-step `1417` non-finite failure window and
  reached `1418`
- it then failed during durable checkpoint save because `/srv/scratch` had only
  about `9 GB` free while the save guard required about `30 GB`

Measured `2026-03-16` scratch consumers show the problem is no longer placement
of Docker or repo roots. Those contracts were already fixed by `T112/T113`.
The recurring issue is ongoing churn inside the scratch tier itself:

- repo `build/runs`: about `217 GB`
- repo `build/verification`: about `97 GB`
- Docker on scratch: about `71 GB`, with about `45 GB` reclaimable
- repo caches: about `26 GB`

So the missing contract is not another one-shot migration. It is recurring
scratch governance:

1. fail early when proof lanes do not have enough headroom
1. keep only hot/active proof artifacts on scratch
1. demote cold completed artifact trees onto `/srv/storage` while preserving
   stable path references

## PR Scope

- Add one committed Hemma scratch audit/remediation command surface for Qwen
  lanes.
- Make that surface capable of:
  - auditing top scratch consumers
  - archiving explicit cold artifact trees from scratch onto storage while
    leaving symlink-backed path stability behind
  - optionally pruning non-active Docker state
- Add one Story 29 proof preflight that refuses detached proof launches when
  Hemma scratch headroom is below the documented threshold.
- Use the committed surface to recover enough headroom for a clean rerun of the
  blocked `T198` accumulation-`2` lane.
- Update the Hemma/Qwen runbooks and current story log so the recurring policy
  is explicit.

## Non-Goals

- Do not remigrate Docker root or repo build root; `T112/T113` already fixed
  those contracts.
- Do not silently delete active Task 101 / Story 29 source checkpoints.
- Do not treat storage cleanup as proof completion; `T198` still needs a clean
  rerun after headroom is restored.

## Deliverables

- [ ] One committed `qwen-scratch-policy` command surface exists for audit and
  explicit cold-artifact demotion.
- [ ] Story 29 proof wrappers fail early on insufficient Hemma scratch
  headroom.
- [ ] One documented Hemma storage policy distinguishes:
  - hot active proof/run roots on `/srv/scratch`
  - cold retained evidence demoted onto `/srv/storage`
  - reclaimable non-active Docker state
- [ ] Enough scratch headroom is restored for a clean `T198` rerun.

## Acceptance Criteria

- [ ] `pdm run run-hemma -- pdm run qwen-scratch-policy audit` writes one
  deterministic audit artifact and reports the current headroom truth.
- [ ] `pdm run run-hemma -- pdm run qwen-scratch-policy remediate ...` can
  archive explicit scratch roots onto `/srv/storage` while preserving symlink
  stability at the original path.
- [ ] `qwen-t197-proof` and `qwen-t198-proof` refuse launch when Hemma scratch
  free bytes are below the required threshold.
- [ ] The selected remediation frees enough space that the next accumulation-`2`
  replay is not blocked by the same checkpoint-save headroom failure.
- [ ] Runbook/current-story/reference docs record the recurring policy and the
  specific `T198` storage-blocker outcome.

## Exact Commands

1. Audit current scratch pressure:
   `pdm run run-hemma -- pdm run qwen-scratch-policy audit`
1. Archive explicit cold artifact roots:
   `pdm run run-hemma -- pdm run qwen-scratch-policy remediate --source-path <scratch-path> ...`
1. Add Docker cleanup if needed:
   `pdm run run-hemma -- pdm run qwen-scratch-policy remediate --prune-docker-state ...`
1. Rerun the accumulation-`2` proof only after headroom is restored:
   `pdm run qwen-t198-proof prepare --proof-id <proof-id> --skip-build`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Hemma remediation executed
- [ ] Docs updated
