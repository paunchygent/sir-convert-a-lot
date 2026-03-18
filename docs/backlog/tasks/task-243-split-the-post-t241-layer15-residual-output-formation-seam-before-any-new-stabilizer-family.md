---
id: 'task-243-split-the-post-t241-layer15-residual-output-formation-seam-before-any-new-stabilizer-family'
title: 'Split the post-T241 layer15 residual-output formation seam before any new stabilizer family'
type: task
status: in_progress
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-241-split-the-post-t240-layer15-output-seam-into-residual-output-formation-sub-boundaries-before-any-new-stabilizer-family.md
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

Split the post-`T241` converged `layer_15.output` seam into residual-output
formation sub-boundaries so Story 31 can determine whether the first
converged `sub_talker_loss` break under the fixed T237/T241 winner occurs in:

- the residual input entering the final layer-15 output formation,
- the residual-add sum itself,
- or the final returned `talker_core.layer_15.output` tensor

before any new stabilizer family is considered.

## PR Scope

- Treat `T241` as closed truth:
  - truthful bounded rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task241-20260318t175714z-a1`
  - resolved classification:
    `converged_layer15_output_residual`
  - fixed winner only:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
  - dominant seam:
    `talker_core.layer_15.output`
- Keep the full Story 32 state vector fixed:
  - same canonical bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same winning T237/T241 member only
  - no optimizer, sampler, recovery, or bundle changes
- Add one diagnosis-only hook profile that instruments layer-15
  residual/output formation itself.
- Constrain the trace corridor to:
  - `talker_core.layer_15.output.residual_input`
  - `talker_core.layer_15.output.residual_sum`
  - `talker_core.layer_15.output`
  - `talker_core.layer_16.input`
- Interpret only the three normative `sub_talker_loss` rows:
  - `pair-sub-talker-loss`
  - `line-13-sub-talker-loss`
  - `line-4-sub-talker-loss`
- Treat `main_loss` and `combined_loss` as observational only in this task.
- Do not add a new stabilizer family in this task.

## Interpretation Contract

- Classify `converged_layer15_residual_input` if all three normative rows
  first break at `talker_core.layer_15.output.residual_input`.
- Classify `converged_layer15_residual_sum` if all three normative rows first
  break at `talker_core.layer_15.output.residual_sum`.
- Classify `converged_layer15_output_return` if all three normative rows
  first break at `talker_core.layer_15.output`.
- Classify `downstream_disagreement` if all three rows stay inside the
  committed layer-15 output corridor but do not agree on one earliest surface.
- Classify `nonlocal_regression` if any required row skips outside the
  committed corridor, reverts upstream, or stays finite.
- Keep `T217` blocked in every branch.

## Deliverables

- [ ] One diagnosis-only layer-15 residual/output-formation hook profile
  exists for the fixed T241 winner.
- [ ] One machine-readable assessment payload classifies the narrowed
  layer-15 output-formation seam.
- [ ] One truthful Hemma rerun records the converged residual/output split
  and the next diagnosis-only rule.

## Acceptance Criteria

- [ ] The task uses only the winning T237/T241 member and does not compare
  baseline or alternate caps.
- [ ] The task keeps the full Story 32 state vector fixed apart from the
  narrowed layer-15 residual/output hook profile.
- [ ] The result ends with exactly one diagnosis classification and one next
  diagnosis rule.

## Validation

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_stability_lab.py -q`
- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task243-<timestamp>-a1 --skip-build --hook-profile <post-t241-layer15-residual-output-split-profile> --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
