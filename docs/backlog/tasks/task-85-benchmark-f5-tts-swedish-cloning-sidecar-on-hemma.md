---
id: task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma
title: Benchmark F5-TTS Swedish cloning sidecar on Hemma
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
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - benchmark
  - tts
  - sidecar
  - hemma
  - swedish
  - cloning
  - f5-tts
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Benchmark F5-TTS with the Swedish fine-tune as the next cloning-capable comparison backend after
OpenVoice V2 produced technically successful but qualitatively sub-par teacher-voice results.

## PR Scope

- Add a committed benchmark/smoke command surface for an F5-TTS sidecar on Hemma.
- Prove that the chosen installation path is compatible with the repo's current runtime policy:
  - isolate F5-TTS dependencies from the main Sir Convert-a-Lot runtime,
  - use Python `3.11` or `3.12` only,
  - verify `f5-tts_infer-cli --help` before attempting synthesis.
- Implement the benchmark against the reusable internal sidecar capability contract from
  ADR-0007 (`/health`, `/capabilities`, `/voices`, `/synthesize`).
- Use the current Task 85 runtime source from `ChiliOlavi/F5-TTS@swedish-tts` rather than the
  upstream `SWivid/F5-TTS` release branch.
- Download and record the Swedish model assets from
  `EkhoCollective/f5-tts-swedish`, including the exact checkpoint filename and `vocab.txt`.
- Reuse the same teacher reference voice clip and Swedish probe text discipline as Task 81, but
  adapt the generation flow to F5-TTS requirements:
  - short cleaned reference clip,
  - exact reference transcript,
  - `24 kHz` mono WAV reference preparation,
  - no automatic reference transcription unless explicit fallback testing is requested.
- Capture runtime fit on Hemma:
  - startup profile,
  - cache reuse behavior,
  - GPU usage,
  - cloning success/failure,
  - Swedish sample artifacts,
  - dependency/runtime pressure compared with OpenVoice V2.

## Deliverables

- [x] Committed `benchmark:task-85` command surface (or equivalent named wrapper).
- [x] Deterministic Hemma evidence under `build/verification/task-85-f5-tts-hemma/`.
- [x] Recorded model asset inventory for the Swedish Hugging Face fine-tune, including the exact
  checkpoint filename used by the benchmark.
- [x] Reference-audio preparation evidence with the exact transcript used for `ref_text`.
- [ ] Explicit comparison notes versus OpenVoice V2 and the deferred XTTS-v2 task.

## Acceptance Criteria

- [x] F5-TTS installation succeeds in an isolated benchmark environment that does not widen the
  dependency surface of the main Sir Convert-a-Lot service runtime.
- [x] `f5-tts_infer-cli --help` runs successfully in the chosen environment before benchmark
  synthesis is attempted.
- [x] The sidecar exposes the normalized capability contract from ADR-0007 rather than a
  benchmark-only backend-native surface.
- [x] The benchmark proves whether F5-TTS can complete a cloning flow with Swedish probe text on
  the real R9700 host using the approved teacher reference clip.
- [x] Evidence records the exact Swedish checkpoint file (`.pt` or `.safetensors`) and
  `vocab.txt` used for the run.
- [ ] Evidence records where F5-TTS is stronger or weaker than OpenVoice V2:
  - cloning workflow ergonomics,
  - Swedish output credibility,
  - runtime/dependency complexity,
  - Hemma operational fit.
- [ ] The task ends with a clear recommendation on whether F5-TTS becomes the new lead Swedish
  teacher-voice candidate or falls behind the existing alternatives.

## Current Evidence

- Current repo `HEAD` now points the Task 85 sidecar image at `ChiliOlavi/F5-TTS@swedish-tts`
  instead of `SWivid/F5-TTS@1.1.17`.
- The preserved Hemma evidence below was collected before that runtime-source switch, so it still
  proves only the earlier upstream-runtime lane until a fresh rerun is recorded.
- 2026-03-07 Hemma technical benchmark succeeded on commit
  `f1343104e625a5118fe713c0a10f8f5c41ea00c3`.
- 2026-03-07 quality-sweep follow-up succeeded on commit
  `c9c92afaaa50584a86563d7efd2fdb4a7aae54f6`, which added explicit benchmark logging and
  pass-through controls for `nfe_step`, `remove_silence`, and `vocoder_name`.
- The dedicated sidecar image built successfully as
  `sir-convert-a-lot/f5-sidecar-task85:local`
  and was later rebuilt with the quality-sweep/logging slice as
  `sha256:9d6f2e563b2900b1f19a36d1f76d4525379028517fae0fc935256ec9b7548799`.
- The normalized sidecar reached ready state in `6.153` seconds and passed both:
  - host-lane probing on `http://127.0.0.1:38093`
  - internal service-container probing from `sir_convert_a_lot_prod`
- The benchmark wrote one synthesized Swedish artifact:
  - `build/verification/task-85-f5-tts-hemma/artifacts/sample_sv.wav`
  - SHA256:
    `4d994e1e82aae2cbaa87900506b3e553d4261e537f2e536e68ac0b0b7e59b412`
  - output format: `wav`, `24 kHz`, mono, duration `15.423333` seconds
- The Swedish model asset inventory used by the successful run is:
  - checkpoint: `model_last.pt`
  - vocab: `vocab.txt`
  - companion metadata: `setting.json`
- Reference-input evidence is now concrete and no longer guessed:
  - source clip: `build/verification/task-85-f5-tts-hemma/inputs/reference_source_sv.m4a`
  - prepared clip: `build/verification/task-85-f5-tts-hemma/inputs/reference_10s_sv.wav`
  - transcript:
    `Jag har ofta tänkt på att man inte ska liksom ta scenen dit man kommer, men vad vet jag om det?`
- The longer custom Swedish probe text also synthesized successfully:
  - baseline long-text artifact:
    `build/verification/task-85-f5-tts-hemma-olof-text/artifacts/sample_sv.wav`
  - format: `wav`, `24 kHz`, mono, duration `17.994` seconds
- Quality sweep evidence is now available for direct listening comparison:
  - `nfe_step=48`:
    `build/verification/task-85-f5-tts-hemma-olof-text-nfe48/artifacts/sample_sv.wav`
    - SHA256:
      `009060907d4510e6e23a47307b7ba5aee11acea8d55c4942d662bf1f62a70c8d`
    - format: `wav`, `24 kHz`, mono, duration `17.994` seconds
  - `nfe_step=48` + `remove_silence=true`:
    `build/verification/task-85-f5-tts-hemma-olof-text-nfe48-remove-silence/artifacts/sample_sv.wav`
    - SHA256:
      `813eae6ba4e84ca20da6ecd5df001cc2c192ed705129234c72b07d94fd4c5d39`
    - format: `wav`, `24 kHz`, mono, duration `16.230` seconds
  - `nfe_step=64`:
    `build/verification/task-85-f5-tts-hemma-olof-text-nfe64/artifacts/sample_sv.wav`
    - SHA256:
      `b462440c874faf69a8a3f48a33b7c02f1735f62635b0585451da6be21fd86a9c`
    - format: `wav`, `24 kHz`, mono, duration `17.994` seconds
  - `nfe_step=64` + `remove_silence=true`:
    `build/verification/task-85-f5-tts-hemma-olof-text-nfe64-remove-silence/artifacts/sample_sv.wav`
    - SHA256:
      `3ad225af8a7e447784604049bf726190ea242a5bfe5808ebae0e2c2c429d9bf6`
    - format: `wav`, `24 kHz`, mono, duration `16.500` seconds
- `vocoder_name=bigvgan` is currently not a viable Task 85 lane with the upstream package as
  installed here:
  - the Hemma sidecar returns `500` during `/synthesize`
  - runtime error text points to missing upstream BigVGAN submodule/source-code preparation
  - failure evidence is preserved under
    `build/verification/task-85-f5-tts-hemma-olof-text-nfe48-bigvgan/`

## Remaining Work

- Rebuild and rerun Task 85 on Hemma so the preserved evidence reflects the current
  `ChiliOlavi/F5-TTS@swedish-tts` runtime rather than the earlier upstream runtime.
- Perform listening review across the preserved OpenVoice Task 81 baseline and the new F5 quality
  sweep artifacts.
- Record explicit comparison notes on:
  - cloning workflow ergonomics,
  - Swedish output credibility,
  - runtime/dependency complexity,
  - Hemma operational fit.
- Decide whether the best Task 85 quality lane is the original baseline, `nfe48`,
  `nfe48 + remove_silence`, or `nfe64`.
- End the task with a recommendation instead of a purely technical pass.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
