---
id: 'task-134-deduplicate-live-colab-remainder-and-enforce-unique-slice-allocation-for-qwen-preprocessing'
title: 'Deduplicate live colab remainder and enforce unique slice allocation for qwen preprocessing'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-129-prepare-large-portable-colab-slice-for-multi-session-qwen-row-processing.md
  - docs/backlog/tasks/task-131-add-backward-compatible-resume-index-for-drive-backed-qwen-row-processing.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - hemma
  - dedupe
  - recovery
---

## Objective

Contain the live `task116`/`task129` overlap incident by:

1. creating one committed dedupe path for the remaining Colab-selected rows,
1. enforcing one harder unique-allocation rule for future portable slices, and
1. keeping the notebook thin by pushing all overlap logic into repo-owned CLI
   surfaces.

## PR Scope

- Add one committed Task 121 helper surface that can load row keys from:
  - completed Task 103 run roots, and
  - selected-source-record JSONL artifacts.
- Add one committed Task 121 command that emits a deduplicated selected-source
  JSONL for an in-flight portable slice by subtracting already completed rows
  from one or more run roots.
- Add one committed Task 121 command for future slice issuance that filters the
  remaining source-selection universe against already processed or already
  reserved rows before deterministic modulo partitioning.
- Update the portable-slice reference and Hemma/Colab runbook so the new
  guarded allocation command becomes the canonical path after any prior run root
  or issued slice exists.

## Deliverables

- [x] Task 121 exposes a repo-owned `dedupe-selected-source-records` command.
- [x] Task 121 exposes a repo-owned guarded allocation command for future
      unique-slice issuance.
- [x] The guarded allocation path accepts already completed run roots and
      already issued selected-source manifests as exclusion sources.
- [x] The live Colab recovery path and the new hard allocation rule are
      documented in the canonical reference/runbook surfaces.
- [x] Focused regression tests cover both the live dedupe path and the future
      guarded-allocation rule.

## Acceptance Criteria

- [x] Operators can produce one deduplicated remaining selected-source manifest
      for the in-flight `task129` Colab lane without notebook-only logic.
- [x] The future guarded allocation path can carve one new slice from the
      remaining source-selection universe after excluding already processed and
      already reserved rows.
- [x] Future incremental slice issuance has one documented canonical command
      that is stricter than the original proof-only `plan` flow.
- [x] Focused Task 121 tests pass for the new overlap and dedupe semantics.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
