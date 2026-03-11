---
id: 'task-136-define-immutable-qwen-shard-registry-and-enforced-unique-work-allocation'
title: 'Define immutable qwen shard registry and enforced unique work allocation'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-134-deduplicate-live-colab-remainder-and-enforce-unique-slice-allocation-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-135-plan-canonical-dedupe-of-qwen-preprocessing-storage-backups.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - shard
  - allocation
  - governance
  - recovery
---

## Objective

Define one foolproof, maintainable operating model for future Qwen preprocessing
allocation so the repo has:

- one canonical deduplicated processed corpus root,
- one immutable shard registry for the remaining source-selection universe,
- one inescapable allocation gate that refuses overlapping work, and
- one lineage trail from every processing unit back to the original shard set.

## Core Decision

Future work must be allocated from immutable dataset shards, not from ad hoc
fresh slice math.

### Canonical Concepts

- `canonical processed root`
  - the deduplicated row-processing truth built from completed run roots
  - used only as exclusion truth and future finalization input
- `shard`
  - one immutable row-key set cut from a completed source-selection universe
  - never regenerated after issuance
  - never partially redefined
- `processing unit`
  - one assignment built from one or more existing shard ids
  - may be routed to Hemma, Colab, or another worker
  - must record lineage to its source shards

## Shard Rule

Shards are ground truth and must be globally unique.

Required properties:

- every shard has one stable `shard_id`
- every shard records:
  - source-selection run root
  - source-selection summary hash or identifier
  - shard ordinal
  - shard row count
  - ordered row-key manifest
- shards are immutable after creation
- the system must reject any attempt to recreate an already issued shard from
  the same universe under a different id

## Work Allocation Rule

Every future processing unit must be built only from existing shards.

Required properties:

- allocation requires one committed shard registry lookup
- allocation records:
  - `processing_unit_id`
  - source shard ids
  - assigned executor
  - assignment timestamp
  - completion state
- allocation must fail if any requested shard is already:
  - assigned and not released, or
  - completed and already absorbed into the canonical processed root

This gate must become the only allowed path for future portable Colab slices
and future multi-worker Hemma/VM allocation.

## Default Shard Size

Use `~5000` rows as the default shard target.

Rationale:

- manageable Colab wall-clock window
- suitable daily work unit for Hemma or disposable GPU workers
- small enough to localize and resume without the `18000`-row startup tax
- large enough to keep coordination overhead reasonable

This is a target size, not an exact fixed row count. Tail shards may be
smaller.

## Lineage Rule

Lineage must be explicit and durable.

Every processing unit and every deduplicated backup artifact must be traceable
to:

- the source-selection universe id
- the source shard ids
- the completed run roots that consumed those shards

This should behave like an append-only ledger:

- shards are issued once
- assignments reference shards
- completed roots reference assignments
- canonical deduped roots reference the completed roots they absorbed

## Planned Implementation Shape

1. Build the canonical deduped processed root from current Hemma/Colab work.
2. Introduce one shard-registry artifact family, likely under the Qwen build
   reference tree.
3. Cut the remaining unprocessed universe into immutable `~5000`-row shards.
4. Introduce one allocation ledger that can reserve shard ids for workers.
5. Replace freeform Task 121 follow-on slice creation with shard-based
   processing-unit issuance.

## Non-Negotiables

- No future overlapping slices after the shard ledger is active.
- No notebook-owned shard math.
- No mutation of existing shards after issuance.
- No hidden allocator state outside committed repo-owned artifact paths.

## Deliverables

- [x] One canonical vocabulary for processed root, shard, and processing unit.
- [x] One immutable shard rule with explicit uniqueness requirements.
- [x] One enforced allocation rule that blocks overlapping work.
- [x] One default shard-size policy around `5000` rows.
- [x] One lineage model linking source-selection universe, shards, assignments,
      run roots, and deduped processed roots.

## Acceptance Criteria

- [x] The plan makes shard recreation forbidden after issuance.
- [x] The plan makes future allocation shard-based rather than freeform
      slice-based.
- [x] The plan makes overlap rejection an inescapable gate, not operator
      convention.
- [x] The plan is specific enough to implement as follow-on repo tasks without
      reopening the shard semantics.

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
