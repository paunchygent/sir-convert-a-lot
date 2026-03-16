---
id: task-203-audit-the-auxiliary-codebook-fusion-hot-path-against-story-29-mixed-precision-and-proof-lane-contracts
title: Audit the auxiliary codebook fusion hot path against Story 29 mixed-precision and proof-lane contracts
type: task
status: in_progress
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/current.md
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-202-harden-qwen-auxiliary-codebook-fusion-numerical-stability-and-assertion-contract.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - mixed-precision
  - hot-path
  - proof-gate
  - hemma
  - gpu
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Decide whether the current auxiliary codebook fusion change is fit to remain in
the Story 29 bounded-proof lane, and prevent a local test-driven hot-path
change from being treated as an accepted Task 101 mitigation without mixed-
precision evidence and hot-path cost review on the governed Hemma ROCm stack.

## PR Scope

- Run the audit on Hemma through the canonical `run-hemma` command surfaces and
  the real ROCm training container/runtime stack.
- Use Hemma-side `qwen-smoke`, `rocminfo`, `rocm-smi`, and bounded Qwen
  training/eval proof surfaces as the acceptance evidence source.
- Audit the current auxiliary codebook fusion reducer against representative
  Task 101 `bf16`/`fp16` tensor shapes using a `float32` oracle on Hemma, not
  through local Mac CPU measurements.
- Measure the hot-path cost of the current reducer on the Hemma train and eval
  helper path and compare it with the pre-change vectorized reduction on that
  same ROCm-governed stack.
- Decide one of these explicit outcomes before `T197` proof evidence is treated
  as canonical:
  - keep the current reducer because it shows a real numeric win at acceptable
    cost
  - replace it with a more suitable vectorized or promoted-dtype reduction
  - revert it from the Story 29 proof lane
- Add focused tests and documentation that distinguish:
  - ancillary hot-path contract hardening
  - the actual Story 29 mitigation candidate
    `text_embedding_mask_policy=text_span_only`
- Update Story 29 planning and the training reference ledger so this helper
  change cannot be confused with the restart-gating mitigation.

## Deliverables

- [ ] One low-precision oracle comparison exists for the auxiliary codebook
  fusion helper on representative Story 29 tensor shapes on Hemma.
- [ ] One Hemma GPU readiness/preflight artifact exists for the exact runtime
  used to make the reducer decision.
- [ ] One hot-path cost record exists for the candidate reducer versus the
  previous vectorized reduction.
- [ ] One keep/replace/revert decision is recorded in code, tests, and docs
  before `T197` proof evidence is treated as canonical.

## Acceptance Criteria

- [ ] Focused `bf16` and `fp16` tests compare the naive reduction and the
  candidate reduction against a `float32` oracle for representative
  codebook-fusion shapes.
- [ ] The decision evidence comes from Hemma ROCm-container runs; local Mac CPU
  probes may guide development but are not acceptance evidence.
- [ ] The accepted evidence includes Hemma GPU readiness truth for the runtime
  under test (`qwen-smoke` and/or equivalent ROCm preflight artifacts).
- [ ] Tolerance loosening alone is not sufficient acceptance evidence for this
  task.
- [ ] If the reducer stays, the task records why the numeric improvement is
  worth the hot-path cost and states explicitly that it is not the primary
  Story 29 mitigation.
- [ ] If the reducer does not show a meaningful numeric win or imposes
  unacceptable hot-path cost, it is replaced or removed before `T197` proof
  artifacts are treated as canonical.

## Notes

- This task is a contract-audit follow-up to `T202`, not a restart gate by
  itself.
- Story 29 remains centered on the bounded replay from
  `state-step-00001406`, the explicit `text_span_only` mitigation, and the
  accumulation ablations only if needed.
- Any long-running Hemma evidence run must stay detached and survivable beyond
  the local client session.

## Implemented Surface

- Direct proof runner:
  - `pdm run qwen-codebook-fusion-proof`
- Detached proof runner:
  - `pdm run qwen-codebook-fusion-proof-detached launch -- --skip-build`
  - `pdm run qwen-codebook-fusion-proof-detached status`
- Canonical remote invocation through the Hemma wrapper:
  - `pdm run run-hemma -- pdm run qwen-codebook-fusion-proof --skip-build`
  - `pdm run run-hemma -- pdm run qwen-codebook-fusion-proof-detached launch -- --skip-build`
  - `pdm run run-hemma -- pdm run qwen-codebook-fusion-proof-detached status`
- Canonical artifact root:
  - `build/verification/qwen-codebook-fusion-proof/`
  - Detached launch/status metadata now lands alongside `report.json`,
    `report.md`, `failure.txt`, `worker-status.json`, and `proof.log`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
