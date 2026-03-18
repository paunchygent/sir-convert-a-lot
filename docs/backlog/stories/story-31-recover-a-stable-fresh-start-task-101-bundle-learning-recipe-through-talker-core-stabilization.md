---
id: story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization
title: Recover a stable fresh-start Task 101 bundle-learning recipe through talker-core stabilization
type: story
status: in_progress
priority: high
created: '2026-03-17'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/tasks/task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-218-implement-the-second-bounded-story31-late-middle-attenuation-candidate-for-the-layer16-layer15-seams.md
  - docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md
  - docs/backlog/tasks/task-220-run-the-exact-original-task-101-fresh-start-control-on-the-canonical-bundle-with-only-the-t206-token-span-correction.md
  - docs/backlog/tasks/task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane.md
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

Under Story 32 experiment governance, this story is the `mechanism` lane. It
does not answer the provenance question on its own, and it does not authorize
the governed recovery proof until one mechanism candidate is promoted.

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
- Before another bounded stabilizer family is treated as the default next move,
  rule out current trainer/runtime divergence as the confounder behind the
  recreated-control and immediate fresh-start failure family.
- Keep the preserved no-projection fine-tune graph and clean text semantics
  fixed while we test the first bounded talker-core stabilization surface.
- Keep Candidate `3` available only as a later contingency if the first
  talker-core stabilization lane fails its smallest-signal local gate or its
  first short fresh-start Hemma proof.
- Use the Story 32 matrix when interpreting the related surfaces:
  - `T221` is the provenance surface
  - `T225-T227` are the next mechanism slice package
  - `T219` is now recorded as completed negative bounded stabilizer evidence
  - `T228-T243` now define the active next mechanism ladder
  - `T217` is the blocked recovery surface

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
- [x] One exact-control runtime surface exists for the original restored
  Task 101 recipe with only the `T206` token-span correction, so the repo can
  answer the practical full-bundle control question without approximation.
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
1. `docs/backlog/tasks/task-220-run-the-exact-original-task-101-fresh-start-control-on-the-canonical-bundle-with-only-the-t206-token-span-correction.md`
1. `docs/backlog/tasks/task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane.md`
1. `docs/backlog/tasks/task-225-define-the-exact-step-1-instability-parity-contract-for-the-recreated-historical-control-failure-family.md`
1. `docs/backlog/tasks/task-226-build-a-deterministic-upstream-vs-current-single-step-parity-probe-for-the-qwen-fine-tuning-path.md`
1. `docs/backlog/tasks/task-227-trace-and-remediate-the-first-verified-finite-to-non-finite-divergence-before-resuming-story-31-stabilizer-candidates.md`
1. `docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md`
1. `docs/backlog/tasks/task-228-close-the-failed-t219-layer16-handoff-family-with-one-ranked-failure-matrix.md`
1. `docs/backlog/tasks/task-229-split-the-post-t219-layer16-handoff-seam-into-sub-boundary-probes.md`
1. `docs/backlog/tasks/task-230-test-one-diagnosed-post-t219-micro-family-against-the-first-verified-layer16-sub-boundary.md`
1. `docs/backlog/tasks/task-231-pin-the-post-t219-bounded-fresh-start-promotion-contract-before-any-governed-proof.md`
1. `docs/backlog/tasks/task-232-make-the-story-31-lane-decision-after-the-post-t219-bounded-promotion-result.md`
1. `docs/backlog/tasks/task-233-split-the-post-t230-layer16-input-layernorm-seam-into-normalization-internal-probes.md`
1. `docs/backlog/tasks/task-234-test-one-diagnosed-post-t233-output-scale-micro-family-against-the-first-verified-layer16-input-layernorm-output-surface.md`
1. `docs/backlog/tasks/task-235-resolve-the-post-t234-sub-talker-loss-disagreement-between-layer16-input-layernorm-and-layer15-output.md`
1. `docs/backlog/tasks/task-236-resolve-the-post-t235-line4-row-local-outlier-before-claiming-a-generic-layer15-output-seam.md`
1. `docs/backlog/tasks/task-237-test-one-post-t236-micro-family-against-the-first-verified-dominant-sub-talker-outlier-seam.md`
1. `docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md`

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized

## Current State

- Story 32 now governs how the related surfaces are interpreted:
  - `T221` is provenance evidence for Story 31 decisions
  - `T225` is complete as the exact parity contract
- `T226` is now complete as the committed local parity-probe surface
- the live in-image historical-bundle run under
  `task226-20260317t224307Z` found no meaningful checkpoint divergence
  between the current and intended paths
  - `T219` then closed as negative bounded evidence under
    `task219-20260317t180700z-a1`
  - `T228` is now complete as the truthful ranked closure of that family
  - `T227` is now contingent only if a later verified trainer/runtime
    divergence appears
  - `T217` is the blocked recovery proof lane
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
- `T220` is now complete as control-surface delivery but invalid as exact
  historical-control evidence:
  - the explicit `full_channel_masked` runtime surface is now implemented
  - the bounded Hemma attempt used the later `task-152` benchmark bundle,
    `batch_size=8`, and the current `qwen-train` launch posture
  - it therefore does not answer the documented historical Task 101 question
- `T221` is now complete as negative recreated-control evidence:
  - this remains provenance evidence for Story 31 decisions, not a Story 31
    mechanism or recovery proof
  - the dedicated committed control surface is:
    `pdm run qwen-t221-historical-control <launch|status|stop>`
  - it validated the surviving historical bundle under
    `/srv/storage/sir-convert-a-lot/backups/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h`
    with documented counts `8445` train / `8` eval and wrote an explicit
    `contract-diff` artifact before launch
  - live run:
    `task221-20260317t193125z-a1`
  - recreated posture:
    - `batch_size=1`
    - `gradient_accumulation_steps=4`
    - `text_embedding_assembly_mode=full_channel_masked`
    - `text_embedding_mask_policy=text_span_only`
    - historical `task100` image
  - result:
    - failed at `current_optimizer_step=1`
    - failed at `current_train_iteration=4`
    - `trigger_reason=pre_clip_non_finite_gradients`
    - `first_non_finite_surface=text_embedding.weight.grad`
    - no checkpoint minted
    - no eval executed
  - interpretation:
    - immediate instability is not unique to Candidate 1 semantic-only assembly
    - the recreated original-recipe shape plus only the `T206` token fix still
      fails immediately under the current trainer/runtime
    - this is stronger evidence than `T220`, but it is still not byte-for-byte
      March 13 attribution because the run uses the current trainer module and
      current sampler/runtime posture
- `T225` is now complete as the exact parity contract:
  - the recreated step-`1` / iteration-`4` failure family is now fixed as the
    canonical comparison window
  - the exact checkpoint list and state-vector invariants are now documented
    before more bounded stabilizer claims are made
- `T226` is now complete as the committed local parity-probe surface:
  - the public command is `pdm run qwen-story31-parity-probe run`
  - it writes one compact comparison artifact set under
    `build/verification/qwen-story31-parity-probe/`
  - it compares the real `execute_train_iteration` window against a
    reconstructed shared-forward optimizer-boundary window on the exact
    `T225` microbatch family
- the live in-image historical-bundle run under
  `task226-20260317t224307Z` then matched the current and intended paths at
  every compared checkpoint and closed with:
  - `first_divergence_checkpoint = null`
  - `first_divergence_classification = no_meaningful_divergence_found`
  - `recommended_next_step = return_to_t219_if_no_higher_priority_runtime_bug_is_found`
- `T227` therefore remains contingent rather than becoming the active
  remediation slice
- `T219` is now recorded as completed negative evidence:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task219-20260317t180700z-a1`
  - the layer-16 handoff family did not earn promotion
- `T228` is now complete as the ranked closure of that family:
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5` is the
    strongest negative signal
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p25_layer15_out_0p5` is the
    second-best negative signal
  - `off` remains the baseline negative family
- `T229` is now complete as the narrowed sub-boundary rerun:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task229-20260318t064712z-a1`
  - the target `sub_talker_loss` family localizes consistently to
    `talker_core.layer_16.input_layernorm`
  - Story 31 is therefore constrained to one pre-`input_layernorm`
    normalization-entry micro-family only
- `T230` is now complete as a negative bounded rerun:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task230-20260318t082049z-a1`
  - both entry-rescale variants reproduced the same failure matrix as the
    ranked baseline
  - no local winner earned promotion consideration
- `T231` is now complete as the explicit no-winner promotion decision:
  - no bounded fresh-start promotion contract is minted
  - `T217` remains blocked
- `T232` is now complete as the lane decision:
  - Story 31 stays in `mechanism`
  - the failed normalization-entry family becomes historical mechanism
    evidence only
  - `T233` opens the next localized question
- `T233` is now complete as the normalization-internal rerun:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task233-20260318t112544z-a1`
  - pair and both single-row `sub_talker_loss` cases all first broke at
    `talker_core.layer_16.input_layernorm.output`
  - the broader nine-row matrix also first broke at
    `talker_core.layer_16.input_layernorm.output`
  - the next mechanism family is therefore constrained to one
    post-normalization output-scale family only
- `T234` is now complete as the bounded post-normalization output-scale rerun:
  - output root:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task234-20260318t123644z-a1`
  - no variant stayed finite and no variant earned promotion
  - the strongest `0p5` member shifted `pair-sub-talker-loss` and
    `line-13-sub-talker-loss` downstream to `talker_core.layer_15.output`
  - `line-4-sub-talker-loss` still first broke at
    `talker_core.layer_16.input_layernorm`
  - all `main_loss` and `combined_loss` cases still first broke at
    `talker_core.layer_16.output`
- `T235` is now complete under `task235-20260318t140352z-a1`:
  - the mixed `sub_talker_loss` result is repeatable under the strongest
    `T234` member
  - `pair-sub-talker-loss` and `line-13-sub-talker-loss` still first broke at
    `talker_core.layer_15.output`
  - `line-4-sub-talker-loss` still first broke at
    `talker_core.layer_16.input_layernorm`
- `T236` is now complete under `task236-20260318t145434z-a1`:
  - the repeatable outlier is a genuine row-local seam difference
  - `pair-sub-talker-loss` and `line-13-sub-talker-loss` stayed at
    `talker_core.layer_15.output`
  - `line-4-sub-talker-loss` stayed at
    `talker_core.layer_16.input_layernorm.output`
- the active follow-on slice is now:
  - `T237`: complete; fp32-output-cap `1e3` converged the normative
    `sub_talker_loss` rows downstream
  - `T240`: complete; `task240-20260318t165458z-a1` fixed the converged seam
    at `talker_core.layer_15.output`
  - `T241`: complete; `task241-20260318t175714z-a1` kept all three normative
    `sub_talker_loss` rows at `talker_core.layer_15.output`
  - `T243`: split the post-`T241` layer-15 residual/output-formation seam in
    the official `Qwen3TTSTalkerDecoderLayer.forward` residual path
- `T217` remains the blocked recovery lane:
  it should not launch until the mechanism lane produces a promoted candidate.
- The lab reuses the exact failing-row backward-lineage kernel and writes one
  compact matrix run under a single output root instead of a proof package per
  experiment.
