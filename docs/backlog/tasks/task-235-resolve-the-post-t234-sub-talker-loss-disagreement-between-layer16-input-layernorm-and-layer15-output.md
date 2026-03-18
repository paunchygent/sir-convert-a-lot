---
id: task-235-resolve-the-post-t234-sub-talker-loss-disagreement-between-layer16-input-layernorm-and-layer15-output
title: Resolve the post-T234 sub-talker-loss disagreement between layer16 input-layernorm and layer15 output
type: task
status: proposed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-234-test-one-diagnosed-post-t233-output-scale-micro-family-against-the-first-verified-layer16-input-layernorm-output-surface.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - stabilization
  - follow-on
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Resolve the mixed `sub_talker_loss` result exposed by `T234` under the
strongest output-scale member so Story 31 can answer one question cleanly:
is `talker_core.layer_15.output` now the dominant downstream seam, or does the
remaining `line-4` failure at `talker_core.layer_16.input_layernorm` block
that claim?

## PR Scope

- Treat `T234` as closed truth:
  - truthful rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task234-20260318t123644z-a1`
  - no variant stayed finite and no variant earned promotion
  - the strongest diagnostic member is:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`
  - under that member:
    - `pair-sub-talker-loss` first broke at `talker_core.layer_15.output`
    - `line-13-sub-talker-loss` first broke at `talker_core.layer_15.output`
    - `line-4-sub-talker-loss` still first broke at
      `talker_core.layer_16.input_layernorm`
- Keep the state vector fixed:
  - same source bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same strongest T234 member only
- Add one diagnosis-only disagreement probe that compares exactly:
  - `pair-sub-talker-loss`
  - `line-13-sub-talker-loss`
  - `line-4-sub-talker-loss`
- Constrain the probe to the post-T234 disagreement corridor only:
  - the residual `talker_core.layer_16.input_layernorm` seam
  - the downstream `talker_core.layer_15.output` seam
  - any minimal intermediate handoff surfaces required to determine which one
    is truly earliest under the strong T234 member
- Do not add a new stabilizer family in this task.
- Do not reopen recovery, optimizer, bundle, or sampler changes in this task.

## Interpretation Contract

- If the pair and both single-row `sub_talker_loss` cases all now agree on
  `talker_core.layer_15.output` or one tighter downstream surface beneath it,
  the next task may test one `layer_15.output`-family mechanism idea only.
- If `line-4-sub-talker-loss` still disagrees while the pair and `line-13`
  stay downstream, the next task must resolve the row-local outlier instead of
  claiming a generic `layer_15.output` winner.
- If all three cases revert to `talker_core.layer_16.input_layernorm`, close
  the T234 output-scale family as a non-repeatable relocation signal.
- `T217` remains blocked unless a later task produces a clear promoted
  mechanism candidate.

## Deliverables

- [ ] One bounded disagreement probe exists for the strongest T234 member.
- [ ] One three-case matrix records whether the earliest `sub_talker_loss`
  surface agrees or disagrees across pair and single-row cases.
- [ ] One explicit next-family rule closes the disagreement cleanly.

## Acceptance Criteria

- [ ] The task tests one question only:
  whether the strongest T234 member yields a consistent downstream seam or a
  real row-local disagreement.
- [ ] The task keeps the entire Story 32 experiment spec fixed apart from the
  narrowed hook profile needed to answer that question.
- [ ] The task does not add or compare new stabilizer variants.
- [ ] The task ends with exactly one next-step interpretation, not a mixed
  guess across multiple possible families.

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
