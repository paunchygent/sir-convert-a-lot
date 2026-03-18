---
id: task-236-resolve-the-post-t235-line4-row-local-outlier-before-claiming-a-generic-layer15-output-seam
title: Resolve the post-T235 line4 row-local outlier before claiming a generic layer15 output seam
type: task
status: in_progress
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-235-resolve-the-post-t234-sub-talker-loss-disagreement-between-layer16-input-layernorm-and-layer15-output.md
  - docs/backlog/tasks/task-237-test-one-post-t236-micro-family-against-the-first-verified-dominant-sub-talker-outlier-seam.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - diagnostics
  - follow-on
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Resolve the repeatable `line-4` row-local outlier exposed by `T235` so Story
31 can answer one narrower question cleanly:

- is the surviving `line-4` upstream seam a genuine row-local mechanism
  difference,
- a pair-interaction masking effect,
- or a non-repeatable one-row instability that should not block a downstream
  `layer_15.output` interpretation?

## PR Scope

- Treat `T235` as closed truth:
  - truthful disagreement probe:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task235-20260318t140352z-a1`
  - strongest fixed member:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`
  - pair and `line-13` first broke at `talker_core.layer_15.output`
  - `line-4` first broke at `talker_core.layer_16.input_layernorm`
- Keep the full state vector fixed:
  - same canonical bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same strongest T234 member only
- Add one diagnosis-only row-local outlier probe:
  - compare exactly:
    - `pair-sub-talker-loss`
    - `line-13-sub-talker-loss`
    - `line-4-sub-talker-loss`
  - instrument only the narrowed corridor needed to classify the outlier:
    - `talker_core.layer_15.output`
    - `talker_core.layer_16.input`
    - `talker_core.layer_16.input_layernorm.output`
- Add one dedicated `T236` assessment payload that classifies the result as
  exactly one of:
  - genuine row-local seam difference
  - pair-interaction masking effect
  - non-repeatable one-row instability
- Do not add a new stabilizer family in this task.
- Do not reopen recovery, optimizer, bundle, batching, or mask-policy changes.

## Interpretation Contract

- If `line-4` still fails upstream while pair and `line-13` stay downstream,
  classify the result as a genuine row-local seam difference and keep the next
  task targeted at that exact upstream seam only.
- If the pair diverges from both single rows, classify the result as a
  pair-interaction masking effect and keep the next task targeted at the exact
  interaction-controlled seam only.
- If all three cases now converge on one surface, classify the prior outlier
  as non-repeatable and allow the next task to target that verified dominant
  seam only.
- `T217` remains blocked unless a later mechanism task produces a promoted
  candidate.

## Deliverables

- [ ] One bounded row-local outlier probe exists for the strongest T234 member.
- [ ] One explicit classification identifies the `line-4` disagreement as
  row-local, pair-masked, or non-repeatable.
- [ ] One next-step rule constrains `T237` to a single verified dominant seam.

## Acceptance Criteria

- [ ] The task tests diagnosis only; it does not add or compare new
  stabilizer variants.
- [ ] The task keeps the Story 32 experiment spec fixed apart from the narrow
  hook profile needed to classify the outlier.
- [ ] The task ends with exactly one outlier classification and one next-step
  rule, not a mixed interpretation.

## Validation

- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
