---
name: speech-model-finetuning-on-hemma
description: >-
  Generic operator skill for speech-model fine-tuning on Hemma and Colab. Use
  when the task involves TTS or speech-model training, GPU runtime choice,
  ROCm or H100 containers, dataset curation, preprocessing, checkpoint
  strategy, evaluation design, or deciding whether a trained model is ready for
  downstream serving consideration.
---

# Speech Model Finetuning On Hemma

## Use This Skill When

- The task involves training or fine-tuning a speech or TTS model.
- The user wants help choosing between Hemma and Colab H100.
- The task involves ROCm, CUDA, flash attention, or GPU container policy.
- The task involves speech dataset curation or preprocessing.
- The task involves evaluation, checkpointing, or promotion criteria for a
  trained model.

## Do Not Use This Skill For

- Pure inference or serving tasks with no training component.
- Audio generation requests that do not involve model training.
- Model-family-specific implementation details when a narrower model skill
  exists and clearly applies.

## First Questions To Resolve

Before proposing a path, answer these:

1. Is the user trying to do:
   - a benchmark,
   - a single-speaker adaptation,
   - or a genuine language-expansion / multi-speaker fine-tune?
1. Does the task need:
   - Hemma bring-up truth,
   - Colab scale,
   - or both?
1. What is the actual dataset policy:
   - pilot subset,
   - scale-up subset,
   - held-out evaluation split?
1. What is the promotion target:
   - research result only,
   - sidecar candidate later,
   - or direct product comparison?

## Runtime Choice Rules

Choose Hemma when the task needs:

- real local GPU truth
- ROCm/container compatibility proof
- cache and wrapper discipline
- clean GPU baseline measurements
- bounded pilot runs

Choose Colab H100 when the task needs:

- faster scale-up
- larger curated subsets
- shorter training wall-clock
- more headroom for checkpoint-heavy runs

Prefer both when the task is strategic:

- Hemma for proof and operational fit
- Colab for scaling and comparison

## GPU and Container Rules

- Use containers for serious training work.
- Do not rely on raw host processes as the primary lane.
- Use detached execution for long-running Hemma work so the job does not
  depend on the local client or tunnel staying alive.
- Treat attached remote execution as probe-only.
- Confirm the GPU is idle before real runs.
- Record exact runtime truth before and after the run.
- For sustained Hemma runs, record historical GPU load from a real host
  time-series collector when available; otherwise launch a committed detached
  resource monitor surface for the run and use its summary artifacts for host
  CPU, host RAM, GPU, and VRAM evidence.
- Keep cache roots explicit and stable.
- Keep storage tiers explicit and stable:
  - `/srv/scratch` for Docker root, caches, and hot generated artifacts
  - `/srv/storage` for raw corpora and colder retained datasets
- If flash attention is disabled, that must be an explicit triage choice, not a
  hidden default.

## Dataset Rules

Never accept "all available speech data" as sufficient planning.

Always separate:

- core training pool
- dev/eval pool
- held-out speakers
- noisy or weakly aligned data that needs filtering
- pilot subset versus scale-up subset

For weakly aligned transcripts, require an explicit filtering policy before
recommending scale-up training.

If the language is Swedish and the corpus includes weakly aligned broadcast or
parliamentary data, prefer an explicit Swedish ASR/WER mismatch filter rather
than only trusting the provided transcript.

## Training Workflow

Use this order by default:

1. Classify the task:
   - benchmark
   - single-speaker adaptation
   - language expansion
1. Pick the runtime:
   - Hemma
   - Colab
   - both
1. Bound the data:
   - pilot subset
   - scale-up subset
   - eval split
1. Define preprocessing:
   - transcript normalization
   - audio normalization
   - manifest schema
   - code/token generation if the model requires it
1. Run a bounded pilot first.
1. Evaluate before scaling.
1. Scale only after the pilot has both runtime truth and quality evidence.

## Evaluation Standard

Do not let evaluation collapse into "loss decreased" or "sounds fine."

Separate:

- runtime truth
- linguistic quality
- speaker generalization
- artifact rate
- throughput and checkpoint behavior
- operational reproducibility

At minimum, keep:

- held-out prompts
- held-out speakers when relevant
- manual listening notes
- runtime and memory metrics
- historical GPU median/min/max evidence for longer unattended Hemma windows
- checkpoint/output locations
- short promotion verdict

Do not treat `journald` alone as historical GPU monitoring unless a separate
sampler service is already writing periodic GPU samples into the journal.

## Failure Patterns To Watch

- GPU not actually idle before the run
- wrong runtime path compared with the claimed environment
- container missing visible GPU devices
- cache drift or redownload churn
- noisy transcripts poisoning the training signal
- pilot evidence without an eval split
- Colab-only success with no Hemma parity
- Hemma-only success with no scale-up plan
- hidden flash-attention or backend changes not reflected in reports

## Evidence Standard

For every serious run, capture:

- repo `HEAD`
- exact command surface
- runtime or image identity
- cache roots
- dataset slice identity
- clean GPU baseline
- peak VRAM and GPU busy
- checkpoint/output paths
- report JSON
- report Markdown
- short qualitative verdict

## Promotion Rule

A trained speech model is not ready for downstream adoption just because it
fits in memory or completes training.

Require:

- bounded pilot proof
- held-out evaluation
- reproducible runtime path
- explicit comparison against current alternatives when product use is implied
