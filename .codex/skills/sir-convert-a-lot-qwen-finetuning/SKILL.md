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

## Use When

- Fine-tuning `Qwen/Qwen3-TTS-12Hz-1.7B-Base` for Swedish.
- Working on Qwen preprocessing, training, evaluation, or recovery.
- Choosing between Hemma and Colab for a governed Qwen run.
- Deciding whether Qwen evidence permits promotion into a sidecar candidate lane.

Use the broader `.codex/skills/speech-model-finetuning-on-hemma/SKILL.md` for
model-agnostic training guidance and
`.codex/skills/sir-convert-a-lot-colab-hemma/SKILL.md` for Colab/Hemma transfer.

## Read Order

1. `references/architecture-and-experiment-contract.md`
1. `docs/backlog/epics/epic-sircon-05-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md`
1. `docs/reference/ref-sircon-research-qwen-training-eval-pilot-progress-ledger-2026-03-15-qwen-training-eval-pilot-progress-ledger-2026-03-15.md`
1. `docs/runbooks/run-sircon-qwen3-tts-swedish-finetuning-runbook-for-hemma-and-colab-qwen3-tts-swedish-finetuning-runbook-for-hemma-and-colab.md`
1. `docs/decisions/adr-sircon-0005-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md`
1. `docs/decisions/adr-sircon-0006-reusable-multi-backend-tts-sidecar-capability-contract.md`

The reference owns agent-facing architecture and evidence rules. The runbook
owns operator procedure. The progress ledger owns current experiment classes,
state vectors, surface status, results, and next-step truth.

## Classify First

- `benchmark`: serving and runtime evidence only.
- `single-speaker adaptation`: voice-transfer experiments, not general Swedish.
- `language expansion`: multi-speaker Swedish support.

Choose language expansion when the requested outcome is general Swedish support.

## Workflow

1. Confirm the governing backlog slice and the current ledger state.
1. Classify the experiment and state its single primary question.
1. Check the architecture and evidence contract before changing code or run shape.
1. Use the Qwen runbook for commands, host procedure, stop conditions, and recovery.
1. Record results and state-vector changes in the progress ledger.
1. Promote only through the documented evidence ladder.

Do not copy live operator status, command transcripts, or experiment results into
this skill.
