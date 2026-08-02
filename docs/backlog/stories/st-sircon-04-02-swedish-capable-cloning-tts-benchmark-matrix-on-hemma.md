---
type: story
id: ST-SIRCON-04-02
title: Swedish-capable cloning TTS benchmark matrix on Hemma
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-04
links:
  decisions: []
acceptance_criteria:
- Task 81 defines deterministic Hemma evidence for OpenVoice V2 startup, cache reuse,
  cloning flow, and Swedish-text synthesis with a teacher reference voice sample.
- Task 81 records the failed-quality baseline plus at least one corrected setup rerun
  before deciding whether OpenVoice remains the lead candidate.
- Task 85 defines parallel evidence for F5-TTS to compare cloning quality, runtime
  fit, and operational complexity against OpenVoice V2.
- Task 86 defines deterministic Hemma evidence for Chatterbox Multilingual Swedish
  cloning, including quality-first settings and watermark/runtime-governance notes.
- Task 83 defines a Swedish pronunciation control benchmark explicitly non-canonical
  for backend selection because cloning is absent.
- Story outputs recommend one primary cloning-capable backend, one comparison backend,
  and one pronunciation control baseline without reopening ADR-0006 or the public
  v2 contract and without inventing a backend-specific path outside ADR-0007.
retired_ids:
- story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma
---


## Context

State the actor or consumer need and the parent epic outcome this story serves.

## Epic Contract Slice

Define one independently reviewable observable behavior or capability slice.

## ADR Coverage

No new governing direction is introduced by this contract.

Applicable ADR IDs must equal the unique IDs in `links.decisions`; this section
records semantic coverage only and does not enforce readiness.

## Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this story.

## Live Verification Plan

- Story checkpoint and applicable acceptance criteria.
- Real route and expected observable result.
- Task evidence consumed and retained story-level verification evidence.

## Non-Goals

- Adjacent behavior or implementation work this story must not absorb.

## Notes

Record current story-local interpretation that does not belong in the contract,
ledger, or non-goals.

## Decision And Assumption Ledger

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

## Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

## Story Closeout Review

Record verification result, evidence, permitted next step, unavailable mandatory
evidence, and residual risk. The `closeout_review` frontmatter mapping is the
machine authority for gate status and approval evidence.

## Source Body Preservation

Implementation slice with acceptance-driven scope.
## Objective
Define the benchmark matrix that will choose the most credible cloning-capable Swedish TTS backend for Hemma before we commit implementation defaults for teacher-voice audio delivery.
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
ADR-SIRCON-0006 rather than backend-native APIs directly.
- Keep Sir-owned Qwen Swedish fine-tuning planning under Epic 08 as a separate
upstream model-creation lane; Story 23 remains a benchmark-and-selection lane for externally sourced runtime candidates.
- Reuse the Hemma model-cache discipline:
  - canonical persistent host cache/storage,
  - no repeated redownloads between runs,
  - no ad hoc container-local model storage.
## Tasks (Ordered)
1. `docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md` 1. `docs/backlog/tasks/task-84-remediate-task-81-openvoice-benchmark-root-causes-and-evidence-export.md` 1. `docs/backlog/tasks/task-sircon-04-02-03-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md` 1. `docs/backlog/tasks/task-sircon-04-02-08-expose-f5-tuning-controls-and-exact-voice-tag-support-on-hemma.md` 1. `docs/backlog/tasks/task-97-align-f5-reference-duration-and-add-segmented-hemma-lane.md` 1. `docs/backlog/tasks/task-sircon-04-02-04-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md` 1. `docs/backlog/tasks/task-sircon-04-02-05-run-chatterbox-multilingual-tuning-sweep-on-hemma.md` 1. `docs/backlog/tasks/task-sircon-04-02-06-research-espeak-ng-phoneme-support-for-swedish-chatterbox-integration.md` 1. `docs/backlog/tasks/task-89-implement-benchmark-only-espeak-ng-preprocessing-for-chatterbox-swedish-lanes.md` 1. `docs/backlog/tasks/task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma.md` 1. `docs/backlog/tasks/task-sircon-04-02-07-implement-speech-aware-chatterbox-stitching-and-tail-cleanup-on-hemma.md` 1. `docs/backlog/tasks/task-93-implement-clause-aware-duration-bounded-chatterbox-chunk-planning-on-hemma.md` 1. `docs/backlog/tasks/task-sircon-04-02-02-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md`
Deferred follow-up:
1. `docs/backlog/tasks/task-sircon-04-02-01-benchmark-xtts-v2-as-the-comparison-cloning-sidecar-on-hemma.md`
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
`EkhoCollective/f5-tts-swedish` currently exposes `model_last.pt`, `setting.json`, and `vocab.txt`,
  - the current Task 85 runtime source has now been switched from `SWivid/F5-TTS@1.1.17` to
`ChiliOlavi/F5-TTS@swedish-tts`,
  - the current branch-backed rerun on commit
`af36f5085d137bc20116086376e4d7e9b36dc9b1` now succeeds end to end on Hemma,
  - the switch exposed one real runtime blocker first:
`torchaudio.load()` required `torchcodec` in the sidecar image,
  - that blocker is now fixed in the Task 85 image and the refreshed evidence bundle lives again
under `build/verification/task-85-f5-tts-hemma/`,
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
  - the benchmark proved the normalized ADR-SIRCON-0006 sidecar contract end to end with the official
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
review before deciding whether Chatterbox becomes the new lead Swedish cloning candidate.
  - `T88` is now opened as the phoneme-research follow-up to determine whether
eSpeak NG should remain a benchmark-only preprocessing experiment or become a stronger part of the Swedish Chatterbox pipeline.
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
  - `T90` is now implemented with live Hemma evidence:
    - single-pass and segmented normal-text lanes both succeeded,
    - the segmented lane preserved a deterministic `3`-segment plan plus
chunk-level debug artifacts,
    - single-pass clone duration was `51.904` seconds,
    - segmented clone duration was `57.473` seconds,
    - single-pass peak VRAM was `5959815168` bytes,
      - segmented peak VRAM was `5742292992` bytes.
  - The qualitative Task 90 verdict is now recorded:
    - segmented output is better overall than single-pass on longer passages,
    - especially toward the end where the single-pass lane sounds more stressed,
    - but stitch-point tails still carry noise and pauses can be too long.
  - `T91` is now the next Chatterbox quality slice:
    - speech-aware tail cleanup,
    - pause-aware boundary stitching,
    - improved cross-fade that preserves natural pauses.
  - `T91` now has live Hemma evidence:
    - both segmented lanes synthesized successfully,
    - the baseline simple stitch lane is recorded under
`build/verification/task-91-chatterbox-speech-aware-stitching-hemma/simple/`,
    - the new speech-aware lane is recorded under
`build/verification/task-91-chatterbox-speech-aware-stitching-hemma/speech_aware/`,
    - the speech-aware lane writes chunk analysis and per-boundary decisions,
    - measured output duration dropped from `123.426` seconds in the simple
segmented lane to `94.954` seconds in the speech-aware lane,
    - peak VRAM also dropped from `6239154176` bytes to `5945778176` bytes,
    - Story 23 still needs the listening verdict before `T91` can be closed
as better, worse, or unchanged.
  - The next Chatterbox quality blocker is now segment planning rather than
stitching:
    - the latest delegate-text run produced a `19.92` second first chunk under
the older sentence-packing planner,
    - that oversized first chunk caused stressed delivery, speedups, and
audible artifacts,
    - `T93` is now the active fix slice for:
      - list-item-aware boundaries,
      - clause-aware planning units,
      - a `4-6` second target band,
      - and a hard `9` second planning ceiling per chunk.
  - `T93` now has live Hemma evidence:
    - the same delegate text now emits `7` chunks instead of `2`,
    - the first chunk dropped from `19.92` seconds to `5.36` seconds,
    - all measured chunk durations now fall between `3.6` and `5.36`
seconds,
    - the measured average chunk duration is approximately `4.5` seconds,
    - the planner now keeps each numbered list item as its own preferred chunk
boundary unless the intro is short enough to merge with item one.
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
without reopening ADR-SIRCON-0005 or the public v2 contract shape.
  - and without inventing a backend-specific service integration path outside ADR-SIRCON-0006.
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
The team has enough live Hemma evidence to choose the next cloning-capable Swedish TTS backend without guessing from upstream docs alone.
## Checklist
- [ ] Implementation complete
- [ ] Tests and validations complete
- [x] Docs synchronized

