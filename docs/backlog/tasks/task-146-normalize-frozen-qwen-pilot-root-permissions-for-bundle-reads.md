---
id: task-146-normalize-frozen-qwen-pilot-root-permissions-for-bundle-reads
title: Normalize frozen qwen pilot root permissions for bundle reads
type: task
status: completed
priority: high
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
  - docs/backlog/tasks/task-144-harden-task-101-bundle-against-unreadable-frozen-freeze-summary.md
  - docs/backlog/tasks/task-145-repair-hemma-kernel-package-drift-and-disable-auto-applied-tailscale-updates.md
  - docs/backlog/tasks/task-147-fail-closed-task101-pilot-bundle-builds-on-insufficient-scratch-capacity.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels: []
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Normalize the current frozen Task 140 pilot root on Hemma so canonical
non-sudo Task 101 bundle builds can read spool rows, audio artifacts, and
reports from the immutable storage-backed source root.

## PR Scope

- Verify the frozen pilot root contains root-only `0600` files that block
  normal Task 101 bundle reads.
- Normalize the existing frozen root to world-readable `a+rX` without making
  it writable.
- Re-run the canonical non-sudo Task 101 pilot-bundle build to confirm the
  permission blocker is removed.
- Record the operational finding that future frozen-root materialization should
  emit read-safe permissions directly instead of depending on post-hoc chmod.

## Deliverables

- [x] Current frozen Task 140 pilot root normalized to read-safe permissions.
- [x] Canonical non-sudo Task 101 bundle build retried after normalization.
- [x] Ops finding documented for future freeze-time permission hardening.

## Acceptance Criteria

- [x] The frozen pilot root no longer contains root-only spool/audio files that
  block normal repo-context Task 101 reads.
- [x] The root remains non-writable to normal users after normalization.
- [x] The next Task 101 bundle retry either succeeds or fails for a reason
  other than frozen-root read permissions.

## Validation

- [x] `pdm run run-hemma -- find /srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a -type f -perm 600 | head`
- [x] `pdm run run-hemma -- sudo -n find /srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a -type f -exec chmod 644 '{}' +`
- [x] `pdm run run-hemma -- sudo -n find /srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a -type d -exec chmod 755 '{}' +`
- [x] `pdm run run-hemma -- pdm run task-101-pilot-bundle build --output-root /srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312d`

## Outcome

`T146` normalizes the current frozen pilot root so it can actually function as
the immutable read-only Task 101 source it was meant to be. The underlying
long-term hardening still belongs in the freeze/materialization path, but the
current root no longer depends on sudo just to be consumed by the canonical
bundle builder.

The live rerun confirms the original permission blocker is gone:

- the retried canonical Task 101 bundle build progressed well past the previous
  unreadable-root failure and began materializing spool/audio/manifests under a
  normal repo-context user
- the next blocker is now separate and storage-related:
  `/srv/scratch` ran out of free space during bundle materialization
- that follow-on failure is tracked in `T147`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
