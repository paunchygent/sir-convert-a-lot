---
id: task-245-confirm-the-post-t244-winner-specific-layer15-output-attenuation-multiply-before-any-new-stabilizer-family
title: Confirm the post-T244 winner-specific layer15 output attenuation multiply before any new stabilizer family
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-244-split-the-post-t243-layer15-output-return-path-before-any-new-stabilizer-family.md
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

Run one minimal root-cause confirmation slice at the smallest localized
post-`T244` seam so Story 31 can determine whether the first reproducible
`sub_talker_loss` break is actually born inside the fixed winner-specific
`layer15_out_0p5` attenuation multiply that emits `talker_core.layer_15.output`,
rather than in a broader layer-15 seam.

## PR Scope

- Treat `T244` as closed truth:
  - truthful rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task244-20260318t193736z-a1`
  - resolved classification:
    `converged_output_return`
  - dominant surface:
    `talker_core.layer_15.output`
  - fixed winner only:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
- Keep the full Story 32 state vector fixed:
  - same canonical bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same fixed winner only
  - no optimizer, sampler, recovery, or bundle changes
- Anchor the confirmation to the real winner-specific wrapper in
  `sft_12hz_talker_core_stabilization.py`, where layer 15 emits
  `hidden_states * output_scale` with `output_scale=0.5`.
- Run exactly one minimal causal intervention at that multiply site rather than
  opening a new stabilizer family.
- Interpret only the three normative `sub_talker_loss` rows:
  - `pair-sub-talker-loss`
  - `line-13-sub-talker-loss`
  - `line-4-sub-talker-loss`
- Keep `main_loss` and `combined_loss` observational only.
- Keep `T217` blocked; this task cannot authorize recovery promotion.

## Interpretation Contract

- Classify `causal_candidate_confirmed` if the minimal multiply-site
  confirmation neutralizes the exact localized seam without simply moving the
  first non-finite surface earlier or elsewhere in the committed corridor.
- Classify `multiply_not_causal` if the seam remains localized at
  `talker_core.layer_15.output` under the confirmation probe.
- Classify `nonlocal_regression` if the confirmation changes more than one
  causal idea, moves the first non-finite surface outside the committed
  corridor, or regresses upstream.

## Deliverables

- [x] One diagnosis-only T245 confirmation contract exists for the fixed T244
  winner.
- [x] One machine-readable assessment payload classifies the confirmation
  outcome at the winner-specific layer-15 attenuation multiply.
- [x] One truthful Hemma rerun records whether the localized T244 seam is a
  confirmed causal candidate.

## Acceptance Criteria

- [x] The task uses only the fixed T244 winner and one minimal causal
  confirmation idea.
- [x] The task keeps the full Story 32 state vector fixed apart from the exact
  multiply-site confirmation probe.
- [x] The result ends with exactly one confirmation classification and one next
  diagnosis rule.

## Result

- Live Hemma rerun:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task245-20260318t202916z-a1`
- Fixed confirmation variant:
  `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3_layer15_output_scale_fp32`
- Resolved classification:
  `multiply_not_causal`
- Dominant surface:
  `talker_core.layer_15.output`
- Normative `sub_talker_loss` cases:
  - `pair-sub-talker-loss` first broke at `talker_core.layer_15.output`
  - `line-13-sub-talker-loss` first broke at `talker_core.layer_15.output`
  - `line-4-sub-talker-loss` first broke at `talker_core.layer_15.output`
- Interpretation:
  - performing the winner-specific `layer15_out_0p5` multiply in fp32 did not
    neutralize or relocate the first reproducible seam
  - the attenuation multiply itself is therefore not a confirmed causal
    candidate
  - the next truthful diagnosis-only branch is `T246`, which must split the
    fp32-scaled layer-15 output result from the final emitted tensor under the
    fixed T245 confirmation variant before any new stabilizer family is
    considered

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_stabilization.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_layer15_output_return_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_layer15_output_multiply_confirmation_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_stability_lab.py -q`
- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run typecheck-all`
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run qwen-stability-lab --help`
- [x] `pdm run run-hemma -- pdm run qwen-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task245-20260318t202916z-a1 --skip-build --hook-profile talker_core_post_t243_layer15_output_return --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3_layer15_output_scale_fp32`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
