---
id: task-240-split-the-post-t237-downstream-convergence-seam-beneath-layer15-output-before-any-promotion-discussion
title: Split the post-T237 downstream convergence seam beneath layer15 output before any promotion discussion
type: task
status: in_progress
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
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

Split the post-`T237` downstream convergence seam into one narrower diagnosis
question so Story 31 can determine whether the first converged
`sub_talker_loss` break under the winning fp32-output-cap member occurs at:

- `talker_core.layer_15.mlp.down_proj`
- `talker_core.layer_15.output`
- or `talker_core.layer_16.input`

before any new stabilizer family or promotion discussion opens.

## PR Scope

- Treat `T237` as closed truth:
  - truthful bounded rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task237-20260318t154708z-a1`
  - resolved family classification:
    `converged_downstream`
  - winning member only:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
  - dominant surface:
    `talker_core.layer_15.output`
- Keep the full Story 32 state vector fixed:
  - same canonical bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same winning T237 member only
  - no optimizer, sampler, recovery, or bundle changes
- Add one diagnosis-only hook profile:
  `talker_core_post_t237_downstream_convergence`
- Constrain the trace corridor to exactly:
  - `talker_core.layer_15.mlp.down_proj`
  - `talker_core.layer_15.output`
  - `talker_core.layer_16.input`
  - `talker_core.layer_16.input_layernorm.output`
- Interpret only the three normative `sub_talker_loss` rows:
  - `pair-sub-talker-loss`
  - `line-13-sub-talker-loss`
  - `line-4-sub-talker-loss`
- Treat `main_loss` and `combined_loss` as observational only in this task.
- Do not add a new stabilizer family in this task.

## Interpretation Contract

- Classify `converged_mlp_down_proj` if all three normative rows first break
  at `talker_core.layer_15.mlp.down_proj`.
- Classify `converged_layer15_output` if all three normative rows first break
  at `talker_core.layer_15.output`.
- Classify `converged_layer16_input_handoff` if all three normative rows first
  break at `talker_core.layer_16.input`.
- Classify `downstream_disagreement` if all three rows stay inside the
  downstream corridor but do not agree on one earliest surface.
- Classify `upstream_or_nonlocal_regression` if any required row stays finite,
  reverts to `talker_core.layer_16.input_layernorm.output`, or first breaks
  outside the committed corridor.
- Keep `T217` blocked in every branch.

## Deliverables

- [ ] One diagnosis-only downstream hook profile exists for the fixed T237
  winner.
- [ ] One machine-readable `post_t237_downstream_convergence_assessment`
  payload classifies the downstream seam.
- [ ] One truthful Hemma rerun records the converged downstream split and the
  next T241 rule.

## Acceptance Criteria

- [ ] The task uses only the winning T237 member and does not compare baseline
  or second-cap variants.
- [ ] The task keeps the full Story 32 state vector fixed apart from the
  narrowed downstream hook profile.
- [ ] The result ends with exactly one downstream classification and one next
  diagnosis rule.

## Validation

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_post_t237_downstream_convergence_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_stability_lab.py -q`
- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task240-<timestamp>-a1 --skip-build --hook-profile talker_core_post_t237_downstream_convergence --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
