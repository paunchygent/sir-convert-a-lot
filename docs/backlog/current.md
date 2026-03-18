---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-18'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md
  - docs/backlog/tasks/task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane.md
  - docs/backlog/tasks/task-225-define-the-exact-step-1-instability-parity-contract-for-the-recreated-historical-control-failure-family.md
  - docs/backlog/tasks/task-226-build-a-deterministic-upstream-vs-current-single-step-parity-probe-for-the-qwen-fine-tuning-path.md
  - docs/backlog/tasks/task-227-trace-and-remediate-the-first-verified-finite-to-non-finite-divergence-before-resuming-story-31-stabilizer-candidates.md
  - docs/backlog/tasks/task-228-close-the-failed-t219-layer16-handoff-family-with-one-ranked-failure-matrix.md
  - docs/backlog/tasks/task-229-split-the-post-t219-layer16-handoff-seam-into-sub-boundary-probes.md
  - docs/backlog/tasks/task-230-test-one-diagnosed-post-t219-micro-family-against-the-first-verified-layer16-sub-boundary.md
  - docs/backlog/tasks/task-231-pin-the-post-t219-bounded-fresh-start-promotion-contract-before-any-governed-proof.md
  - docs/backlog/tasks/task-232-make-the-story-31-lane-decision-after-the-post-t219-bounded-promotion-result.md
  - docs/backlog/tasks/task-242-establish-permanent-docker-visible-hemma-bind-roots-for-scratch-backed-qwen-runtimes.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - session-log
  - active-work
---

## Context

Epic 08 remains the active lane. Story 32 now governs how active Qwen Task 101
work is classified and compared, using the Task 101 progress reference as the
single live ledger.
The current experiment posture is:

- `provenance`
  - latest resolved result: `T221` negative recreated-control evidence
  - active surface: `qwen-t221-historical-control`
- `mechanism`
  - active lane: Story 31 through `qwen-story31-stability-lab`
  - `T225-T226` complete: exact parity contract plus committed parity-probe; `task226-20260317t224307Z` closed `no_meaningful_divergence_found`
  - `T219` now stands as recorded negative unpromoted evidence
  - `T228` complete: ranked closure recorded from `task219-20260317t180700z-a1`
  - `T229` complete: `task229-20260318t064712z-a1` localized to `talker_core.layer_16.input_layernorm`
  - `T230-T232` complete: the normalization-entry family closed negative, `T217` stayed blocked, and Story 31 stayed in `mechanism`
  - `T233` complete: `task233-20260318t112544z-a1` fixed the first internal surface at `talker_core.layer_16.input_layernorm.output`
  - `T234` complete: `task234-20260318t123644z-a1` closed the output-scale family without promotion
  - `T235` complete: `task235-20260318t140352z-a1` confirmed the line-4 outlier is repeatable
  - `T236` complete: `task236-20260318t145434z-a1` classified the outlier as a genuine row-local seam difference
  - `T237` complete: `task237-20260318t154708z-a1` converged downstream to `talker_core.layer_15.output`
  - `T240` complete: `task240-20260318t165458z-a1` confirmed all three normative `sub_talker_loss` rows first break at `talker_core.layer_15.output`
  - `T241` is now the active diagnosis-only layer-15 residual/output split
  - `T227` is now contingent only if a later parity/runtime divergence is verified
- parallel Hemma infra: `T242` is now complete and makes the home-backed Docker-visible bind roots the explicit permanent host contract on Hemma
- `recovery`: governed `qwen-train` fresh-start proof, blocked at `T217` until a mechanism candidate is promoted
- historical-only surfaces: `qwen-story30-freshstart-proof`, `qwen-story30-backward-lineage`, `qwen-t197-proof`, `qwen-t198-proof`

Story 28 is now operating policy:

- `RULE-095` enforces the Qwen package split and `400` LoC hot-path cap
- `RULE-096` enforces experiment taxonomy, one-question-per-run discipline, one-factor-at-a-time causal comparisons, and the promotion ladder
- `qwen_train.py` is a composition root only
- host control-plane logic lives under `ml/qwen/training/control_plane/`, detached runtime logic under `ml/qwen/training/detached_runtime/`, and reporting under `ml/qwen/training/reporting/`
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
  - `T192` added the fast ML gate lane with `test-ml`, `typecheck-ml`, and importlib-safe pytest collection.
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
  - `T212` (`task212-20260317t141500z-lineage-a3`) proved all three loss
    branches failed on the row pair, both isolated rows failed independently,
    `hidden_states` stayed finite first, and the earliest instrumented
    non-finite hook was `input_embeddings`.
  - `T213` (`task213-20260317t143810z-talkercore-a1`) pushed the earliest
    localized break into the talker core:
    `layer_16.post_attention_layernorm` for pair `main_loss` /
    `combined_loss`, `layer_15.output` for `sub_talker_loss`.
  - `T214` (`task214-20260317t151800z-boundary-a1`) then narrowed the main
    pair seam to `talker_core.layer_16.mlp.gated_product` and kept
    `sub_talker_loss` at `talker_core.layer_15.output`.
  - Story 31 is now the active solution lane: stable fresh-start bundle
    learning is the target, and the first Hemma matrix under
    `task215-20260317t160500z-a2` is already negative evidence:
    `off`, `layer16_gated_fp32`, and `layer16_gated_fp32_clamp_1e4`
    all reproduced the same `T214` pair-family seams
  - `T220` now has a committed explicit control runtime surface:
    `--text-embedding-assembly-mode full_channel_masked` runs the original
    restored no-projection recipe with the `T206` token-span correction only
  - but the bounded `T220` Hemma attempt is not credible exact-control
    evidence, because it drifted to the later `task-152` benchmark bundle and
    `batch_size=8` instead of the documented historical Task 101 contract
  - `T221` is now implemented as the corrected exact-control surface:
    `pdm run qwen-t221-historical-control <launch|status|stop>` recreates the
    documented historical contract, validates the surviving `8445/8` bundle
    under `/srv/storage/...qwen3-tts-swedish-task101-pilot-bundle-20260312h`,
    and writes an explicit `contract-diff` artifact before launch
  - `T221` then closed as negative recreated-control evidence:
    `task221-20260317t193125z-a1` failed at optimizer step `1` /
    train iteration `4` with `pre_clip_non_finite_gradients` on
    `text_embedding.weight.grad`, no checkpoint, and no eval
  - this is materially stronger than `T220` because it used the recreated
    historical bundle contract, but it still does not prove that `T206` alone
    broke the byte-for-byte March 13 lane
  - Story 32 / `T222-T224` then landed the consolidation package:
    one experiment taxonomy, one active surface matrix, one canonical
    experiment spec, and one live ledger contract for future Qwen work
  - `T225` then completed the exact parity contract before more stabilizer
    iteration:
    it fixed the recreated step-`1` / iteration-`4` failure-family input, the
    checkpoint comparison table, and the stop rules for `T226-T227`
  - `T226` then landed the committed local parity-probe surface:
    `pdm run qwen-story31-parity-probe run` now compares the real
    `execute_train_iteration` window against the reconstructed shared-forward
    optimizer-boundary window on the exact `T225` microbatch family and writes
    `current-path.json`, `intended-path.json`, `results.json`, and `results.md`
  - the live in-image `T226` Hemma execution under
    `task226-20260317t224307Z` then matched the current and intended paths at
    every compared checkpoint and closed with
    `first_divergence_classification = no_meaningful_divergence_found`, so
    Story 31 returns to `T219` rather than escalating to `T227`
- 2026-03-18:
  - `T219` was backfilled as already-failed bounded Story 31 evidence; `T228` closed that family, `T229` localized the next seam to `talker_core.layer_16.input_layernorm`, `T230-T232` kept the lane in mechanism, `T233` resolved the internal seam to `talker_core.layer_16.input_layernorm.output`, `T234` closed the output-scale family as no-promotion mechanism evidence under `task234-20260318t123644z-a1`, `T235` confirmed the mixed `sub_talker_loss` result is repeatable under `task235-20260318t140352z-a1`, `T236` then classified that disagreement as a genuine row-local seam difference under `task236-20260318t145434z-a1`, `T237` converged all three normative `sub_talker_loss` rows downstream under `task237-20260318t154708z-a1`, and `T240` then confirmed the converged seam itself under `task240-20260318t165458z-a1`: pair, `line-13`, and `line-4` all first broke at `talker_core.layer_15.output`, which opens `T241` as the diagnosis-only layer-15 residual/output split.
  - `T242` then closed the recurring Hemma bind-root workaround as a permanent platform contract: the repo-rendered `sir-convert-a-lot-qwen-docker-bind-roots.service` is installed and active, `status` now proves the home roots are mounted onto the canonical `/srv/scratch` trees by round-trip verification, and `probe` confirms Docker must use `/home/paunchygent/.data/sir-convert-a-lot/{build,cache}` as the effective bind roots while `/srv/scratch/...` remains the canonical storage truth.

## Next Actions

- Keep the preserved Task 101 lane on the restored no-projection fine-tuning
  graph; do not reopen the projection-enabled experiment.
- Keep `state-step-00001406` as the canonical RCA checkpoint for preserved-lane history.
- Keep `T221` classified as provenance evidence: it is stronger than `T220`,
  but it is not a mechanism or recovery result.
- Continue through Story 31 as the mechanism lane:
  - `T225-T226` are complete as the exact parity contract plus committed
    parity-probe; `task226-20260317t224307Z` closed `no_meaningful_divergence_found`
  - `T219` is now recorded as negative bounded evidence without promotion
  - `T228` is now complete as the ranked closure of that failed family
  - `T229` is now complete under `task229-20260318t064712z-a1` and constrains Story 31 to the pre-`input_layernorm` normalization-entry family only
  - `T230-T232` are now complete under `task230-20260318t082049z-a1` with no local winner and the lane still in `mechanism`
  - `T233` is now complete under `task233-20260318t112544z-a1`
  - `T234` is now complete under `task234-20260318t123644z-a1` with no promotable winner
  - `T235` is now complete under `task235-20260318t140352z-a1`
  - `T236` is now complete under `task236-20260318t145434z-a1`
  - `T237` is now complete under `task237-20260318t154708z-a1`
  - `T240` is now complete under `task240-20260318t165458z-a1`
  - `T241` is now the immediate diagnosis-only layer-15 residual/output split
  - `T242` is now complete; use `pdm run run-hemma -- pdm run qwen-docker-bind-roots status` and `probe` as the normal Qwen Docker preflight on Hemma
  - record the full Story 32 experiment spec for any new active run
  - keep one-factor-at-a-time deltas inside the same lane before making causal claims
- Keep `T217` blocked as the recovery lane until a mechanism candidate passes the local promotion gate.
- Keep Story 29 and Story 30 proof surfaces as historical-only references, not as next-step operational surfaces.
- Keep the Task 242 Hemma bind-root contract active: `/srv/scratch/...` remains canonical SSD-backed storage truth, `/home/paunchygent/.data/sir-convert-a-lot/{build,cache}` is the effective Docker-visible bind source, use `status` and `probe`, and treat dynamic runtime bind fallback as compatibility-only.
- Keep the Hemma scratch-governance surfaces active and available:
  - `pdm run run-hemma -- pdm run qwen-scratch-policy audit`
  - `pdm run run-hemma -- pdm run qwen-scratch-policy maintain --prune-docker-state`
  - `pdm run run-hemma -- pdm run qwen-scratch-policy status-timer`
- Use `pdm run test-ml` and `pdm run typecheck-ml` as the fast local gate for Qwen ML iteration
  before broader repo validation, and keep Task 101 operator truth in
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Keep new Qwen control-plane/runtime work inside Story 28 boundaries
  (`RULE-095`) and new experiment interpretation inside Story 32 governance
  (`RULE-096`).
