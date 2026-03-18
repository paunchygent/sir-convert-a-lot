---
id: task-229-split-the-post-t219-layer16-handoff-seam-into-sub-boundary-probes
title: Split the post-T219 layer16 handoff seam into sub-boundary probes
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md
  - docs/backlog/tasks/task-228-close-the-failed-t219-layer16-handoff-family-with-one-ranked-failure-matrix.md
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

After a negative `T219` closure, split the shifted layer-16 handoff seam into
smaller sub-boundary probes so the next intervention targets one diagnosed
micro-boundary instead of another coarse family.

## PR Scope

- Activate only if `T228` concludes that no `T219` handoff variant earned
  promotion.
- Reuse the existing Story 31 tracing/probe surfaces rather than inventing a
  new proof wrapper.
- Hold the Story 32 state vector fixed while probing the shifted neighborhood
  exposed by `T219`.
- Split and compare this exact sub-boundary chain:
  - `talker_core.layer_16.mlp.down_proj`
  - `talker_core.layer_16.output`
  - `talker_core.layer_16.residual_handoff`
  - `talker_core.layer_16.input_layernorm`
- Run the same diagnosis on:
  - the surviving pair-family input
  - the corresponding single-row decomposition when needed to resolve
    ambiguity
- Produce one first-sub-boundary conclusion or one explicit ambiguity record.
- Do not test new stabilizer variants in this task.

## Deliverables

- [x] One post-`T219` sub-boundary probe profile exists for the shifted
  layer-16 handoff seam.
- [x] One comparison table identifies the earliest failing sub-boundary across
  the pair and single-row checks, or records that the evidence is still
  ambiguous.
- [x] One explicit shaping rule states which micro-family `T230` is allowed to
  test next.

## Implementation Status

- A new `talker_core_handoff_sub_boundary` hook profile now exists inside the
  existing Story 31 surface:
  `pdm run qwen-story31-stability-lab run --hook-profile talker_core_handoff_sub_boundary`.
- The committed narrowed target chain is:
  - `talker_core.layer_16.mlp.down_proj`
  - `talker_core.layer_16.output`
  - `talker_core.layer_16.residual_handoff`
  - `talker_core.layer_16.input_layernorm`
- The Story 31 runner now derives one focused `sub_boundary_assessment` from
  the ranked `T219` winner only:
  `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`.
- That assessment shapes `T230` automatically:
  - `layer_16.mlp.down_proj` -> late-MLP/down-projection family only
  - `layer_16.output` or `layer_16.residual_handoff` -> residual-side
    handoff family only
  - `layer_16.input_layernorm` -> pre-`input_layernorm`
    normalization-entry family only

## Result

- Truthful narrowed rerun:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task229-20260318t064712z-a1`
- Surface:
  `pdm run qwen-story31-stability-lab run --hook-profile talker_core_handoff_sub_boundary`
- Fixed state vector:
  - bundle root:
    `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle`
  - source lines: `13,4`
  - text embedding mask policy: `text_span_only`
  - stabilization variant:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`
- Unambiguous first sub-boundary for the target `sub_talker_loss` family:
  - pair case: `talker_core.layer_16.input_layernorm`
  - line `13`: `talker_core.layer_16.input_layernorm`
  - line `4`: `talker_core.layer_16.input_layernorm`
- The narrowed chain did not localize any earlier break at:
  - `talker_core.layer_16.mlp.down_proj`
  - `talker_core.layer_16.output`
  - `talker_core.layer_16.residual_handoff`
- `T230` is therefore constrained to one pre-`input_layernorm`
  normalization-entry micro-family only.

## Acceptance Criteria

- [x] The task does not mix diagnosis with new stabilization search.
- [x] The probe holds the same bundle, batching, seed, mask, and assembly
  posture fixed while the seam is being split.
- [x] The output identifies one earliest sub-boundary or explicitly documents
  why the evidence is ambiguous.
- [x] `T230` is constrained by this result to one diagnosed micro-family only.

## Validation

- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run qwen-story31-stability-lab --help`
- [x] `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task229-20260318t064712z-a1 --skip-build --hook-profile talker_core_handoff_sub_boundary --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
