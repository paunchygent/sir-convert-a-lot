---
type: runbook
id: RUN-qwen3-swedish-finetuning-on-hemma-and-colab
title: Qwen3-TTS Swedish Finetuning Runbook for Hemma and Colab
status: active
created: 2026-03-08
updated: 2026-03-18
owners:
  - platform
system: hemma.hule.education
tags:
  - qwen
  - tts
  - finetuning
  - swedish
  - hemma
  - colab
links:
  - .agents/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-27-transition-to-domain-centric-ml-pipeline-structure.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/tasks/task-181-add-real-in-training-held-out-eval-loop-to-task-101-qwen-training.md
---

## Purpose

Define the canonical Sir Convert-a-Lot workflow for planning and eventually
running Swedish `Qwen/Qwen3-TTS-12Hz-1.7B-Base` fine-tuning on the real Hemma
ROCm host and on Google Colab H100, using the domain-centric ML architecture.

## Ground Truth

This runbook is intentionally anchored to these truth surfaces:

- Repo governance and operations:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - `docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md`
- ML Domain Root:
  - `scripts/sir_convert_a_lot/ml/qwen/`
- CLI Entrypoints:
  - `scripts/sir_convert_a_lot/cli/ml/`

## What We Are Actually Trying To Do

The target is:

- `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- full fine-tuning objective
- Swedish language expansion
- multi-speaker training/evaluation discipline
- containerized Hemma runtime as the default training and scale lane

## Non-Negotiables

- Use containers, never raw host `systemd` training.
- Use domain-centric commands:
  - `pdm run qwen-train launch`
  - `pdm run qwen-preprocess`
- Keep training runtimes isolated from the main service image.
- Preserve canonical persistent cache roots on Hemma.

## Frozen Pilot Dataset Rule

The current canonical pilot-owned preprocessing source is:

- `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`

Training must use a deterministic training bundle projected from this root.

## Current Runtime Separation

Use the current repo surfaces as two different lanes:

1. Existing Qwen serving/benchmark lane:
   - `scripts/sir_convert_a_lot/cli/ml/qwen_benchmarks.py`
   - `vllm/vllm-omni-rocm`
1. New Qwen fine-tuning lane:
   - `scripts/sir_convert_a_lot/ml/qwen/training/`
   - dedicated training runtime (`ml.qwen.common.runtime`)

## Runtime-Model

The containerized Qwen runtime is canonical for preprocessing and training.
The Hemma host is for orchestration only.

- `pdm run qwen-preprocess` dispatches to the detached stage orchestrator.
- Immutable scratch-backed run roots are mandatory for all preprocessing runs.

## Training Lane Direction

- Hemma is the default training lane for bounded pilot work and scale-up.
- Colab remains an optional fallback or comparison lane.

## Fine-Tune Graph Contract

For the canonical fine-tuning lane, keep the upstream no-projection training
graph:

- train and held-out eval use text embeddings directly in the fine-tune
  forward path
- `talker_runtime` should still fingerprint `text_projection` when present so
  runtime-shape drift remains visible
- do not inject `text_projection` into the fine-tune graph unless a future
  task explicitly redefines the training contract and proves it live

## Current Saturation Evidence (2026-03-13)

Bounded Story 26 evidence currently shows:

- `task161-20260313t212725z-cache-off`: steady-state train GPU median `26%`
- `task161-20260313t212725z-cache-on`: steady-state train GPU median `8%`
- `task162-20260313t220644z-profile`: steady-state train GPU median `3%`
- all three runs reported `ref_mel_cache` stats as
  `cache_hits=0`, `cache_misses=0`, `cache_size=0`
- `task162` ROCm attribution:
  - HIP API `98.74s`
  - kernels `102.08s`
  - memory copy `1.73s`
  - top HIP API calls:
    `hipLaunchKernel=44.18s`, `hipMemcpyWithStream=21.52s`,
    `hipEventSynchronize=17.89s`

Operational interpretation:

- the current lane is host-orchestration/synchronization bound
- runtime `ref_mel` cache should not be treated as a proven saturation lever
- persistent `NaN` loss is a quality blocker; no saturation acceptance should
  be claimed from a run with unfixed `NaN` training state

## Held-Out Eval Posture

The Task 101 lane already carries the held-out `swedish_checkpoint_dev`
manifest through launch metadata, status, and terminal reports. That contract
is no longer sufficient for long pilot runs.

Current implementation truth after the `T181` eval slice lands locally:

- the held-out eval manifest exists and is required,
- the inner patched Qwen trainer prepares a real eval dataset and dataloader
  from `--eval-jsonl`,
- bounded in-training held-out eval runs at explicit optimizer-step cadence,
- and eval loss now persists into trackers, live status, and terminal reports.

The next required proof is operational rather than contractual:

- run one short bounded Hemma launch with the real eval loop enabled,
- confirm `status.json` and `report.json` carry live and terminal eval fields,
- then promote the eval loop into the longer pilot lane.

Follow-on control posture after `T182`:

- use `qwen-train eval` for standalone checkpoint eval against explicit held-out
  material when we want a real check without rebuilding the full pilot bundle,
- and use the schedule runner for planned
  `train -> stop -> eval -> resume` cadence around durable checkpoints.
- when a resumed lane fails with non-finite behavior, use
  `qwen-train diagnose-non-finite` as the canonical next step before any new
  bounded retry.
- Story 28 / `T187-T191` is the permanent architecture-governance lane for the
  Qwen training control plane and patched runtime and is now delivered. New
  feature work must stay inside the bounded package owners:
  `ml/qwen/training/control_plane/`,
  `ml/qwen/training/detached_runtime/`,
  `ml/qwen/training/reporting/`, and the focused `sft_12hz_*` runtime modules.
  The deleted `orchestrator.py` and `reporting.py` files must not return.

## Shard and Work Allocation

Future incremental allocation has a strict canonical path:

- dedupe completed run roots into one canonical processed root
- build one immutable shard registry from the remaining universe
- issue worker processing units only from shard ids

Canonical commands:

- `pdm run qwen-canonical-root build`
- `pdm run qwen-shard build-registry`
- `pdm run qwen-shard issue-unit`

## Dependency Baseline

Qwen training image baseline:

- `qwen_tts`
- ROCm-compatible `torch`
- `accelerate`, `transformers`, `flash_attn`

Canonical runtime assets:

- `containers/qwen-finetune-hemma/Dockerfile`
- `scripts/sir_convert_a_lot/ml/qwen/training/trainer_smoke_probe.py`

Wrapper-driven Hemma smoke command:

```bash
pdm run run-hemma -- pdm run qwen-smoke
```

Task 203 codebook-fusion proof commands:

- Attached short proof when the image already exists:

```bash
pdm run run-hemma -- pdm run qwen-codebook-fusion-proof --skip-build
```

- Detached proof launch for longer Hemma evidence collection:

```bash
pdm run run-hemma -- pdm run qwen-codebook-fusion-proof-detached launch -- --skip-build
```

- Detached proof status / artifact refresh:

```bash
pdm run run-hemma -- pdm run qwen-codebook-fusion-proof-detached status
```

Artifacts land under:

- `build/verification/qwen-codebook-fusion-proof/`
- `launch.json`, `status.json`, `status.md`, `proof.log`,
  `worker-status.json`, `report.json`, `report.md`, and `failure.txt`

Preprocessing/eval baseline:

- `datasets`, `jiwer`, `librosa`, `soundfile`

Canonical repo surface for the preprocessing lane:

- install: `pdm install -G qwen-preprocessing`
- run: `pdm run qwen-preprocess`
- runner: `scripts/sir_convert_a_lot/cli/ml/qwen_preprocess.py`

## Execution Order (New Posture)

1. **Verify Infrastructure:**
   - `pdm run run-hemma -- pdm run qwen-smoke`
1. **Source Selection:**
   - `pdm run qwen-preprocess --stage source-selection --source-mode staged-public-corpus`
1. **Row Processing (Detached):**
   - `pdm run qwen-preprocess --stage row-processing --row-worker-count 4`
1. **Finalization (GPU-backed):**
   - `pdm run qwen-preprocess --stage finalization`
1. **Bundle Materialization:**
   - `pdm run qwen-bundle build`
1. **Training Launch:**
   - `pdm run qwen-train launch`
1. **Status Inspection:**
   - `pdm run qwen-train status`

## Fault-Tolerant Resume

- Scheduled Task 101 runs use this canonical control posture:
  - durable checkpoint every `500` optimizer steps
  - held-out eval every `100` optimizer steps
  - retain newest `3` durable trainer-state checkpoints
  - force one durable checkpoint at epoch end before resume/eval decisions
- Latest durable step is recorded in `latest_checkpoint.json`.
- Schedule-driven resumes advance the canonical latest detached launch pointer,
  so pointerless `qwen-train status` and `qwen-train stop` target the resumed
  launch rather than the earlier stopped source launch.
- Schedule control fails closed when checkpoint, eval-manifest, or bundle-root
  paths escape the mounted scratch root or are missing from disk.
- Resume with: `pdm run qwen-train resume`.

## Bounded RCA Mitigation Gate From `1406`

After the exact `1401` capture, the clean bounded replay through `1406`, the
failed bounded continuation at `1417`, and the later bounded replay that
reproduced `1417`, the current operator rule is no longer "resume the pilot
again and hope the instability moved away." It is:

- treat
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
  as the canonical RCA checkpoint
- do not launch another fresh continuation or restart yet
- use `1406` only for bounded mitigation proofs

Current narrowed RCA:

- the `1417` failure is reproducible from the exact `1406` checkpoint
- the first bad backward surface is `input_text_embedding.grad` on microbatch
  `851`
- `507` of `508` token positions in that sample went non-finite
- the poisoned `93` `text_embedding.weight` rows match the sample's `93`
  unique token ids exactly
- token id `151671` appeared `375` times in the failing sample, which aligns
  with the active codec-span text-pad surface in the current Qwen batch
  contract

Operational consequence:

- the next proof must be a bounded mitigation replay, not a long pilot resume
- the first mitigation to test is narrowing `text_embedding_mask` to the true
  text span only, or equivalently zeroing/detaching the codec-span text-pad
  positions
- `T195` now makes that mitigation explicit in the committed control plane:
  - `--text-embedding-mask-policy legacy_codec_span`
  - `--text-embedding-mask-policy text_span_only`
  - fresh `qwen-train launch` runs default to `text_span_only`
  - replay/resume/eval/capture flows keep backward-compatible legacy behavior
    unless operators pass an override
- `T196` now makes accumulation explicit in the same operator surface:
  - `--gradient-accumulation-steps 4`
  - `--gradient-accumulation-steps 2`
  - `--gradient-accumulation-steps 1`
  - the canonical default remains `4`
  - launch/resume/capture/diagnose/eval/schedule artifacts now record the
    effective value
- only if that mask-only mitigation does not clear the `1417` failure should
  operators test lower `gradient_accumulation_steps` as the secondary bounded
  ablation
- once Story 29 proves the winning mitigation, remove `legacy_codec_span`
  before launching the next clean restart; keep the legacy mode only for
  bounded RCA reproduction until that point
- the preferred and fallback replay gates are both now negative on the current
  code path:
  - accumulation `4`, `2`, and `1` all failed the preferred gate
  - the direct fallback replay also failed at optimizer step `1449`
- Story 29 therefore now moves to `T206` as the final code-bearing RCA/design
  lane:
  - prove the true trainable text-token span contract
  - land one canonical correction for that contract
  - if several nearby fixes perform similarly, choose the variant that is most
    semantically correct and least invasive before using performance as a
    tiebreaker
  - then run exactly one decisive post-fix proof
- the final post-fix restart rule is:
  - clear `1406 -> 1470`
  - then complete detached standalone eval from that checkpoint
  - if that post-fix proof passes, restart may proceed
- the stop rule is:
  - if that single post-fix proof still fails numerically before `1470`,
    bounded RCA on the preserved Task 101 lane stops and any further work must
    be a new design/architecture story
- Story 29 / `T195-T206` is now historical bounded-RCA evidence:
  the replay-family wrappers stay callable for reference and reproduction, but
  they are no longer part of the active operator flow

## Story 32 Experiment Governance

Use one active question at a time:

| Experiment class | Current active surface | Operator purpose |
| --- | --- | --- |
| `provenance` | `pdm run qwen-t221-historical-control <launch|status|stop>` | Historical-contract recreation and control evidence |
| `mechanism` | `pdm run qwen-story31-stability-lab run` and `gate` | Bounded stabilization exploration and promotion gating |
| `recovery` | governed `qwen-train launch/status` proof lane | Short fresh-start governed proof only after promotion |

Operator rules:

- record active run truth in
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`
  and do not create a second live ledger
- keep one question per run
- do not make causal claims when code, bundle root, sampler/batching policy,
  seed/shuffle, assembly mode, mask policy, or stabilizer variant changed
  together
- use the promotion ladder:
  local gate -> short bounded fresh-start run -> longer governed proof

## Active Operator Flow

For provenance questions:

- use `qwen-t221-historical-control`
- latest resolved result:
  `task221-20260317t193125z-a1` is negative recreated-control evidence
- treat that result as provenance only:
  it is stronger than `T220`, but it is not a mechanism or recovery result

For mechanism questions:

- Story 31 owns the active mechanism lane
- for bounded stabilizer exploration, use the committed exploration surface:
  - local or attached short run:
    `pdm run qwen-story31-stability-lab run --skip-build`
  - attached Hemma short run through the canonical wrapper:
    `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab --skip-build`
- the lab writes one compact matrix run under a single output root:
  - `results.json`
  - `results.md`
  - `variant-reports/<variant>.json`
- the mandatory local promotion step before any recovery proof is:
  `pdm run qwen-story31-stability-lab gate --output-root <lab-output-root>`
- for the recreated `T221` step-`1` / iteration-`4` failure family, run the
  committed parity surface before any further stabilizer claim:
  - `pdm run qwen-story31-parity-probe run`
- the parity probe writes:
  - `current-path.json`
  - `intended-path.json`
  - `results.json`
  - `results.md`
- use the parity probe result to decide whether `T227` remediates a verified
  trainer/runtime divergence or Story 31 continues through bounded stabilizer
  work
- `T219` is now recorded as negative bounded evidence under
  `task219-20260317t180700z-a1`
- `T228` is now complete as the ranked closure of that family
- `T229` is now complete as the narrowed rerun under
  `task229-20260318t064712z-a1`
- the target `sub_talker_loss` family localizes to
  `talker_core.layer_16.input_layernorm`
- `T230` is now complete as the negative bounded normalization-entry rerun
  under `task230-20260318t082049z-a1`
- `T231` is now complete as the explicit no-winner promotion decision
- `T232` is now complete as the lane decision to stay in mechanism
- `T233` is now complete as the normalization-internal rerun under
  `task233-20260318t112544z-a1`
- the first verified internal surface is now
  `talker_core.layer_16.input_layernorm.output`
- `T234` is now complete under `task234-20260318t123644z-a1`
- no variant stayed finite or earned promotion; the strongest `0p5` member
  shifted the pair and `line-13` `sub_talker_loss` cases to
  `talker_core.layer_15.output`, while `line-4` still first broke at
  `talker_core.layer_16.input_layernorm`
- `T235` is now complete under `task235-20260318t140352z-a1`
- the disagreement is repeatable: pair and `line-13` stay at
  `talker_core.layer_15.output`, while `line-4` stays at
  `talker_core.layer_16.input_layernorm`
- `T236` is now complete under `task236-20260318t145434z-a1`
- the outlier is a genuine row-local seam difference: pair and `line-13`
  stay at `talker_core.layer_15.output`, while `line-4` stays at
  `talker_core.layer_16.input_layernorm.output`
- `T237` is now complete under `task237-20260318t154708z-a1`
- the `1e3` fp32-output-cap winner converged pair, `line-13`, and `line-4`
  `sub_talker_loss` to `talker_core.layer_15.output`
- `T240` is now complete under `task240-20260318t165458z-a1`
- all three normative `sub_talker_loss` rows first broke at
  `talker_core.layer_15.output`, so the convergence class is
  `converged_layer15_output`
- `T241` is now complete under `task241-20260318t175714z-a1`
- all three normative `sub_talker_loss` rows still first broke at
  `talker_core.layer_15.output`, so the classification is
  `converged_layer15_output_residual`
- `T242` is now complete as the permanent Hemma bind-root contract:
  install the persistent bind-root service with
  `pdm run run-hemma -- pdm run qwen-docker-bind-roots install`, then use
  `status` and `probe` as the normal preflight before new Qwen runs
- expected host truth after install:
  - `/srv/scratch/sir-convert-a-lot/{build,cache}` remains canonical storage
  - Docker still cannot use fresh `/srv/scratch/...` bind mounts directly
  - `probe` should therefore report `canonical_probe_ok=false`,
    `home_probe_ok=true`, and the preferred effective roots under
    `/home/paunchygent/.data/sir-convert-a-lot/`
- ad hoc runtime bind fallback is compatibility-only after `T242`
- `T243` is now complete under `task243-20260318t190832z-a1`
- all three normative `sub_talker_loss` rows first broke at
  `talker_core.layer_15.output`, so the classification is
  `converged_layer15_output_return`
- `T244` is now complete under `task244-20260318t193736z-a1`
- all three normative `sub_talker_loss` rows still first broke at
  `talker_core.layer_15.output`, so the classification is
  `converged_output_return`
- `T245` is now complete under `task245-20260318t202916z-a1`
- all three normative `sub_talker_loss` rows still first broke at
  `talker_core.layer_15.output`, so the classification is `multiply_not_causal`
- `T246` is now the immediate diagnosis-only mechanism action
- `T246` must split the fp32-scaled layer-15 output result from the final
  emitted tensor before any new stabilizer family or promotion discussion

For recovery questions:

- do not launch the governed fresh-start proof until a mechanism candidate
  passes the local promotion gate
- `T217` is the blocked recovery owner
- when recovery is authorized, use the existing governed `qwen-train`
  fresh-start proof lane rather than inventing a new proof wrapper

## Historical Story 29/30 Surfaces

These surfaces remain callable, but they are not part of the active operator
flow:

- `qwen-story30-freshstart-proof`: `legacy-readonly`
- `qwen-story30-backward-lineage`: `legacy-readonly`
- `qwen-t197-proof`: `deprecated` for new work
- `qwen-t198-proof`: `deprecated` for new work

## Story 29 Scratch Governance

Story 29 proof lanes are now governed by an explicit hot-versus-cold storage
policy on Hemma:

- keep active proof/run roots on `/srv/scratch`
- demote cold completed artifact trees onto `/srv/storage` while preserving
  symlink-backed path stability at the original scratch path
- prune only non-active Docker state when reclaiming scratch headroom

Canonical commands:

1. Audit current pressure:
   `pdm run run-hemma -- pdm run qwen-scratch-policy audit`
1. Run the recurring idle-safe maintenance pass first for routine headroom
   recovery:
   `pdm run run-hemma -- pdm run qwen-scratch-policy maintain --prune-docker-state`
1. Archive explicit cold artifact trees and optionally prune Docker:
   `pdm run run-hemma -- pdm run qwen-scratch-policy remediate --source-path <scratch-path> [--source-path <scratch-path> ...] [--prune-docker-state]`
1. Install the recurring timer once the maintenance policy is trusted on the
   host:
   `pdm run run-hemma -- pdm run qwen-scratch-policy install-timer --enable-linger --prune-docker-state`
1. Inspect timer state:
   `pdm run run-hemma -- pdm run qwen-scratch-policy status-timer`

Operator rule:

- do not relaunch `T197` or `T198` until the scratch audit reports enough free
  bytes for the proof wrapper headroom gate
- do not let the recurring timer race an active proof or training lane; the
  committed maintenance pass blocks itself when active `qwen-*` containers or
  the explicit scratch-maintenance block file are present
- when older proof/run roots must remain referenceable from docs, archive them
  onto `/srv/storage` and keep a symlink at the original path instead of
  deleting them blindly

## Legacy Checkpoint Recovery Rule

When recovering an older Task 101 checkpoint that predates the current
scheduled-control contract, do not jump straight into resumed training.

Canonical recovery order:

1. Run standalone held-out eval against the candidate checkpoint first.
1. Only then consider `qwen-train resume`.
1. If the legacy launch metadata points at a stale bundle root, pass an
   explicit replacement `--pilot-bundle-root`.
1. If that preserved legacy launch also carries stale checkpoint cadence or
   retention settings, pass explicit resume overrides for
   `--checkpoint-interval-steps`, `--eval-interval-steps`, and
   `--durable-checkpoint-retention` so the relaunched lane truthfully matches
   the current scheduled contract.
1. If the saved durable checkpoint cursor is impossible for the current bundle
   length, treat that as a hard stop rather than a recoverable warning.
1. If a bounded diagnostic recovery probe already wrote a newer durable
   checkpoint with a compatible cursor, prefer that newer checkpoint for the
   next strict resume instead of rolling back to the older legacy step.

Operator interpretation:

- A resumed launch that reuses an old run root must not surface stale
  pre-resume `status.json` or `report.json` artifacts as if they belonged to
  the active container.
- A checkpoint whose saved `next_step_in_epoch` exceeds the current
  `dataloader_length` is not safe to resume blindly; this usually means the
  checkpoint is being paired with a different bundle contract.
- Short recovery probes that only prove "the container came back and wrote a
  new checkpoint" are diagnostic evidence, not acceptance evidence.
- Keep live recovery and progress notes in the dedicated reference ledger,
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`,
  rather than adding operational logs to the skill doc.
- For repeated non-finite failures on the preserved Task 101 lane, the
  canonical flow is now:
  `status -> keep the no-projection graph -> mint a checkpoint near the known boundary -> diagnose-non-finite -> fix -> bounded retry`.

## Hemma Storage Tiers

- SSD work tier: `/srv/scratch` (Builds, caches, active training).
- HDD bulk-data tier: `/srv/storage` (Raw corpora, frozen roots, cold retained
  proof/run artifacts).
- OS disk: `/` (Avoid for ML artifacts).
