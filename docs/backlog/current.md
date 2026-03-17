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
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/tasks/task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
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
  - `T212` then completed with truthful fresh-start backward-lineage evidence:
    - first truthful proof:
      `task212-20260317t141500z-lineage-a3`
    - all three loss branches failed on the row pair:
      `main_loss`, `sub_talker_loss`, `combined_loss`
    - both isolated rows failed independently:
      line `13` alone and line `4` alone
    - `hidden_states` and `talker_hidden_states` gradients stayed finite
      first
    - the earliest instrumented non-finite hook then appeared at
      `input_embeddings`
    - the additive branches inherited non-finite gradients only after that:
      `fused_auxiliary_embedding`, `input_codec_embedding`,
      `input_text_embedding`, `semantic_text_embeddings`
    - the targeted RCA still reported
      `input_text_embedding.grad` first and
      `text_embedding.weight.grad` as the first poisoned parameter surface
  - `T213` then completed with stronger talker-core localization:
    - truthful proof:
      `task213-20260317t143810z-talkercore-a1`
    - pair `main_loss` and `combined_loss` first localized at
      `talker_core.layer_16.post_attention_layernorm`
    - pair `sub_talker_loss` first localized at
      `talker_core.layer_15.output`
    - isolated rows localized to `talker_core.layer_16.output` for
      `main_loss` / `combined_loss` and to `talker_core.layer_15.output` for
      `sub_talker_loss`
    - pair-main finite gradient magnitudes exploded from `1.07e-4` at
      `layer_27.output` to `3.19e38` at `layer_16.output` before
      `layer_16.post_attention_layernorm` turned non-finite
    - Candidate `3` is not the next truthful move yet, because a smaller
      talker-core causal split is still available
  - `T214` then closed the last smaller causal split:
    - truthful proof:
      `task214-20260317t151800z-boundary-a1`
    - pair `main_loss` / `combined_loss` first broke at
      `talker_core.layer_16.mlp.gated_product` with `MulBackward0`
    - pair `sub_talker_loss` first broke at `talker_core.layer_15.output`
      with `MmBackward0`
    - pair main/combined gradients were still finite at
      `layer_16.output` / `layer_16.mlp.down_proj` around `3.19e38` /
      `3.26e38` before the first non-finite hook
  - Story 31 is now the active solution lane: stable fresh-start bundle
    learning is the target, and the first Hemma matrix under
    `task215-20260317t160500z-a2` is already negative evidence:
    `off`, `layer16_gated_fp32`, and `layer16_gated_fp32_clamp_1e4`
    all reproduced the same `T214` pair-family seams

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
  lane: the explicit position-mask correction removed the audited leakage, but
  the single final post-fix Hemma proof still failed at optimizer step `1407`
  without a truthful `1470` checkpoint or detached eval.
- Treat `T207-T209` as complete and
  `tests/sir_convert_a_lot/ml/qwen/training/test_semantic_text_embeddings.py`
  as the first required local gate before any new Hemma long proof attempt for
  Candidate 1.
- Treat `T211` as closed negative fresh-start evidence:
  - the semantic-only Candidate 1 lane failed immediately at optimizer step `1`
  - replay-amassed inherited state is no longer the leading explanation for
    the current failure family
  - do not spend more time on replay framing before the backward-lineage lane
- `T212` is now closed positive discovery evidence:
  - both rows fail independently and the truthful fresh-start single-step
    probe reproduced the family directly
  - Candidate 1 semantic-only assembly is not where the earliest
    instrumented corruption first appears; that edge is `input_embeddings`
- `T213` is now closed positive discovery evidence:
  - the earliest non-finite backward hook is inside the talker core, not just
    at `input_embeddings`, with the freshest localized boundary around
    `layer_16.post_attention_layernorm` and `layer_15.output`
  - do not open Candidate `3` while a smaller talker-core split is still
    available
- Treat `T214` as closed discovery evidence:
  - pair `main_loss` / `combined_loss` first break at `talker_core.layer_16.mlp.gated_product`
  - pair `sub_talker_loss` first breaks at `talker_core.layer_15.output`
  - replay framing is no longer the productive center of gravity
- Story 31 is now active:
  - `T216` is now complete:
    - the first bounded variants are `off`, `layer16_gated_fp32`, and
      `layer16_gated_fp32_clamp_1e4`
    - the exploration surface is `pdm run qwen-story31-stability-lab run`
    - the lab writes one compact matrix run under a single output root:
      `results.json`, `results.md`, and `variant-reports/<variant>.json`
    - it reuses the exact failing-row backward-lineage probe instead of
      minting a proof package per hypothesis
  - `T215` is now complete:
    - the promotion surface is `pdm run qwen-story31-stability-lab gate --output-root <lab-output-root>`
    - it consumes `results.json`, writes `gate.json` / `gate.md`, and requires
      exact `T214` pair-family failure on baseline `off` plus finiteness on candidate `layer16_gated_fp32`
  - the first real gate run under `task215-20260317t160500z-a2` is negative:
    `off`, `layer16_gated_fp32`, and `layer16_gated_fp32_clamp_1e4` all preserved the same pair-family failures
  - `T217` stays blocked until a later exploration candidate actually passes
    the local promotion gate
  - the next clean move is another bounded exploration candidate around the layer-16 gated-product / layer-15 output family
- `T199` remains blocked until Story 31 records a positive fresh-start
  stabilization proof that justifies a larger clean-start proof lane.
- Do not spend the next story on Candidate 2.
- Use `pdm run test-ml` and `pdm run typecheck-ml` as the fast local gate for
  Qwen ML iteration before broader repo validation.
- Keep Task 101 operator truth in `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Keep new Qwen control-plane/runtime work inside Story 28 boundaries (`RULE-095`).
