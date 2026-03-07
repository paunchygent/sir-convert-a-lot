---
type: reference
id: REF-espeak-ng-swedish-phoneme-integration-for-chatterbox
title: eSpeak NG Swedish Phoneme Integration Research for Chatterbox
status: active
created: 2026-03-07
updated: 2026-03-07
owners:
  - platform
tags:
  - chatterbox
  - espeak-ng
  - phonemes
  - swedish
  - research
links:
  - docs/backlog/tasks/task-88-research-espeak-ng-phoneme-support-for-swedish-chatterbox-integration.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
  - https://github.com/resemble-ai/chatterbox
  - https://github.com/espeak-ng/espeak-ng
  - https://github.com/bootphon/phonemizer
---
## Purpose

Record the current research truth for using eSpeak NG to improve Swedish
phoneme handling in the Chatterbox benchmark pipeline, without assuming a
direct model-native phoneme input path that the upstream docs do not prove.

## Verified Facts

- The current repo-side Chatterbox implementation calls the official
  multilingual surface through `ChatterboxMultilingualTTS.from_pretrained` and
  `model.generate(...)`.
- The current repo passes only:
  - `text`
  - `language_id`
  - `audio_prompt_path`
  - `exaggeration`
  - `cfg_weight`
- The current repo does not expose any documented phoneme-input field in the
  Chatterbox sidecar contract.
- The official eSpeak NG project describes itself as a compact speech
  synthesizer that includes a text-to-phoneme path and supports many languages.

## Research Implications

### What Is Proven

The repo can already benchmark Swedish Chatterbox lanes through the documented
text-input path.

The repo can also prepare deterministic reference audio artifacts before
inference.

### What Is Not Yet Proven

- That the official Chatterbox multilingual API accepts external phoneme
  strings as a documented input mode.
- That eSpeak NG phoneme output improves Swedish Chatterbox quality in this
  repo's current benchmark shape.

## Best Current Incorporation Boundary

Based on the repo architecture and the current official source surfaces, the
best starting point is:

- treat eSpeak NG as an external preprocessing experiment first
- keep it outside the current Chatterbox runtime image until the integration
  behavior is reviewed explicitly
- benchmark it as an optional helper path that produces alternate Swedish input
  forms or phoneme-side evidence
- do not assume a production service dependency until the research task is
  closed with a clearer contract decision

In practical terms, the safest first implementation shape is a benchmark-only
tool or helper container, not a silent in-process dependency added directly to
the production sidecar.

## Recommended Task Setup

Suggested docs-as-code sequence:

1. `T88` research:
   - confirm API reality
   - confirm Swedish verification steps
   - decide the integration boundary
2. follow-on design task:
   - define the exact repo contract for optional phoneme preprocessing
   - document whether the output is phoneme text, alternate normalized text, or
     benchmark-only evidence
3. implementation task:
   - add the bounded preprocessing surface in the chosen boundary
4. benchmark task:
   - run Swedish A/B comparisons against the current Chatterbox baseline

## Recommendation

Do not add eSpeak NG directly to the production Chatterbox sidecar yet.

Start with research and a benchmark-only incorporation path, because:

- the current official Chatterbox multilingual docs do not yet prove a direct
  phoneme-input contract for our existing adapter surface
- Swedish benefit should be demonstrated empirically on Hemma before changing
  the runtime boundary
