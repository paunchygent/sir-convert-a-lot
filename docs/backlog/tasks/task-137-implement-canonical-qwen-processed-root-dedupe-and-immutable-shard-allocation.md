---
id: task-137-implement-canonical-qwen-processed-root-dedupe-and-immutable-shard-allocation
title: Implement canonical qwen processed-root dedupe and immutable shard allocation
type: task
status: completed
priority: high
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-135-plan-canonical-dedupe-of-qwen-preprocessing-storage-backups.md
  - docs/backlog/tasks/task-136-define-immutable-qwen-shard-registry-and-enforced-unique-work-allocation.md
  - docs/backlog/tasks/task-134-deduplicate-live-colab-remainder-and-enforce-unique-slice-allocation-for-qwen-preprocessing.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - shard
  - dedupe
  - allocation
  - governance
---

## Objective

Implement the first committed shard-governed allocation system for Qwen
preprocessing so the repo can:

1. materialize one canonical deduplicated processed root from multiple run
   roots,
1. cut the remaining source-selection universe into immutable `~5000`-row
   shards,
1. reserve shards through one assignment ledger, and
1. issue future processing units only from shard ids, not freeform overlap-prone
   slice math.

## PR Scope

- Add one committed backup-dedupe CLI for Task 103 run roots that emits:
  - a deduplicated processed root
  - a dedupe report
  - a conflict report
- Add one immutable shard-registry artifact family for a completed
  source-selection universe.
- Add one shard-assignment ledger that reserves shard ids for processing units.
- Add one Task 121 command that issues a processing unit from shard ids and
  rejects unavailable or already-owned shards.
- Keep the notebook thin: all dedupe, shard, and allocation logic must stay in
  repo-owned CLI surfaces.

## Deliverables

- [x] Backup-dedupe CLI surface implemented and tested.
- [x] Immutable shard-registry artifact family implemented and tested.
- [x] Shard-assignment ledger implemented and tested.
- [x] Task 121 shard-based processing-unit issuance implemented and tested.
- [x] Canonical docs updated so shard-based issuance becomes the required
  future path.

## Acceptance Criteria

- [x] The dedupe CLI can build one canonical processed root from multiple run
  roots without mutating the originals.
- [x] The dedupe CLI quarantines same-row conflicts instead of silently merging
  them.
- [x] The shard registry emits immutable shard manifests for a completed
  source-selection universe with a default target around `5000` rows.
- [x] The assignment ledger rejects overlapping shard reservations.
- [x] Task 121 can issue one processing unit from shard ids only.
- [x] Focused tests cover dedupe ownership, conflict quarantine, shard
  immutability, and assignment rejection.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Outcome

`T137` establishes the first durable shard-governed allocation model for Qwen
preprocessing.

Implemented surfaces:

- `task103_qwen_canonical_processed_root.py`
  - builds one immutable canonical processed root from ordered Task 103 run
    roots
  - emits summary, duplicate, and conflict reports
- `task121_qwen_shard_registry.py`
  - cuts the remaining universe into immutable shard manifests
- `task121_qwen_assignment_ledger.py`
  - owns shard reservation, release, completion, and replay
- `task121_qwen_colab_slice_bundle.py`
  - is now a thin canonical CLI over planning, localization, shard registry,
    and shard assignment modules

Allocation rule after `T137`:

- future work issuance must go through shard ids
- `plan-remaining-unique` remains available only for in-flight recovery and
  incident salvage of already-issued manifests, not as a normal allocation
  path
