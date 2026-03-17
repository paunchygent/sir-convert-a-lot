---
name: sir-convert-a-lot-qwen-finetuning
description: >-
  Model-specific operator skill for Qwen3-TTS fine-tuning on Hemma and Colab.
  Use when the task is specifically about Qwen TTS training, Swedish language
  expansion with Qwen, Qwen preprocessing or runtime policy, or deciding
  whether a fine-tuned Qwen model should enter the Sir Convert-a-Lot sidecar
  candidate lane.
---

# Sir Convert-a-Lot Qwen Finetuning

## Use This Skill When

- The user wants to fine-tune `Qwen/Qwen3-TTS-12Hz-1.7B-Base`.
- The user wants Swedish support, not just a single custom voice.
- The task involves choosing between Hemma and Colab H100.
- The task involves ROCm, Triton flash attention, or GPU container policy.
- The task involves Swedish speech data curation, preprocessing, or evaluation.
- The task involves deciding whether a trained model is good enough to become a
  sidecar candidate later.

## Do Not Use This Skill For

- Normal sidecar benchmarking that does not involve model training.
- Chatterbox, F5, OpenVoice, or MMS implementation work unless the task is
  explicitly comparing them against a future Qwen fine-tuned candidate.
- Generic speech-model training questions when no Qwen-specific decision is in
  play. For those, use the broader `speech-model-finetuning-on-hemma` skill.

## Source of Truth

Use this skill together with the broader local skill:

- `.agents/skills/speech-model-finetuning-on-hemma/SKILL.md`

- `.agents/skills/sir-convert-a-lot-colab-hemma/SKILL.md`

- `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`

- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

- `docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md`

- `docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md`

- `docs/backlog/tasks/task-116-expand-rixvox-staging-and-run-a-sustained-detached-row-processing-window-for-the-bounded-hemma-pilot.md`

- `docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md`

- `docs/backlog/tasks/task-141-define-frozen-qwen-pilot-dataset-use-for-finetuning.md`

- `docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md`

- `docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md`

- `docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md`

Upstream truth to verify before major claims or runtime changes:

- [Qwen3-TTS model card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)
- [Qwen finetuning README](https://github.com/QwenLM/Qwen3-TTS/tree/main/finetuning)
- [vLLM ROCm docs](https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html#amd-rocm)
- [flash-attention](https://github.com/Dao-AILab/flash-attention)

## First Move

Before proposing anything, classify the request into one of these lanes:

1. `Benchmark lane`
   - Serving/runtime truth only.
   - Current repo home: Task 79 / Task 98.
1. `Single-speaker adaptation lane`
   - Useful for voice transfer experiments.
   - Not the same as general Swedish support.
1. `Language-expansion lane`
   - Multi-speaker Swedish.
   - Current repo home: Epic 08.

If the user says "general Swedish support," always choose lane 3 unless they
explicitly narrow the scope.

## Core Project Position

- The main project target is full fine-tuning of the `1.7B` base model.
- Hemma is viable for bounded pilot work.
- Colab H100 is the scale-up lane, not the only viable lane.
- The end goal is general Swedish support, not a single teacher voice.
- The first bounded Task 101 Hemma pilot must consume a deterministic training
  bundle projected from the frozen pilot root, not the generic promoted Task
  103 preprocessing root.
- The canonical repo-owned materialization surface for that bundle is:
  - `pdm run task-101-pilot-bundle build`
- The detached Task 101 runtime must record both the train and held-out eval
  manifest paths in launch/status/report metadata while staying explicit that
  upstream `sft_12hz.py` is still train-only and does not perform in-training
  evaluation.
- Scheduled Task 101 runs now use the canonical `500/100/3` posture:
  durable checkpoint every `500` optimizer steps, held-out eval every `100`
  steps, retain newest `3` durable trainer-state checkpoints.
- For older pre-schedule checkpoints, the canonical recovery order is:
  standalone held-out eval first, then resume only if the saved cursor is
  compatible with the current bundle contract.
- If a legacy launch requires `--pilot-bundle-root` override, do not assume the
  saved intra-epoch cursor is still meaningful; treat any impossible cursor as
  a fail-closed condition, not a warning.
- If a bounded recovery probe already produced a newer durable checkpoint with
  a compatible cursor, prefer that newer checkpoint for the next strict resume
  rather than resetting to the older legacy step.
- If a preserved legacy launch still carries stale checkpoint cadence or
  retention values, pass explicit resume overrides so the relaunched lane
  truthfully matches the current `500/100/3` scheduled posture.
- If a resumed Task 101 lane fails with repeated non-finite behavior, do not
  keep retrying blind full training runs. The canonical next step is:
  `status -> diagnose-non-finite -> fix -> bounded retry`.
- Story 29 now has explicit committed proof commands for both the preferred
  and fallback gates:
  - preferred gate:
    `qwen-t197-proof launch-window|status-window|launch-gate1500|status-gate1500`
    and
    `qwen-t198-proof launch-window|status-window|launch-gate1500|status-gate1500`
  - fallback gate:
    `qwen-t198-proof launch-fallback1470|status-fallback1470|launch-fallback-eval|status-fallback-eval`
  - the fallback standalone eval is detached through
    `qwen-story29-eval-detached`
- Current Story 29 operator rule after the failed fallback replay:
  - treat the accumulation/fallback replay family as exhausted negative
    evidence on the current code path
  - do not keep launching replay-only RCA variants
  - move to `T206`: prove the true trainable text-token span contract and land
    one canonical code-bearing correction
  - choose that correction by semantic span correctness and minimal blast
    radius first; use performance only as a secondary tiebreaker if multiple
    variants satisfy the same contract
  - after that correction, allow exactly one decisive post-fix proof to
    `1470 + detached standalone eval`
  - if that final post-fix proof still fails numerically before `1470`, stop
    bounded RCA on this preserved lane and escalate to a new design story
- Current post-Story-29 operator rule after Story 30 Candidate 1 landed
  through `T209`:
  - treat `test_semantic_text_embeddings.py` as the required first local gate
    before any new Hemma long proof
  - the next governed long-run owner is `T210`
  - rerun the bounded `1406 -> 1470` gate on the semantic-only assembly code
    path with `gradient_accumulation_steps=1`
  - launch detached standalone eval only if the `1470` checkpoint is truthful
  - if that governed proof still fails before `1470`, do not relaunch the
    same lane; open Candidate 3 instead
- Story 28 / `T187-T191` is the permanent anti-god-file architecture lane for
  the Qwen training control plane and is now delivered. Keep new host-side
  logic in `ml/qwen/training/control_plane/`, detached launch logic in
  `ml/qwen/training/detached_runtime/`, reporting logic in
  `ml/qwen/training/reporting/`, and patched runtime logic in the bounded
  `sft_12hz_*` runtime modules. `orchestrator.py` and `reporting.py` are gone
  and must not be reintroduced.
- Do not trust reused-run `status.json` or `report.json` artifacts unless they
  clearly belong to the active resumed container.
- Intentional detached Task 101 stops now request graceful shutdown and one
  final durable checkpoint when progress advanced beyond the latest saved step.
- Task 100/101 launch surfaces now emit an explicit BuildKit cold-build warning
  before heavy image compilation begins.
- Any future production use must still fit the sidecar-only architecture from
  ADR-0006 and ADR-0007.
- Long-running Hemma preprocessing, training, and corpus-acquisition work must
  run detached from the local client session.
- When Colab runs persist status, logs, or spool JSON into Google Drive and the
  Drive connector is authenticated, inspect those artifacts directly before
  asking the user to run notebook-side status commands.
- When the user provides a direct Drive link, prefer direct id-based metadata
  lookup before Drive search. Search can miss artifacts that are plainly
  reachable by id.
- Hemma storage tiers are fixed:
  - `/srv/scratch` for Docker root, HF/model caches, and hot generated
    preprocessing/training artifacts
  - `/srv/storage` for raw Swedish corpora and colder retained datasets

## Qwen-Specific Decisions

The broader Hemma speech-model skill covers the generic training workflow.
This Qwen skill adds the model-family-specific decisions:

- separate Task 79 / Task 98 serving truth from Epic 08 training truth
- keep the target on the `1.7B` base model
- distinguish official Qwen single-speaker guidance from the repo's planned
  multi-speaker Swedish language-expansion lane. **Crucially, `sft_12hz.py` must be patched to preserve the `speaker_encoder` and `tts_model_type="base"` to avoid collapsing into a single-speaker state.**
- **Patch `dataset.py` to parse multiple speakers, build a `spk_id_map`, and carry a dataset-scoped `speaker_id` through the manifest and batch surfaces. In the current base-model path, this is metadata for governance, eval, and optional future speaker-bank export, not the primary conditioning signal.**
- **Ensure the training patch includes the known community text-projection fix to maintain language adaptation stability.**
- **Rely on Qwen's LLM tokenizer for text normalization. Feed raw Swedish orthography directly with strict punctuation. Do not use external phonemizers.**
- keep Triton flash attention as the default Qwen ROCm path
- decide when a fine-tuned Qwen model is strong enough to enter future
  sidecar-candidate comparison work

## Flash Attention Rules

- Triton flash attention is the default Qwen ROCm lane.
- Do not recommend a permanent disabled-flash-attention posture.
- Disable it only to triage a concrete regression and record that in the
  evidence.
- If serving and training assumptions diverge, call that out explicitly.

## Dataset Strategy

Treat Swedish data as three different roles:

- `KBLab/rixvox`
  - main hours source
  - requires transcript filtering and speaker curation
  - prefer Swedish ASR/WER-backed mismatch filtering before scale-up
- `google/fleurs` Swedish
  - clean short utterances
  - good high-trust smoke and dev/eval source
- `KTH/waxholm`
  - high-trust smoke data and held-out checks

Never treat "available Swedish data" as a single undifferentiated pool.

When planning the corpus, always answer:

- what is the bounded pilot subset?
- what is the scale-up subset?
- what is held out?
- which speakers are excluded from training for evaluation?
- how are low-confidence transcripts filtered?
- which Swedish ASR/WER surface is used to detect transcript mismatch?

For the current pilot lane, also answer:

- which frozen pilot root owns the rows?
- where is the deterministic Task 101 pilot bundle root?
- which finalized manifest families are included?
- how are stable per-speaker `ref_audio` anchors materialized inside the
  bundle?

## Qwen Workflow Overlay

After the broader speech-model skill has set the runtime/data/eval frame, apply
this Qwen-specific order:

1. Confirm the model target:
   - `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
1. Confirm the data policy:
   - pilot subset
   - scale-up subset
   - eval split
   - frozen ownership root for the pilot
   - deterministic Task 101 pilot bundle root
1. Build or verify Qwen preprocessing:
   - transcript normalization
   - reference-audio policy: **One 5-10 second canonical reference clip per speaker, reused across all rows for that speaker.**
   - audio-code generation
   - manifests: **Two layers (rich intermediate + Qwen-ready JSONL with `speaker_id`).**
   - `speaker_id` note: **track it for metadata, splits, and optional future speaker-bank export; current conditioning still comes from `ref_audio -> ref_mel -> speaker_encoder`.**
   - dependency split: **Task 100 owns the training-image stack; Task 103 owns the extra preprocessing/eval stack.**
1. Run a bounded pilot:
   - detached on Hemma by default
   - only after the deterministic pilot bundle exists
   - one real optimizer step minimum
   - **Hemma Smoke Run:** 8-12 hours, 12-16 speakers.
   - **Hemma Pilot:** 24-36 hours, 24-40 speakers.
   - **Colab Scale-up:** 100-300 hours.
   - for sustained Hemma row-processing or training windows, record historical
     GPU load from a real host time-series collector when available; otherwise
     launch the committed Task 116 detached resource monitor in parallel and
     use its `summary` surface for median/min/max host CPU, host RAM, GPU busy,
     and VRAM evidence
1. Evaluate:
   - pronunciation
   - intelligibility
   - prosody
   - held-out speaker behavior
   - operational fit
1. Decide whether the result is:
   - not credible
   - promising but not sidecar-ready
   - ready to enter a future sidecar-comparison lane

## Common Failure Modes

Watch for these specifically:

- transcript quality from `rixvox` is too noisy
- single-speaker assumptions leaking into multi-speaker planning
- flash attention silently disabled without being recorded
- treating the bounded Hemma pilot `20s` clip target as a hard upstream Qwen
  rule instead of a conservative repo heuristic that must be checked against
  live runtime and duration evidence
- claiming that Colab progress cannot be inspected when the relevant status,
  logs, or spool artifacts are already persisted in Google Drive and the Drive
  connector is available
- relying on Drive search alone when the user has already provided the direct
  file or folder link needed for id-based lookup
- assuming `journald` alone is historical GPU monitoring when no periodic GPU
  sampler is actually writing to the journal
- treating official Qwen single-speaker docs as if they already solved the
  multi-speaker Swedish language-expansion problem
- mixing Task 79 serving constraints with the future dedicated fine-tune runtime
- launching Task 101 from the generic promoted preprocessing root instead of a
  deterministic pilot bundle projected from the frozen pilot ownership root

## Promotion Rule

A fine-tuned Qwen model does not become a production candidate just because it
trained successfully.

Before recommending it as a sidecar candidate, require:

- real Swedish language quality evidence
- held-out evaluation
- operational reproducibility
- compatibility with ADR-0006 and ADR-0007
- comparison against the current benchmarked TTS candidates when relevant
