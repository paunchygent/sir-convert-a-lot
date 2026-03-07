---
id: story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma
title: Swedish-capable cloning TTS benchmark matrix on Hemma
type: story
status: in_progress
priority: high
created: '2026-03-06'
last_updated: '2026-03-07'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-84-remediate-task-81-openvoice-benchmark-root-causes-and-evidence-export.md
  - docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-87-run-chatterbox-multilingual-tuning-sweep-on-hemma.md
  - docs/backlog/tasks/task-88-research-espeak-ng-phoneme-support-for-swedish-chatterbox-integration.md
  - docs/backlog/tasks/task-89-implement-benchmark-only-espeak-ng-preprocessing-for-chatterbox-swedish-lanes.md
  - docs/backlog/tasks/task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma.md
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
- Benchmark F5-TTS with the Swedish fine-tune as the active comparison cloning backend using the
  same Hemma sidecar discipline and evidence structure.
- Keep XTTS-v2 available as a deferred follow-up candidate rather than the active next lane.
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
1. `docs/backlog/tasks/task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md`
1. `docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md`
1. `docs/backlog/tasks/task-87-run-chatterbox-multilingual-tuning-sweep-on-hemma.md`
1. `docs/backlog/tasks/task-88-research-espeak-ng-phoneme-support-for-swedish-chatterbox-integration.md`
1. `docs/backlog/tasks/task-89-implement-benchmark-only-espeak-ng-preprocessing-for-chatterbox-swedish-lanes.md`
1. `docs/backlog/tasks/task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma.md`
1. `docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md`

Deferred follow-up:

1. `docs/backlog/tasks/task-82-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md`

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
- Current complete Hemma rerun on `61b263cab56118677dc47810b615daaf0adbe463` now meets that
  benchmark-standard:
  - one atomic complete evidence bundle now exists for `run_id=20260306T224057Z`,
  - the earlier export failure remains disproved,
  - machine-readable benchmark/evidence status matches the live rerun,
  - processed-reference, base-audio, converter-input, and cloned artifacts are all preserved.
- `T84` is therefore complete.
- Story 23 remains in the `T81` lane only for qualitative judgment:
  - compare the corrected successful rerun against the failed baseline,
  - decide whether OpenVoice stays credible enough to remain the lead candidate,
  - if not, proceed directly to `T82`.
- Qualitative judgment is now recorded:
  - the default Swedish base artifact is very unnatural, with pitch, tone, and phrasing issues,
  - the cloned artifact is somewhat better than the base artifact,
  - the cloned artifact is still sub-par for the teacher-voice goal,
  - OpenVoice therefore remains technically feasible but is no longer the lead Swedish
    teacher-voice candidate.
- Story 23 now advances to `T82`, with `T83` still kept as the Swedish pronunciation control.
- 2026-03-07 planning update:
  - after `T81` closed with a negative recommendation on OpenVoice quality, the next active
    cloning lane was redirected from XTTS-v2 to F5-TTS based on the explicit user decision,
  - `T85` now owns the active comparison benchmark,
  - `T82` remains documented as a deferred follow-up rather than the immediate next slice,
  - the benchmark must prove the environment-adapted install path first by running
    `f5-tts_infer-cli --help`,
  - the Swedish model asset inventory is now concrete upstream evidence:
    `EkhoCollective/f5-tts-swedish` currently exposes `model_last.pt`, `setting.json`, and
    `vocab.txt`,
  - the shared teacher reference clip still requires an exact transcript and `24 kHz` mono WAV
    preprocessing before any fair F5-TTS quality judgment.
- 2026-03-07 Chatterbox follow-up update:
  - `T85` produced a technically successful F5-TTS integration but remained qualitatively
    unacceptable on the evaluated Swedish outputs,
  - the next active cloning lane is now `T86` Chatterbox Multilingual,
  - `T86` is intentionally constrained to officially documented Chatterbox controls and
    multilingual runtime surfaces only,
  - `T86` also records a key contract difference versus F5-TTS: Chatterbox cloning does not
    require a reference transcript.
  - `T86` now has its first technically successful live Hemma benchmark run on commit
    `a93bf39edcf62b456bf65eff4e4b5f20b23ce769`,
  - the benchmark proved the normalized ADR-0007 sidecar contract end to end with the official
    multilingual runtime:
    - `GET /health`
    - `GET /capabilities`
    - `GET /voices`
    - `POST /synthesize`
  - the same-language Swedish cloning artifact now exists under
    `build/verification/task-86-chatterbox-hemma/artifacts/scenario-a-sv-ref-sv-out.wav`,
  - runtime truth is now concrete instead of inferred:
    - startup `33.207` seconds,
    - warm restart `21.065` seconds,
    - Swedish clone peak VRAM `8982421504` bytes on `AMD Radeon AI PRO R9700`,
    - cached model snapshot reused from the canonical Hugging Face cache,
  - `T87` is now the follow-on execution slice for the first committed
    Chatterbox tuning sweep on Hemma,
  - the sweep is constrained to the documented runbook values only:
    - `exaggeration` in `{0.5, 0.7}`
    - `cfg_weight` in `{0.5, 0.3, 0.0}`
  - Story 23 now needs the completed conservative-first sweep and listening
    review before deciding whether Chatterbox becomes the new lead Swedish
    cloning candidate.
  - `T88` is now opened as the phoneme-research follow-up to determine whether
    eSpeak NG should remain a benchmark-only preprocessing experiment or become
    a stronger part of the Swedish Chatterbox pipeline.
  - `T89` is now the first implementation slice for that conclusion:
    - a benchmark-only eSpeak preprocessing path,
    - separate helper image,
    - no Chatterbox sidecar contract change,
    - baseline-vs-preprocessed comparison on Hemma.
  - `T89` is now complete with live Hemma evidence:
    - baseline and eSpeak-preprocessed lanes both succeeded,
    - the helper path is operationally proven,
    - but it does not replace the missing segmentation-and-stitching layer.
  - The Chatterbox decision after `T89` is now explicit:
    - keep the eSpeak helper path for future non-Chatterbox experiments,
    - stop using it in the active Chatterbox quality lane,
    - continue Chatterbox only on the documented normal-text path.
  - Current Chatterbox quality limitations are now explicit repo-truth items:
    - the current path is still single-pass,
    - no sentence splitting,
    - no prosodic-boundary detection,
    - no chunk batching,
    - no chunk stitching or cross-fade,
    - so maximal-quality long-form output now requires a follow-on
      segmentation-and-stitching slice beyond `T89`.

## Acceptance Criteria

- [x] Task 81 defines deterministic Hemma evidence for OpenVoice V2 startup, cache reuse,
  cloning flow, and Swedish-text synthesis with a teacher reference voice sample.
- [x] Task 81 records the current failed-quality baseline plus at least one corrected setup rerun
  before we decide whether OpenVoice remains the lead candidate.
- [x] Task 85 defines parallel evidence for F5-TTS so we can compare cloning quality, runtime
  fit, and operational complexity against OpenVoice V2.
- [x] Task 86 defines deterministic Hemma evidence for Chatterbox Multilingual Swedish cloning,
  including quality-first settings and watermark/runtime-governance notes.
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
- [ ] OpenVoice V2 and F5-TTS tasks require an explicit cloning workflow using one approved
  teacher reference clip.
- [x] Quality failures must be recorded explicitly in the active task/story docs with:
  - what worked technically,
  - why the result still failed,
  - what setup change will be tested next.
- [x] `T81` must isolate setup defects in evidence by preserving:
  - the processed reference artifact actually used for embedding extraction,
  - the Swedish base artifact before cloning,
  - the final cloned Swedish artifact.
- [x] `T81` now preserves processed-reference, base, and converter-input artifacts on the
  corrected rerun before the audio quality can be evaluated fairly.
- [ ] Each task records Python/runtime truth, model cache path, and whether the sidecar remains
  internal-network only.
- [x] `T86` now records deterministic Hemma evidence for:
  - successful image build via BuildKit,
  - official multilingual runtime startup,
  - normalized sidecar readiness,
  - smoke-test plus Swedish-cloning artifacts,
  - package/runtime versions,
  - cached model snapshot path,
  - GPU before/after plus per-probe peak usage.
- [x] `T85` now records deterministic Hemma evidence for:
  - successful image build plus `f5-tts_infer-cli --help`,
  - normalized sidecar readiness,
  - service-container probe success,
  - Swedish model inventory (`model_last.pt`, `setting.json`, `vocab.txt`),
  - synthesized artifact `build/verification/task-85-f5-tts-hemma/artifacts/sample_sv.wav`.

## Done Definition

The team has enough live Hemma evidence to choose the next cloning-capable Swedish TTS backend
without guessing from upstream docs alone.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [x] Docs synchronized
