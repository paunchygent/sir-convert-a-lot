---
type: runbook
id: RUN-chatterbox-multilingual-tuning-on-hemma
title: Chatterbox Multilingual Tuning Runbook for Hemma
status: active
created: 2026-03-07
updated: 2026-03-07
owners:
  - platform
system: hemma.hule.education
tags:
  - chatterbox
  - tts
  - hemma
  - tuning
  - swedish
links:
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-89-implement-benchmark-only-espeak-ng-preprocessing-for-chatterbox-swedish-lanes.md
  - docs/backlog/tasks/task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma.md
  - docs/backlog/tasks/task-91-implement-speech-aware-chatterbox-stitching-and-tail-cleanup-on-hemma.md
  - docs/backlog/tasks/task-93-implement-clause-aware-duration-bounded-chatterbox-chunk-planning-on-hemma.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - scripts/sir_convert_a_lot/devops/run_task86_hemma_chatterbox_benchmark.py
  - scripts/sir_convert_a_lot/devops/run_task89_hemma_chatterbox_espeak_experiment.py
  - scripts/sir_convert_a_lot/devops/task86_chatterbox_runtime.py
  - scripts/sir_convert_a_lot/tts_sidecar/chatterbox_runtime.py
  - containers/textprep-espeak-phonemizer/Dockerfile
  - https://github.com/resemble-ai/chatterbox
  - https://pypi.org/project/chatterbox-tts/
---

## Purpose

Provide one quality-first, repo-grounded procedure for tuning Chatterbox
Multilingual on Hemma without inventing unsupported controls, hidden runtime
behavior, or unofficial benchmark rules.

Current lifecycle status in this repo:

- `containers/tts-sidecar-chatterbox/` is the current Hemma production-candidate
  TTS sidecar image
- `containers/tts-sidecar-openvoice/`, `containers/tts-sidecar-f5/`, and
  `containers/textprep-espeak-phonemizer/` remain experiment-only surfaces and
  must not be treated as Hemma production deploy targets

## Ground Truth Sources

This runbook is intentionally limited to two truth surfaces:

- The Sir Convert-a-Lot repo implementation for Task 86:
  - `scripts/sir_convert_a_lot/devops/run_task86_hemma_chatterbox_benchmark.py`
  - `scripts/sir_convert_a_lot/devops/task86_chatterbox_runtime.py`
  - `scripts/sir_convert_a_lot/tts_sidecar/chatterbox_runtime.py`
  - `containers/tts-sidecar-chatterbox/Dockerfile`
- The official upstream Chatterbox project:
  - `resemble-ai/chatterbox` README
  - upstream `pyproject.toml`
  - the published `chatterbox-tts` package

Anything outside those surfaces is out of scope for this runbook.

## What This Repo Actually Exposes

The current Task 86 benchmark surface is:

```bash
pdm run run-hemma -- pdm run benchmark:task-86
```

The committed benchmark CLI currently exposes these relevant controls:

- `--reference-audio`
- `--probe-text`
- `--exaggeration`
- `--cfg-weight`
- `--output-root`
- `--skip-build`

The sidecar runtime currently exposes these environment-backed Chatterbox knobs:

- `SIR_TTS_SIDECAR_CHATTERBOX_EXAGGERATION`
- `SIR_TTS_SIDECAR_CHATTERBOX_CFG_WEIGHT`
- `SIR_TTS_SIDECAR_CHATTERBOX_SEGMENT_TEXT`
- `SIR_TTS_SIDECAR_CHATTERBOX_SEGMENT_MAX_CHARS`
- `SIR_TTS_SIDECAR_CHATTERBOX_SEGMENT_CROSS_FADE_MS`
- `SIR_TTS_SIDECAR_CHATTERBOX_SEGMENT_STITCH_MODE`

The sidecar always calls the official multilingual API through:

- `chatterbox.mtl_tts.ChatterboxMultilingualTTS.from_pretrained(device="cuda")`
- `model.generate(...)`

The repo currently passes only these Chatterbox generation arguments:

- `text`
- `language_id`
- `exaggeration`
- `cfg_weight`
- `audio_prompt_path` when reference cloning is used

## Hard Constraints

- Use Hemma only for live tuning runs:
  - `pdm run run-hemma -- ...`
- Keep the benchmark on the GPU path:
  - no silent CPU fallback
- Keep Hemma storage tiers explicit:
  - `/srv/scratch` for Docker root, model caches, and active benchmark output
  - `/srv/storage` for large cold bulk data, not hot sidecar artifacts
- Tune only supported, documented multilingual controls:
  - `cfg_weight`
  - `exaggeration`
- Do not add undocumented multilingual knobs to the runbook.
- Change one variable at a time.
- Use one dedicated `--output-root` per lane so evidence stays reviewable.

## Current Quality Limits In This Repo

Task 90 changed the quality floor for long-form Chatterbox runs in this repo.

The sidecar now supports a repo-owned segmented normal-text path with:

- sentence-aware splitting
- deterministic chunk execution
- deterministic stitching with cross-fade
- optional chunk-level debug evidence

Current repo truth:

- segmentation is internal and environment-backed, not a public API field
- the sidecar contract remains text-based
- the benchmark can now compare:
  - single-pass normal text
  - segmented normal text
- the segmented lane writes a `segment_plan.json` plus chunk artifacts when
  debug retention is enabled
- Task 93 now changes the planner shape itself:
  - structural list items are preferred split boundaries,
  - clause-aware planning units are used before word fallback,
  - the planner targets `4-6` second chunks on average,
  - and enforces a hard `9` second planning ceiling per chunk

Practical consequence:

- the repo now has a real long-form quality path for Chatterbox
- the next quality lever is no longer generic segmentation, but better segment
  planning for structured Swedish text
- `segment_max_chars` should now be treated as a secondary safety rail, not as
  the primary chunking policy

## Reference Audio Behavior in This Repo

The sidecar does not pass the uploaded reference file through unchanged.
Before Chatterbox sees it, the repo converts the reference clip with `ffmpeg`
to a deterministic prompt WAV:

- mono
- `24000` Hz
- `s16`

That conversion happens in
`scripts/sir_convert_a_lot/tts_sidecar/chatterbox_runtime.py` via:

```bash
ffmpeg -y -i <source> -ac 1 -ar 24000 -sample_fmt s16 <target>
```

Repo truth for cloning behavior:

- reference audio is required for `reference_clone`
- reference transcript is not used
- reference transcript is rejected if supplied

## Upstream Tuning Facts That Are Safe To Use

The official Chatterbox README documents these multilingual tuning facts:

- the default settings `exaggeration=0.5` and `cfg_weight=0.5` are the
  recommended general baseline
- lowering `cfg_weight` to around `0.3` can improve pacing when the reference
  speaker is fast
- when the reference clip language does not match the target language,
  `cfg_weight=0` is the documented mitigation to reduce accent bleed
- increasing `exaggeration` makes speech more dramatic and tends to make it
  faster
- lowering `cfg_weight` can compensate for that faster pacing

This runbook does not generalize beyond those documented statements.

## Official Best Practices and Current Repo Alignment

The table below records what the Chatterbox maintainers explicitly recommend,
and how closely the current Sir Convert-a-Lot implementation follows that
guidance.

| Official recommendation or documented pattern | Current repo alignment | Notes |
| --- | --- | --- |
| Use the official package `chatterbox-tts` and the multilingual class `chatterbox.mtl_tts.ChatterboxMultilingualTTS` for multilingual synthesis. | Full | Task 86 uses the official package and class directly. |
| Use `audio_prompt_path` for cloning. | Full | The sidecar passes the prepared reference WAV as `audio_prompt_path`. |
| Use `language_id="sv"` for Swedish synthesis. | Full | The current benchmark keeps Swedish output explicit and rejects unsupported languages. |
| Treat `0.5 / 0.5` as the general baseline for `exaggeration` and `cfg_weight`. | Full | The first successful Hemma lane and the current benchmark default both use `0.5 / 0.5`. |
| Lower `cfg_weight` when a fast reference speaker causes pacing issues. | Partial | The repo supports this knob and this runbook standardizes a `0.3` comparison lane, but it has not yet been locked in as the winning Swedish lane. |
| Set `cfg_weight=0` for cross-language cloning to reduce accent bleed. | Partial | The benchmark surface supports it, but Story 23 has not yet completed an approved cross-language lane. |
| Use the official Python 3.11 / Debian 11 baseline from upstream packaging guidance. | Full | The Chatterbox sidecar image is built on `python:3.11-slim-bullseye`. |
| Track the official upstream dependency surface. | Partial with deliberate runtime divergence | The repo keeps `chatterbox-tts==0.1.6`, `transformers==4.46.3`, and `diffusers==0.29.0`, but intentionally uses `torch==2.10.0+rocm7.1` / `torchaudio==2.10.0+rocm7.1` on Hemma instead of the upstream default torch pins because the benchmark must run on the Hemma ROCm stack. |
| Treat watermarking as part of the product reality of generated output. | Partial | Task 86 docs record the PerTh watermark as a governance consideration, but the current benchmark does not run watermark detection as part of each lane. |

The most important practical conclusion is:

- the current repo is strongly aligned with the official multilingual API and
  the official tuning knobs
- the main intentional divergence is the ROCm torch runtime needed for Hemma
- cross-language tuning guidance is supported by the repo surface but is not yet
  fully benchmarked in Story 23

## Tuning Goal for Story 23

For the Swedish teacher-voice benchmark in this repo, the tuning goal is:

- maximize perceived cloning quality and intelligibility
- keep Swedish output as the evaluation target
- avoid confounding the result with mixed-language probe text
- preserve deterministic evidence for each lane

This is a quality-first tuning runbook, not a latency-minimization runbook.

For future maximal-quality work, this runbook now has two phases:

1. tune the current single-pass path
1. implement segmentation, batching, and stitching as a separate follow-on
   slice

## Task 89 Result and Current Decision

Task 89 proved that the benchmark-only eSpeak preprocessing path is
implementable and measurable on Hemma.

Evidence:

- baseline text-input lane:
  `build/verification/task-89-chatterbox-espeak-hemma/baseline/`
- eSpeak-preprocessed lane:
  `build/verification/task-89-chatterbox-espeak-hemma/espeak_sv/`
- Task 89 summary:
  `build/verification/task-89-chatterbox-espeak-hemma/report.json`

Task 89 does **not** remove the need for segmentation, batching, and stitching.
It adds one alternate text-input form for comparison, but it does not change
the underlying single-pass generation shape.

Current repo decision for Chatterbox:

- do not use the eSpeak-preprocessed lane as part of the active Chatterbox
  quality path
- keep the helper path only for future comparisons against other models
- move Chatterbox quality work to normal-text segmentation, batching, and
  stitching under `T90`

## Task 90 Result

Task 90 now provides live Hemma evidence for the new normal-text segmented
path:

- single-pass evidence:
  `build/verification/task-90-chatterbox-segmented-hemma/single_pass/`
- segmented evidence:
  `build/verification/task-90-chatterbox-segmented-hemma/segmented/`
- summary report:
  `build/verification/task-90-chatterbox-segmented-hemma/report.json`

Measured outcome:

- both lanes synthesized successfully
- the segmented lane used `3` deterministic text segments
- single-pass duration: `51.904`
- segmented duration: `57.473`
- single-pass peak VRAM: `5959815168`
- segmented peak VRAM: `5742292992`

This runbook does not claim a winner from those numbers alone. The next
decision now includes the listening review:

- segmented output is the better Chatterbox path overall
- the remaining defects are stitch-specific, not segmentation-specific

The next quality slice is therefore not “more segmentation tuning.” It is:

- tail-noise cleanup after speech stops
- pause-aware stitch decisions at chunk boundaries
- cross-fade that respects intended natural pauses

## Task 91 Result

Task 91 now provides live Hemma evidence for speech-aware stitched segmented
output:

- simple segmented baseline:
  `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/simple/`
- speech-aware segmented lane:
  `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/speech_aware/`
- summary report:
  `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/report.json`

Measured outcome:

- both segmented lanes synthesized successfully
- simple segmented duration: `123.426`
- speech-aware duration: `94.954`
- simple peak VRAM: `6239154176`
- speech-aware peak VRAM: `5945778176`
- the speech-aware lane now records:
  - `chunk_analysis.json`
  - `boundary_decisions.json`
  - `chunk_XX_post.wav`

Current repo truth for speech-aware stitching:

- it remains an internal segmented-generation behavior, not a public API field
- it trims low-energy chunk edges before stitching
- it applies short edge fades after trimming
- the default speech-aware edge fade cap is now `12 ms`
- it chooses pause targets from the preceding boundary type:
  - clause: `110 ms`
  - sentence: `180 ms`
  - generic: `80 ms`

This still does not prove a quality winner on its own. The listening verdict
remains the final decision point for whether `speech_aware` becomes the default
segmented stitch mode.

## Canonical Baseline Lane

Use a Swedish-only probe text and keep the approved teacher reference clip
fixed while establishing the baseline lane.

Example:

```bash
pdm run run-hemma -- pdm run benchmark:task-86 \
  --skip-build \
  --output-root build/verification/task-86-chatterbox-hemma-sv-baseline \
  --reference-audio build/verification/task-81-openvoice-v2-hemma/inputs/teacher_reference_voice.m4a \
  --probe-text "Hej. Det här är ett rent svenskt prov. Vi testar om modellen kan klona en lärarröst och läsa svensk text tydligt, naturligt och utan störande artefakter." \
  --exaggeration 0.5 \
  --cfg-weight 0.5
```

## Canonical Tuning Order

### 1. Lock Inputs Before Any Sweep

Keep these fixed across one same-language sweep:

- the same reference clip
- the same Swedish-only probe text
- the same output format
- the same image/runtime path

Do not change reference audio and tuning knobs in the same comparison step.

### 2. Sweep `cfg_weight` First

For same-language Swedish cloning, `cfg_weight` is the first tuning knob to
sweep because it is the main documented style-following control and the README
gives explicit guidance for lower values.

Start with:

- `0.5` baseline
- `0.3` pacing-focused comparison

Same-language low-guidance lane:

```bash
pdm run run-hemma -- pdm run benchmark:task-86 \
  --skip-build \
  --output-root build/verification/task-86-chatterbox-hemma-sv-cfg-0p3 \
  --reference-audio build/verification/task-81-openvoice-v2-hemma/inputs/teacher_reference_voice.m4a \
  --probe-text "Hej. Det här är ett rent svenskt prov. Vi testar om modellen kan klona en lärarröst och läsa svensk text tydligt, naturligt och utan störande artefakter." \
  --exaggeration 0.5 \
  --cfg-weight 0.3
```

Use `cfg_weight=0` only for an explicitly cross-language lane.
Do not treat `0` as the default same-language quality target unless the
benchmark is intentionally testing deconditioning.

### 3. Change `exaggeration` Only After `cfg_weight`

`exaggeration` is not a neutral quality knob. Upstream documents it as a
drama/intensity control, and also notes that higher values tend to make speech
faster.

For a teacher-voice benchmark, do not change `exaggeration` first.
Only test it after the `cfg_weight` sweep if the target delivery actually wants
more expressive speech.

Example expressive comparison lane:

```bash
pdm run run-hemma -- pdm run benchmark:task-86 \
  --skip-build \
  --output-root build/verification/task-86-chatterbox-hemma-sv-exag-0p7 \
  --reference-audio build/verification/task-81-openvoice-v2-hemma/inputs/teacher_reference_voice.m4a \
  --probe-text "Hej. Det här är ett rent svenskt prov. Vi testar om modellen kan klona en lärarröst och läsa svensk text tydligt, naturligt och utan störande artefakter." \
  --exaggeration 0.7 \
  --cfg-weight 0.3
```

That lane is for an explicitly more expressive target. It is not the default
benchmark lane.

## Cross-Language Lane Rule

Only run a cross-language lane if there is an approved non-Swedish reference
clip.

When the reference clip language differs from the target Swedish output, the
official README guidance is:

- keep `language_id="sv"`
- set `cfg_weight=0`

The current repo benchmark supports that path only when an approved alternative
reference clip is supplied.

## Unsupported Tuning Ideas in This Repo

Do not put these into a Chatterbox tuning runbook for the current Task 86
surface:

- `temperature`
- `top_p`
- `seed`
- `style_instructions`
- `reference_transcript`
- non-WAV output tuning
- hidden prompt engineering claims that are not encoded in the repo surface

The current sidecar rejects `style_instructions` and `reference_transcript`,
and the benchmark reports only WAV output.

## Experimental eSpeak Path

The repo now includes one benchmark-only eSpeak preprocessing experiment for
Swedish Chatterbox lanes.

Important boundary:

- this does not change the Chatterbox sidecar contract
- this does not add a phoneme mode to `/synthesize`
- this does not move preprocessing into the sidecar container

Instead, Task 89 adds one separate helper image and one separate experiment
runner that:

- writes the original Swedish probe text to an input artifact
- generates one eSpeak-backed phonemized text artifact
- runs one baseline Chatterbox lane from the original text
- runs one comparison lane from the phonemized text

Canonical command:

```bash
pdm run benchmark:task-89
```

Remote execution surface used by the orchestrator:

```bash
pdm run run-hemma -- pdm run benchmark:task-89-hemma
```

Use this path only for experimental A/B evaluation of Swedish phoneme handling.
Do not treat it as a proven production-sidecar improvement until the benchmark
evidence is reviewed.

## Evidence Checklist For Every Lane

Each tuning lane should produce its own deterministic output root containing:

- `report.json`
- `report.md`
- `capabilities.json`
- `voices.json`
- `package_versions.json`
- `gpu-before.txt`
- `gpu-after.txt`
- `docker_logs.txt`
- `artifacts/scenario-a-sv-ref-sv-out.wav`

If the lane is meant to compare against the baseline, the probe text and
reference audio path must also be captured in the report.

## Recommended Decision Discipline

Use this order when judging a tuning lane:

1. Confirm the lane stayed on the official multilingual runtime.
1. Confirm the lane used the intended Swedish-only probe text.
1. Confirm only one tuning variable changed.
1. Listen for:
   - cloning similarity
   - Swedish intelligibility
   - pacing
   - start/end artifacts
   - instability or accent bleed
1. Keep the winning lane only if it is audibly better than the baseline,
   not merely different.

## Current Repo Baseline

The first successful Chatterbox Hemma benchmark evidence already exists under:

- `build/verification/task-86-chatterbox-hemma/`

A Swedish-only comparison lane also exists locally under:

- `build/verification/task-86-chatterbox-hemma-swedish-only-probe/`

Use those as the immediate comparison floor before adding more lanes.
