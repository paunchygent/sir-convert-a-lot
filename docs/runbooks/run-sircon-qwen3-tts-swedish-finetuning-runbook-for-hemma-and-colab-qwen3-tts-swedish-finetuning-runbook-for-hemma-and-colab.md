---
type: runbook
id: RUN-SIRCON-qwen3-tts-swedish-finetuning-runbook-for-hemma-and-colab
title: Qwen3-TTS Swedish Finetuning Runbook for Hemma and Colab
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-02'
status: active
summary: Qwen3-TTS Swedish Finetuning Runbook for Hemma and Colab
system: hemma.hule.education
retired_ids:
  - RUN-qwen3-swedish-finetuning-on-hemma-and-colab
---

## Trigger

## Preconditions

## Steps

## Expected Results

## Stop Conditions

## Rollback

## Historical Source Content

### Purpose

Define the canonical Sir Convert-a-Lot workflow for planning and eventually
running Swedish `Qwen/Qwen3-TTS-12Hz-1.7B-Base` fine-tuning on the real Hemma
ROCm host and on Google Colab H100, using the domain-centric ML architecture.

### Ground Truth

This runbook is intentionally anchored to these truth surfaces:

- Repo governance and operations:
  - `docs/runbooks/run-sircon-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot.md`
  - `docs/decisions/adr-sircon-0005-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md`
- ML Domain Root:
  - `scripts/sir_convert_a_lot/ml/qwen/`
- CLI Entrypoints:
  - `scripts/sir_convert_a_lot/cli/ml/`

### What We Are Actually Trying To Do

The target is:

- `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- full fine-tuning objective
- Swedish language expansion
- multi-speaker training/evaluation discipline
- containerized Hemma runtime as the default training and scale lane

### Non-Negotiables

- Use containers, never raw host `systemd` training.
- Use domain-centric commands:
  - `pdm run qwen-train launch`
  - `pdm run qwen-preprocess`
- Keep training runtimes isolated from the main service image.
- Preserve canonical persistent cache roots on Hemma.

### Frozen Pilot Dataset Rule

The retained pilot-owned preprocessing source is recorded at this historical path:

- `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task140-qwen-pilot-frozen-20260311a`

Preserve this evidence path. New primary corpus placement uses
`/home/paunchygent/.local/share/sir-convert-a-lot/data/qwen3-tts-swedish-corpus`;
the backup SSD is not a new working corpus destination. The parent must verify
the migrated source and preserved logical paths before training projects a
deterministic bundle from it. See [Storage And Cutover](#storage-and-cutover).

### Current Runtime Separation

Use the current repo surfaces as two different lanes:

1. Existing Qwen serving/benchmark lane:
   - `scripts/sir_convert_a_lot/cli/ml/qwen_benchmarks.py`
   - `vllm/vllm-omni-rocm`
2. New Qwen fine-tuning lane:
   - `scripts/sir_convert_a_lot/ml/qwen/training/`
   - dedicated training runtime (`ml.qwen.common.runtime`)

### Training Lane Direction

- Hemma is the default training lane for bounded pilot work and scale-up.
- Colab remains an optional fallback or comparison lane.

### Fine-Tune Graph Contract

For the canonical fine-tuning lane, keep the upstream no-projection training
graph:

- train and held-out eval use text embeddings directly in the fine-tune
  forward path
- `talker_runtime` should still fingerprint `text_projection` when present so
  runtime-shape drift remains visible
- do not inject `text_projection` into the fine-tune graph unless a future
  task explicitly redefines the training contract and proves it live

### Held-Out Eval Posture

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

### Shard and Work Allocation

Future incremental allocation has a strict canonical path:

- dedupe completed run roots into one canonical processed root
- build one immutable shard registry from the remaining universe
- issue worker processing units only from shard ids

Canonical commands:

- `pdm run qwen-canonical-root build`
- `pdm run qwen-shard build-registry`
- `pdm run qwen-shard issue-unit`

### Dependency Baseline

Qwen research dependencies are owned by the non-distributable nested project
under `qwen/`:

- `qwen/pyproject.toml` declares the Python 3.12 dependency boundary.
- `qwen/pdm.lock` is the authoritative Qwen research lock.
- install or refresh the isolated environment with
  `pdm install -p qwen -G dev`.
- verify the boundary with `pdm run -p qwen test` and
  `pdm run -p qwen typecheck`.
- continue to invoke operational commands through their stable root surfaces,
  such as `pdm run qwen-preprocess` and `pdm run qwen-train`.

The Hemma requirement set is derived from the nested lock. Regenerate it with
`pdm run -p qwen export-container-requirements`. The export excludes generic
Torch, Triton, CUDA, and NVIDIA runtime packages because the image installs its
governed ROCm-compatible Torch and Triton stack separately.

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

- install: `pdm install -p qwen -G dev`
- run: `pdm run qwen-preprocess`
- runner: `scripts/sir_convert_a_lot/cli/ml/qwen_preprocess.py`

### Execution Order (New Posture)

1. **Verify Infrastructure:**
   - `pdm run run-hemma -- pdm run qwen-smoke`
2. **Source Selection:**
   - `pdm run qwen-preprocess --stage source-selection --source-mode staged-public-corpus`
3. **Row Processing (Detached):**
   - `pdm run qwen-preprocess --stage row-processing --row-worker-count 4`
4. **Finalization (GPU-backed):**
   - `pdm run qwen-preprocess --stage finalization`
5. **Bundle Materialization:**
   - `pdm run qwen-bundle build`
6. **Training Launch:**
   - `pdm run qwen-train launch`
7. **Status Inspection:**
   - `pdm run qwen-train status`

### Fault-Tolerant Resume

- Scheduled Qwen pilot runs use this canonical control posture:
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

### Bounded RCA Mitigation Gate From `1406`

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

### Story 32 Experiment Governance

Use one active question at a time:

| Experiment class | Current active surface                                                     | Operator purpose                                       |
| ---------------- | -------------------------------------------------------------------------- | ------------------------------------------------------ |
| `provenance`     | `pdm run qwen-historical-pilot-control` with `launch`, `status`, or `stop` | Historical-contract recreation and control evidence    |
| `mechanism`      | `pdm run qwen-stability-lab run` and `gate`                                | Bounded stabilization exploration and promotion gating |
| `recovery`       | governed `qwen-train launch/status` proof lane                             | Short fresh-start governed proof only after promotion  |

Operator rules:

- record active run truth in
  `docs/reference/ref-sircon-research-qwen-training-eval-pilot-progress-ledger-2026-03-15-qwen-training-eval-pilot-progress-ledger-2026-03-15.md`
  and do not create a second live ledger
- keep one question per run
- do not make causal claims when code, bundle root, sampler/batching policy,
  seed/shuffle, assembly mode, mask policy, or stabilizer variant changed
  together
- use the promotion ladder:
  local gate -> short bounded fresh-start run -> longer governed proof

### Active Operator Flow

For provenance questions:

- use `qwen-historical-pilot-control`
- latest resolved result:
  `task221-20260317t193125z-a1` is negative recreated-control evidence
- treat that result as provenance only:
  it is stronger than `T220`, but it is not a mechanism or recovery result

For mechanism questions:

- Story 31 owns the active mechanism lane
- for bounded stabilizer exploration, use the committed exploration surface:
  - local or attached short run:
    `pdm run qwen-stability-lab run --skip-build`
  - attached Hemma short run through the canonical wrapper:
    `pdm run run-hemma -- pdm run qwen-stability-lab run --output-root build/verification/qwen-stability-lab --skip-build`
- new runs require the parent-verified Hot backing for repository `build/`;
  retained `/srv/scratch/...` run paths remain historical evidence addresses
- the lab writes one compact matrix run under a single output root:
  - `results.json`
  - `results.md`
  - `variant-reports/<variant>.json`
- the mandatory local promotion step before any recovery proof is:
  `pdm run qwen-stability-lab gate --output-root <lab-output-root>`
- for the recreated `T221` step-`1` / iteration-`4` failure family, run the
  committed parity surface before any further stabilizer claim:
  - `pdm run qwen-parity-probe run`
- the parity probe writes:
  - `current-path.json`
  - `intended-path.json`
  - `results.json`
  - `results.md`
- use the parity probe result to decide whether `T227` remediates a verified
  trainer/runtime divergence or Story 31 continues through bounded stabilizer
  work
- read the [pilot progress ledger](../reference/ref-sircon-research-qwen-training-eval-pilot-progress-ledger-2026-03-15-qwen-training-eval-pilot-progress-ledger-2026-03-15.md)
  for `T219`–`T245` run identifiers, classifications and historical `T242`
  bind-root observations; those observations do not establish new Hot backing
- ad hoc runtime bind fallback remains compatibility-only after `T242`;
  installation and fresh physical probes follow [Storage And Cutover](#storage-and-cutover)
- `T246` is now the immediate diagnosis-only mechanism action
- `T246` must split the fp32-scaled layer-15 output result from the final
  emitted tensor before any new stabilizer family or promotion discussion

For recovery questions:

- do not launch the governed fresh-start proof until a mechanism candidate
  passes the local promotion gate
- `T217` is the blocked recovery owner
- when recovery is authorized, use the existing governed `qwen-train`
  fresh-start proof lane rather than inventing a new proof wrapper

### Storage And Cutover

TASK-SIRCON-REP-0033 implements source authority from TASK-SKILL-REP-0316
D05/D09/D11. Nonvisual build/proof output defaults to Hot owner jobs at
`/home/paunchygent/.local/share/sir-convert-a-lot/jobs/build`. The parent cutover
supplies Hot home backing and preserves repository `build/` and Docker-visible
`~/.data/sir-convert-a-lot/build`. Existing symlinks refuse retargeting until
their backing is migrated and verified. Cache retains its separate legacy source
default `/srv/scratch/sir-convert-a-lot/cache`; its owner must reconcile placement
under the shared contract before activation.

The [Hemma operations doorway](run-sircon-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot.md#storage-placement-and-cutover)
routes to the authoritative shared migration and backup procedure. The parent
owns bind-root installation with `pdm run run-hemma -- pdm run qwen-docker-bind-roots install`
and subsequent `status`/`probe` receipts during that cutover. Record actual
backing and probe results; source defaults establish neither physical placement
nor expected values of `canonical_probe_ok` and `home_probe_ok`.

Legacy scratch candidates preserve the 12-hour age, newest 2/4 roots, 64/96 GiB
free thresholds, protected paths, active-Qwen guard and manual block file.
Selected trees evacuate with original-path symlinks into
`/home/paunchygent/.local/share/sir-convert-a-lot/jobs/legacy-scratch-archive`,
without automatic deletion or an archive TTL. `/srv/storage` is backup-only;
scratch is visual-only. Both refuse nonvisual primary destinations.

Sir never prunes Docker. The shared weekly `hemma-docker-cleanup` owns that
maintenance. `--prune-docker-state` and true runtime/timer settings refuse before
mutation. The legacy storage command's `--skip-docker-cleanup` is a compatibility
option; cleanup stays off regardless.

Keep the hourly timer disabled during cutover. Execution history and dated host
receipts belong with TASK-SIRCON-REP-0033 and its parent evidence.
The parent owns writer-safe migration,
replacement maintenance, installation and observed proof. Source checks do not
prove activation. The exclusive private-Qwen GPU hold remains in force.

`maintain` and `remediate` require separate host mutation authority. Inspect with:

1. Audit current pressure:
   `pdm run run-hemma -- pdm run qwen-scratch-policy audit`

2. Inspect timer state:
   `pdm run run-hemma -- pdm run qwen-scratch-policy status-timer`

Before any separately authorized `T197`/`T198` launch, satisfy the proof wrapper
headroom gate. Preserve referenceable proof bytes and logical paths; the backup
owner covers actual research data independently.
