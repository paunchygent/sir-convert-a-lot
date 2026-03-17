---
id: story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule
title: Define the post-Task-101 design lane after the final Story 29 stop rule
type: story
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly.md
  - docs/backlog/tasks/task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly.md
  - docs/backlog/tasks/task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3.md
  - docs/backlog/tasks/task-212-run-a-single-step-backward-lineage-probe-for-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-213-trace-the-first-talker-core-backward-operation-after-input-embeddings-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/reviews/review-03-architect-review-of-post-task-101-qwen-stabilization-candidates-after-story-29.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - architecture
  - stabilization
  - design-selection
---

Implementation slice with acceptance-driven scope.

## Objective

Execute the chosen post-Story-29 design lane for the preserved Task 101 Qwen
series after bounded RCA closed on the current no-projection lane.

The architect verdict is now fixed:

- choose Candidate 1: structural semantic-only embedding assembly
- keep ordered contingency `1 -> 3`
- reject Candidate 2 as the primary next story
- favor the most powerful truthful fix even when it is harder to implement

## Scope

- Treat the `T206` explicit position-mask correction as established local
  truth:
  - the old trainable-span leakage was real
  - the leakage is now removed in local audit and focused tests
  - the final governed Hemma proof still failed numerically before `1470`
- Keep the Story 29 stop rule intact:
  - no more replay-only RCA variants on the preserved lane
  - no more accumulation sweeps
  - no reopening of the old projection-enabled replay lane
- Treat the architect review as closed:
  - Candidate 1 is selected
  - Candidate 3 is the immediate contingency if Candidate 1 fails its
    smallest-signal validation or later proof lane
  - Candidate 2 is explicitly rejected as the primary next story
- Treat the following as non-candidates for the new story:
  - another prefix-length mask tweak
  - more `text_span_only` replay proofs on the same lane
  - auxiliary codebook-fusion work as a primary explanation
  - restart attempts before a new design lane is explicitly chosen
- Require the architect review to use the full collected evidence:
  - pre-fix leak evidence
  - post-fix zero-leak evidence
  - exact test outputs
  - exact final post-fix Hemma failure evidence
  - relevant `ml/qwen` and patched runtime code
- After candidate selection, split the chosen lane into task-sized execution
  units with one explicit smallest-signal validation before any new Hemma
  long-run proof.

## Selected Lane

### Primary: Candidate 1

Structural semantic-only embedding assembly is the selected next design lane.

Why it won:

- the earliest causal evidence remained in the text-embedding backward path
- `T206` proved the old leakage bug but also proved that a late mask correction
  is not a hard enough architectural boundary
- the repo still performs full-channel text-embedding lookup and only later
  masks the non-semantic positions

### Ordered Contingency: Candidate 3

Freeze-or-adapter text embedding is the immediate fallback if Candidate 1 does
not survive its smallest-signal validation or the next governed proof lane.

### Explicit Rejection: Candidate 2 As Primary

Text-embedding-specific optimizer/precision isolation is not the next story.
It may become a later tactic only if the structural assembly correction proves
insufficient, but it is currently judged too late-stage and too cushioning to
be the most truthful next answer.

## Candidate Selection Rule

- Choose the most powerful and truthful fix, regardless of implementation
  effort.
- Use semantic correctness and architectural truth before implementation cost.
- Prefer the design that removes or most directly redefines the unstable
  mechanism, not the one that merely survives the next bounded replay most
  cheaply.
- Use smaller-scope variants only when they explain the evidence at least as
  well as the larger fix.
- Apply contingency `1 -> 3`; do not divert the next story into Candidate 2.

## Acceptance Criteria

- [x] Story 29 stop-rule evidence is treated as final for the preserved replay
  lane and is not reopened informally.
- [x] One architect review artifact compares candidates `1-3` against the full
  collected evidence bundle.
- [x] One repomix package exists for the offline review and contains the
  relevant `ml/qwen` code, patched runtime surfaces, proof artifacts, and docs.
- [x] The story records the candidate-selection rule explicitly:
  the most powerful truthful fix wins even if it is harder.
- [x] The next implementation lane is not chosen by runtime convenience,
  minimal diff size, or another blind bounded replay.
- [x] The story is split into task-sized execution units for:
  - semantic-only batch contract
  - semantic-only train-step assembly
  - local gradient-membership proof
- [x] Candidate 2 remains excluded as the primary next implementation lane.

## Test Requirements

- [ ] The chosen candidate must define one smallest-signal validation that runs
  before any new Hemma long proof.
- [ ] The review package must include the exact passing local tests for the
  position-mask correction and the exact failing Hemma proof evidence.
- [ ] Docs validation and task indexing stay green after the review materials
  land.

## Done Definition

Done when the repo has one explicit post-Story-29 design-selection story, one
full evidence-backed architect review artifact, and one repomix package that
lets an external reviewer choose among candidates `1-3` without reconstructing
the RCA trail from terminal history, and when the selected Candidate 1 lane is
split into executable backlog tasks with Candidate 3 recorded as the only
immediate contingency.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md`
1. `docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md`
1. `docs/backlog/tasks/task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly.md`
1. `docs/backlog/tasks/task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly.md`
1. `docs/backlog/tasks/task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3.md`
1. `docs/backlog/tasks/task-212-run-a-single-step-backward-lineage-probe-for-the-fresh-start-candidate-1-failure.md`
1. `docs/backlog/tasks/task-213-trace-the-first-talker-core-backward-operation-after-input-embeddings-in-the-fresh-start-candidate-1-failure.md`
1. If Candidate 1 fails its smallest-signal validation or the subsequent
   governed proof, open the immediate Candidate 3 contingency lane.

## Current Status

- `T207` is complete:
  semantic text ids and semantic positions are now first-class batch fields.
- `T208` is complete:
  train and eval now embed only `semantic_text_ids` and scatter those
  embeddings back into full-sequence runtime positions.
- `T209` is complete:
  the local gradient-membership proof now demonstrates that only semantic ids
  can appear in `text_embedding.weight.grad`, including the poisoned-scaffold
  upstream case.
- `T210` is terminal negative rescue evidence:
  Candidate 1 still failed when resumed from the inherited `1406` state, so
  it does not authorize restart as an in-place rescue lane.
- `T211` is complete as terminal negative fresh-start evidence:
  Candidate 1 failed at optimizer step `1`, so replay-amassed inherited state
  is no longer the leading explanation for the current failure family.
- `T212` is complete with truthful discovery evidence:
  the exact fresh-start failing row pair was probed in the requested branch
  order, both rows failed independently, and the earliest instrumented
  non-finite backward hook appeared at `input_embeddings` after still-finite
  `hidden_states` and `talker_hidden_states` gradients.
- `T213` is now the active discovery lane:
  trace the first talker-core backward operation between finite
  `hidden_states` gradients and non-finite `input_embeddings` gradients before
  deciding whether Candidate 3 should open immediately.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
