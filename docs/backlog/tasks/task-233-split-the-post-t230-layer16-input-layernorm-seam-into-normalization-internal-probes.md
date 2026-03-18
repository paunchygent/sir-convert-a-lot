---
id: 'task-233-split-the-post-t230-layer16-input-layernorm-seam-into-normalization-internal-probes'
title: 'Split the post-T230 layer16 input-layernorm seam into normalization-internal probes'
type: 'task'
status: 'proposed'
priority: 'high'
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
- Add one tighter hook profile that splits `talker_core.layer_16.input_layernorm`
  into internal sub-surfaces only, for example:
  - pre-normalization input tensor
  - post-normalization internal activation
  - post-scale module output
- Compare the pair case and both single-row `sub_talker_loss` cases only.
- Do not mix in new stabilizers, optimizer changes, bundle changes, or recovery
  launches.
- Stop when one earliest internal normalization sub-surface is identified or
  when the evidence is explicitly ambiguous.

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
- [ ] The output identifies one earliest internal normalization sub-surface or
  explicitly documents why the evidence is ambiguous.
- [ ] The next follow-on family is constrained by this result to one diagnosed
  causal idea only.

## Validation

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
