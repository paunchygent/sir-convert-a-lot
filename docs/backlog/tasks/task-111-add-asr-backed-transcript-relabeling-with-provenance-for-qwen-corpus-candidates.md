---
id: task-111-add-asr-backed-transcript-relabeling-with-provenance-for-qwen-corpus-candidates
title: Add ASR-backed transcript relabeling with provenance for Qwen corpus candidates
type: task
status: proposed
priority: medium
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - preprocessing
  - asr
  - provenance
  - transcripts
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and implement an optional ASR-backed transcript relabeling lane for
Swedish corpus candidates while preserving explicit provenance, original source
text, and deterministic admission rules.

## Why This Exists

Current policy uses Swedish ASR as a quality gate:

- detect transcript/audio mismatch
- assign quality tiers
- admit or reject rows

That is the correct conservative baseline, but it leaves potentially useful
rows on the floor when the public transcript is close enough to the audio to be
recoverable yet noisy enough to fail a strict training-admission rule.

Current persisted-state truth:

- row-processing already writes `asr_transcript`, `asr_wer`, `asr_model`, and
  `asr_revision` into durable spool rows
- finalization already carries those fields into curated artifacts

So this task is **not** primarily about rerunning Whisper over completed rows.
It is about building a provenance-safe decision and projection path that can
promote already persisted ASR transcripts into the training lane when approved.

## Canonical Position

The source transcript remains canonical by default.

This task does **not** authorize silent transcript replacement. Any ASR-backed
relabeling must be explicit, reviewable, and provenance-preserving.

## PR Scope

- Define provenance fields for original transcript text and ASR-generated text.
- Define one explicit relabeling-decision contract, for example:
  - keep source transcript
  - create ASR relabel candidate
  - approve ASR relabel
  - reject row
- Preserve both transcript versions in curated/report artifacts.
- Reuse already persisted spool/curated ASR transcripts for the first relabel
  candidate lane instead of requiring a fresh whole-corpus Whisper rerun.
- Keep the Swedish ASR backend pinned to the existing policy:
  - `KBLab/kb-whisper-large`
  - `revision="strict"`
- Restrict any first implementation to a bounded candidate lane rather than
  changing the default preprocessing path for all admitted rows.

## Non-Goals

- Do not silently overwrite public-source transcripts.
- Do not treat ASR output as universally correct.
- Do not make ASR relabeling a blocker for `T101`.
- Do not weaken the existing high-trust admission rules to force more data
  through the pipeline.

## Expected Outcome

After this task:

- the repo can preserve original transcript truth and ASR candidate text side
  by side
- relabeling decisions are visible and auditable
- low-BLEU or high-WER rows can be re-evaluated from already persisted ASR
  transcript evidence
- future Swedish corpus expansion can test whether ASR-backed recovery improves
  usable hours without losing provenance

## Deliverables

- [ ] One explicit provenance contract for transcript origin and relabel
  decision state.
- [ ] One bounded ASR-relabel candidate path that does not alter the default
  admitted-row behavior silently.
- [ ] One deterministic report surface summarizing kept, relabeled, and
  rejected rows.

## Acceptance Criteria

- [ ] Curated/report artifacts preserve both original and ASR transcript values
  when relabeling is attempted.
- [ ] Transcript provenance is explicit and machine-readable.
- [ ] Default preprocessing behavior remains conservative unless a bounded
  relabel lane is explicitly enabled.
- [ ] The task documents which quality tiers and review rules may feed an
  ASR-backed relabel candidate.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
