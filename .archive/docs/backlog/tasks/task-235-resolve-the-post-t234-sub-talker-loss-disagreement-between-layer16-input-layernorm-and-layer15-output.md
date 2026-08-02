---
id: task-235-resolve-the-post-t234-sub-talker-loss-disagreement-between-layer16-input-layernorm-and-layer15-output
title: Resolve the post-T234 sub-talker-loss disagreement between layer16 input-layernorm and layer15 output
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-234-test-one-diagnosed-post-t233-output-scale-micro-family-against-the-first-verified-layer16-input-layernorm-output-surface.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
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
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task234-20260318t123644z-a1`
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

## Implementation Status

- Implemented as one diagnosis-only Story 31 disagreement probe:
  - hook profile:
    `talker_core_post_t234_disagreement`
  - allowed stabilizer:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`
- Landed code surfaces:
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_core_trace.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_backward_lineage_hooks.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_sub_talker_disagreement_assessment.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_stability_lab_contracts.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_stability_lab_runner.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_stability_lab_markdown.py`

## Result

- Truthful bounded rerun:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task235-20260318t140352z-a1`
- The pair and `line-13` `sub_talker_loss` cases stayed downstream at:
  `talker_core.layer_15.output`
- `line-4-sub-talker-loss` stayed upstream at:
  `talker_core.layer_16.input_layernorm`
- No required case failed first at `talker_core.layer_16.input`.
- Interpretation:
  - the strongest `T234` member does not authorize a generic
    `layer_15.output` winner
  - the mixed result is repeatable rather than a one-off reporting artifact
  - the next task must resolve the row-local `line-4` outlier before any new
    micro-family is tested

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

- [x] One bounded disagreement probe exists for the strongest T234 member.
- [x] One three-case matrix records whether the earliest `sub_talker_loss`
  surface agrees or disagrees across pair and single-row cases.
- [x] One explicit next-family rule closes the disagreement cleanly.

## Acceptance Criteria

- [x] The task tests one question only:
  whether the strongest T234 member yields a consistent downstream seam or a
  real row-local disagreement.
- [x] The task keeps the entire Story 32 experiment spec fixed apart from the
  narrowed hook profile needed to answer that question.
- [x] The task does not add or compare new stabilizer variants.
- [x] The task ends with exactly one next-step interpretation, not a mixed
  guess across multiple possible families.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_sub_talker_disagreement_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_stability_lab.py -q`
- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run run-hemma -- pdm run qwen-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task235-20260318t140352z-a1 --skip-build --hook-profile talker_core_post_t234_disagreement --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
