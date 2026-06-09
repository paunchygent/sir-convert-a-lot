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
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly.md
  - docs/backlog/tasks/task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly.md
  - docs/backlog/tasks/task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - restart
  - proof-gated
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Launch the first clean base restart only after the repo records a truthful
fresh-start stabilization proof that shows stable bundle learning is back on
the canonical clean-semantics lane.

## PR Scope

- Treat Story 29 and Story 30 as closed prerequisite evidence:
  - replay-family rescue is exhausted
  - clean text semantics are now a correctness baseline, not a stability proof
  - fresh-start Candidate 1 also failed before stable learning was recovered
- Block this task until Story 31 records:
  - one bounded talker-core stabilization surface (`T216`)
  - one passing local finiteness gate (`T215`)
  - one positive fresh-start governed Hemma proof (`T217`) that justifies a
    larger clean-start proof lane
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

- [ ] The task does not start before Story 31 records an explicit fresh-start
  stabilization proof in the training reference ledger that justifies a larger
  clean-start proof lane.
- [ ] The first restart acceptance gate is completion of the first scheduled
  eval at step `100` without a non-finite guard event.
- [ ] Any new restart failure window is written back into the training
  reference ledger immediately rather than treated as an informal note.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
