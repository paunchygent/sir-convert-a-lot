---
id: task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma
title: Benchmark Chatterbox Multilingual Swedish cloning sidecar on Hemma
type: task
status: in_progress
priority: high
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - benchmark
  - tts
  - sidecar
  - hemma
  - swedish
  - cloning
  - chatterbox
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Benchmark Resemble AI Chatterbox Multilingual as the next Swedish-capable cloning backend after
the negative qualitative outcome from Task 85 F5-TTS, using only officially documented
Chatterbox capabilities and a quality-first benchmark discipline on Hemma.

## PR Scope

- Add a committed benchmark/smoke command surface for a Chatterbox Multilingual sidecar on Hemma.
- Prove the official multilingual model path first:
  - `pip install chatterbox-tts`,
  - `from chatterbox.mtl_tts import ChatterboxMultilingualTTS`,
  - one successful smoke synthesis through the official Python API.
- Keep the benchmark isolated from the main Sir Convert-a-Lot runtime.
- Map Chatterbox to the normalized ADR-0007 sidecar contract:
  - `/health`,
  - `/capabilities`,
  - `/voices`,
  - `/synthesize`.
- Reuse the approved teacher reference clip from the Story 23 discipline, but record the
  Chatterbox-specific difference that no reference transcript is required.
- Benchmark only officially supported Chatterbox Multilingual controls:
  - `language_id="sv"`,
  - `audio_prompt_path`,
  - `exaggeration`,
  - `cfg_weight`.
- Prioritize output quality over low GPU usage:
  - no benchmark acceptance credit for minimizing VRAM,
  - record the real GPU/runtime footprint instead of optimizing it away,
  - do not introduce CPU fallback as a silent substitute for the benchmark target.
- Record two explicit cloning scenarios:
  - same-language cloning: Swedish reference -> Swedish output,
  - cross-language cloning only if a real English reference clip is available and approved.
- Record only verified upstream facts in the evidence bundle and task notes:
  - `chatterbox-tts` package/runtime truth,
  - official multilingual language support including `sv`,
  - official sample rate (`24000` Hz),
  - official watermarking behavior,
  - actual Hemma runtime results.

## Deliverables

- [ ] Committed `benchmark:task-86` command surface (or equivalent named wrapper).
- [ ] Deterministic Hemma evidence under `build/verification/task-86-chatterbox-hemma/`.
- [ ] One successful official-API smoke artifact from `ChatterboxMultilingualTTS`.
- [ ] One successful Swedish cloning artifact using the approved teacher reference clip.
- [ ] Recorded runtime-truth bundle:
  - package version,
  - model cache location,
  - cold-start time,
  - warm-start time,
  - per-utterance synthesis time,
  - GPU usage before/during/after.
- [ ] Explicit comparison notes versus OpenVoice V2 and F5-TTS, including whether Chatterbox
  becomes the lead Swedish teacher-voice candidate.

## Acceptance Criteria

- [ ] The benchmark uses the official multilingual Chatterbox class rather than an inferred or
  community-only wrapper:
  - `chatterbox.mtl_tts.ChatterboxMultilingualTTS`
- [ ] The benchmark proves whether official `language_id="sv"` synthesis works on Hemma with the
  approved teacher reference clip.
- [ ] The sidecar exposes the normalized capability contract from ADR-0007 rather than a
  Chatterbox-native benchmark-only surface.
- [ ] Same-language Swedish cloning is benchmarked with:
  - the approved teacher reference clip,
  - `language_id="sv"`,
  - recorded `cfg_weight` and `exaggeration`,
  - saved `24 kHz` output artifacts.
- [ ] The benchmark records that Chatterbox does not require a reference transcript for cloning.
- [ ] If cross-language cloning is benchmarked, it uses an explicitly approved English reference
  clip and records the official Chatterbox guidance to set `cfg_weight=0` to reduce accent bleed.
- [ ] The benchmark records actual Hemma runtime truth instead of assumptions:
  - model download/cache behavior,
  - package/runtime versions,
  - GPU memory/utilization,
  - synthesis latency.
- [ ] Watermarking is recorded explicitly as a production-governance consideration because the
  official model embeds PerTh watermarks in generated output.
- [ ] The task ends with a clear recommendation:
  - Chatterbox becomes the new lead Swedish cloning candidate, or
  - Chatterbox is rejected with explicit evidence.

## Verified Upstream Facts To Anchor The Benchmark

- Official package name: `chatterbox-tts`
- Official multilingual class: `chatterbox.mtl_tts.ChatterboxMultilingualTTS`
- Official source repo: `https://github.com/resemble-ai/chatterbox`
- Official Hugging Face repo: `ResembleAI/chatterbox`
- Official multilingual support includes Swedish `sv`
- Official multilingual model size claim: `0.5B` Llama backbone
- Official training-data claim: `0.5M hours of cleaned data`
- Official sample rate in code: `24000`
- Official installed dependency pins in upstream `pyproject.toml` include:
  - `torch==2.6.0`
  - `torchaudio==2.6.0`
  - `transformers==4.46.3`
  - `diffusers==0.29.0`
- Official controls documented for multilingual generation:
  - `audio_prompt_path`
  - `language_id`
  - `exaggeration`
  - `cfg_weight`
- Official watermarking statement: generated outputs include PerTh watermarking
- Official license: MIT

## Non-Goals

- Do not invent unsupported Chatterbox settings or quality knobs that are not present in the
  official multilingual API.
- Do not treat third-party hosting guidance as normative runtime truth for Hemma.
- Do not silently downgrade the benchmark target to CPU if the official GPU path fails.
- Do not adopt a community sidecar server as the production shape during this task; the benchmark
  only needs to prove that the ADR-0007 contract is satisfiable.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
