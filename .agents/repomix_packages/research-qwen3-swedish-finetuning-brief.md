---
title: Qwen3-TTS Swedish Finetuning Research Brief
created: '2026-03-08'
status: active
purpose: external-research
---

# Qwen3-TTS Swedish Finetuning Research Brief

## Goal

Use the attached repomix package plus targeted external research to identify the
best publicly documented path for adding general Swedish language support to
`Qwen/Qwen3-TTS-12Hz-1.7B-Base` under Sir Convert-a-Lot's real operating
constraints.

## Our Real Setup

- Repo:
  - `sir-convert-a-lot`
- On-prem host:
  - Hemma
  - `AMD Radeon AI PRO R9700`
  - approximately `32.06 GB` VRAM
  - ROCm
  - containers only
- Scale-up lane:
  - Google Colab H100
- Model target:
  - `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- Training target:
  - full fine-tuning
  - `AdamW`
  - multi-speaker Swedish language expansion
- Non-goal:
  - a one-speaker custom-voice shortcut

## What Is Already Proven

- Hemma can fit bounded `1.7B` full-finetune work.
- A real official Swedish training step with `AdamW` already ran on Hemma.
- This repo already has a Qwen ROCm serving lane with Triton flash attention
  re-enabled by default.
- The repo already separates:
  - serving/benchmark work,
  - training work,
  - and future sidecar-candidate decisions.

## What We Need You To Find

### Primary Questions

1. What is the best public pattern for moving from Qwen's documented
   single-speaker recipe to a multi-speaker language-expansion recipe?
1. What is the best data curation policy for Swedish `rixvox` plus
   `fleurs` plus `waxholm` in a TTS setting?
1. What reference-audio and manifest strategy is most defensible for a
   multi-speaker Swedish run?
1. What pilot-hours target and speaker split look most likely to give a useful
   first answer?
1. What evaluation design should we use for Swedish language support rather
   than speaker cloning?

### Evidence Sources To Search

Prioritize:

- open Colab notebooks
- GitHub repos
- Hugging Face model cards
- paper-as-code repos
- research papers

Prefer sources that are as close as possible to:

- Qwen3-TTS
- multi-speaker TTS
- multilingual or language-expansion fine-tuning
- codec-based TTS
- Swedish or Nordic speech synthesis
- containerized ROCm or reproducible Colab workflows

## Deliverables Requested

Please produce:

1. A link collection with short annotations.
1. A distilled guide of best practices, anti-patterns, and reusable recipe
   choices for this exact setup.
1. A recommendation memo with your preferred:
   - pilot subset,
   - preprocessing contract,
   - evaluation design,
   - and first-run training recipe.

## Output Format

For each recommended source, capture:

- link
- source type
- why it matters for this repo
- what it says about:
  - curation
  - preprocessing
  - training
  - runtime
  - evaluation
- whether it is directly reusable or only indirectly informative

For the final recommendation memo, answer:

- What should we do first on Hemma?
- What should we scale on Colab H100?
- What should we avoid because it is too generic, too notebook-fragile, or too
  voice-cloning-centric for our goal?

## Things To Look For Specifically

- Qwen3-TTS community fine-tunes with enough detail to infer real training
  choices.
- Notebook or repo examples that go beyond single-speaker custom-voice tuning.
- Public evidence on filtering non-verbatim transcript corpora for TTS.
- Swedish or Nordic multilingual TTS evaluation patterns we can reuse.
- Evidence about manifest design, speaker splits, reference handling, and
  checkpoint cadence that fits our full-finetune objective.

## Useful Starting Links

- [Qwen/Qwen3-TTS-12Hz-1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)
- [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)
- [Qwen3-TTS `finetuning/`](https://github.com/QwenLM/Qwen3-TTS/tree/main/finetuning)
- [KBLab/rixvox](https://huggingface.co/datasets/KBLab/rixvox)
- [google/fleurs](https://huggingface.co/datasets/google/fleurs)
- [KTH/waxholm](https://huggingface.co/datasets/KTH/waxholm)
- [Qwen3-TTS Technical Report](https://arxiv.org/abs/2601.15621)
- [FLEURS-R](https://arxiv.org/abs/2406.18093)
- [Nord-ParlTTS](https://arxiv.org/abs/2412.07853)
- [Qwen CustomVoice fine-tune listing](https://huggingface.co/models?other=base_model:finetune:Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)
