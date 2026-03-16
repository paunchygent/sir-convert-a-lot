---
id: task-202-harden-qwen-auxiliary-codebook-fusion-numerical-stability-and-assertion-contract
title: Harden Qwen auxiliary codebook fusion numerical stability and assertion contract
type: task
status: completed
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/current.md
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

Fix the remaining flaky/full-suite failure in
`test_fuse_auxiliary_codebook_embeddings_matches_manual_sum` with a numerical
algorithm hardening approach, not a shim or test bypass.

## PR Scope

- Harden auxiliary codebook fusion accumulation in
  `sft_12hz_codebook_fusion.py` to reduce floating-point cancellation drift.
- Keep the vectorized codebook lookup path and update only the reduction step.
- Align test assertion tolerances with floating-point contract expectations for
  equivalent but non-bit-identical reductions.

## Deliverables

- [x] Fusion helper uses compensated summation with stable accumulation dtype.
- [x] Fusion tests assert close with explicit numeric tolerances.
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

## Validation

- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_codebook_fusion.py -q`
- [x] `pdm run run-local-pdm pytest-root tests`
  - result: `838 passed, 5 skipped`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
