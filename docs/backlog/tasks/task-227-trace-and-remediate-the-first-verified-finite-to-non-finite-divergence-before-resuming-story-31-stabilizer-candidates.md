---
id: task-227-trace-and-remediate-the-first-verified-finite-to-non-finite-divergence-before-resuming-story-31-stabilizer-candidates
title: Trace and remediate the first verified finite-to-non-finite divergence before resuming Story 31 stabilizer candidates
type: task
status: proposed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-225-define-the-exact-step-1-instability-parity-contract-for-the-recreated-historical-control-failure-family.md
  - docs/backlog/tasks/task-226-build-a-deterministic-upstream-vs-current-single-step-parity-probe-for-the-qwen-fine-tuning-path.md
  - docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - remediation
  - trainer-runtime
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Use the `T226` parity evidence to make the smallest truthful next move before
Story 31 resumes bounded stabilizer candidates:

- remediate the first verified divergence if one exists, or
- explicitly rule out trainer/runtime divergence and hand the lane back to
  `T219`.

## PR Scope

- Consume the `T226` parity artifacts as the primary evidence source.
- If the parity slice found a verified first divergence:
  - patch the smallest responsible code surface
  - avoid bundle-wide retuning or speculative "stability parameter" search
- If the parity slice found no meaningful divergence:
  - record that result explicitly
  - restore `T219` as the next bounded mechanism slice
- Re-run the deterministic local parity check after any remediation.
- Record one explicit operator decision:
  - resume `T219`
  - continue targeted remediation
  - or reshape Story 31 if the evidence no longer supports the current
    stabilizer framing
- Keep `T217` blocked throughout this task.

## Deliverables

- [ ] One verified remediation exists for the first confirmed divergence, or
  one explicit no-divergence conclusion is recorded.
- [ ] One rerun parity result confirms the post-remediation behavior or the
  no-divergence conclusion.
- [ ] One operator-facing decision states whether `T219` now resumes or whether
  a different mechanism task must replace it.
- [ ] Story 31 and the live ledger are updated with the result before any
  recovery proof is reconsidered.

## Acceptance Criteria

- [ ] The task acts only on a divergence that `T226` verified at a named
  checkpoint.
- [ ] Any remediation is the smallest justified patch, not a broad recipe
  sweep.
- [ ] If no divergence is verified, the docs explicitly say so and return the
  lane to `T219`.
- [ ] `T217` remains blocked regardless of the outcome of this task alone.
- [ ] The result is recorded in Story 31, `current.md`, and the Task 101 live
  ledger before downstream work resumes.

## Validation

- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run <parity-probe-surface> ...`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
