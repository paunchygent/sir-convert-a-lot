---
id: task-148-batch-task101-pilot-bundle-finalization-and-progress-logging-on-hemma
title: batch task101 pilot bundle finalization and progress logging on Hemma
type: task
status: completed
priority: high
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/tasks/task-143-harden-qwen-pilot-training-eval-and-bundle-preflight-contracts.md
  - docs/backlog/tasks/task-147-fail-closed-task101-pilot-bundle-builds-on-insufficient-scratch-capacity.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - hemma
  - pilot
  - training-bundle
  - finalization
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the current monolithic Task 101 pilot-bundle finalization path with
true bounded batch-finalization surfaces on Hemma so `audio_codes`
materialization can be resumed, inspected, and logged batch by batch instead
of running one long warm-process pass across the entire retained pilot slice.

## PR Scope

- Keep Hemma as the canonical target for pilot-bundle materialization.
- Add explicit Task 101 pilot-bundle stages:
  - copy retained pilot rows and audio only
  - finalize one bounded batch only
  - assemble final prepared manifests and report only after all batches exist
- Make batch definitions deterministic from the copied spool rows:
  - family-specific row order must remain stable
  - batch row counts and batch indices must be machine-readable
- Persist operator-visible progress artifacts so a wedge or interruption leaves
  clear evidence of:
  - planned batches
  - batch start/end events
  - last completed batch
  - exact family and batch index reached
- Keep the current capacity preflight from `T147`.
- Keep the existing frozen-root ownership and bundle-local path validation
  contracts from `T142`-`T147`.
- Ensure the canonical `build` surface no longer performs one whole-family
  finalization pass in-process on Hemma.

## Non-Goals

- Do not move Task 101 bundle finalization off Hemma in this task.
- Do not redesign the frozen pilot ownership source.
- Do not change the accepted pilot dataset rows or manifest-family policy.
- Do not treat `audio_codes_chunk_size` alone as sufficient batching once this
  task lands.

## Required Implementation Shape

1. Copy stage
   - materialize retained spool rows and `audio_24k` files into a new bundle
     root
   - create deterministic stable `refs/`
   - emit one machine-readable batch plan artifact before any Qwen tokenizer
     work starts
1. Batch-finalization stage
   - run one family-specific bounded batch at a time
   - write batch-local manifest shards deterministically
   - emit start/end progress artifacts for each batch
   - make reruns skip already-completed batch outputs safely
1. Assemble/report stage
   - concatenate validated batch shards into final
     `swedish_pilot_train.prepared.jsonl` and
     `swedish_checkpoint_dev.prepared.jsonl`
   - write the final Task 101 bundle report only after all expected batch
     shards exist and validate

## Logging / Hypothesis Guardrails

This task exists partly to test the current operational hypothesis that Hemma
wedges because Task 101 finalization still processes the whole retained pilot
family in one long-lived tokenizer process.

The implementation must therefore log enough deterministic progress to confirm
or falsify that hypothesis on the next live Hemma run:

- total batch count per family
- row count per batch
- first and last row identity per batch
- batch start timestamp
- batch completion timestamp
- skipped/already-complete batch detection
- final assemble/report completion

## Deliverables

- [x] New Task 101 pilot-bundle stage surfaces for copy, finalize-batch, and
  assemble/report.
- [x] Deterministic batch-plan and batch-progress artifacts under the bundle
  `reports/` tree.
- [x] Canonical `build` surface updated so it uses the batch surfaces instead
  of one monolithic finalization pass.
- [x] Focused tests that prove deterministic batch planning, batch output
  validation, resume-safe reruns, and progress artifact emission.

## Acceptance Criteria

- [x] Task 101 bundle materialization no longer performs one whole-family
  finalization pass directly after copy on Hemma.
- [x] One interrupted or wedged batch leaves enough on-disk progress evidence
  to identify the last started and last completed batch without guessing.
- [x] Re-running the bundle build after a partial completion can skip validated
  completed batches instead of restarting full finalization from zero.
- [x] Final prepared manifests are assembled only from validated batch shards.
- [x] The Task 101 task doc and Qwen Hemma/Colab runbook describe the new
  batch-finalization contract and operator posture.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- [x] `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_cli.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_source.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_validation.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_contracts.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_progress.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_execution.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Post-Implementation Review Findings (2026-03-12)

The first post-implementation ruthless review surfaced five issues that must be
closed before this task can be treated as fully hardened:

- the new CLI surface still fails the repo-wide `typecheck-all` gate because
  the parsed manifest-family values are forced through `str(...)` instead of a
  typed normalization helper
- reusable batch-shard validation is not yet strong enough to prove that the
  full ordered curated/raw/prepared shard contents still agree
- the tests do not yet prove the key interrupted-batch operator contract where
  `batch_started` is recorded but `batch_completed` is absent after a crash
- the tests bypass the real subprocess launch boundary, so the
  `build -> finalize-batch` production handoff is still unproven
- handoff/current operator guidance drifted away from the verified `ENOSPC`
  prerequisite and must keep scratch-space recovery explicit before the next
  live Hemma retry

## Remediation Plan

- add typed CLI manifest-family normalization and rerun `pdm run typecheck-all`
- strengthen batch-output validation so reruns only skip shards whose ordered
  row signatures still match across curated/raw/prepared outputs
- add a failure-path regression that proves progress artifacts survive a batch
  interruption and support a safe rerun
- add a subprocess-launch contract test for the fresh-process batch runner
- restore the scratch-space prerequisite in session/current guidance before the
  next live retry

## Outcome

`T148` is now implemented.

The canonical `pdm run task-101-pilot-bundle build` surface still exists, but
it no longer performs one whole-family finalization pass in-process. Instead it
now:

- copies retained spool rows and `audio_24k` artifacts into the bundle root
- emits `reports/task101_pilot_bundle_plan.json`
- finalizes one bounded family batch at a time through the committed
  `finalize-batch` surface
- records append-only `reports/task101_pilot_bundle_events.jsonl` plus rolled-up
  `reports/task101_pilot_bundle_status.json`
- assembles final prepared manifests only from validated batch shards

Focused regression coverage now proves:

- deterministic batch planning from copied spool rows
- end-to-end batched build materialization
- partial rerun behavior that skips already validated batch shards
- explicit operator log statements for copy, batch start/completion, assemble,
  and final report completion

The same-day post-implementation review follow-up is also now closed inside
`T148`:

- the CLI normalizes manifest-family arguments through typed validation so the
  repo-wide `typecheck-all` gate passes again
- the CLI parsing and dispatch now live in the dedicated
  `task101_qwen_pilot_bundle_cli.py` module instead of expanding the
  orchestration module
- source/materialization helpers now live in
  `task101_qwen_pilot_bundle_source.py` and manifest/report validation now
  lives in `task101_qwen_pilot_bundle_validation.py`, leaving
  `task101_qwen_pilot_bundle.py` as the focused orchestration surface under
  the repo split threshold
- reusable batch-shard validation now compares ordered curated/raw/prepared row
  signatures instead of only counts plus first/last row keys
- the regression suite now proves interrupted-batch progress evidence plus safe
  rerun behavior after a failed batch attempt
- the fresh-process batch runner now has explicit subprocess launch/failure
  contract coverage
- session/current guidance now keeps the verified scratch-space prerequisite
  explicit before the next live Hemma retry

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
