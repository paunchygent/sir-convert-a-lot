---
id: task-243-split-the-post-t241-layer15-residual-output-formation-seam-before-any-new-stabilizer-family
title: Split the post-T241 layer15 residual-output formation seam before any new stabilizer family
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-241-split-the-post-t240-layer15-output-seam-into-residual-output-formation-sub-boundaries-before-any-new-stabilizer-family.md
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

Split the post-`T241` converged `layer_15.output` seam into residual-output
formation sub-boundaries so Story 31 can determine whether the first
converged `sub_talker_loss` break under the fixed T237/T241 winner occurs in
the exact residual/output path implemented by
`Qwen3TTSTalkerDecoderLayer.forward` in the official upstream
`QwenLM/Qwen3-TTS` source:

- the saved residual addend (`residual = hidden_states`) before
  `post_attention_layernorm`,
- the residual-add sum (`residual + hidden_states`) after the MLP return path,
- or the final returned `talker_core.layer_15.output` tensor

before any new stabilizer family is considered.

## PR Scope

- Treat `T241` as closed truth:
  - truthful bounded rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task241-20260318t175714z-a1`
  - resolved classification:
    `converged_layer15_output_residual`
  - fixed winner only:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
  - dominant seam:
    `talker_core.layer_15.output`
- Anchor this task to the real upstream talker decoder path under
  `qwen_tts/core/models/modeling_qwen3_tts.py`:
  - `residual = hidden_states`
  - `hidden_states = self.post_attention_layernorm(hidden_states)`
  - `hidden_states = self.mlp(hidden_states)`
  - `hidden_states = residual + hidden_states`
  - `outputs = (hidden_states,)`
- Treat the MLP return path as already narrowed by `T241`:
  - `Qwen3TTSTalkerTextMLP.forward(...)` returns `down_proj` directly
  - `T241` already proved the converged seam does not first break at
    `talker_core.layer_15.mlp.down_proj`
  - `T243` therefore focuses on the saved residual addend, the residual sum,
    and the returned output tensor rather than reopening the MLP branch
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
    - the saved residual addend before `post_attention_layernorm`
  - `talker_core.layer_15.output.residual_sum`
    - the exact `residual + hidden_states` tensor after the MLP return path
  - `talker_core.layer_15.output`
    - the final returned `hidden_states` tensor emitted from the layer
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

## Result

- Live Hemma rerun:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task243-20260318t190832z-a1`
- Fixed variant:
  `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
- Resolved classification:
  `converged_layer15_output_return`
- Dominant surface:
  `talker_core.layer_15.output`
- Normative `sub_talker_loss` cases:
  - `pair-sub-talker-loss` first broke at `talker_core.layer_15.output`
  - `line-13-sub-talker-loss` first broke at `talker_core.layer_15.output`
  - `line-4-sub-talker-loss` first broke at `talker_core.layer_15.output`
- Interpretation:
  - the converged seam does not first break at the saved residual addend
  - the converged seam does not first break at the raw residual sum
  - the next truthful diagnosis-only slice is therefore `T244`, which must
    split the post-sum return path itself before any new stabilizer family
    is considered

## Deliverables

- [x] One diagnosis-only layer-15 residual/output-formation hook profile
  exists for the fixed T241 winner.
- [x] One machine-readable assessment payload classifies the narrowed
  layer-15 output-formation seam using the upstream-anchored residual-input /
  residual-sum / output-return semantics.
- [x] One truthful Hemma rerun records the converged residual/output split
  and the next diagnosis-only rule.

## Acceptance Criteria

- [x] The task uses only the winning T237/T241 member and does not compare
  baseline or alternate caps.
- [x] The task keeps the full Story 32 state vector fixed apart from the
  narrowed layer-15 residual/output hook profile.
- [x] The result ends with exactly one diagnosis classification and one next
  diagnosis rule.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_backward_lineage_hooks.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_layer15_residual_output_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_stability_lab.py -q`
- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run typecheck-all`
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run qwen-stability-lab --help`
- [x] `pdm run run-hemma -- pdm run qwen-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task243-20260318t190832z-a1 --skip-build --hook-profile talker_core_post_t241_layer15_residual_output --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
