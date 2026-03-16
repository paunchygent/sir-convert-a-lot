---
id: story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart
title: Counteract Task 101 codec-span text-pad instability and gate the next clean restart
type: story
status: in_progress
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-194-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405.md
  - docs/backlog/tasks/task-203-audit-the-auxiliary-codebook-fusion-hot-path-against-story-29-mixed-precision-and-proof-lane-contracts.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - stability
  - hemma
  - rca
---

Implementation slice with acceptance-driven scope.

## Objective

Counteract the reproducible Task 101 codec-span text-pad instability, prove
that the chosen mitigation makes the preserved no-projection training lane
numerically stable on bounded windows from `state-step-00001406`, and block
any new clean base restart until that proof gate is satisfied.

## Scope

- Add one explicit text-embedding mask policy to the committed Qwen training
  runtime and control plane.
- Add one explicit runtime override for `gradient_accumulation_steps` so
  bounded proofs can compare `4`, `2`, and `1` without ad hoc code edits.
- Audit any auxiliary codebook-fusion hot-path change separately before
  accepting it as part of the bounded proof contract; do not let a local
  test-fix slice redefine the Story 29 mitigation without mixed-precision and
  hot-path evidence.
- Treat `legacy_codec_span` as an RCA reproduction surface only while the
  mitigation proof is still open.
- Once `T197` or `T198` proves the winning mitigation, remove
  `legacy_codec_span` before `T199` launches the next clean restart.
- Use the canonical RCA checkpoint
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
  for all bounded proofs in this story.
- Prefer proving the mitigation through the old `1417` failure window and on to
  the next scheduled review/eval step `1500`.
- Allow one realistic fallback gate if `1500` still fails after the structural
  mitigation and the planned accumulation ablations:
  - clear at least two full pilot-data passes from `1406` to `1470`
  - mint a checkpoint at `1470`
  - run standalone held-out eval from that fallback checkpoint
- Keep the training reference ledger as the canonical operator record of:
  - RCA truth
  - proof outcomes
  - the decision to allow or block the next clean restart

Out of scope:

- new learning-rate sweeps before the mask-policy and accumulation proofs fail
- gradient sanitization as a first-line mitigation
- treating replay success at `1418` alone as sufficient evidence for the next
  clean restart

## Acceptance Criteria

- [ ] Story 29 is the explicit restart gate for the preserved Task 101 lane.
- [ ] The preferred proof target is documented and enforced:
  - clear the mitigated `1406 -> 1418` replay
  - then reach `1500`
  - then complete the scheduled eval at `1500`
- [ ] The fallback proof target is documented and enforced:
  - only after the structural mitigation and accumulation ablations
  - clear `1406 -> 1470`
  - then run standalone held-out eval from the `1470` checkpoint
- [ ] No fresh clean base restart is allowed before either the preferred or
  fallback proof gate is met.
- [ ] Any auxiliary codebook-fusion helper change in the proof lane is either
  separately proven beneficial and acceptable for mixed-precision hot-path use
  on the Hemma ROCm stack, or removed before `T197` proof artifacts are
  treated as canonical.
- [ ] The training reference ledger is a required update target for every proof
  and decision in this story.
- [ ] Proof closure on `text_span_only` or `text_span_only` plus reduced
  accumulation explicitly triggers removal of the `legacy_codec_span` mask
  surface before the next clean restart.
- [ ] Story 29 stays aligned with Story 28 package boundaries and does not
  reopen god-file style runtime/control-plane changes.

## Test Requirements

- [ ] The new mask policy is covered by focused runtime/collation/reporting
  tests.
- [ ] The accumulation override is covered by focused parser/runtime/reporting
  tests.
- [ ] The bounded proof tasks define explicit machine-readable acceptance
  artifacts for both the preferred and fallback gates.
- [ ] Docs validation and task indexing stay green after the new story/tasks
  and operator-doc updates land.

## Done Definition

Done when the repo has one explicit mitigation-and-proof story for the Task 101
instability, the next restart gate is documented consistently across backlog,
runbook, handoff, and reference surfaces, and the resulting task chain makes it
impossible to justify another blind restart without first proving bounded
numerical stability.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-195-land-an-explicit-task-101-text-embedding-mask-policy-and-text-span-only-mitigation.md`
1. `docs/backlog/tasks/task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs.md`
1. `docs/backlog/tasks/task-203-audit-the-auxiliary-codebook-fusion-hot-path-against-story-29-mixed-precision-and-proof-lane-contracts.md`
1. `docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md`
1. `docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md`
1. `docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md`

## Current Status

- `T195` is complete and made `text_span_only` the fresh-launch default while
  preserving `legacy_codec_span` only for bounded RCA reproduction.
- `T196` is complete and made `gradient_accumulation_steps` explicit and
  runtime-configurable across launch, resume, capture, diagnose, eval, and
  schedule flows.
- `T203` is now the next contract-audit step because the current local
  auxiliary codebook fusion change is not yet accepted as canonical Story 29
  proof-lane behavior.
- `T203` now has committed attached and detached Hemma proof surfaces:
  `qwen-codebook-fusion-proof` and
  `qwen-codebook-fusion-proof-detached`.
- `T197` remains the first bounded proof step after `T203` decides whether the
  fusion helper change stays, is replaced, or is removed from the proof lane.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
