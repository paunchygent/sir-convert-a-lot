---
id: review-03-architect-review-of-post-task-101-qwen-stabilization-candidates-after-story-29
title: Architect review of post-Task-101 Qwen stabilization candidates after Story 29
type: review
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - architecture-review
  - qwen
  - stabilization
  - story-30
---
Structured review artifact for implementation or readiness checks.

## Review Scope

External architecture review of the preserved Task 101 Qwen stabilization lane
after Story 29 reached its bounded-RCA stop rule.

This review is not asked to approve another replay. It is asked to choose the
next truthful design lane from these candidates:

1. structural semantic-only embedding assembly
1. text-embedding-specific optimizer/precision regime
1. freeze-or-adapter text embedding

Selection rule:

- choose the most powerful and truthful fix
- do not prefer the smallest diff or the cheapest implementation if it leaves
  a more direct design answer unexplored

## Review Package

Offline architect package:

- repomix XML:
  `.agents/repomix_packages/repomix-qwen-post-task101-architecture-review.xml`
- package size: `406,391` bytes
- file count: `36`
- total token estimate: `92,805`
- included evidence classes:
  - `ml/qwen` training and preprocessing code relevant to the failure family
  - patched dataset and text-embedding mask surfaces
  - detached proof/runtime surfaces
  - final post-fix proof artifacts
  - Story 29 / Task 206 reference docs and evidence ledger

## Findings

### 1. Final bounded-RCA state

- Story 29 is now closed as negative bounded-RCA evidence on the preserved
  no-projection lane.
- The last governed proof ran under:
  - proof id: `task206-20260317t074600z-postfix1470-a1`
  - replay target: `1406 -> 1470`
  - accumulation: `1`
  - policy: `text_embedding_mask_policy=text_span_only`

### 2. Pre-fix leak evidence

- The pre-fix offline audit proved the old helper was still prefix-shaped:
  - current trainable span: `0..136`
  - intended semantic span: `8..135`
  - leaked positions: `0..7` plus `136`
  - leaked ids:
    `151644`, `77091`, `198`, `151671`, `151672`, `151673`

### 3. Post-fix leak-removal evidence

- The explicit position-mask correction landed locally and passed the smallest
  direct regression.
- Exact direct test output:

```text
collected 1 item
tests/sir_convert_a_lot/ml/qwen/training/test_training_rows.py .
============================== 1 passed in 4.71s ===============================
```

- Exact focused suite output:

```text
collected 19 items
tests/sir_convert_a_lot/ml/qwen/training/test_token_span_audit.py .....
tests/sir_convert_a_lot/ml/qwen/training/test_training_rows.py ...........
tests/sir_convert_a_lot/ml/qwen/training/test_gradient_rca.py ...
============================== 19 passed in 4.93s ==============================
```

- Exact typecheck output:

```text
Success: no issues found in 471 source files
```

- Exact post-fix audit values:
  - `current_start=8`
  - `current_end=136`
  - `leaked_positions=[]`
  - `leaked_token_ids=[]`
  - `leaked_non_finite_count=0`
  - `current_trainable_non_finite_count=128`
  - `intended_semantic_non_finite_count=128`

### 4. Final post-fix Hemma failure evidence

- The final post-fix Hemma proof still failed:
  - `status=exited`
  - `exit_code=1`
  - `current_phase=failed`
  - `current_optimizer_step=1407`
  - `current_train_iteration=809`
- Container log truth:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
- No truthful `1470` checkpoint was minted.
- Detached standalone eval was therefore correctly not launched.

### 5. Latest failing sample details

- The first captured bad microbatch in the final post-fix replay was:
  - `train_iteration=809`
  - manifest line `14`
  - row id:
    `/app/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1/manifests/swedish_pilot_train.prepared.jsonl#L14`
- Sample-level forensic facts:
  - `32` non-finite token positions
  - positions `0..31`
  - `87` unique token ids in the sample
- Important interpretation:
  - the old trainable-span leakage was real and is now fixed
  - the lane still fails in the same broader text-embedding gradient family
  - therefore the leak was not the full cause

### 6. Candidate framing for the architect

#### Candidate 1

Structural semantic-only embedding assembly.

Question:
Should the repo move from mask-corrected semantics to a harder architectural
contract where only semantic text tokens ever enter the trainable
text-embedding path?

#### Candidate 2

Text-embedding-specific optimizer/precision regime.

Question:
Should `text_embedding` remain trainable but move under a separate optimizer,
precision, and clipping contract because the repeated first poisoned parameter
surface is still `text_embedding.weight.grad`?

#### Candidate 3

Freeze-or-adapter text embedding.

Question:
Should direct updates to the base text embedding be removed from this preserved
lane entirely, with adaptation moved into a smaller or more controlled learned
surface?

## Decision

Closed with external architect verdict:

1. Select Candidate 1 as the next design lane.
1. Keep ordered contingency `1 -> 3`.
1. Explicitly reject Candidate 2 as the primary next story.
1. Keep `T199` blocked until Candidate 1 clears its local smallest-signal proof
   and any later governed restart-authorizing gate.

Architect reasoning, normalized into repo terms:

- Candidate 1 best explains the total evidence because the repo still performs
  full-channel text-embedding lookup before late masking.
- Candidate 1 is the most powerful truthful fix because it directly removes
  the structural impurity instead of cushioning a later poisoned surface.
- Candidate 3 is the right immediate fallback if Candidate 1 fails.
- Candidate 2 is weaker as the next story because the evidence still points to
  an earlier causal surface than optimizer-state or parameter-group handling.

## Response

The architect response is now accepted as repo guidance:

1. Candidate 1 best explains the total evidence.
1. Candidate 1 is the most powerful truthful fix.
1. Candidate 1 should be implemented first, regardless of effort.
1. Candidate 2 should be rejected as the next primary lane.
1. Candidate 3 should be retained as the ordered contingency behind Candidate 1.

## Follow-up Actions

1. Keep `T199` blocked.
1. Execute Candidate 1 through:
   - `T207` semantic-only batch contract
   - `T208` semantic-only train-step assembly
   - `T209` local gradient-membership proof
1. Do not spend the next story on Candidate 2.
1. If Candidate 1 fails its smallest-signal validation or later governed lane,
   open Candidate 3 directly as the next contingency.

## Completion

Closed with design-lane selection recorded.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
