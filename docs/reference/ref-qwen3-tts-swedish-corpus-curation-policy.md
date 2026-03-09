---
type: reference
id: REF-qwen3-tts-swedish-corpus-curation-policy
title: Qwen3-TTS Swedish Corpus Curation Policy
status: active
created: 2026-03-08
updated: 2026-03-08
owners:
  - Olof
links:
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-guide.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-research-map-2026-03-08.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - https://huggingface.co/datasets/KBLab/rixvox
  - https://huggingface.co/datasets/google/fleurs
  - https://huggingface.co/datasets/KTH/waxholm
---

## Purpose

Define the canonical Swedish corpus policy for Epic 08 so the Qwen `1.7B`
full-finetune lane uses one reviewable corpus contract instead of drifting
between ad hoc subset choices.

This policy closes `T102` by naming:

- the dataset roles,
- the transcript and speaker filters,
- the bounded Hemma pilot subset,
- the later Colab scale-up subset,
- the checkpoint-dev versus final held-out split,
- and the preprocessing hand-off into `T103`.

## Dataset Inventory

| Dataset | Approximate volume | Speaker situation | Transcript caveats | Canonical role |
| --- | --- | --- | --- | --- |
| `KBLab/rixvox` | about `5493h` total, with about `5383h` train | about `1194` speakers across split-defined train/validation/test | transcripts are not always verbatim speech and alignments are automatic | dominant training backbone after filtering |
| `google/fleurs` Swedish (`sv_se`) | about `10h` train plus dev/test | speaker-disjoint train versus dev/test by dataset design | read speech, comparatively clean and stable | dev/test quantitative evaluation and control prompts, not main training backbone |
| `KTH/waxholm` | about `2h 16m` total | small multi-speaker dialogue corpus | some files lack labels and must be excluded; usable files have stronger manual labeling/alignment trust | smoke/control evaluation only, not backbone training |

## Canonical Role Assignment

### Training Backbone

Use filtered `rixvox` train as the only main training backbone for both:

- the bounded Hemma pilot (`T101`)
- and the later Colab H100 scale-up (`T104`)

Reason:

- it is the only approved source with enough hours and speaker breadth to
  support general Swedish language expansion
- it already comes with official train/validation/test boundaries
- it is large enough that we can balance speakers instead of overfitting to a
  small clean corpus

### Dev and Test Controls

Reserve these for evaluation/control:

- `google/fleurs` Swedish validation and test
- `KBLab/rixvox` validation and test
- `KTH/waxholm` labeled usable subset only

Policy:

- do not use `rixvox` validation or test in training
- do not use `fleurs` validation or test in training
- do not use `waxholm` in training

Policy:

- treat `rixvox` validation plus `fleurs` validation as checkpoint-dev only
- treat `rixvox` test plus `fleurs` test as final reporting only
- do not recycle the final test split for checkpoint or subset selection

### Optional Non-Training Smoke Controls

`fleurs` train and labeled `waxholm` may be used for preprocessing smoke checks
and qualitative controls during `T103`, but they are not part of the main
bounded pilot training pool.

## Filtering Policy for `rixvox`

`rixvox` must be filtered rather than used raw.

The filtering contract for `T102` is:

1. keep only rows with usable Swedish speech and non-empty normalized text
1. exclude rows with obvious protocol-only or stage-direction content
1. exclude rows with missing or unusable speaker identity for per-speaker
   reference selection
1. prefer `speaker_from_id=True` rows for the smoke subset and bounded Hemma
   pilot; quarantine the rest until manual review proves they are safe
1. exclude suspected multi-speaker contamination or diarization failures
1. apply transcript-mismatch filtering with Swedish ASR during `T103`
1. apply a boilerplate-text dedup pass before speaker caps are counted
1. cap per-speaker contribution so a few parliamentary voices do not dominate

### Transcript-Mismatch Policy

`T103` must implement a reproducible Swedish ASR mismatch filter before pilot
manifests are finalized.

Pinned backend:

- `KBLab/kb-whisper-large`
- default revision:
  - `strict`

Initial thresholds:

- Hemma smoke and bounded pilot:
  - ASR-WER `<= 0.15`
  - quality tier:
    - high-trust / pilot-admissible
- Colab scale-up admission:
  - ASR-WER `<= 0.20`
  - quality tier:
    - medium-trust / scale-up-only

Rows above `0.20` are out of scope for admission.

These thresholds are intentionally strict for the first pilot. They can be
relaxed later only after manual review shows the filter is discarding too much
good data.

### Duration Policy

Initial clip-duration guidance:

- smoke subset:
  - `2s` to `15s`
- bounded Hemma pilot:
  - target around `2s` to `20s`
  - soft upper bound:
    - allow modest spillover above `20s` when runtime remains stable and the
      speaker-balance policy still holds
- Colab scale-up:
  - `2s` to `30s`

Important interpretation:

- these are repo heuristics, not a strongly evidenced upstream Qwen hard rule
- the official Qwen public docs/model card do not currently establish a clear
  `<20s` training-clip requirement for the base model
- the original bounded-Hemma pilot `20s` target existed mainly to:
  - keep the first Hemma pilot conservative on sequence/runtime cost
  - bias the first pilot toward more utterance diversity per hour
  - reduce domination by a small number of long parliamentary clips

Live Hemma evidence update:

- the sustained detached `T116` row-processing run has so far produced an
  average admitted clip duration around `23.19s`
- that is not treated as a stop condition by itself
- it is a signal that the original `20s` pilot target should be interpreted as
  soft guidance rather than a hard cutoff

Follow-on policy for pilot finalization:

- inspect duration distribution before finalizing the next real
  `swedish_pilot_train`
- prefer:
  - median and tail review
  - speaker-balance enforcement
  - runtime stability evidence
- over a blind hard cutoff at `20s`

### Speaker-Balance Policy

Initial per-speaker caps:

- smoke subset:
  - `20` to `45` minutes per speaker
- bounded Hemma pilot:
  - maximum `60` minutes per speaker
- Colab scale-up:
  - maximum `3` hours per speaker

Speaker hours are counted after:

- transcript-mismatch filtering
- boilerplate-text deduplication
- speaker-contamination exclusion

## Bounded Subsets

### Preprocessing Smoke Subset

Purpose:

- validate the `T103` manifest and preprocessing path
- prove reference-audio selection and audio-code generation
- catch dataset-shape issues before pilot training

Definition:

- source:
  - filtered `rixvox` train only
- target size:
  - `8` to `12` hours
- speaker count:
  - `12` to `16` speakers
- per-speaker cap:
  - `20` to `45` minutes
- clip duration:
  - `2s` to `15s`

### Bounded Hemma Pilot Subset

Purpose:

- first real multi-speaker Swedish language-expansion fine-tune on Hemma

Definition:

- source:
  - filtered `rixvox` train only
- target size:
  - `24` to `36` hours
- speaker count:
  - `24` to `40` speakers
- per-speaker cap:
  - maximum `60` minutes
- clip duration:
  - `2s` to `20s`

Recommendation:

- target `24h` first unless filtering quality is better than expected
- increase toward `36h` only if the preprocessing/eval lane is already stable

### Colab Scale-Up Subset

Purpose:

- volume phase after the bounded Hemma pilot proves the training/runtime path

Definition:

- source:
  - filtered `rixvox` train only
- target size:
  - `100` to `300` hours
- speaker count:
  - `80` to `160` speakers
- per-speaker cap:
  - maximum `3` hours
- clip duration:
  - `2s` to `30s`

## Held-Out Evaluation Split

### Quantitative Dev

Use:

- `rixvox` validation
- `fleurs` Swedish validation

Purpose:

- monitor Swedish intelligibility and overfitting during pilot training
- serve as checkpoint-dev only

### Quantitative Test

Use:

- `rixvox` test
- `fleurs` Swedish test

Purpose:

- compare the Hemma pilot and later Colab scale-up on untouched evaluation
  data
- serve as final reporting only

### Auxiliary Held-Out Control

Use:

- labeled usable `waxholm` subset only

Purpose:

- smoke/regression control
- qualitative listening prompts
- additional ASR/WER sanity checks on a corpus with better labeling trust

## Reference-Audio Policy Hand-Off to `T103`

This task does not build manifests, but it fixes the corpus-side policy that
`T103` must implement:

- corpus admission can start from the public `16 kHz` source assets
- all training-side artifacts must be standardized to `24 kHz` before manifest
  emission and mel extraction
- assign exactly one canonical `5` to `10` second reference clip per speaker
- reuse that reference clip across all rows for that speaker
- do not let per-row random `ref_audio` selection leak into the first pilot

## Deterministic Artifact Roots

`T103` should generate its corpus-policy artifacts under:

- `build/reference/qwen3-tts-swedish-corpus/`

Suggested files:

- `dataset_inventory.json`
- `smoke_subset_spec.json`
- `pilot_subset_spec.json`
- `scaleup_subset_spec.json`
- `held_out_eval_split.json`

## Outcome

Task 102 is considered complete once the repo follows this policy:

- `rixvox` train is the filtered backbone
- `fleurs` and `waxholm` are explicit control/eval corpora
- the first Hemma pilot targets `24` to `36` filtered hours from `24` to `40`
  speakers
- the scale-up lane targets `100` to `300` filtered hours from `80` to `160`
  speakers
- held-out evaluation is fixed before preprocessing and training begin
