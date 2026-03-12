---
id: task-135-plan-canonical-dedupe-of-qwen-preprocessing-storage-backups
title: Plan canonical dedupe of qwen preprocessing storage backups
type: task
status: completed
priority: high
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-134-deduplicate-live-colab-remainder-and-enforce-unique-slice-allocation-for-qwen-preprocessing.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - backup
  - dedupe
  - recovery
---

## Objective

Define the canonical plan for deduplicating a storage backup that contains
multiple Task 103 preprocessing roots so the retained backup keeps only unique
row records and one canonical owner for each associated audio and metadata
artifact.

## Planning Decision

The backup dedupe must be row-key driven, not file-name driven.

Canonical row identity:

- `(dataset, source_split, dataset_row_id)`

Canonical ownership rule for the current incident:

- prefer the Hemma `task116` root for any overlapping row key
- keep Colab `task129` rows only when that row key is absent from the canonical
  Hemma-owned set

Never mutate the original run roots or the raw backup in place.

The dedupe output must be one new immutable backup root plus a machine-readable
report describing:

- which source root won each overlapping row
- which rows were dropped as duplicates
- which rows were retained as novel
- whether any conflicting same-row payloads or audio hashes were detected

## Planned Phases

1. Inventory the candidate roots.
   - Enumerate every run root that will participate in the backup dedupe.
   - Require explicit inputs; do not infer roots from ambient directories.
1. Build a canonical row-ownership ledger.
   - Load completed rows from each run root through the existing Task 103
     resume-index/spool surfaces.
   - For each row key, record:
     - source run root
     - spool row path
     - audio path
     - audio hash when practical
1. Resolve ownership deterministically.
   - If one row key exists only once, retain it.
   - If one row key exists multiple times, apply the declared precedence rule.
   - If one row key exists multiple times but critical payload fields disagree,
     quarantine it into a conflict report instead of silently choosing.
1. Materialize one deduplicated backup root.
   - Copy or hardlink only the winning spool rows.
   - Copy or hardlink only the winning `audio_24k` artifacts referenced by
     those spool rows.
   - Carry forward only metadata that is still reachable from the winning row
     set.
   - Do not synthesize promoted manifests in this step.
1. Validate the deduplicated backup.
   - No duplicate row keys remain.
   - Every retained spool row points to an existing retained audio artifact.
   - The dedupe report counts match the materialized artifact counts.

## PR Scope For The Future Implementation Slice

- Add one committed backup-dedupe CLI surface for Task 103 run roots.
- Emit one machine-readable dedupe report plus a quarantined-conflicts report.
- Keep the implementation backup-oriented only:
  - no manifest finalization
  - no promotion
  - no notebook-only logic

## Deliverables

- [x] One canonical row-identity rule for backup dedupe.
- [x] One deterministic ownership rule for the current Hemma/Colab overlap
  incident.
- [x] One phased plan for inventory, ownership resolution, materialization, and
  validation of a deduplicated backup root.
- [x] One explicit non-goal statement that original run roots must remain
  immutable.

## Acceptance Criteria

- [x] The plan explains how duplicate spool rows will be detected.
- [x] The plan explains how duplicate audio artifacts will be retained only for
  the canonical winning rows.
- [x] The plan explains how conflicting same-row payloads will be quarantined
  instead of silently merged.
- [x] The plan is specific enough to implement as one follow-on task without
  reopening the ownership model.

## Checklist

- [x] Planning complete
- [x] Docs updated

## Objective

TBD.

## PR Scope

TBD.

## Deliverables

- [ ] TBD

## Acceptance Criteria

- [ ] TBD

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
