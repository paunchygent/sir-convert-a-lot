---
id: task-218-implement-the-second-bounded-story31-late-middle-attenuation-candidate-for-the-layer16-layer15-seams
title: Implement the second bounded Story 31 late-middle attenuation candidate for the layer16 layer15 seams
type: task
status: proposed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - stabilization
  - talker-core
  - exploration
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the second bounded Story 31 exploration candidate after the first
matrix showed that `off`, `layer16_gated_fp32`, and
`layer16_gated_fp32_clamp_1e4` all preserved the same fresh-start failure
family.

This candidate must stay solution-oriented and target both surviving seams
together:

- `talker_core.layer_16.mlp.gated_product` for pair `main_loss` /
  `combined_loss`
- `talker_core.layer_15.output` for pair `sub_talker_loss`

## Candidate Shape

Treat the next candidate as one bounded late-middle attenuation family, not a
new proof program.

The family should:

- keep the existing `layer16_gated_fp32` posture as a base ingredient
- replace or augment the failed fixed clamp with a bounded amplitude control
  that is more truthful to the surviving seam than another looser clamp-only
  retry
- add one small downstream attenuation at the layer `15` / layer `16` output
  seam so the candidate addresses the `sub_talker_loss` branch directly

The intended first implementation posture is:

- normalize or cap the layer `16` gated-product activation in a scale-aware
  way before `down_proj`
- add one bounded late-middle output attenuation around the layer `15` output
  seam
- expose at most `2-3` numeric variants inside this one family so the existing
  Story 31 lab can compare them in one matrix run

## PR Scope

- Reuse the existing Story 31 exploration vehicle:
  - `pdm run qwen-story31-stability-lab run`
  - `pdm run qwen-story31-stability-lab gate`
- Reuse the exact failing-row pair, hook profile, and promotion rule from
  `T215`.
- Extend the existing stabilization module rather than introducing a second
  experimental harness:
  - `sft_12hz_talker_core_stabilization.py`
  - `sft_12hz_forward_surfaces.py`
- Keep the intervention bounded and local:
  - do not reopen replay framing
  - do not change text-token semantics
  - do not broaden into optimizer-regime changes
  - do not jump to Candidate `3`
- Record the second candidate as one compact Story 31 matrix result, not as a
  new proof package.

## Deliverables

- [ ] One second bounded Story 31 stabilization family exists for the
  layer-16 gated-product / layer-15 output neighborhood.
- [ ] The existing lab can run that family without any new proof wrapper.
- [ ] The existing gate can judge whether the new family earns promotion.
- [ ] Operator docs record that this is the active next exploration slice.

## Acceptance Criteria

- [ ] The new family is explicitly shaped by the negative evidence from
  `task215-20260317t160500z-a2`.
- [ ] The intervention addresses both surviving seams together rather than
  retesting only the layer-16 gated-product clamp idea.
- [ ] The implementation reuses the current Story 31 lab and gate unchanged
  aside from variant registration.
- [ ] `T217` remains blocked unless one of the new variants actually passes the
  existing promotion gate.

## Validation

- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run qwen-story31-stability-lab run --skip-build`
- [ ] `pdm run qwen-story31-stability-lab gate --output-root <lab-output-root>`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
