---
type: task
id: TASK-SIRCON-REP-0003
title: Add resumable row-processing for Qwen preprocessing runs
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- "[ ] A Task 103 row-processing rerun can target an existing run root without\n \
  \ deleting its preserved spool/audio artifacts when resume mode is enabled."
- "[ ] Source rows with an existing deterministic spool row are skipped rather\n \
  \ than recomputed."
- "[ ] Row heartbeat on resume reflects already completed row count plus newly\n \
  \ completed rows."
- "[ ] The Colab row-processing notebook can rerun after timeout/interruption\n  without\
  \ redoing already completed spool rows."
- '[ ] Focused tests prove resume semantics for row-processing.'
retired_ids:
- task-123-add-resumable-row-processing-for-qwen-preprocessing-runs
---

## Context

## Impact And Escalation

## Decision And Assumption Ledger

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Readiness

## Closeout

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Make Task 103 row-processing resumable from an existing run root so interrupted
Hemma or Colab preprocessing can continue from preserved spool state instead of
deleting the run root and restarting from row zero.

### Why This Exists

The first live Colab portable-slice proof demonstrated that the row-processing
lane works, but the notebook timeout revealed a hard operational gap: the
current `row-processing` stage wipes `inventory/`, `audio_24k/`, and `spool/`
at stage start, so rerunning the same selection must restart the entire slice.

That behavior is now unacceptable for:

- long Hemma row-processing windows
- Colab proof runs with notebook watchdogs
- any future multi-machine preprocessing campaign

### PR Scope

- Add an explicit Task 103 runner flag to resume row-processing from an existing
  run root.
- Prevent `prepare_output_root(..., stage=\"row-processing\")` from deleting
  preserved row-processing artifacts when resume mode is enabled.
- Skip source rows that already have a completed deterministic spool row on
  disk.
- Seed row heartbeat counters from the existing spool row count on resume.
- Preserve deterministic inventory output while allowing resume from partial
  progress.
- Update the Colab notebook flow so rerunning the row-processing cell can reuse
  the existing run root instead of forcing a full restart.

### Non-Goals

- Do not redesign finalization resume in this task.
- Do not change the source-selection artifact contract.
- Do not reopen canonical worker-count policy.

### Acceptance Criteria

- [ ] A Task 103 row-processing rerun can target an existing run root without
  deleting its preserved spool/audio artifacts when resume mode is enabled.
- [ ] Source rows with an existing deterministic spool row are skipped rather
  than recomputed.
- [ ] Row heartbeat on resume reflects already completed row count plus newly
  completed rows.
- [ ] The Colab row-processing notebook can rerun after timeout/interruption
  without redoing already completed spool rows.
- [ ] Focused tests prove resume semantics for row-processing.

### Deliverables

- Resume-aware Task 103 row-processing CLI surface and storage behavior.
- Focused Task 103 resume tests that prove spool-row skipping and heartbeat
  continuation.
- Colab notebook row-processing cell updated to rerun against an existing run
  root with `--resume-row-processing`.

### Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task103_qwen_preprocessing.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
