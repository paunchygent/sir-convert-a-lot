---
id: task-220-run-the-exact-original-task-101-fresh-start-control-on-the-canonical-bundle-with-only-the-t206-token-span-correction
title: Run the exact original Task 101 fresh-start control on the canonical bundle with only the T206 token-span correction
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - control
  - canonical-bundle
  - fresh-start
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the explicit full-channel masked control surface and use one bounded
control attempt to verify whether the current runtime can faithfully recreate
the documented historical Task 101 lane:

- original restored Task 101 no-projection recipe
- canonical full Task 101 pilot bundle
- only the `T206` token-span correction carried forward
- none of the later semantic-only assembly changes from `T207-T209`
- none of the Story 31 talker-core stabilization variants

This task exists so the repo stops approximating that control with mini-bundles,
selected-row probes, or Candidate 1 semantic-only assembly when the real
question is whether the original recipe can still learn on the bundle once the
audited token leakage is fixed.

## PR Scope

- Treat this as an exact control lane, not as another approximate Story 31
  micro-experiment.
- Preserve the restored no-projection fine-tuning graph from `T193`.
- Preserve the `T206` explicit position-mask correction for
  `text_embedding_mask_policy=text_span_only`.
- Explicitly exclude the later Candidate 1 semantic-only assembly work:
  - do not use `semantic_text_ids` as the trainable text-embedding lookup
    source
  - do not use the semantic-only assembly path from `T207-T208`
  - do not use the semantic-only gradient-membership success from `T209` as
    proof that this control has already been tested
- Reintroduce or expose one exact control surface that matches the original
  recipe shape:
  - full collated text-channel lookup through `text_embedding(input_ids[:, :, 0])`
  - corrected `text_embedding_mask` from `T206` still applied
  - no semantic-only scattering path
- Launch one bounded Hemma control attempt through that explicit surface and
  record whether it is a credible recreation of the documented historical
  Task 101 lane or whether contract drift remains.
- Keep the run bounded and decision-oriented:
  - fresh start from `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
  - canonical bundle input
  - detached Hemma execution
  - short bounded early window first, not an immediate full long run
- Record the exact code-path distinction in operator metadata and the
  reference ledger so future sessions cannot confuse:
  - `T206` mask-corrected original recipe
  - `T207-T209` semantic-only Candidate 1 recipe

## Deliverables

- [x] One committed control surface exists for the exact original Task 101
  recipe plus only the `T206` token-span correction.
- [x] One bounded fresh-start Hemma control attempt is run through the explicit
  full-channel masked surface.
- [x] One operator-facing result states whether that run is a credible
  recreation of the documented historical Task 101 control or still an
  approximation that cannot answer the question.

## Acceptance Criteria

- [x] The backlog records whether the attempted control actually matches the
  documented historical Task 101 launch contract.
- [x] The control lane keeps the `T206` explicit token-span correction active.
- [x] The control lane does not use the semantic-only assembly path from
  `T207-T208`.
- [x] The control lane does not apply Story 31 talker-core stabilization
  variants.
- [x] The Hemma result is recorded in the backlog/reference docs with the exact
  code-path and contract-drift caveats spelled out.
- [x] The run is not overclaimed as a valid answer to the historical
  stable-bundle-learning control question when the launch contract differs.

## Validation

- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run qwen-train launch --launch-id task220-20260317t183856z-control-a1 --pilot-bundle-root /srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1 --text-embedding-mask-policy text_span_only --text-embedding-assembly-mode full_channel_masked --max-steps 8 --gradient-accumulation-steps 4 --skip-build`
- [x] `pdm run qwen-train status --launch-root /srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task220-20260317t183856z-control-a1`

## Notes

The exact distinction this task must preserve is:

- `T206` fixed the token-span contract in dataset collation and
  `text_embedding_mask`
- `T207-T208` changed the text-embedding assembly contract itself

This control is specifically:

- yes to `T206`
- no to `T207-T208`

## Implementation Status

The exact control surface is now implemented through the canonical runtime
contract, not a one-off approximation:

- `qwen-train`, detached launch/status, resume, diagnose, capture, schedule,
  and standalone eval all now accept
  `--text-embedding-assembly-mode`
- `semantic_only` remains the default Story 30 / Candidate 1 posture
- `full_channel_masked` is the explicit T220 control posture:
  - full collated lookup through `text_embedding(input_ids[:, :, 0])`
  - corrected `text_embedding_mask` from `T206` still applied
  - no semantic-only scatter/lookup path from `T207-T209`
- runtime metadata, detached command lines, talker-runtime fingerprints, and
  standalone eval reports now persist the active assembly mode so the control
  lane cannot be confused with Candidate 1 later

`T220` no longer owns the exact historical-control rerun. That work now lives
in `T221`, because the first bounded attempt proved the launch contract still
drifted away from the documented historical Task 101 lane.

## Result

The explicit full-channel masked control surface is now delivered, but the
bounded Hemma attempt is invalid as exact historical-control evidence.

- launch id: `task220-20260317t183856z-control-a1`
- attempted posture:
  - restored no-projection Task 101 recipe
  - `text_embedding_assembly_mode=full_channel_masked`
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=4`
  - `max_steps=8`
  - current `qwen-train` detached runtime and `:latest` image
- bundle root actually used:
  - `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1`

Why this run is not a credible answer to the historical control question:

- the documented historical Task 101 contract in
  `ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md` is:
  - bundle root `qwen3-tts-swedish-task101-pilot-bundle-20260312h`
  - `batch_size=1`
  - `num_epochs=1000`
  - `max_steps=1000000`
  - `checkpoint_interval_steps=2`
  - `train_rows=8445`
- `T220` instead used:
  - the later `task-152` benchmark bundle root
  - `batch_size=8`
  - `max_steps=8`
  - the modern `qwen-train` entrypoint and current `:latest` image
- this means `T220` was still an approximation of the original recipe, not a
  faithful recreation of the documented historical launch contract

Observed result:

- `status=exited`
- `exit_code=1`
- `optimizer_step=1`
- `train_iteration=4`
- `trigger_reason=pre_clip_non_finite_gradients`
- `first_non_finite_stage=pre_clip`
- `first_non_finite_surface=text_embedding.weight.grad`
- `optimizer_step_attempted=false`
- `optimizer_step_completed=false`
- `latest_loss=13.888879776000977`
- `main_loss=11.087739944458008`
- `sub_talker_loss=9.33713436126709`
- no checkpoint minted
- no eval reached

Important read:

- forward tensors and losses stayed finite across the accumulated microbatches
- the first non-finite tensor in step forensics was `grad_norm` on
  train iteration `4`
- the attempted run failed very early
- but that result cannot be used to claim that the documented historical
  original recipe plus the `T206` mask correction fails immediately

Control implication:

- `T220` delivered the explicit `full_channel_masked` control surface
- `T220` did not deliver a credible exact historical-control answer
- the next trustworthy move is to recreate the documented historical Task 101
  launch contract under `T221` before using this branch in the Story 31
  decision tree

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
