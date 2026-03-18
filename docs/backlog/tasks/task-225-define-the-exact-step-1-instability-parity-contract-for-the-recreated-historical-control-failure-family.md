---
id: task-225-define-the-exact-step-1-instability-parity-contract-for-the-recreated-historical-control-failure-family
title: Define the exact step-1 instability parity contract for the recreated historical-control failure family
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-226-build-a-deterministic-upstream-vs-current-single-step-parity-probe-for-the-qwen-fine-tuning-path.md
  - docs/backlog/tasks/task-227-trace-and-remediate-the-first-verified-finite-to-non-finite-divergence-before-resuming-story-31-stabilizer-candidates.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - parity
  - trainer-runtime
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the exact mechanism question, comparison contract, and stop rules for
the post-`T221` parity-trace slice before the repo runs another bounded Story
31 stabilizer candidate.

This task exists because `T221` showed that the recreated historical-control
shape still fails immediately under the current trainer/runtime. Before the
repo treats another stabilizer family as the default next move, it must first
state exactly what the parity slice is allowed to answer and what evidence
counts as an implementation-side divergence.

## PR Scope

- Define the exact question for the next mechanism slice:
  - why does the current implementation fail in the recreated
    `T221` step-`1` / train-iteration-`4` window?
- Fix one deterministic comparison contract between:
  - the current patched trainer/runtime execution path
  - one repo-owned intended upstream-compatible no-projection parity path
- Fix the exact failure-family input and checkpoint list that `T226` must
  compare before the repo runs another bounded Story 31 stabilizer candidate.
- Fix the stop rules that decide whether `T227` remediation takes priority or
  whether the lane can return to `T219`.

## Deliverables

- [x] One exact parity question is documented for the post-`T221` mechanism
  slice.
- [x] One deterministic failure-family input contract is documented.
- [x] One comparison checkpoint table defines where current and intended
  upstream-compatible behavior must be compared.
- [x] One explicit rule states when `T219` may resume and when remediation must
  take priority instead.

## Acceptance Criteria

- [x] The task explicitly treats `T221` as provenance evidence that motivates
  this slice, not as a mechanism or recovery answer by itself.
- [x] The parity contract fixes the exact failure-family window at the recreated
  early-step failure rather than a looser "close enough" run.
- [x] The contract names the required parity checkpoints from batch assembly
  through the optimizer boundary.
- [x] The contract records which state-vector fields must remain fixed under
  Story 32 governance before causal claims are made.
- [x] The task leaves `T217` blocked and makes `T219` contingent on the parity
  slice outcome.

## Exact Mechanism Question

The next Story 31 mechanism question is now fixed:

- given that `T221` recreated the historical Task 101 control shape closely
  enough to fail again at optimizer step `1` / train iteration `4`, where does
  the current trainer/runtime first diverge from the intended
  upstream-compatible no-projection fine-tuning path on that exact failure
  family?

This task does **not** answer:

- whether the full bundle now trains stably end to end
- whether a Story 31 stabilizer family deserves promotion
- whether a governed recovery proof may launch

Those remain downstream questions for `T226-T227`, then `T219`, then `T217`.

## Comparison Surfaces

The parity slice must compare these two surfaces and no others:

| Surface | Meaning | Repo anchor |
| --- | --- | --- |
| current patched path | The exact current trainer/runtime path that produced the `T221` recreated-control failure | `pdm run qwen-t221-historical-control`, `scripts/sir_convert_a_lot/ml/qwen/training/t221_historical_control.py`, `scripts/devops/qwen_finetuning_patches/sft_12hz.py`, `scripts/devops/qwen_finetuning_patches/dataset.py` |
| intended upstream-compatible path | A repo-owned parity reconstruction of the no-projection fine-tuning contract restored in `T193`, stripped down to the exact early failure family with explicit checkpoint captures | `T193` no-projection contract plus the deterministic parity probe required by `T226` |

The intended path must preserve these truths:

- no active `text_projection` injection into the fine-tune graph
- no `T207-T209` semantic-only assembly
- no Story 31 talker-core stabilizer variant
- no governed proof wrapper or detached Hemma launch
- no bundle-scale recipe search

## Fixed Failure-Family Input Contract

`T226` must hold the following state vector fixed while comparing the two
paths:

- `experiment_class`: `mechanism`
- `question_answered`: first current-vs-intended divergence before the first
  non-finite boundary in the recreated `T221` failure family
- `surface_name`: one local deterministic parity probe surface introduced by
  `T226`
- `code_revision`: one single synced repo revision for both compared paths
- `image`: the same installed package set used by the recreated historical
  control lane; do not compare across different images or dependency trees
- `bundle_root`:
  `/srv/storage/sir-convert-a-lot/backups/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h`
- `sampler_or_batching_policy`: explicit row selection, not shuffled dataloader
  iteration
- `seed_or_shuffle_policy`: fixed by the explicit selected-row order below
- `batch_size`: `1`
- `gradient_accumulation_steps`: `4`
- `text_embedding_assembly_mode`: `full_channel_masked`
- `text_embedding_mask_policy`: `text_span_only`
- `stabilizer_variant`: `off`
- `max_steps`: one accumulated optimizer-step window only
- `eval_policy`: none during parity tracing
- `input_artifact_roots`:
  - the `T221` launch root
  - the surviving historical bundle root above
- `expected_promotion_target`: none; this slice is not a recovery or promotion
  gate
- `status`: local parity contract defined
- `result_interpretation`: mechanism-only evidence

The exact microbatch family is the first accumulated optimizer step recorded by
`T221`, using manifest lines in this exact order:

1. `6367`
1. `6966`
1. `4958`
1. `623`

The parity slice must treat those four rows as the canonical failure-family
input. If the compared paths are not operating on those same rows in that same
order, the parity run is invalid.

## Comparison Checkpoints

`T226` must compare current and intended behavior in this order and stop at the
first meaningful difference:

| Checkpoint | Required capture | What counts as divergence |
| --- | --- | --- |
| selected rows | manifest path, line number, row id, speaker id, text preview, codec frame count | different rows, different order, or missing provenance |
| per-item dataset output | `text_ids`, `audio_codes`, `ref_mel`, `speaker_id`, row provenance | different token ids, different audio-code shape, different `ref_mel` shape, or different provenance before collation |
| collated batch tensors | `input_ids`, `semantic_text_ids`, `semantic_text_positions`, `semantic_text_mask`, `attention_mask`, `text_embedding_mask`, `codec_embedding_mask`, `codec_ids`, `codec_mask`, `codec_0_labels` | shape/value mismatch before model forward |
| runtime posture | device, dtype, autocast/mixed precision, accumulation semantics, non-blocking transfer posture | paths run under different precision or step semantics |
| forward entry surfaces | `input_text_ids`, `input_text_embedding`, talker hidden/input surfaces when available | first tensor mismatch while values are still finite |
| loss decomposition | `main_loss`, `sub_talker_loss`, `combined_loss` | materially different finite losses before backward |
| backward pre-clip | first non-finite hook, targeted gradient probes, gradient RCA payload | different first failing tensor or different earlier finite gradients |
| clip boundary | `first_non_finite_stage`, `grad_norm`, clip result classification | different finite-to-non-finite transition at clip time |
| optimizer preconditions | `optimizer_step_attempted`, `optimizer_step_completed`, parameter/optimizer-state finiteness | one path reaches the step boundary under different finite preconditions |

The first checkpoint where the compared paths differ becomes the only
mechanism answer that `T227` is allowed to act on.

## Stop Rules

- If row selection, dataset output, or collated tensors differ, stop and treat
  the parity surface as invalid. Do not interpret any downstream forward or
  backward differences.
- If the first divergence appears while all compared tensors are still finite,
  treat that as a current trainer/runtime divergence and move to `T227`
  remediation before `T219`.
- If no meaningful divergence is found before the first non-finite boundary,
  record an explicit no-divergence result and return the lane to `T219`.
- If the only divergence is at the clip/optimizer boundary while earlier
  tensors match, treat that as a trainer/runtime boundary divergence and move
  to `T227`.
- `T217` remains blocked throughout this parity slice.

## Current Implementation State

- `T225` now fixes the exact post-`T221` parity contract for Story 31.
- `T226` is now the immediate mechanism implementation task:
  it must build the deterministic local parity probe against this contract.
- `T227` is now the first allowed remediation task:
  it may only patch the first checkpoint divergence that `T226` verifies.
- `T219` remains available as the next bounded stabilizer family only if this
  parity slice closes without surfacing a higher-priority trainer/runtime
  divergence.

## Validation

- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
