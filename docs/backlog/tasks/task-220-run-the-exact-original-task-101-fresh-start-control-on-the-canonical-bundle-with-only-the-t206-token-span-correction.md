---
id: task-220-run-the-exact-original-task-101-fresh-start-control-on-the-canonical-bundle-with-only-the-t206-token-span-correction
title: Run the exact original Task 101 fresh-start control on the canonical bundle with only the T206 token-span correction
type: task
status: in_progress
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

Define and run the exact fresh-start control lane that answers the practical
question the repo has not yet tested cleanly:

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
- Use the canonical full Task 101 pilot bundle from `T142`, not a mini-bundle,
  row pair, or prefix slice:
  - `DEFAULT_PILOT_BUNDLE_ROOT`
  - `swedish_pilot_train`
  - `swedish_checkpoint_dev`
- Launch a fresh-start bounded Hemma control on that exact bundle/code path so
  the result is about the real recipe rather than an approximation.
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
- [ ] One bounded fresh-start Hemma control is run on the canonical full Task
  101 bundle through that exact surface.
- [ ] One operator-facing result states whether that exact control remains
  stable or fails, without conflating it with Candidate 1 or Story 31
  approximations.

## Acceptance Criteria

- [x] The control lane uses the canonical full pilot bundle from `T142`, not a
  mini-bundle or selected-row approximation.
- [x] The control lane keeps the `T206` explicit token-span correction active.
- [x] The control lane does not use the semantic-only assembly path from
  `T207-T208`.
- [x] The control lane does not apply Story 31 talker-core stabilization
  variants.
- [ ] The Hemma result is recorded in `current.md` and the Task 101 reference
  ledger with the exact code-path contract spelled out.
- [ ] The result is treated as a control answer to the stable-bundle-learning
  question, not as proof that Candidate 1 or Story 31 was correct or incorrect
  in the abstract.

## Validation

- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run <exact-control-surface> prepare`
- [ ] `pdm run <exact-control-surface> launch`
- [ ] `pdm run <exact-control-surface> status`

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

The remaining work in `T220` is now operational rather than architectural:

- prepare the bounded fresh-start control on the canonical full pilot bundle
- launch it on Hemma through the explicit `full_channel_masked` posture
- record whether that exact original-recipe control remains stable or fails

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
