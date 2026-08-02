---
type: reference
id: REF-SIRCON-RESEARCH-qwen-training-eval-pilot-progress-ledger-2026-03-15
title: Qwen Training/Eval Pilot Progress Ledger (2026-03-15)
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: research
summary: Qwen Training/Eval Pilot Progress Ledger (2026-03-15)
retired_ids:
- REF-qwen-training-eval-pilot-progress-2026-03-15
---

## Research Purpose And Boundary

## Evidence And Sources

## Findings And Interpretation

## Evidence Gaps And Follow-Up

## Historical Source Content

### Purpose

Provide one canonical operator-facing ledger for the active Qwen
experiment program after Story 32 consolidated the surface taxonomy.

This document is the single live ledger for active Qwen Qwen experiment
work. Operators should not create a second live ledger for provenance,
mechanism, or recovery runs.

It records:

- the active experiment classes and surface-status matrix
- the canonical experiment-spec contract for future active runs
- the per-run ledger entry template for future active runs
- the historical `1236` checkpoint baseline eval result and later RCA trail
- the current active provenance, mechanism, and blocked recovery posture

### Story 32 Experiment Governance

Every active Qwen Qwen pilot run must belong to exactly one experiment class.

| Experiment class | Question it may answer | Current active surface |
| --- | --- | --- |
| `provenance` | Why did the historical lane behave the way it did? | `qwen-historical-pilot-control` |
| `mechanism` | Where does the current failure originate and which bounded stabilizer changes that mechanism? | `qwen-stability-lab` |
| `recovery` | Which recipe now trains stably enough to justify a governed proof? | governed `qwen-train launch/status` proof lane after promotion |

### Active Surface Matrix

| Surface | Experiment class | Status | Operator meaning |
| --- | --- | --- | --- |
| `qwen-historical-pilot-control` | `provenance` | `active` | Historical-contract recreation and control evidence only |
| `qwen-stability-lab` | `mechanism` | `active` | Bounded stabilization exploration and promotion gating |
| governed `qwen-train launch/status` fresh-start proof | `recovery` | `active but blocked until promotion` | Short governed proof only after a mechanism candidate passes |
| `qwen-freshstart-proof` | `mechanism` | `legacy-readonly` | Historical fresh-start proof surface; not a current operator default |
| `qwen-backward-lineage` | `mechanism` | `legacy-readonly` | Historical causal-localization surface; not a current operator default |
| `qwen-fallback-proof` | `mechanism` | `deprecated` | Historical Story 29 replay evidence; not for new work |
| `qwen-fallback-accumulation-proof` | `mechanism` | `deprecated` | Historical Story 29 accumulation/fallback evidence; not for new work |

### Canonical Qwen Experiment Spec

Every future active run recorded in this ledger must declare the full state
vector below before the repo treats the run as comparable evidence:

- `experiment_class`
- `question_answered`
- `surface_name`
- `code_revision`
- `image`
- `bundle_root`
- `sampler_or_batching_policy`
- `seed_or_shuffle_policy`
- `batch_size`
- `gradient_accumulation_steps`
- `text_embedding_assembly_mode`
- `text_embedding_mask_policy`
- `stabilizer_variant`
- `max_steps`
- `eval_policy`
- `input_artifact_roots`
- `expected_promotion_target`
- `status`
- `result_interpretation`

### Ledger Entry Template

Use the following field order for every future active run entry, including
future `T221`, Story 31 mechanism, and governed recovery entries:

- `experiment_class:`
- `question_answered:`
- `surface_name:`
- `code_revision:`
- `image:`
- `bundle_root:`
- `sampler_or_batching_policy:`
- `seed_or_shuffle_policy:`
- `batch_size:`
- `gradient_accumulation_steps:`
- `text_embedding_assembly_mode:`
- `text_embedding_mask_policy:`
- `stabilizer_variant:`
- `max_steps:`
- `eval_policy:`
- `input_artifact_roots:`
- `expected_promotion_target:`
- `status:`
- `result_interpretation:`

### Current Operator Rule

Use this ledger as the single live operator truth for active Qwen Task 101
work.

- the latest resolved provenance result is `T221`: the recreated
  historical-control run failed immediately at optimizer step `1` / train
  iteration `4` on the same pre-clip text-embedding family
- `qwen-historical-pilot-control` remains the active provenance surface for
  future historical-contract or control questions
- Story 31 is the active mechanism lane:
  - `T225` is complete as the exact parity contract
  - `T226` is complete as the committed local parity-probe surface
  - the live in-image historical-bundle run
    `task226-20260317t224307Z` resolved with
    `first_divergence_classification = no_meaningful_divergence_found`
  - `T219` is now recorded as negative bounded evidence under
    `task219-20260317t180700z-a1`
  - `T228` is now complete as the ranked closure of that family
  - `T229` is now complete as the narrowed sub-boundary rerun under
    `task229-20260318t064712z-a1`
  - the target `sub_talker_loss` family localizes to
    `talker_core.layer_16.input_layernorm`
  - `T230` is now complete as a negative bounded normalization-entry rerun
    under `task230-20260318t082049z-a1`
  - `T231` is now complete as the explicit no-winner promotion decision
  - `T232` is now complete as the lane decision to stay in mechanism
  - `T233` is now complete as the normalization-internal rerun under
    `task233-20260318t112544z-a1`
  - the pair and both single-row `sub_talker_loss` cases, plus the wider
    nine-row matrix, all first broke at
    `talker_core.layer_16.input_layernorm.output`
  - `T234` is now complete as the bounded output-scale rerun under
    `task234-20260318t123644z-a1`
  - no variant stayed finite or earned promotion; the strongest `0p5` member
    shifted the pair and `line-13` `sub_talker_loss` cases to
    `talker_core.layer_15.output`, while `line-4` remained at
    `talker_core.layer_16.input_layernorm`
  - `T235` is now complete as the disagreement-resolution rerun under
    `task235-20260318t140352z-a1`
  - the mixed `sub_talker_loss` result is repeatable: pair and `line-13`
    stayed at `talker_core.layer_15.output`, while `line-4` stayed at
    `talker_core.layer_16.input_layernorm`
  - `T236` is now complete as the row-local outlier-resolution rerun under
    `task236-20260318t145434z-a1`
  - the outlier is now classified as a genuine row-local seam difference:
    pair and `line-13` stayed at `talker_core.layer_15.output`, while `line-4`
    stayed at `talker_core.layer_16.input_layernorm.output`
  - `T237` is now complete as the post-`T236` row-local micro-family rerun
    under `task237-20260318t154708z-a1`
  - the `1e3` fp32-output-cap winner converged pair, `line-13`, and `line-4`
    `sub_talker_loss` downstream to `talker_core.layer_15.output`
  - `T240` is now complete as the downstream convergence split under
    `task240-20260318t165458z-a1`
  - all three normative `sub_talker_loss` rows first broke at
    `talker_core.layer_15.output`, so the convergence class is
    `converged_layer15_output`
  - `T241` is now complete as the layer-15 split under
    `task241-20260318t175714z-a1`
  - all three normative `sub_talker_loss` rows still first broke at
    `talker_core.layer_15.output`, so the classification is
    `converged_layer15_output_residual`
  - the rerun used the installed Task 242 bind-root contract:
    `/srv/scratch/...` stayed canonical storage truth while Docker used the
    effective home-backed cache/output roots under
    `/home/paunchygent/.data/sir-convert-a-lot/`
  - `T243` is now complete as the residual/output-formation split under
    `task243-20260318t190832z-a1`
  - all three normative `sub_talker_loss` rows first broke at
    `talker_core.layer_15.output`, so the classification is
    `converged_layer15_output_return`
  - `T244` is now complete as the return-path split under
    `task244-20260318t193736z-a1`
  - all three normative `sub_talker_loss` rows still first broke at
    `talker_core.layer_15.output`, so the classification is
    `converged_output_return`
  - `T245` is now complete as the winner-specific multiply confirmation under
    `task245-20260318t202916z-a1`
  - all three normative `sub_talker_loss` rows still first broke at
    `talker_core.layer_15.output`, so the classification is
    `multiply_not_causal`
  - `T246` is now the immediate diagnosis-only next step and must split the
    fp32-scaled layer-15 output result from the final emitted tensor before
    any new stabilizer family is considered
  - `T227` remains contingent only if a later verified trainer/runtime
    divergence appears
  - do not infer recovery readiness directly from a mechanism run
- the governed `qwen-train` fresh-start proof lane is the active recovery
  surface, but it remains blocked until a mechanism candidate passes the local
  promotion gate
- record future live progress here, not in the skill doc
- do not count projection-enabled diagnostics, preserved-lane RCA, historical
  control, and Story 31 mechanism runs as one continuous training series
- do not make causal claims across runs that changed code, bundle root,
  sampler/batching policy, seed/shuffle policy, mask policy, assembly mode, or
  stabilizer variant together
- treat Story 28 / `T187-T191` as the delivered architecture-hardening lane;
  new control-plane or runtime logic must stay in the bounded
  `control_plane/`, `detached_runtime/`, `reporting/`, and focused
  `sft_12hz_*` runtime modules

Historical preserved-lane truth that still matters:

- treat `state-step-00001236` as the evaluated baseline checkpoint
- treat `state-step-00001238` as the canonical no-projection RCA checkpoint
  for the preserved Task 101 lane
- treat `state-step-00001406` from the bounded no-projection replay as the
  current canonical RCA checkpoint
- Story 29 / `T195-T206` is closed bounded-RCA evidence on the preserved lane
- Story 30 is closed design-selection evidence
- Story 31 is the active mechanism owner under the new taxonomy
- the detailed chronology for `T210-T221` remains below in the dated sections
  of this ledger; those sections are the authoritative historical narrative
  for the latest mechanism and provenance evidence

### Active Artifact Roots

- Canonical run root:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z`
- Canonical legacy launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot/task101-20260313t102144z`
- Replacement bundle root for current recovery:
  `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1`
- Held-out eval manifest:
  `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1/manifests/swedish_checkpoint_dev.prepared.jsonl`
- Current strict resume checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/checkpoints/state-step-00001238`
- Exact diagnostic capture checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-capture1401-a3/diagnostic-state/checkpoints/state-step-00001401`
- Current canonical RCA checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
- Latest checkpoint pointer:
  `/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-20260313t102144z/latest_checkpoint.json`

### Superseded Operator Plan

The abandoned plan is:

- “run standalone eval on `1236`, then resume from `1236` again”
- “promote the projection-enabled replay/restart as the authoritative new
  mainline”

That plan is now superseded because:

- the probe already minted `1238`
- `1238` preserves more training progress
- `1238` has a truthful compatible cursor for the replacement bundle
- rolling back to `1236` would spend operator time for no gain
- after the strict `1238` relaunch failed at `1358`, the later
  instrumented replay failed at `1408`, and the guarded diagnostic then failed
  closed at `1405`, the next move is no longer "resume immediately again"; it
  is "use the completed `T186` proof to decide the next bounded `T179` retry"
- after the projection-enabled replay failed even earlier at `1239` and the
  projection-enabled base restart failed at step `1`, the next move is no
  longer "promote the projection-enabled graph"; it is "restore the upstream
  no-projection contract and debug the preserved lane with better stage
  forensics"

### Canonical Next Step

Do not relaunch the projection-enabled training experiment.
Do not launch another fresh Task 101 training continuation or restart yet.

The next canonical action is a bounded no-projection mitigation proof from
`state-step-00001406`:

1. reuse `state-step-00001406` as the canonical RCA checkpoint
1. narrow the active `text_embedding_mask` to the true text span only, or
   equivalently zero/detach the codec-span text-pad positions
1. rerun only the bounded `1406 -> 1418` replay window
1. treat reduced `gradient_accumulation_steps` as the secondary ablation if the
   mask-only mitigation does not remove the instability
1. prefer proving the mitigated lane all the way to step `1500` and completing
   the scheduled eval there before allowing the next clean restart
1. if `1500` still fails after the structural fix and planned accumulation
   ablations, use the fallback gate:
   - clear `1406 -> 1470`
   - mint the `1470` checkpoint
   - run standalone held-out eval from that checkpoint

### 2026-03-16: Story 29 Created To Gate The Next Clean Restart

- New story:
  `docs/backlog/stories/st-sircon-05-05-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md`
- New tasks:
  - `T195` explicit `text_embedding_mask_policy` with `legacy_codec_span` and
    `text_span_only`
  - `T196` runtime-configurable `gradient_accumulation_steps`
  - `T197` preferred bounded proof through `1406 -> 1418` and then to `1500`
    with scheduled eval
  - `T198` conditional accumulation ablation and fallback
    `1470 + standalone eval` gate
  - `T199` first clean base restart after a proof gate passes

Why this matters:

- the repo now has a single canonical RCA checkpoint for cheap bounded proofs:
  `state-step-00001406`
- the RCA already identifies the leading structural amplifier:
  codec-span text-pad activation on the no-projection training graph
- the story makes the restart gate explicit instead of leaving it implied by
  ad hoc operator judgment
- the training reference ledger is now the mandatory place to record whether
  the preferred `1500` gate or the fallback `1470 + standalone eval` gate
  justified the next clean restart

### 2026-03-16: `T195` Landed The Explicit Text-Embedding Mask Policy

- Delivered task:
  `docs/backlog/tasks/task-195-land-an-explicit-task-101-text-embedding-mask-policy-and-text-span-only-mitigation.md`
- Runtime/control-plane contract:
  - `legacy_codec_span`
  - `text_span_only`
- Launch/control truth:
  - fresh `qwen-train launch` defaults to `text_span_only`
  - `resume`, `capture-diagnostic-state`, `diagnose-non-finite`, standalone
    eval, and schedule flows accept explicit overrides while keeping older
    launch metadata compatible through `legacy_codec_span`
- Artifact truth:
  - dataset collation now computes the active text-embedding span from the
    explicit policy rather than a hard-coded codec-span assumption
  - `talker_runtime` fingerprints now record the active
    `text_embedding_mask_policy`
  - detached launch metadata, training status/report payloads, replay bundle
    settings, and standalone eval artifacts now surface the same policy
- Validation truth:
  - focused tests proved `legacy_codec_span` preserves the old active span
  - focused tests proved `text_span_only` narrows the active text-embedding
    surface to the true text span only

Operator conclusion:

- the first structural mitigation surface is now committed and visible
- `legacy_codec_span` is now a bounded RCA reproduction mode only; it is not
  allowed to silently ride along into the future restart lane
- the next implementation step is `T196`, so the same bounded proof lane can
  compare accumulation `4`, `2`, and `1` without code edits
- the next Hemma proof must use the explicit Story 29 contract rather than any
  implicit batch-mask behavior

### 2026-03-16: `T196` Landed Runtime-Configurable Gradient Accumulation

- Delivered task:
  `docs/backlog/tasks/task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs.md`
- Runtime/control-plane contract:
  - supported values are `1`, `2`, and `4`
  - canonical default remains `4`
- Control-plane truth:
  - `launch`, `resume`, `capture-diagnostic-state`, `diagnose-non-finite`,
    `eval`, and `schedule` now all accept
    `--gradient-accumulation-steps`
- Artifact truth:
  - detached launch metadata now snapshots the effective accumulation value
  - in-container trainer and standalone evaluator entrypoints both receive the
    same explicit setting
  - status/report payloads, step semantics, standalone eval artifacts, replay
    bundles, and schedule control math now surface the effective value
- Validation truth:
  - focused tests passed across launch/control-plane parsing, detached command
    building, standalone eval orchestration, schedule targeting, diagnostic
    replay, capture flow, and train-loop reporting

Operator conclusion:

- the bounded proof lane no longer needs code edits to compare accumulation
  `4`, `2`, and `1`
- reduced accumulation remains the secondary ablation only; the first proof is
  still `text_span_only` with accumulation `4`
- if Story 29 proves `text_span_only` as part of the winning mitigation,
  `legacy_codec_span` must be removed before `T199` launches the next clean
  restart

### 2026-03-16: `T203` Closed By Reverting The Auxiliary Codebook Fusion Helper

- Delivered task:
  `docs/backlog/tasks/task-203-audit-the-auxiliary-codebook-fusion-hot-path-against-story-29-mixed-precision-and-proof-lane-contracts.md`
- Hemma proof surfaces used:
  - `pdm run run-hemma -- pdm run qwen-codebook-fusion-proof-detached launch`
  - `pdm run run-hemma -- pdm run qwen-codebook-fusion-proof-detached status`
- Proof artifact root:
  - `build/verification/qwen-codebook-fusion-proof/`
- Hemma runtime truth:
  - repo `HEAD` on Hemma was `5f421072e89bb5517210dd46b237f70900f2eab7`
  - the detached proof completed with ROCm available and the governed Qwen
    image rebuilt successfully
- Numeric/runtime result:
  - `bf16`: worst max error stayed `0.0625`, while runtime rose from about
    `0.492ms` to about `0.620ms`
  - `fp16`: worst max error stayed `0.0078125`, while runtime rose from about
    `0.492ms` to about `0.619ms`
- Decision:
  - revert the explicit `float32` auxiliary-codebook reducer from the Story 29
    proof lane and keep the plain vectorized reduction
- Operator conclusion:
  - the auxiliary codebook helper is not the winning Task 101 mitigation and
    must not be treated as part of the restart-gating proof lane
  - `T197` is now the next canonical step from `state-step-00001406`

### 2026-03-16: `T197` Hemma Proof Failed Again At `1417` Under `text_span_only`

- Delivered task:
  `docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md`
- Proof id:
  `task197-20260316t183555z-a1`
- Local proof artifact root:
  `build/verification/qwen-fallback-proof/task197-20260316t183555z-a1/`
- Remote replay launch root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task197-20260316t183555z-a1-window`
- Runtime truth:
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=4`
  - the replay reused the canonical RCA checkpoint `state-step-00001406`
- Replay result:
  - detached replay exited with `exit_code=1`
  - `current_optimizer_step=1417`
  - `current_train_iteration=852`
  - the preferred `1500` continuation did not launch
- Failure truth:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_stage=pre_clip`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - the first bad backward surface remained `input_text_embedding.grad`
  - the replay preserved the same step-`1417` failure shape as the earlier
    bounded RCA lane
- Operator conclusion:
  - `text_span_only` alone is not sufficient to clear the preferred Story 29
    gate
  - `T198` is now the next active task for the planned accumulation ablations
  - the next clean restart remains blocked

### Historical Reference Boundary

`docs/reference/ref-sircon-research-qwen-live-training-pipeline-analysis-and-monitoring-evidence-2026-03-13-qwen-live-training-pipeline-analysis-and-monitoring-evidence-2026-03-13.md`
remains valuable as historical throughput and bottleneck evidence, but it is
not the live recovery plan for this lane. Use this ledger for current
training/eval recovery truth and use the March 13 reference for older
throughput analysis only.
