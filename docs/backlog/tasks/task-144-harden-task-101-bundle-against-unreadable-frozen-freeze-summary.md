---
id: task-144-harden-task-101-bundle-against-unreadable-frozen-freeze-summary
title: Harden task 101 bundle against unreadable frozen freeze summary
type: task
status: completed
priority: high
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/tasks/task-143-harden-qwen-pilot-training-eval-and-bundle-preflight-contracts.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels: []
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Keep the deterministic Task 101 pilot-bundle materializer usable from a normal
Hemma repo context when the frozen pilot root is intentionally immutable and
its freeze summary file is unreadable, while preserving the same owned-row and
conflict-exclusion semantics.

## PR Scope

- Harden `task101_qwen_pilot_bundle.py` so it can fall back to the canonical
  readable row-key ledgers when `reports/canonical_processed_root_freeze.json`
  is present but unreadable.
- Preserve the existing freeze-summary path when it is readable so relocated
  frozen roots and conflict counts still behave exactly as before.
- Make the Task 101 operator contract explicit in docs:
  - the frozen `--source-root` is input-only
  - the builder writes only to the new `--output-root`
  - sudo should not be required for a normal bundle build just to read pilot
    ownership metadata

## Why This Exists

The current Hemma frozen pilot root under
`/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`
has readable owned/conflict ledgers but a root-only freeze summary file. The
Task 101 builder currently reads that summary first, so a normal non-sudo
bundle build fails before it can use the readable immutable ledgers that carry
the actual exclusion data.

This is a small operational hardening slice inside the existing Task 101/T143
contract, not a redesign of pilot ownership or bundle semantics.

## Non-Goals

- Do not change which rows belong to the frozen pilot bundle.
- Do not loosen fail-closed behavior for missing freeze artifacts.
- Do not repair the host package-manager incident inside this task.

## Ordered Execution

1. Record the unreadable-freeze-summary failure mode in docs-as-code.
1. Add a bundle-builder fallback that uses canonical readable ledgers when the
   freeze summary cannot be read.
1. Add a focused regression test for the permission-denied path.
1. Update operator-facing Task 101/runbook text to clarify the immutable
   source-root contract.

## Deliverables

- [x] Task 101 bundle-builder fallback for unreadable freeze-summary files.
- [x] Regression test for the permission-denied frozen-root path.
- [x] Task/runbook wording that states the frozen source root is input-only.

## Acceptance Criteria

- [x] `pdm run task-101-pilot-bundle build` no longer requires read access to
  `canonical_processed_root_freeze.json` when the canonical owned/conflict
  ledgers are readable.
- [x] The builder still fails closed if the canonical row-key ledgers are
  missing.
- [x] Existing readable-summary and relocated-root behavior remains intact.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`

## Outcome

`T144` hardens the deterministic Task 101 pilot bundle against one real Hemma
immutability edge case: unreadable freeze summaries with still-readable row-key
ledgers. The frozen pilot root remains input-only, the bundle still writes only
to a new output root, and normal repo-context builds no longer need sudo just
to consume immutable pilot ownership metadata.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
