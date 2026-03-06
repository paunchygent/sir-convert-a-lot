---
id: story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma
title: Swedish-capable cloning TTS benchmark matrix on Hemma
type: story
status: in_progress
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-84-remediate-task-81-openvoice-benchmark-root-causes-and-evidence-export.md
  - docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/reference/ref-hemma-sidecar-tts-md-to-wav-contract-outline.md
labels:
  - tts
  - sidecar
  - benchmark
  - swedish
  - cloning
---

Implementation slice with acceptance-driven scope.

## Objective

Define the benchmark matrix that will choose the most credible cloning-capable Swedish TTS backend
for Hemma before we commit implementation defaults for teacher-voice audio delivery.

## Scope

- Benchmark OpenVoice V2 as the primary Swedish-probable cloning candidate based on official
  cross-lingual voice-cloning claims.
- Benchmark XTTS-v2 as the comparison cloning backend using the same Hemma sidecar discipline and
  evidence structure.
- Benchmark MMS Swedish as a direct-pronunciation control to separate language quality from
  cloning capability.
- Keep the main Sir Convert-a-Lot public API and provider-neutral `tts_options` contract stable
  while the sidecar backend choice remains open.
- Require candidate benchmarks to target the reusable internal sidecar capability contract from
  ADR-0007 rather than backend-native APIs directly.
- Reuse the Hemma model-cache discipline:
  - canonical persistent host cache/storage,
  - no repeated redownloads between runs,
  - no ad hoc container-local model storage.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md`
1. `docs/backlog/tasks/task-84-remediate-task-81-openvoice-benchmark-root-causes-and-evidence-export.md`
1. `docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md`
1. `docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md`

## Current Story Notes (2026-03-06)

- `T81` has now proven technical feasibility on live Hemma:
  - sidecar boots,
  - canonical caches are reused,
  - Swedish cloned output is generated from the approved teacher reference clip.
- `T81` has not yet proven product credibility:
  - manual listening review rejected the current sample because the timbre is not close enough,
    artifacts are present, and pacing is uneven.
- Story 23 therefore remains in the `T81` lane until one corrected OpenVoice setup rerun is
  judged, rather than treating the current result as a pass and moving on too quickly.
- The current remediation order for `T81` is explicit:
  - fix the sample-rate mismatch between the Swedish base model and the OpenVoice converter,
  - switch to the intended OpenVoice reference-speaker preprocessing path,
  - emit processed-reference plus base-vs-cloned Swedish artifacts,
  - rerun the same approved teacher-voice benchmark before considering `T82`.
- `T84` is now the explicit root-cause remediation lane for `T81`, so benchmark fixes and the
  reasoning behind them stay reviewable instead of being buried inside the broader benchmark task.
- The binding ruthless review changed the immediate Story 23 standard for `T81`:
  - the next OpenVoice rerun must produce one atomic evidence bundle,
  - declare the Torch/Silero cache surface explicitly,
  - record machine-readable benchmark status,
  - and preserve reference/setup artifacts strongly enough for a second review pass.
- Current-head Hemma rerun on `beac775f1f6c021946105adef0f007cf06b908d3` met the first half of
  that standard:
  - one atomic partial evidence bundle now exists for `run_id=20260306T220740Z`,
  - the earlier export failure did not reproduce,
  - machine-readable benchmark/evidence status now matches the live rerun.
- Story 23 is still blocked in `T81` because the remaining failure has moved earlier into
  `/synthesize`:
  - `whisper-timestamped` still asserts a missing Silero repo under `/root/.cache/torch/hub`,
  - the declared `TORCH_HOME=/cache/huggingface/torch` is therefore not yet the effective runtime
    path,
  - processed-reference and base-audio artifacts still cannot be judged on the corrected setup.

## Acceptance Criteria

- [ ] Task 81 defines deterministic Hemma evidence for OpenVoice V2 startup, cache reuse,
  cloning flow, and Swedish-text synthesis with a teacher reference voice sample.
- [ ] Task 81 records the current failed-quality baseline plus at least one corrected setup rerun
  before we decide whether OpenVoice remains the lead candidate.
- [ ] Task 82 defines parallel evidence for XTTS-v2 so we can compare cloning quality, runtime
  fit, and operational complexity against OpenVoice V2.
- [ ] Task 83 defines a Swedish pronunciation control benchmark whose result is explicitly
  non-canonical for backend selection because cloning is absent.
- [ ] Story outputs are strong enough to recommend:
  - one primary cloning-capable backend candidate,
  - one comparison backend,
  - one pronunciation control baseline,
    without reopening ADR-0006 or the public v2 contract shape.
  - and without inventing a backend-specific service integration path outside ADR-0007.

## Test Requirements

- [ ] Each task writes deterministic Hemma evidence under `build/verification/` with:
  - `report.json`,
  - `report.md`,
  - sidecar logs,
  - at least one synthesized Swedish sample artifact.
- [ ] OpenVoice V2 and XTTS-v2 tasks require an explicit cloning workflow using one approved
  teacher reference clip.
- [ ] Quality failures must be recorded explicitly in the active task/story docs with:
  - what worked technically,
  - why the result still failed,
  - what setup change will be tested next.
- [ ] `T81` must isolate setup defects in evidence by preserving:
  - the processed reference artifact actually used for embedding extraction,
  - the Swedish base artifact before cloning,
  - the final cloned Swedish artifact.
- [ ] `T81` must clear the current synthesize-stage Torch Hub / Silero path mismatch before the
  corrected setup can be evaluated for audio quality.
- [ ] Each task records Python/runtime truth, model cache path, and whether the sidecar remains
  internal-network only.

## Done Definition

The team has enough live Hemma evidence to choose the next cloning-capable Swedish TTS backend
without guessing from upstream docs alone.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [x] Docs synchronized
