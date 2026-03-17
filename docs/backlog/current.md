---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-17'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-192-add-ml-specific-quality-gates-and-importlib-safe-qwen-test-collection.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/backlog/tasks/task-204-restore-story-29-scratch-headroom-and-establish-cold-artifact-demotion-policy-on-hemma.md
  - docs/backlog/tasks/task-205-establish-idle-safe-recurring-hemma-scratch-maintenance.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly.md
  - docs/backlog/tasks/task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly.md
  - docs/backlog/tasks/task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3.md
  - docs/backlog/reviews/review-03-architect-review-of-post-task-101-qwen-stabilization-candidates-after-story-29.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - session-log
  - active-work
---

## Context

Epic 08 remains the active lane. The repo focus is bounded closure for the
preserved no-projection Task 101 training series, with Story 29 acting as the
mandatory mitigation gate before any new clean restart.

The current proof posture is:

- exhausted replay-family evidence:
  - preferred gate attempts with accumulation `4`, `2`, and `1` all failed
  - the fallback `1406 -> 1470` replay also failed on the current code path
- final post-fix rule:
  - land one code-bearing text-token span correction
  - then run exactly one decisive Hemma proof:
    - clear `1406 -> 1470`
    - then complete detached standalone eval from that checkpoint
  - if that final post-fix proof still fails numerically before `1470`, stop
    bounded RCA on this preserved lane

Story 28 is now operating policy:

- `RULE-095` enforces the Qwen package split and `400` LoC hot-path cap
- `qwen_train.py` is a composition root only
- host control-plane logic lives under `ml/qwen/training/control_plane/`
- detached runtime logic lives under `ml/qwen/training/detached_runtime/`
- reporting lives under `ml/qwen/training/reporting/`
- deleted legacy god files must not return

## Worklog

- 2026-03-13:
  - Story 26 throughput and observability evidence established the lane as
    host-orchestration/synchronization bound with persistent `NaN` risk.
- 2026-03-15:
  - `T184/T185/T180/T186` established truthful checkpoint cadence, the `1236`
    eval baseline, strict-resume `1238`, and fail-closed optimizer-boundary
    proof at step `1405`.
  - Story 28 / `T187-T191` landed the permanent SRP/DDD split.
  - `T192` added the fast ML gate lane with `test-ml`, `typecheck-ml`, and
    importlib-safe pytest collection.
  - `T193` restored the upstream no-projection fine-tuning contract and added
    stage-resolved clip-boundary forensics.
  - `T194` became the RCA narrowing slice for the first pre-clip text-embedding
    gradient failure.
- 2026-03-16:
  - exact capture at `1401` and bounded replay through `1406` succeeded, but
    the later continuation and replay family still failed on the same
    optimizer-boundary class centered on `input_text_embedding.grad` /
    `text_embedding.weight.grad`
  - Story 29 then exhausted the bounded mitigation ladder:
    - `T195-T196` landed `text_span_only` plus explicit accumulation control
    - `T203` removed the slower codebook-fusion experiment from the proof lane
    - `T197` failed at `1417` with accumulation `4`
    - `T198` accumulation `2` and `1` cleared `1418` but still failed the
      preferred/fallback gates later at `1428` and `1449`
  - `T204-T205` restored Hemma scratch governance and recurring idle-safe
    cleanup so proof launches stop failing on SSD exhaustion
  - `T198` closed as terminal negative replay-family evidence and handed off
    to `T206`
- 2026-03-17:
  - `T206` landed the explicit position-mask correction in dataset collation,
    and the post-fix offline audit proved active span `8..135` with zero
    leaked positions, zero leaked token ids, and zero leaked non-finite rows.
  - the single final post-fix Hemma proof under
    `task206-20260317t074600z-postfix1470-a1` still failed before `1470` with
    `pre_clip_non_finite_gradients` on `text_embedding.weight.grad` at step
    `1407`, so no truthful `1470` checkpoint or detached eval was produced and
    Story 29 bounded RCA is closed for the preserved lane.
  - Story 30 is now active with the closed architect verdict:
    Candidate 1 selected, contingency `1 -> 3`, Candidate 2 rejected.
  - `T207-T209` completed the local Candidate 1 lane:
    semantic-only batch fields landed, train/eval now embed only
    `semantic_text_ids`, and the new local proof shows only semantic ids can
    enter `text_embedding.weight.grad` even under poisoned scaffold upstream
    gradients.
  - `T210` then failed immediately at optimizer step `1407`, so Candidate 1 is
    negative rescue evidence on inherited `1406` state and does not authorize
    restart
  - `T211` is now closed terminal negative evidence for Candidate 1 as a
    fresh-start lane:
    `task211-20260317t130740z-freshstart-a4` failed at optimizer step `1`
    with `pre_clip_non_finite_gradients` on `text_embedding.weight.grad`
    while forward tensors and losses stayed finite
  - the next clean move is `T212`: one single-step backward-lineage probe on
    Hemma against the exact failing rows `13` and `4`, with probe order:
    `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation

## Next Actions

- Keep the preserved Task 101 lane on the restored no-projection fine-tuning
  graph; do not reopen the projection-enabled experiment.
- Keep `state-step-00001406` as the canonical RCA checkpoint.
- Keep the auxiliary codebook fusion helper on the plain vectorized reduction;
  do not revive the explicit `float32` reducer without new Hemma evidence.
- Keep the Hemma scratch-governance surfaces active and available:
  - `pdm run run-hemma -- pdm run qwen-scratch-policy audit`
  - `pdm run run-hemma -- pdm run qwen-scratch-policy maintain --prune-docker-state`
  - `pdm run run-hemma -- pdm run qwen-scratch-policy status-timer`
- Treat Story 29 / `T197-T206` as closed bounded-RCA evidence on the preserved
  lane:
  - the explicit position-mask correction removed the audited leakage
  - the single final post-fix Hemma proof still failed at optimizer step `1407`
  - no truthful `1470` checkpoint was minted and detached eval was not launched
  - `T199` therefore remains blocked
  - the next step is Story 30 Candidate 1, not another replay or post-fix
    proof variant
- Treat `T207-T209` as complete and
  `tests/sir_convert_a_lot/ml/qwen/training/test_semantic_text_embeddings.py`
  as the first required local gate before any new Hemma long proof attempt for
  Candidate 1.
- Treat `T211` as closed negative fresh-start evidence:
  - the semantic-only Candidate 1 lane failed immediately at optimizer step
    `1`
  - this removes replay-amassed inherited state as the leading explanation
    for the current failure family
  - do not spend more time on replay framing before the backward-lineage lane
- `T212` is now the active discovery owner before any Candidate 3 opening:
  - use the exact fresh-start failing row pair from `T211`:
    manifest lines `13` and `4`
  - run one single-step backward-lineage probe on Hemma
  - use the probe order:
    `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation
  - make the goal the first non-finite backward edge/tensor inside the graph,
    not the first failed parameter surface
  - keep the work on a committed repo-owned probe surface, not inline shell
    debugging
- `T199` remains blocked until a later explicit clean-start proof authorizes
  restart.
- Do not spend the next story on Candidate 2.
- Use `pdm run test-ml` and `pdm run typecheck-ml` as the fast local gate
  before broader repo validation while iterating on Qwen ML code.
- Keep Task 101 operator truth in `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Keep all new Qwen control-plane/runtime work inside the Story 28 package
  boundaries enforced by `RULE-095`.
