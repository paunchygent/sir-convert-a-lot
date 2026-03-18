---
id: task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams
title: Implement the third bounded Story 31 layer16 handoff candidate for the shifted seams
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-218-implement-the-second-bounded-story31-late-middle-attenuation-candidate-for-the-layer16-layer15-seams.md
  - docs/backlog/tasks/task-225-define-the-exact-step-1-instability-parity-contract-for-the-recreated-historical-control-failure-family.md
  - docs/backlog/tasks/task-226-build-a-deterministic-upstream-vs-current-single-step-parity-probe-for-the-qwen-fine-tuning-path.md
  - docs/backlog/tasks/task-227-trace-and-remediate-the-first-verified-finite-to-non-finite-divergence-before-resuming-story-31-stabilizer-candidates.md
  - docs/backlog/tasks/task-228-close-the-failed-t219-layer16-handoff-family-with-one-ranked-failure-matrix.md
  - docs/backlog/tasks/task-229-split-the-post-t219-layer16-handoff-seam-into-sub-boundary-probes.md
  - docs/backlog/tasks/task-230-test-one-diagnosed-post-t219-micro-family-against-the-first-verified-layer16-sub-boundary.md
  - docs/backlog/tasks/task-231-pin-the-post-t219-bounded-fresh-start-promotion-contract-before-any-governed-proof.md
  - docs/backlog/tasks/task-232-make-the-story-31-lane-decision-after-the-post-t219-bounded-promotion-result.md
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

Implement the third bounded Story 31 exploration candidate after `T218` proved
that the second family could move the fresh-start failure neighborhood away
from the original `T214` seams, but still could not keep the exact target
surfaces finite.

This task was temporarily gated by the `T225-T227` parity package. That gate
closed cleanly, and `T219` then became the next bounded Story 31 mechanism
slice.

This candidate should now target the shifted pair-family neighborhood exposed
by the stronger `T218` evidence:

- `talker_core.layer_16.output` for pair `main_loss` / `combined_loss`
- `talker_core.layer_16.input_layernorm` for the most improved
  `sub_talker_loss` pair posture
- the still-surviving `talker_core.layer_16.mlp.gated_product` path on
  `sub_talker_loss`

## Candidate Shape

Treat the next candidate as one bounded layer-16 handoff family, not a new
proof stack.

The family should:

- keep the moderate `T218` posture as the preferred base ingredient:
  - `layer16_gated_fp32_rescale_1e3_layer15_out_0p5`
- add one small stabilization at the layer-16 output handoff before the next
  layer consumes that stream
- bias toward output/residual-handoff attenuation or bounded rescaling rather
  than another clamp-only retry
- preserve direct visibility into whether `sub_talker_loss` falls back to the
  old `layer_16.mlp.gated_product` seam
- expose at most `2-3` variants so the existing Story 31 lab still compares
  one bounded family under a single output root

## Recorded Result

`T219` is now recorded as negative bounded mechanism evidence.

- The layer-16 handoff family is now grounded in the recovered Hemma artifact
  root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task219-20260317t180700z-a1`
- The surviving result artifacts are:
  - `results.json`
  - `results.md`
  - per-variant reports under `variant-reports/`
- No `T219` variant earned promotion from the existing Story 31 local gate.
- No separate `gate.json` artifact survived, but every recorded matrix row
  remained non-finite, so there is no truthful basis for promotion.
- Because no candidate promoted, Story 31 now advances to `T228-T232`
  instead of `T217`.

## PR Scope

- Reuse the existing Story 31 exploration vehicle:
  - `pdm run qwen-story31-stability-lab run`
  - `pdm run qwen-story31-stability-lab gate`
- Reuse the now-closed `T225-T226` parity result as the mechanism evidence
  that no higher-priority trainer/runtime remediation displaced this slice.
- Reuse the exact failing-row pair, hook profile, and promotion rule from
  `T215`.
- Extend the existing stabilization module rather than introducing a new
  harness.
- Keep the intervention bounded and local:
  - do not reopen replay framing
  - do not change text semantics
  - do not widen into optimizer-regime changes
  - do not open Candidate `3`
- Record the result as one compact Story 31 matrix plus promotion-gate outcome.
- Backfill the negative result into Story 31 operator docs so downstream work
  can proceed to `T228-T232`.

## Deliverables

- [x] One third bounded Story 31 stabilization family exists for the shifted
  layer-16 handoff neighborhood.
- [x] The existing lab can run that family without a new proof wrapper.
- [x] The existing gate can judge whether the family earns promotion.
- [x] Operator docs now record `T219` as completed negative evidence and
  route follow-on work through `T228-T232`.

## Acceptance Criteria

- [x] The new family is explicitly shaped by the negative-but-shifted evidence
  from `task218-20260317t173122z-a1`.
- [x] The intervention targets the shifted `layer_16.output` /
  `layer_16.input_layernorm` handoff while still watching the surviving
  `sub_talker_loss` gated-product fallback.
- [x] The implementation reuses the current Story 31 lab and gate unchanged
  aside from variant registration.
- [x] `T217` remains blocked unless one of the new variants actually passes the
  existing promotion gate.

## Validation

- [x] `pdm run run-hemma -- cat /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task219-20260317t180700z-a1/results.json`
- [x] `pdm run run-hemma -- cat /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task219-20260317t180700z-a1/results.md`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
