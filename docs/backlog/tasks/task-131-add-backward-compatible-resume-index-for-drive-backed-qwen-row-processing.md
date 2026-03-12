---
id: task-131-add-backward-compatible-resume-index-for-drive-backed-qwen-row-processing
title: Add backward-compatible resume index for Drive-backed Qwen row-processing
type: task
status: completed
priority: high
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-123-add-resumable-row-processing-for-qwen-preprocessing-runs.md
  - docs/backlog/tasks/task-129-prepare-large-portable-colab-slice-for-multi-session-qwen-row-processing.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - preprocessing
  - resume
  - reliability
  - throughput
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Reduce restart latency for persistent Drive-backed Qwen row-processing runs by
adding one backward-compatible repo-owned resume index that can answer
"which rows are already complete?" without reopening and parsing thousands of
spool JSON files on every Colab resume.

## Problem Statement

Task 103 currently rebuilds `completed_row_keys` by scanning the entire spool
tree on resume. On Google Drive-backed Colab run roots this means `rglob` plus
per-file JSON reads across thousands of tiny files before any new row can be
scheduled. The current behavior is correct but produces large resume stalls for
multi-session slices once several thousand rows are already complete.

## PR Scope

- Preserve the existing spool JSON tree as the canonical row-processing truth.
- Add one repo-owned sequential resume index under the Task 103 run root that
  records completed row keys as rows finish.
- Teach row-processing resume to prefer the sequential index when present.
- Keep backward compatibility by rebuilding the index from canonical spool JSON
  when resuming an older run root that predates the optimization.
- Keep the design intentionally small:
  - one process-local writer path for the index,
  - one bounded stale-index replay rule,
  - one minimal resume-observability surface.
- Keep notebooks thin and unchanged except for benefiting from the faster repo
  behavior automatically.

## Deliverables

- [x] One persisted resume-index artifact inside the Task 103 run root, scoped
  to the same durable storage surface as the spool tree.
- [x] One backward-compatible resume path that:
  - uses the index when it exists,
  - rebuilds it from spool JSON when it does not,
  - falls back safely if the index is missing or invalid.
- [x] One simple process-local index writer that is safe under the existing
  Task 103 thread pool.
- [x] One committed helper surface to rebuild or validate the resume index for
  existing run roots.
- [x] One docs update that records the new resume contract for persistent
  Hemma and Colab slices.

## Acceptance Criteria

- [x] Resume no longer requires a full spool JSON tree scan for new runs that
  already maintain the index.
- [x] Older run roots with only canonical spool JSON can generate the index on
  first resume without losing compatibility.
- [x] The resume index is stored inside the same run root as the spool tree, so
  Drive-backed Colab sessions read the persisted index directly from Drive.
- [x] Task 103 continues to treat spool JSON rows as canonical truth; the index
  is an accelerator, not a replacement storage model.
- [x] A corrupt or partial index does not strand a run; the system can rebuild
  from spool JSON deterministically.
- [x] The implementation defines one bounded stale-index rule after crashes and
  prevents duplicate expensive row work for rows whose canonical spool JSON
  already exists.
- [x] Resume emits one clear progress/log surface for:
  - loading the index fast path, or
  - rebuilding the index from spool JSON.
- [x] The new index path does not materially regress steady-state row
  throughput for Drive-backed Colab runs.
- [x] The notebook remains a thin orchestrator around repo-owned commands and
  gains the faster resume behavior without notebook-only logic.

## Proposed Design Notes

- Candidate artifact path:
  - `spool/completed_row_keys.jsonl`
- Candidate row payload:
  - `dataset`
  - `source_split`
  - `dataset_row_id`
- Candidate writer model:
  - open one append handle for the process
  - guard writes with one process-local lock
  - avoid per-row open/close churn on Drive-backed run roots
- Write ordering:
  - write canonical spool row first
  - append to the resume index second
  - emit the completed-row heartbeat after the index append
- Recovery model:
  - if the index is absent, rebuild from spool JSON
  - if the index is unreadable or inconsistent, discard and rebuild from spool
    JSON
- Bounded stale-index rule:
  - a crash may leave canonical spool JSON ahead of the index by a small tail
  - on resume, the fast path may therefore undercount a few just-finished rows
  - before doing expensive row work, check whether the canonical spool-row path
    already exists for the claimed row and skip it if present
- Minimal observability rule:
  - log whether resume used the index fast path or a spool-tree rebuild
  - log the completed-row count loaded before new work starts
- Persistence rule:
  - place the index under the same run root as `status.json`, logs, and spool
    rows so persistent Google Drive Colab sessions and Hemma detached runs share
    the same durability model

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
