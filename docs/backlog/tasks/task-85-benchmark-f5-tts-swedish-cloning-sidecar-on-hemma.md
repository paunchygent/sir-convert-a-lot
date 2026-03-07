---
id: task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma
title: Benchmark F5-TTS Swedish cloning sidecar on Hemma
type: task
status: proposed
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

- [ ] Committed `benchmark:task-85` command surface (or equivalent named wrapper).
- [ ] Deterministic Hemma evidence under `build/verification/task-85-f5-tts-hemma/`.
- [ ] Recorded model asset inventory for the Swedish Hugging Face fine-tune, including the exact
  checkpoint filename used by the benchmark.
- [ ] Reference-audio preparation evidence with the exact transcript used for `ref_text`.
- [ ] Explicit comparison notes versus OpenVoice V2 and the deferred XTTS-v2 task.

## Acceptance Criteria

- [ ] F5-TTS installation succeeds in an isolated benchmark environment that does not widen the
  dependency surface of the main Sir Convert-a-Lot service runtime.
- [ ] `f5-tts_infer-cli --help` runs successfully in the chosen environment before benchmark
  synthesis is attempted.
- [ ] The sidecar exposes the normalized capability contract from ADR-0007 rather than a
  benchmark-only backend-native surface.
- [ ] The benchmark proves whether F5-TTS can complete a cloning flow with Swedish probe text on
  the real R9700 host using the approved teacher reference clip.
- [ ] Evidence records the exact Swedish checkpoint file (`.pt` or `.safetensors`) and
  `vocab.txt` used for the run.
- [ ] Evidence records where F5-TTS is stronger or weaker than OpenVoice V2:
  - cloning workflow ergonomics,
  - Swedish output credibility,
  - runtime/dependency complexity,
  - Hemma operational fit.
- [ ] The task ends with a clear recommendation on whether F5-TTS becomes the new lead Swedish
  teacher-voice candidate or falls behind the existing alternatives.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
