---
id: task-233-split-the-post-t230-layer16-input-layernorm-seam-into-normalization-internal-probes
title: Split the post-T230 layer16 input-layernorm seam into normalization-internal probes
type: task
status: in_progress
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-230-test-one-diagnosed-post-t219-micro-family-against-the-first-verified-layer16-sub-boundary.md
  - docs/backlog/tasks/task-232-make-the-story-31-lane-decision-after-the-post-t219-bounded-promotion-result.md
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

Split the post-`T230` `talker_core.layer_16.input_layernorm` seam into
normalization-internal probes so the repo can answer one narrower mechanism
question:

- does the first verified `sub_talker_loss` failure appear in the incoming
  residual tensor before normalization,
- inside the normalization arithmetic,
- or only after the normalization output is rescaled by the module output path?

## PR Scope

- Treat `T230` as closed negative evidence:
  - truthful bounded rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task230-20260318t082049z-a1`
  - all three normalization-entry variants reproduced the same failure matrix
  - no bounded entry-rescale winner exists
- Reuse the exact Story 31 lab and keep all non-diagnostic factors fixed:
  - same canonical bundle root
  - same selected source lines: `13,4`
  - same text mask policy: `text_span_only`
  - same ranked baseline stabilizer:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`
- Add one dedicated hook profile:
  - `talker_core_input_layernorm_internal`
- Implement the profile by instrumenting the actual RMSNorm arithmetic path
  instead of inferring internals from coarse module boundaries.
- The canonical internal chain to compare is:
  - `talker_core.layer_16.input_layernorm.residual_input`
  - `talker_core.layer_16.input_layernorm.fp32_input`
  - `talker_core.layer_16.input_layernorm.variance`
  - `talker_core.layer_16.input_layernorm.normalized_hidden_states`
  - `talker_core.layer_16.input_layernorm.output`
- Compare exactly these three `sub_talker_loss` cases only:
  - `pair-sub-talker-loss`
  - `line-13-sub-talker-loss`
  - `line-4-sub-talker-loss`
- Keep the stabilization family fixed to the ranked baseline only under this
  hook profile; no multi-variant family is allowed in `T233`.
- Add one focused `T233` assessment payload that identifies the earliest
  internal normalization sub-surface across the three required cases.
- If the existing `story31_sub_boundary_assessment.py` would become mixed-purpose
  or oversized, add a separate bounded `story31_input_layernorm_internal_assessment.py`
  module instead of bloating the `T229/T230` assessment path.
- Do not mix in new stabilizers, optimizer changes, bundle changes, or recovery
  launches.
- Stop when one earliest internal normalization sub-surface is identified or
  when the evidence is explicitly ambiguous.

## Implementation Status

- This task is diagnosis only.
- The planned instrumentation should follow the existing reversible wrapper
  pattern already used by the talker-core stabilization surface:
  install the internal trace wrapper only for the active probe session and
  restore the original `input_layernorm.forward` afterward.
- The planned interpretation contract is:
  - if the earliest internal surface is `residual_input` or `fp32_input`,
    the next task may test one upstream residual-amplitude family only
  - if the earliest internal surface is `variance` or
    `normalized_hidden_states`, the next task may test one
    normalization-internal numeric-safety family only
  - if the earliest internal surface is `output`, the next task may test one
    post-normalization output-scale family only
  - if the three required cases disagree, the next task remains blocked until
    the ambiguity is resolved

## Deliverables

- [ ] One normalization-internal hook profile exists for the
  `layer_16.input_layernorm` seam.
- [ ] One comparison table identifies the earliest internal normalization
  sub-surface across pair and single-row `sub_talker_loss` cases, or records
  that the evidence is still ambiguous.
- [ ] One explicit shaping rule states which follow-on mechanism family may be
  tested next.

## Acceptance Criteria

- [ ] The task tests diagnosis only; it does not add a new stabilization
  family.
- [ ] The probe holds bundle, rows, batching, mask policy, and ranked baseline
  stabilizer fixed while the normalization seam is being split.
- [ ] The probe compares only the pair and single-row `sub_talker_loss` cases;
  it does not widen back into `main_loss`, `combined_loss`, or a multi-variant
  family.
- [ ] The output identifies one earliest internal normalization sub-surface or
  explicitly documents why the evidence is ambiguous.
- [ ] The next follow-on family is constrained by this result to one diagnosed
  causal idea only.

## Validation

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_stability_lab.py -q`
- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run qwen-story31-stability-lab run --skip-build --hook-profile talker_core_input_layernorm_internal --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
