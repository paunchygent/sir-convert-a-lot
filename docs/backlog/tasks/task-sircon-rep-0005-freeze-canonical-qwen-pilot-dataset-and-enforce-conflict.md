---
type: task
id: TASK-SIRCON-REP-0005
title: Freeze canonical qwen pilot dataset and enforce conflict exclusions in shard
  allocation
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- "[x] One immutable canonical processed root can be treated as the frozen pilot\n\
  \  dataset without additional operator bookkeeping."
- "[x] Quarantined conflicts are serialized into one machine-readable row-key\n  manifest."
- "[x] `build-shard-registry` can exclude row keys from explicit manifests in\n  addition\
  \ to completed run roots and already-issued manifests."
- '[x] The conflict-exclusion path is visible from the canonical docs/runbook.'
retired_ids:
- task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation
---
## Context

Source record: docs/backlog/tasks/task-140-freeze-canonical-qwen-pilot-dataset-and-enforce-conflict-exclusions-in-shard-allocation.md

### Objective

> Freeze the current canonical Qwen pilot dataset into one explicit row-ownership
> surface and make future shard issuance reject quarantined conflict rows by
> contract instead of relying on operator memory.

## Impact And Escalation

## Decision And Assumption Ledger

## Plan

## Implementation Steps

## Proof

### Deliverables

> - [x] Canonical processed-root build emits explicit owned-row and
>   conflict-row-key artifacts.
> - [x] Canonical processed-root build emits one freeze summary that names the
>   exclusion artifacts.
> - [x] Task 121 exclusion helpers and CLI accept explicit row-key exclusion
>   manifests.
> - [x] Canonical docs explain that future shard issuance must exclude the
>   frozen pilot conflicts explicitly.

### Outcome

> The canonical processed root is now the frozen pilot truth surface through one
> repo-owned artifact family:
>
> - `completed_row_keys.jsonl` for owned pilot rows
> - `reports/canonical_processed_root_conflict_row_keys.jsonl` for unavailable
>   conflict rows
> - `reports/canonical_processed_root_freeze.json` for the immutable freeze
>   summary
>
> Materialized Hemma artifacts:
>
> - frozen pilot canonical root:
>   - `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`
>   - `retained_row_count=15748`
>   - `conflict_row_count=88`
> - post-pilot shard registry:
>   - `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-shards/task140-task129-post-pilot-remaining-20260311a`
>   - `remaining_row_count=13001`
>   - `shard_count=3`
>   - `target_rows_per_shard=5000`
>
> Future shard allocation can now exclude both:
>
> - completed/owned rows from the frozen canonical pilot root
> - quarantined conflict rows through `--exclude-row-keys-path`
>
> That makes the conflict exclusions part of the enforced allocation contract
> instead of a remembered cleanup step.

## Validation

## Stop Conditions

## Lessons Learned

## Notes

### PR Scope

> - Extend the canonical processed-root build outputs with explicit owned-row and
>   conflict-row-key artifacts plus one freeze summary.
> - Extend Task 121 exclusion loading so shard-registry and unique-allocation
>   flows can consume explicit row-key exclusion manifests.
> - Wire the canonical Task 121 CLI to accept the new explicit exclusion surface.
> - Update the canonical preprocessing/runbook docs so future shard issuance is
>   documented against the frozen pilot root and its conflict exclusions.

## Readiness

## Closeout
