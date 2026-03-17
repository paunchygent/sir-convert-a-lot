---
id: task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane
title: Recreate the documented historical Task 101 control contract before judging the T206-only fresh-start lane
type: task
status: in_progress
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-220-run-the-exact-original-task-101-fresh-start-control-on-the-canonical-bundle-with-only-the-t206-token-span-correction.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - control
  - historical-contract
  - fresh-start
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Recreate the documented historical Task 101 fresh-start launch contract as
faithfully as the repo can now support, then run the `T206`-only control on
that recreated contract before drawing any conclusion about whether the
original recipe still learns once the token-span bug is fixed.

## PR Scope

- Treat the docs-as-code historical launch contract as normative:
  - [ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md:344](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md:344)
  - launch id `task101-20260313t102144z`
  - bundle root `qwen3-tts-swedish-task101-pilot-bundle-20260312h`
  - `batch_size=1`
  - `num_epochs=1000`
  - `max_steps=1000000`
  - `checkpoint_interval_steps=2`
  - `train_rows=8445`
  - `eval_rows=8`
- Do not let later RCA/recovery artifacts silently overwrite that historical
  question.
- Reconcile the historical docs contract with the surviving legacy launch root
  and current runnable surfaces:
  - [ref-task101-training-eval-pilot-progress-2026-03-15.md:241](/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md:241)
  - `/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot/task101-20260313t102144z`
- Make the minimum committed runtime adjustment needed so the repo can launch a
  faithful historical-contract control instead of forcing the later
  `task-152` benchmark bundle or the current default launch posture.
- Keep the code-path distinction explicit:
  - yes to `T206` token-span correction
  - no to `T207-T209` semantic-only assembly
  - no to Story 31 stabilizers
- Run one bounded fresh-start Hemma control only after the contract is proven
  faithful enough to answer the question.

## Deliverables

- [x] One written contract diff exists between:
  - the documented historical Task 101 launch
  - the invalid `T220` approximation
  - the corrected `T221` recreation
- [x] One committed launch surface can target the historical bundle/layout
  without silently falling back to the later `task-152` benchmark lane.
- [ ] One bounded Hemma control run exists whose result is credible evidence
  about the historical original-recipe + `T206` question.

## Acceptance Criteria

- [x] The recreated control uses the documented historical Task 101 launch
  contract as its source of truth, not the later RCA/recovery lane.
- [x] The recreated control keeps:
  - restored no-projection graph from `T193`
  - `text_embedding_assembly_mode=full_channel_masked`
  - `text_embedding_mask_policy=text_span_only`
- [x] The recreated control does not use:
  - `T207-T209` semantic-only assembly
  - Story 31 stabilization variants
  - the `task-152` 128-row benchmark bundle as a silent substitute for the
    historical full-bundle contract
- [ ] The backlog/reference docs explicitly state whether the recreated run is
  now credible exact-control evidence.
- [ ] Only after that recreation succeeds should the run result be used to
  support or reject the “original recipe + token fix” branch in Story 31.

## Current Implementation State

- Implemented committed surface:
  - `pdm run qwen-t221-historical-control launch`
  - `pdm run qwen-t221-historical-control status`
  - `pdm run qwen-t221-historical-control stop`
- The new surface writes:
  - `contract-diff.json`
  - `contract-diff.md`
  - `launch.json`
  - `status.json`
  - `status.md`
  - `stop.json`
- The recreated control now binds the surviving historical bundle directly from:
  - `/srv/storage/sir-convert-a-lot/backups/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h`
- It validates the documented manifest counts before launch:
  - `8445` train rows
  - `8` eval rows
- It launches against image:
  - `sir-convert-a-lot-qwen-finetune-hemma:task100`
- The current bounded recreation is intentionally explicit about remaining diffs:
  - the surviving historical bundle now lives under `/srv/storage` backup rather than the original `/srv/scratch` reference root
  - the recreation uses the current trainer module with the original recipe shape plus the `T206` token fix
  - the first launch will be a bounded probe, not the original million-step run

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_t221_historical_control_runtime.py tests/sir_convert_a_lot/ml/qwen/training/test_t221_historical_control.py -q`
- [x] `pdm run typecheck-ml`
- [x] `pdm run typecheck-all`
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
