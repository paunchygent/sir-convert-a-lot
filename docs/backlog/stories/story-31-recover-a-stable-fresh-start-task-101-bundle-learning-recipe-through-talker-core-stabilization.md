---
id: story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization
title: Recover a stable fresh-start Task 101 bundle-learning recipe through talker-core stabilization
type: story
status: in_progress
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/tasks/task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-218-implement-the-second-bounded-story31-late-middle-attenuation-candidate-for-the-layer16-layer15-seams.md
  - docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - stabilization
  - talker-core
  - fresh-start
---

Implementation slice with acceptance-driven scope.

## Objective

Recover a working fresh-start Task 101 bundle-learning recipe on the canonical
bundle after the replay-family and text-span-family RCA ladders have both been
exhausted.

The new primary target is no longer "save the `1406` replay lane." It is:

- keep the semantically clean Candidate 1 token/text contract,
- stop centering replay as the main explanation,
- target the newly localized talker-core late-middle failure seam directly,
- and judge success by fresh-start learning stability on the bundle.

This story is intentionally split into two lanes:

1. `Exploration lane`
   - fast, cheap, repeatable
   - no proof package per hypothesis
   - compact result ledger and promotion criteria
1. `Governed proof lane`
   - only for the first candidate that earns promotion from the exploration
     lane
   - reuses the existing detached Hemma surfaces instead of inventing a new
     proof stack

## Scope

- Treat Story 29 as closed bounded replay evidence:
  - do not reopen replay-only RCA variants
  - do not spend the next story on rescue from inherited `1406` state
- Treat Story 30 Candidate 1 as a delivered correctness baseline, not the
  final working recipe:
  - semantic-only batch contract from `T207`
  - semantic-only train/eval assembly from `T208`
  - semantic-only gradient-membership proof from `T209`
- Treat `T211-T214` as the decisive fresh-start discovery chain:
  - `T211`: fresh-start failure at optimizer step `1`
  - `T212`: earliest instrumented non-finite hook at `input_embeddings`
  - `T213`: talker-core localization at
    `layer_16.post_attention_layernorm` / `layer_15.output`
  - `T214`: smaller split showing:
    - pair `main_loss` / `combined_loss` first break at
      `talker_core.layer_16.mlp.gated_product`
    - pair `sub_talker_loss` first breaks at `talker_core.layer_15.output`
- Open a solution-oriented lane that targets the late-middle talker-core seam
  directly instead of adding more proof-only discovery work.
- Keep the preserved no-projection fine-tune graph and clean text semantics
  fixed while we test the first bounded talker-core stabilization surface.
- Keep Candidate `3` available only as a later contingency if the first
  talker-core stabilization lane fails its smallest-signal local gate or its
  first short fresh-start Hemma proof.

## Reuse Plan

Build the exploration vehicle by reusing the pieces that are already good:

- reuse [story30_freshstart_bundle.py](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/ml/qwen/training/story30_freshstart_bundle.py)
  for tiny truthful train-slice materialization
- reuse [story30_backward_lineage_bundle.py](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/ml/qwen/training/story30_backward_lineage_bundle.py)
  when exact selected failing rows are the sharper input than a prefix slice
- reuse [backward_lineage_probe.py](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/ml/qwen/training/backward_lineage_probe.py)
  as the fastest existing forward/backward experiment kernel on the real lane
- reuse [story30_backward_lineage_hooks.py](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/ml/qwen/training/story30_backward_lineage_hooks.py)
  and [sft_12hz_talker_core_trace.py](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/devops/qwen_finetuning_patches/sft_12hz_talker_core_trace.py)
  for hook profiles and layer-target resolution
- reuse [story30_freshstart_runtime.py](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/ml/qwen/training/story30_freshstart_runtime.py)
  plus `qwen-train launch/status` only when a candidate is promoted
- reuse [story30_backward_lineage_detached.py](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/ml/qwen/training/story30_backward_lineage_detached.py)
  only for long-running or detached evidence that outlives the local session

Avoid reusing the heavy parts for exploration:

- do not create `plan.md` / `checklist.md` / proof-id packages for each matrix
  cell
- do not create a new detached wrapper per stabilization idea
- do not require one new backlog task per micro-experiment

## Acceptance Criteria

- [ ] `T214` is recorded as closed discovery evidence rather than left as the
  active explanation lane.
- [x] One lightweight Story 31 exploration surface exists for rapid matrix
  iteration on the late-middle talker-core seam without a proof package per
  hypothesis.
- [x] One bounded talker-core stabilization surface exists that targets the
  late-middle seam exposed by `T214` without reopening replay framing or
  altering the clean text-token semantics.
- [x] One smallest-signal local promotion gate exists that tests the exact
  fresh-start failure family before any governed Hemma run.
- [ ] Only the first promoted candidate gets a short governed fresh-start
  Hemma proof.
- [ ] The restart target remains blocked until the stabilization lane records a
  truthful success surface that justifies a larger clean-start proof.

## Test Requirements

- [ ] The exploration lane must produce one compact, comparable results table
  rather than scattered proof artifacts.
- [ ] The first promoted stabilization lane must pass a local finiteness gate
  on the exact fresh-start failure family before Hemma launch.
- [ ] The first Hemma proof must be a short fresh-start governed run, not a
  replay, resume, or restart authorization.
- [ ] Docs/task indexing must remain green after the story and task package
  lands.

## Done Definition

Done when the repo has replaced replay-centered reasoning with one explicit
talker-core stabilization lane, has one reusable exploration harness, one
local promotion gate, and one short fresh-start Hemma proof task for the first
promoted candidate, and records that stable clean-start bundle learning is now
the governing success criterion for future restart work.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md`
1. `docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md`
1. `docs/backlog/tasks/task-218-implement-the-second-bounded-story31-late-middle-attenuation-candidate-for-the-layer16-layer15-seams.md`
1. `docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md`
1. `docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md`

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized

## Current State

- `T216` is now complete.
- The first bounded Story 31 stabilization posture is available through:
  - `off`
  - `layer16_gated_fp32`
  - `layer16_gated_fp32_clamp_1e4`
- The reusable exploration surface is:
  - `pdm run qwen-story31-stability-lab run`
- `T215` is now complete.
- The mandatory local promotion command is:
  - `pdm run qwen-story31-stability-lab gate --output-root <lab-output-root>`
- The gate consumes the existing `results.json` artifact and writes:
  - `gate.json`
  - `gate.md`
- Promotion currently targets the first bounded candidate:
  - baseline variant: `off`
  - candidate variant: `layer16_gated_fp32`
- The first real Hemma matrix and gate run under
  `task215-20260317t160500z-a2` is now recorded:
  - baseline `off` reproduced the exact `T214` pair-family seams
  - `layer16_gated_fp32` did not earn promotion
  - `layer16_gated_fp32_clamp_1e4` also reproduced the same pair-family seams
- `T218` is now complete as negative exploration evidence:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task218-20260317t173122z-a1`
  - both bounded late-middle attenuation variants changed the pair-family
    neighborhood
  - neither candidate kept the exact target seams finite, so both failed the
    existing promotion gate
- `T219` is now the active next exploration slice:
  - keep the moderate `T218` posture as the preferred base ingredient
  - target the shifted `layer_16.output` / `layer_16.input_layernorm`
    handoff neighborhood
  - keep visibility on the surviving `sub_talker_loss`
    `layer_16.mlp.gated_product` fallback
- `T217` remains blocked until a later exploration candidate passes on the
  exact fresh-start pair family.
- The lab reuses the exact failing-row backward-lineage kernel and writes one
  compact matrix run under a single output root instead of a proof package per
  experiment.
- The next active slice inside Story 31 is another bounded exploration
  candidate around the shifted layer-16 handoff neighborhood, not a governed
  Hemma proof yet.
