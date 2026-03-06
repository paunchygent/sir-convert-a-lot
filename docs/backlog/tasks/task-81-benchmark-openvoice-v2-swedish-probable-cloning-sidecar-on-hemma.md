---
id: task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma
title: Benchmark OpenVoice V2 Swedish-probable cloning sidecar on Hemma
type: task
status: in_progress
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
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
  - openvoice
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Prove whether OpenVoice V2 is the strongest next Hemma sidecar candidate for Swedish-capable
teacher voice cloning, using live R9700 evidence rather than upstream claims alone.

## PR Scope

- Add a committed benchmark/smoke command surface for an OpenVoice V2 sidecar on Hemma.
- Implement the benchmark against the reusable internal sidecar capability contract from
  ADR-0007 (`/health`, `/capabilities`, `/voices`, `/synthesize`).
- Reuse the canonical Hemma persistent model-cache discipline so reruns do not redownload model
  weights.
- Exercise a cloning flow with one approved teacher reference voice clip.
- Exercise Swedish probe text generation and capture sample artifacts for listening review.
- Record runtime truth:
  - Python version,
  - backend package/runtime versions,
  - GPU identity and peak utilization,
  - whether the sidecar remains reachable from Sir Convert-a-Lot over the internal Docker network.

## Deliverables

- [x] Committed `benchmark:task-81` command surface (or equivalent named wrapper).
- [x] Deterministic Hemma evidence under `build/verification/task-81-openvoice-v2-hemma/`.
- [x] Swedish sample artifacts generated from a cloning flow.
- [ ] Explicit recommendation on whether OpenVoice V2 becomes the primary cloning-capable backend
  candidate for the next implementation slice.

## Current Evidence (2026-03-06)

- Live Hemma benchmark evidence exists under `build/verification/task-81-openvoice-v2-hemma/`.
- The OpenVoice sidecar now boots on Hemma, reuses canonical caches, answers the normalized
  ADR-0007 endpoints, and returns `audio/wav` for a Swedish cloning request.
- The current generated artifact is `build/verification/task-81-openvoice-v2-hemma/artifacts/sample_sv.wav`.
- Manual listening review rejected the current setup:
  - timbre not close enough to the approved teacher reference voice,
  - audible artifacts,
  - uneven pacing.
- Current conclusion: the model setup is bad even though the benchmark is technically working.
  Task 81 remains open until we rerun with a corrected setup and decide whether OpenVoice stays
  credible for this use case.

## Failure Record

- Failure type: quality/setup failure, not runtime failure.
- What failed:
  - cloned Swedish output quality,
  - voice similarity to the approved teacher reference clip.
- Why we are not closing the task:
  - technical success alone is insufficient for the teacher-voice requirement,
  - the current OpenVoice plus Swedish-base setup should not be treated as accepted.

## Current Setup Concerns (2026-03-06)

- The current adapter writes Swedish MMS base audio using the OpenVoice converter sample rate
  rather than the Swedish base model's native sample rate. This is a likely pacing/timbre defect
  in the current benchmark output and must be corrected before another quality judgment.
- The current adapter extracts the target speaker embedding directly from the full approved
  reference clip instead of using OpenVoice's intended reference-speaker preprocessing flow.
  That means the benchmark is skipping the model's speech-segmentation/reference-cleanup path.
- The current benchmark evidence only preserves the final cloned artifact. It does not yet write
  the processed reference artifact plus the pre-conversion Swedish base artifact needed to isolate
  whether defects come from the base voice, the reference embedding, or the tone-color conversion
  step.

## Remediation Track

- [ ] Correct the sample-rate contract between the Swedish base model and the OpenVoice converter:
  - write base audio at the base model's native sample rate,
  - resample explicitly only when the converter requires a different rate,
  - record both rates in the benchmark report.
- [ ] Replace the current simplified reference-speaker setup with the intended OpenVoice
  reference-speaker preprocessing path and preserve the processed reference artifact used for
  embedding extraction.
- [ ] Produce paired rerun artifacts so we can compare:
  - processed reference audio,
  - Swedish base output before cloning,
  - Swedish cloned output after tone-color conversion.
- [ ] Rerun Task 81 on Hemma with the corrected setup and preserve the failed sample as baseline
  evidence rather than overwriting the learning.
- [ ] Record whether the corrected setup removes the reported artifacts, improves pacing, and
  materially improves timbre match to the approved teacher voice.
- [ ] If the corrected rerun is still poor, record OpenVoice as technically feasible but not the
  primary Swedish teacher-voice candidate, then proceed to `T82`.

## Immediate Execution Order

1. Fix the base-model vs converter sample-rate handling first.
1. Switch reference embedding extraction onto the intended OpenVoice preprocessing path.
1. Extend the benchmark evidence to emit processed-reference, base, and cloned Swedish artifacts.
1. Rerun the same Swedish probe text with the same approved teacher reference clip on Hemma.
1. Decide whether OpenVoice remains credible only after listening to the corrected rerun.

## Acceptance Criteria

- [x] OpenVoice V2 sidecar boots on Hemma and is reachable from the Sir Convert-a-Lot service
  container over the internal Docker network only.
- [x] The sidecar exposes the normalized capability contract from ADR-0007 rather than a
  benchmark-only backend-native surface.
- [x] The benchmark proves model-cache reuse via the canonical host storage pattern rather than
  repeated runtime downloads.
- [x] One cloning flow succeeds with the approved teacher reference clip and Swedish probe text.
- [x] Evidence clearly separates:
  - official upstream support claims,
  - live Hemma runtime truth,
  - subjective listening notes.
- [ ] The task records whether OpenVoice V2 is sufficiently credible to be the default Swedish-
  probable cloning backend for follow-on implementation work.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
