---
id: task-244-split-the-post-t243-layer15-output-return-path-before-any-new-stabilizer-family
title: Split the post-T243 layer15 output return path before any new stabilizer family
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-243-split-the-post-t241-layer15-residual-output-formation-seam-before-any-new-stabilizer-family.md
  - docs/backlog/tasks/task-245-confirm-the-post-t244-winner-specific-layer15-output-attenuation-multiply-before-any-new-stabilizer-family.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - diagnostics
  - follow-on
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Split the post-`T243` converged `talker_core.layer_15.output` seam into the
smallest meaningful winner-specific return-path sub-boundaries so Story 31 can
determine whether the first reproducible `sub_talker_loss` break under the
fixed `T237/T243` winner is born:

- in the raw post-sum tensor handed off into the `layer15_out_0p5` winner
  wrapper, or
- only after that winner-specific output attenuation emits the returned
  `talker_core.layer_15.output` tensor

before any new stabilizer family is considered.

## PR Scope

- Treat `T243` as closed truth:
  - truthful rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task243-20260318t190832z-a1`
  - resolved classification:
    `converged_layer15_output_return`
  - fixed winner only:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
  - dominant seam:
    `talker_core.layer_15.output`
- Keep the full Story 32 state vector fixed:
  - same canonical bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same fixed winner only
  - no optimizer, sampler, recovery, or bundle changes
- Add one diagnosis-only hook profile that traces the post-sum return path
  beneath `talker_core.layer_15.output`.
- Treat the real winner-specific return path truthfully:
  - under the fixed `layer15_out_0p5` winner, the post-attenuation wrapper
    output and the final emitted `talker_core.layer_15.output` are the same
    tensor
  - `T244` must therefore split the smallest meaningful return corridor rather
    than inventing two distinct post-scale surfaces that do not exist
- Constrain the trace corridor to:
  - `talker_core.layer_15.output.pre_output_scale_return`
    - the raw post-sum tensor before the winner-specific attenuation multiply
  - `talker_core.layer_15.output`
    - the emitted post-scale tensor returned from layer 15
  - `talker_core.layer_16.input`
    - downstream guard surface if the seam has already moved beyond the
      winner-specific return wrapper
- Interpret only the three normative `sub_talker_loss` rows:
  - `pair-sub-talker-loss`
  - `line-13-sub-talker-loss`
  - `line-4-sub-talker-loss`
- Treat `main_loss` and `combined_loss` as observational only in this task.
- Do not add a new stabilizer family in this task.

## Interpretation Contract

- Classify `converged_pre_output_scale_return` if all three normative rows
  first break at `talker_core.layer_15.output.pre_output_scale_return`.
- Classify `converged_output_return` if all three normative rows first break
  at `talker_core.layer_15.output`.
- Classify `converged_layer16_input_handoff` if all three normative rows
  first break at `talker_core.layer_16.input`.
- Classify `downstream_disagreement` if all three rows stay inside the return
  corridor but do not agree on one earliest surface.
- Classify `nonlocal_regression` if any required row skips outside the
  committed corridor, reverts upstream, or stays finite.
- Keep `T217` blocked in every branch.

## Deliverables

- [x] One diagnosis-only return-path hook profile exists for the fixed T243
  winner.
- [x] One machine-readable assessment payload classifies the narrowed
  `layer_15.output` return seam.
- [x] One truthful Hemma rerun records the converged return-path split and the
  next diagnosis-only rule.

## Acceptance Criteria

- [x] The task uses only the winning T237/T243 member and does not compare
  alternate variants.
- [x] The task keeps the full Story 32 state vector fixed apart from the
  narrowed `layer_15.output` return-path hook profile.
- [x] The result ends with exactly one diagnosis classification and one next
  diagnosis rule.

## Result

- Live Hemma rerun:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task244-20260318t193736z-a1`
- Fixed variant:
  `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
- Resolved classification:
  `converged_output_return`
- Dominant surface:
  `talker_core.layer_15.output`
- Normative `sub_talker_loss` cases:
  - `pair-sub-talker-loss` first broke at `talker_core.layer_15.output`
  - `line-13-sub-talker-loss` first broke at `talker_core.layer_15.output`
  - `line-4-sub-talker-loss` first broke at `talker_core.layer_15.output`
- Interpretation:
  - the converged seam does not first break in the raw post-sum tensor before
    the winner-specific attenuation multiply
  - the smallest localized seam now sits at the emitted
    `talker_core.layer_15.output` tensor under the fixed winner
  - the next truthful root-cause slice is therefore `T245`, which must confirm
    or split the winner-specific layer-15 output attenuation multiply itself
    before any new stabilizer family is considered

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_backward_lineage_hooks.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_layer15_residual_output_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_layer15_output_return_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_stability_lab.py -q`
- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run typecheck-all`
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run qwen-stability-lab --help`
- [x] `pdm run run-hemma -- pdm run qwen-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task244-20260318t193736z-a1 --skip-build --hook-profile talker_core_post_t243_layer15_output_return --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
