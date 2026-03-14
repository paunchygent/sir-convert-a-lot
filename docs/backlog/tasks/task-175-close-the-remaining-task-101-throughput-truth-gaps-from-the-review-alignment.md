---
id: task-175-close-the-remaining-task-101-throughput-truth-gaps-from-the-review-alignment
title: Close the remaining Task 101 throughput truth gaps from the review alignment
type: task
status: proposed
priority: high
created: '2026-03-14'
last_updated: '2026-03-14'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md
  - docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md
  - docs/backlog/tasks/task-174-rebuild-the-task-101-bundle-on-the-t173-contract-and-remove-legacy-bundle-fallbacks-after-stable-throughput-proof.md
labels:
  - qwen
  - training
  - throughput
  - observability
  - hemma
  - review
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close the remaining throughput and observability gaps identified in the review
alignment so Task 101 saturation evidence becomes truthful, attributable, and
operationally enforceable rather than inferred from partial runtime signals.

## Why This Exists

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

## PR Scope

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

## Non-Goals

- Do not redesign the Qwen objective or speaker-conditioning architecture in
  this task.
- Do not remove the rebuilt-bundle cleanup work tracked by `T174`.
- Do not accept “better-looking logs” as completion without new bounded Hemma
  evidence under `build/verification/`.

## Deliverables

- [ ] Aggressive throughput-profile launches can no longer degrade silently to a
  misleading tiny live `max_batch_size`.
- [ ] Live Task 101 artifacts expose realized batch occupancy and batch-budget
  truth for each validation run.
- [ ] One committed proof surface exists for worker-truth dataset/ref-input
  attribution.
- [ ] Throughput/saturation runs fail closed when the rebuilt-bundle contract is
  missing persisted precomputed reference inputs.
- [ ] Export/checkpoint phases are labeled so train-only utilization summaries
  exclude those windows.
- [ ] The auxiliary codebook path is further collapsed beyond the current
  Python-comprehension stack-and-sum posture.

## Acceptance Criteria

- [ ] A bounded Hemma proof run shows realized occupancy evidence consistent
  with the selected throughput profile rather than hidden batch collapse.
- [ ] A bounded Hemma proof run can attribute ref-input activity truthfully and
  distinguish persisted-load behavior from runtime extraction behavior.
- [ ] Train-phase utilization summaries exclude export/checkpoint windows in a
  way that remains consistent with the phase history artifacts.
- [ ] The repo no longer allows saturation claims from runs that silently fell
  back to legacy runtime ref-input preparation after the rebuilt bundle became
  canonical.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root <focused-paths>`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma evidence written under `build/verification/` for occupancy,
  worker-truth data attribution, and corrected train-phase monitoring.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
