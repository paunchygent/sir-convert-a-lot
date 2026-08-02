---
id: task-202-harden-qwen-auxiliary-codebook-fusion-numerical-stability-and-assertion-contract
title: Harden Qwen auxiliary codebook fusion numerical stability and assertion contract
type: task
status: completed
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - .codex/handoff.md
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-203-audit-the-auxiliary-codebook-fusion-hot-path-against-story-29-mixed-precision-and-proof-lane-contracts.md
labels:
  - qwen
  - training
  - numerical-stability
  - tests
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close the remaining flaky/full-suite failure in
`test_fuse_auxiliary_codebook_embeddings_matches_manual_sum` without a shim or
test bypass, while handing the runtime hot-path decision to `T203`.

## PR Scope

- Restore green local tests around the auxiliary codebook fusion helper.
- Isolate one candidate reducer and test contract for later Hemma-side audit.
- Keep the decision about the hot-path runtime contract delegated to `T203`.

## Deliverables

- [x] The local repo failure was closed without shims or skips.
- [x] The helper/test contract was isolated for later Hemma-side audit.
- [x] Full repo test suite passes after the change.

## Acceptance Criteria

- [x] `tests/sir_convert_a_lot/ml/qwen/training/test_codebook_fusion.py` passes.
- [x] `pdm run run-local-pdm pytest-root tests` passes.
- [x] No compatibility shim or skip-based workaround is introduced.

## Notes

- This task closed the local repo test failure and documented one candidate
  reducer.
- It does not, by itself, approve that reducer as part of the canonical Story
  29 proof lane.
- `T203` owns the keep/replace/revert decision based on mixed-precision oracle
  evidence and hot-path cost.
- `T203` later completed that audit on Hemma and reverted the candidate
  reducer after it showed no numeric win and about `1.26x` slowdown.

## Validation

- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_codebook_fusion.py -q`
- [x] `pdm run run-local-pdm pytest-root tests`
  - result: `838 passed, 5 skipped`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
