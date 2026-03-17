---
id: task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate
title: Launch the first clean base restart after the bounded stability gate
type: task
status: proposed
priority: high
created: '2026-03-16'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - restart
  - proof-gated
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Launch the first clean base restart only after Story 29 proves bounded
numerical stability through the single final post-fix
`1470 + standalone eval` gate defined by `T206`.

## PR Scope

- Block this task until the selected Story 30 Candidate 1 lane lands through
  `T207-T209`, then satisfies the next restart-authorizing governed proof for
  the preserved Task 101 series.
- Current truth after the final `T206` post-fix proof:
  - the explicit position-mask correction landed
  - the single final post-fix proof failed at optimizer step `1407`
  - no truthful `1470` checkpoint was minted
  - detached standalone eval was not launched
  - this task therefore remains blocked until a new design/architecture story
    defines a new restart-authorizing lane
- Current Story 30 decision:
  - Candidate 1 is selected as the next lane
  - Candidate 3 is the ordered contingency
  - Candidate 2 is rejected as the primary next story
- Launch from `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, not from a legacy checkpoint.
- Use the winning mitigation contract from the proof phase.
- If the winning mitigation confirms `text_span_only` as the right fix, remove
  `legacy_codec_span` from the live restart lane before launch.
- Use the canonical scheduled posture:
  - checkpoint every `500`
  - eval every `100`
  - retain newest `3`
- Record the restart result immediately in the training reference ledger.

## Deliverables

- [ ] One proof-gated clean restart launch record exists.
- [ ] One operator-facing ledger entry records which proof gate justified the
  restart.
- [ ] If the proof closed in favor of `text_span_only`, one explicit cleanup
  record exists showing `legacy_codec_span` was removed before restart.
- [ ] One restart acceptance record states whether step `100` eval completed
  without a non-finite guard event.

## Acceptance Criteria

- [ ] The task does not start before the selected Story 30 lane records an
  explicit restart-authorizing proof in the training reference ledger.
- [ ] The first restart acceptance gate is completion of the first scheduled
  eval at step `100` without a non-finite guard event.
- [ ] Any new restart failure window is written back into the training
  reference ledger immediately rather than treated as an informal note.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
