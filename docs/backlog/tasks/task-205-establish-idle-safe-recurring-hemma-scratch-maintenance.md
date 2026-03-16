---
id: task-205-establish-idle-safe-recurring-hemma-scratch-maintenance
title: Establish idle-safe recurring Hemma scratch maintenance
type: task
status: in_progress
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/backlog/tasks/task-204-restore-story-29-scratch-headroom-and-establish-cold-artifact-demotion-policy-on-hemma.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - hemma
  - qwen
  - storage
  - scratch
  - scheduler
  - story-29
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Turn the new scratch-governance surface into one recurring, idle-safe Hemma
maintenance contract so cold artifact trees are archived automatically when the
host is quiet, active Story 29 work is protected, and scratch-space collapse no
longer surprises the next bounded proof lane.

## Why This Exists

`T204` added manual audit/remediation and proof-launch headroom checks, which
closed the first operational gap. The next gap is recurrence: completed proof
roots, export checkpoints, and Docker churn accumulate again unless the host has
one lightweight maintenance loop that runs only when it is safe.

The scheduler must therefore be conservative rather than merely aggressive:

- keep active training, proof, and evaluation roots on `/srv/scratch`
- archive only cold completed artifact roots onto `/srv/storage`
- leave canonical symlink-backed paths behind for stable references
- block itself while active Qwen containers or an explicit maintenance block
  file are present

## PR Scope

- Add `pdm run qwen-scratch-policy maintain` as the committed recurring
  maintenance surface.
- Add one lightweight user-level systemd timer/service install surface for that
  command.
- Encode archive policy directly in committed code:
  - age gate for cold candidates
  - keep-most-recent retention per governed parent root
  - protected active RCA/resume roots
  - optional Docker prune only when still below target headroom
- Use the same committed maintenance surface to reclaim headroom before the
  clean rerun of `task198-20260316t185616z-accum2-a1`.
- Update Story 29 operator docs so the scheduler becomes part of the storage
  contract, not an ad hoc shell habit.

## Non-Goals

- Do not move active training/proof artifacts directly onto `/srv/storage`.
- Do not auto-archive the current canonical `1406` RCA source or the most
  recent restart-critical checkpoints.
- Do not treat timer installation alone as sufficient; one successful manual
  maintenance pass and clean `T198` rerun still matter.

## Deliverables

- [ ] `qwen-scratch-policy maintain` exists and enforces idle-safe archive
  policy.
- [ ] `qwen-scratch-policy install-timer` installs a lightweight user-level
  systemd timer/service pair.
- [ ] `qwen-scratch-policy status-timer` reports timer health deterministically.
- [ ] Story 29 storage docs record the new recurring policy.
- [ ] Hemma scratch headroom is reclaimed with the committed maintenance
  surface before the next `T198` rerun.

## Acceptance Criteria

- [ ] `pdm run run-hemma -- pdm run qwen-scratch-policy maintain` writes one
  deterministic maintenance artifact and archives only cold eligible roots.
- [ ] The maintenance pass refuses to archive while active Qwen containers or
  the explicit maintenance block file are present.
- [ ] `pdm run run-hemma -- pdm run qwen-scratch-policy install-timer ...`
  writes deterministic install artifacts and enables the user-level timer.
- [ ] The timer reuses the committed `maintain` surface instead of embedding ad
  hoc shell logic.
- [ ] The restored headroom is sufficient for a clean rerun of
  `task198-20260316t185616z-accum2-a1` without repeating the earlier
  checkpoint-save disk failure.

## Exact Commands

1. Run one idle-safe maintenance pass now:
   `pdm run run-hemma -- pdm run qwen-scratch-policy maintain --prune-docker-state`
1. Install the recurring timer:
   `pdm run run-hemma -- pdm run qwen-scratch-policy install-timer --enable-linger --prune-docker-state`
1. Inspect timer state:
   `pdm run run-hemma -- pdm run qwen-scratch-policy status-timer`
1. After scratch headroom is healthy again, rerun the accumulation-`2` lane:
   `pdm run qwen-t198-proof launch-window --proof-id task198-20260316t185616z-accum2-a1`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Hemma maintenance executed
- [ ] Docs updated
