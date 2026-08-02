---
type: task
id: TASK-SIRCON-05-03-09
title: Close the remaining Task 101 throughput truth gaps from the review alignment
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
story: ST-SIRCON-05-03
task_kind: story
acceptance_criteria:
- "[ ] A bounded Hemma proof run shows realized occupancy evidence consistent\n  with\
  \ the selected throughput profile rather than hidden batch collapse."
- "[ ] A bounded Hemma proof run can attribute ref-input activity truthfully and\n\
  \  distinguish persisted-load behavior from runtime extraction behavior."
- "[ ] Train-phase utilization summaries exclude export/checkpoint windows in a\n\
  \  way that remains consistent with the phase history artifacts."
- "[ ] The repo no longer allows saturation claims from runs that silently fell\n\
  \  back to legacy runtime ref-input preparation after the rebuilt bundle became\n\
  \  canonical."
retired_ids:
- task-175-close-the-remaining-task-101-throughput-truth-gaps-from-the-review-alignment
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Close the remaining throughput and observability gaps identified in the review
alignment so Task 101 saturation evidence becomes truthful, attributable, and
operationally enforceable rather than inferred from partial runtime signals.

### Why This Exists

The current lane has already fixed the two clearest reviewer-aligned defects:

- per-step scalar loss synchronization in the hot loop
- pre-train sample contamination in train-phase utilization summaries

But the live lane still lacks hard guarantees and truthful attribution for
several remaining review findings:

- “aggressive” throughput profiles can still realize tiny batches in practice
- realized batch occupancy is not surfaced in live evidence
- worker-side ref-input and dataset-path activity is not truthfully attributed
- performance runs can still silently fall back to legacy runtime `ref_mel`
  extraction before the rebuilt-bundle path is made canonical
- auxiliary codebook fusion is still Python-side multi-lookup aggregation, not
  a truly collapsed path
- short bounded train medians can still be distorted by missing export/checkpoint
  phase labeling

The current bundle rebuild lane also exposed a separate operator-truth gap:

- governed bundle batches do not stream live logs
- the bundle status artifact does not expose the current batch identity
- stale `build.exit` markers can be misread during retries if the build is
  relaunched on the same output root

### Current Progress

- First non-bundle `T175` slice is implemented locally:
  - the aggressive throughput profile now fails closed when paired with a tiny
    live `max_batch_size`
  - the training lane now computes machine-readable batch-occupancy evidence
    from the resolved sampler plan, including per-batch row/token/frame totals
    and a realized batch-size histogram
  - the terminal training summary/report surfaces now carry the occupancy
    payload alongside the resolved throughput-profile contract
- Second non-bundle `T175` slice is implemented locally:
  - detached launch, in-container trainer, and patched trainer CLI surfaces now
    expose an explicit `data_path_proof_mode` contract
  - proof mode now fails closed unless `dataloader_num_workers == 0`, so the
    dataset-path counters stay authoritative instead of being inferred across
    worker processes
  - the patched dataset now records persisted `ref_mel` loads, runtime
    ref-mel extraction, `__getitem__` timings, and `collate_fn` timings into a
    typed machine-readable payload
  - terminal training summary/report and detached status markdown now surface
    the data-path attribution payload for bounded proof runs
- Third non-bundle `T175` slice is implemented locally:
  - explicit phase transitions now wrap interval durable checkpoints, epoch-end
    exports, final durable checkpoint writes, and final model export writes
  - when training continues after a save/export window, the trainer now emits a
    matching `train` phase restoration immediately instead of waiting for a
    later cadence heartbeat
  - monitor grouping tests now prove that later train windows are counted as
    train after checkpoint-save restores instead of being smeared into the
    save/export phase
- Fourth non-bundle `T175` slice is implemented locally:
  - the canonical detached launch surface now revalidates rebuilt bundles with
    fail-closed persisted-ref-input requirements once a bundle report exists
  - the patched training-row loader now has a second fail-closed path so direct
    trainer invocation cannot silently fall back to legacy runtime reference
    preparation when a rebuilt-bundle contract is active
  - focused host-preflight and row-loader tests now prove rebuilt bundles are
    rejected when `precomputed_ref_input_*` metadata is missing
- Fifth non-bundle `T175` slice is implemented locally:
  - auxiliary codebook fusion now uses one vectorized indexed lookup across a
    stacked weight tensor instead of one Python/module call per codebook
  - focused tests prove the new path matches the previous summed semantics for
    both wrapped fake embeddings and direct `nn.Embedding` modules
- Bundle-log / bundle-observability follow-up is intentionally deferred to the
  next session so the current slice stays focused on core throughput-truth work.

### PR Scope

- Make the aggressive throughput profile contract enforce an actually aggressive
  live batch cap instead of inheriting tiny caller-provided values silently.
- Emit realized batch occupancy evidence for the Task 101 lane:
  row count, summed text tokens, summed codec frames, realized batch size
  histogram, and the active profile/max-batch contract.
- Add truthful worker-side dataset/ref-input attribution for bounded proof runs:
  persisted `ref_mel` loads, runtime mel extraction, `__getitem__` timing, and
  `collate_fn` timing, or an equivalent committed proof mode that makes those
  counters authoritative.
- Make throughput/saturation validation fail closed on missing
  `precomputed_ref_input_*` fields once the rebuilt `T173` bundle is the active
  canonical source of truth.
- Tighten phase labeling so epoch-end/final model export work is not counted as
  train-phase utilization in short bounded monitor summaries.
- Replace or further reduce the remaining Python-side auxiliary codebook
  fragmentation so the T172 lane moves closer to one truly vectorized path.
- Restore operator-grade bundle observability by streaming governed batch output
  into canonical log files, surfacing current-batch status fields, and clearing
  stale exit markers on bundle-build relaunch.

### Non-Goals

- Do not redesign the Qwen objective or speaker-conditioning architecture in
  this task.
- Do not remove the rebuilt-bundle cleanup work tracked by `T174`.
- Do not accept “better-looking logs” as completion without new bounded Hemma
  evidence under `build/verification/`.

### Deliverables

- [x] Aggressive throughput-profile launches can no longer degrade silently to a
  misleading tiny live `max_batch_size`.
- [x] Live Task 101 artifacts expose realized batch occupancy and batch-budget
  truth for each validation run.
- [x] One committed proof surface exists for worker-truth dataset/ref-input
  attribution.
- [x] Throughput/saturation runs fail closed when the rebuilt-bundle contract is
  missing persisted precomputed reference inputs.
- [x] Export/checkpoint phases are labeled so train-only utilization summaries
  exclude those windows.
- [x] The auxiliary codebook path is further collapsed beyond the current
  Python-comprehension stack-and-sum posture.
- [ ] Bundle builds stream governed batch output into canonical operator log
  files and expose current-batch identity in the status artifact.

### Acceptance Criteria

- [ ] A bounded Hemma proof run shows realized occupancy evidence consistent
  with the selected throughput profile rather than hidden batch collapse.
- [ ] A bounded Hemma proof run can attribute ref-input activity truthfully and
  distinguish persisted-load behavior from runtime extraction behavior.
- [ ] Train-phase utilization summaries exclude export/checkpoint windows in a
  way that remains consistent with the phase history artifacts.
- [ ] The repo no longer allows saturation claims from runs that silently fell
  back to legacy runtime ref-input preparation after the rebuilt bundle became
  canonical.

### Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root <focused-paths>`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma evidence written under `build/verification/` for occupancy,
  worker-truth data attribution, and corrected train-phase monitoring.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [x] Docs updated
