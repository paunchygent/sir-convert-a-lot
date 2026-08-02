---
type: reference
id: REF-SIRCON-RESEARCH-reference-qwen3-tts-swedish-finetuning-research-map-2026-03-08
title: 'Reference: Qwen3-TTS Swedish finetuning research map (2026-03-08)'
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: research
summary: 'Reference: Qwen3-TTS Swedish finetuning research map (2026-03-08)'
retired_ids:
- REF-qwen3-tts-swedish-finetuning-research-map-2026-03-08
---

## Research Purpose And Boundary

## Evidence And Sources

## Findings And Interpretation

## Evidence Gaps And Follow-Up

## Historical Source Content

### Purpose

Capture the current research truth for the planned Swedish
`Qwen/Qwen3-TTS-12Hz-1.7B-Base` full-finetune lane, and define the exact
questions an external research pass should answer before the first real
multi-speaker experiment starts.

### Current Sir Convert-a-Lot Setup

### Repo and Runtime Discipline

- This repo treats Qwen fine-tuning as a dedicated training lane under Epic 08,
  separate from the current public sidecar-serving contract in Epic 07.
- Hemma is the canonical on-prem host:
  - `AMD Radeon AI PRO R9700`
  - approximately `32.06 GB` VRAM
  - ROCm-first
  - container-only for training/runtime work
- Local execution must stay wrapper-driven:
  - `pdm run run-local-pdm <script>`
  - `pdm run run-hemma -- <command> [args]`
- Build surfaces must remain reproducible and containerized:
  - no raw `systemd` training flows
  - no ad hoc host-only training loops
  - use BuildKit-backed image builds, never legacy `docker build`

### Model and Fine-Tuning Aim

- Target model:
  - `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- Fine-tuning objective:
  - full fine-tune
  - `AdamW`
  - Swedish language expansion
  - multi-speaker outcome
- Non-goal:
  - single-speaker custom-voice adaptation as the end state

### Runtime Split

- Existing Qwen serving/benchmark lane:
  - Task 79 / Task 98
  - sidecar runtime and flash-attention serving truth
- New Qwen fine-tuning lane:
  - Story 24 / Story 25
  - Tasks 100-105
  - dedicated training runtime and evaluation path

### Proven Facts We Should Stop Re-Arguing

- Hemma has already been shown to fit bounded `Qwen3-TTS-1.7B` full-finetune
  work on the real GPU.
- A real official Swedish training step with `AdamW` already ran on Hemma.
- The current measured Hemma proof point is a real Swedish Waxholm-driven step,
  not only a synthetic model load.
- Triton flash attention has been re-enabled in the current Qwen Hemma
  benchmark lane and is now the default policy again for that serving path.
- The official public Qwen fine-tuning surface still documents a
  single-speaker flow, so our multi-speaker Swedish plan is a repo-owned
  engineering extension rather than an off-the-shelf upstream recipe.

### What We Are Actually Trying To Learn Before The First Experiment

### Dataset and Curation Questions

- Which `rixvox` subsets are good enough for TTS training rather than only ASR?
- Which transcript-quality thresholds are worth enforcing before preprocessing?
- How should we split:
  - train,
  - dev,
  - held-out speakers,
  - qualitative listening prompts?
- What pilot-hours target is most likely to answer the first language-support
  question without wasting days on a poorly curated run?

### Training and Recipe Questions

- How far can the official Qwen `prepare_data.py` and `sft_12hz.py` flow be
  pushed toward a true multi-speaker Swedish lane before repo-owned patches are
  needed?
- What reference-audio policy should we use in a multi-speaker experiment when
  upstream documentation centers a single-speaker recipe?
- Which public Qwen3-TTS fine-tunes or notebook workflows show multilingual or
  general-language transfer patterns rather than only custom-voice cloning?

### Evaluation Questions

- Which Swedish prompt set is strong enough to catch:
  - pronunciation failures,
  - prosody issues,
  - speaker leakage,
  - text normalization mistakes,
  - held-out speaker regressions?
- Which objective or semi-objective metrics are worth collecting in addition to
  listening review?
- What would count as:
  - continue,
  - stop,
  - or pivot evidence after the first bounded pilot?

### Open Questions To Answer With Research

These are not blockers in the "can't proceed at all" sense. They are the
highest-value knowledge gaps that should be tightened before the first serious
multi-speaker run:

1. Best known public pattern for extending a TTS base model from an upstream
   single-speaker recipe to a multi-speaker or language-expansion recipe.
1. Best public data-filtering strategy for parliamentary or broadcast corpora
   with non-verbatim transcripts.
1. Best public manifest/reference-audio contract for Qwen-style codec-TTS
   fine-tuning when the language goal matters more than speaker cloning.
1. Strong Swedish or closely related multilingual evaluation practice we can
   reuse instead of inventing an ad hoc prompt sheet.
1. Examples of successful community Qwen3-TTS fine-tunes that document:
   - training subset size,
   - runtime shape,
   - checkpoint cadence,
   - failure modes,
   - and outcome quality.

### Research Priorities

Rank the evidence sources in this order:

1. Official Qwen model card, repo, scripts, and technical report.
1. Official dataset cards and papers for `rixvox`, `fleurs`, and `waxholm`.
1. Public Qwen3-TTS fine-tuned model cards that document training choices.
1. Public GitHub repos and open notebooks that show reproducible Qwen3-TTS or
   nearby multi-speaker TTS fine-tuning workflows.
1. Related research papers and paper-as-code repos for multilingual or
   language-expansion TTS that can inform:
   - curation,
   - manifest design,
   - evaluation,
   - and speaker split policy.

### Targeted Link Collection

### Official Qwen Sources

- Model card:
  - [Qwen/Qwen3-TTS-12Hz-1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)
- Upstream repository:
  - [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)
- Fine-tuning subtree:
  - [Qwen3-TTS `finetuning/`](https://github.com/QwenLM/Qwen3-TTS/tree/main/finetuning)
- Community fine-tune listing for inspiration:
  - [Hugging Face models based on `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`](https://huggingface.co/models?other=base_model:finetune:Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)

### Swedish Dataset Sources

- Dataset card:
  - [KBLab/rixvox](https://huggingface.co/datasets/KBLab/rixvox)
- Dataset card:
  - [google/fleurs](https://huggingface.co/datasets/google/fleurs)
- Dataset card:
  - [KTH/waxholm](https://huggingface.co/datasets/KTH/waxholm)

### Runtime and ROCm References

- Official vLLM ROCm guidance:
  - [vLLM AMD ROCm installation/runtime guide](https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html#amd-rocm)
- Flash attention project:
  - [Dao-AILab/flash-attention](https://github.com/Dao-AILab/flash-attention)

### Paper and Research Leads

- Technical report:
  - [Qwen3-TTS Technical Report](https://arxiv.org/abs/2601.15621)
- Multilingual restored speech benchmark lead:
  - [FLEURS-R: A Restored Multilingual Speech Corpus for Speech Generation](https://arxiv.org/abs/2406.18093)
- Nordic multilingual TTS lead:
  - [Nord-ParlTTS: A Large Scale Corpus for Nordic Parliamentary Speech Synthesis](https://arxiv.org/abs/2412.07853)

### What The Research Team Should Extract From Each Source

For every useful source, capture:

- link
- source type
- whether it is official, community, or research
- what exact problem it helps with:
  - curation,
  - preprocessing,
  - training,
  - runtime,
  - evaluation,
  - or deployment fit
- concrete method details:
  - dataset size,
  - speaker count,
  - filtering rules,
  - transcript normalization,
  - reference-audio handling,
  - batch/sequence settings,
  - optimizer and scheduler choices,
  - reported failure modes,
  - reported quality outcomes
- relevance score for this repo:
  - high / medium / low
- whether the result looks directly reusable, indirectly informative, or mostly
  noise

### Best-Practice Direction For The First Experiment

### What To Prefer

- Sources that document multi-speaker or multilingual transfer, not only
  single-voice adaptation.
- Sources that show dataset filtering decisions in enough detail to reuse.
- Sources that separate training, dev, held-out speakers, and listening sets.
- Sources that publish enough runtime detail to compare Hemma and Colab
  realistically.
- Sources that stay close to codec-based neural TTS and modern open-source
  practice.

### What To Discount

- Model cards that only say "fine-tuned on my own voice" without dataset,
  runtime, or evaluation detail.
- Notebook demos that skip manifest generation, cache layout, or checkpoint
  recovery.
- Papers that are too far from the current architecture and give no reusable
  preprocessing or evaluation strategy.
- Advice that assumes raw-host GPU tuning rather than containerized ROCm or
  containerized Colab workflows.

### Recommended Research Outputs

The research pass should produce three concrete outputs:

1. One curated link collection grouped by:
   - official sources,
   - model cards,
   - repos/notebooks,
   - papers,
   - dataset references.
1. One distilled guide of best practices and anti-patterns for this exact
   effort:
   - Swedish,
   - multi-speaker,
   - Qwen `1.7B`,
   - Hemma plus Colab,
   - full fine-tuning.
1. One recommendation memo that answers the current open questions with:
   - preferred pilot subset,
   - preferred preprocessing contract,
   - preferred evaluation design,
   - and the highest-confidence first-run recipe.

### Current Recommendation

Do not start the serious multi-speaker experiment with only internal notes and
generic TTS intuition.

Start with the new repomix package plus a focused external research pass so the
first bounded Hemma pilot is anchored to:

- real public Qwen evidence,
- real Swedish corpus handling guidance,
- and the closest reproducible multi-speaker language-expansion patterns we can
  find.
