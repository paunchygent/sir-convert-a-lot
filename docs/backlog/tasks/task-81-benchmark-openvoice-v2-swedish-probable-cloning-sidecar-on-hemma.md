---
id: task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma
title: Benchmark OpenVoice V2 Swedish-probable cloning sidecar on Hemma
type: task
status: completed
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-84-remediate-task-81-openvoice-benchmark-root-causes-and-evidence-export.md
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
- [x] Explicit recommendation on whether OpenVoice V2 becomes the primary cloning-capable backend
  candidate for the next implementation slice.

## Current Evidence (2026-03-06)

- Live Hemma benchmark evidence exists under `build/verification/task-81-openvoice-v2-hemma/`.
- The preserved failed-setup baseline now lives under
  `build/verification/task-81-openvoice-v2-hemma/baseline_failed_setup/`.
- The failed-setup baseline generated one Swedish cloned sample at
  `build/verification/task-81-openvoice-v2-hemma/baseline_failed_setup/sample_sv.wav`.
- Manual listening review rejected that baseline setup:
  - timbre not close enough to the approved teacher reference voice,
  - audible artifacts,
  - uneven pacing.
- Current conclusion about the failed baseline:
  - the model setup was bad even though the benchmark was technically working,
  - the baseline sample remains useful only as before/after evidence.
- Local remediation implementation is now in place:
  - the sidecar separates Swedish base-model sample-rate handling from converter sample-rate
    handling,
  - the sidecar uses a committed local VAD-only reference-preprocessing helper instead of
    importing upstream `openvoice.se_extractor`,
  - the sidecar image no longer depends on `faster-whisper`, which was the broken Hemma Python
    3.12 build path.
- The `torchaudio` / runtime dependency blocker has been fixed in the benchmark image.
- Current complete Hemma rerun on `61b263cab56118677dc47810b615daaf0adbe463` now emits one atomic
  success bundle:
  - `run_id=20260306T224057Z`,
  - `benchmark_status=succeeded`,
  - `evidence_status=complete`,
  - `blocking_step=null`,
  - `failure=null`.
- The earlier synthesize-stage Torch Hub / Silero blocker is fixed on current benchmark `HEAD`:
  - the sidecar no longer uses `whisper-timestamped` in the active reference-preprocessing path,
  - `/synthesize` returns `200 OK`,
  - canonical Torch cache truth is declared and used without reintroducing legacy cache paths.
- The earlier export failure also remains disproved on the successful rerun:
  - processed-reference artifacts are preserved under
    `build/verification/task-81-openvoice-v2-hemma/artifacts/processed_reference/`,
  - Swedish base audio is preserved at
    `build/verification/task-81-openvoice-v2-hemma/artifacts/base_sv.wav`,
  - converter-input audio is preserved at
    `build/verification/task-81-openvoice-v2-hemma/artifacts/base_sv_converter_input.wav`,
  - the final cloned artifact is preserved at
    `build/verification/task-81-openvoice-v2-hemma/artifacts/sample_sv.wav`.
- Current conclusion:
  - the benchmark plumbing is now validated end-to-end on Hemma,
  - the failed-quality baseline is preserved for before/after comparison,
  - `T84` is complete,
  - listening review of the corrected rerun says:
    - the Swedish base voice remains very unnatural with pitch, tone, and phrasing issues,
    - the cloned result is somewhat better than the base voice,
    - the cloned result is still sub-par for the teacher-voice goal,
  - recommendation: OpenVoice V2 is technically feasible on Hemma but should not remain the
    primary Swedish teacher-voice candidate for the next implementation slice.

## Result Record

- Result type: technical success with negative product recommendation.
- What worked:
  - sidecar/runtime/cache plumbing,
  - Swedish base generation,
  - cloning flow with the approved teacher reference clip,
  - deterministic evidence preservation on Hemma.
- What still failed:
  - Swedish base voice quality,
  - cloned output quality,
  - teacher-voice credibility for the intended product path.
- Decision:
  - close `T81` as completed evidence,
  - do not promote OpenVoice V2 as the primary Swedish teacher-voice backend,
  - proceed to `T82`.

## Failed-Baseline Setup Concerns (2026-03-06)

- The current adapter writes Swedish MMS base audio using the OpenVoice converter sample rate
  rather than the Swedish base model's native sample rate. This is a likely pacing/timbre defect
  in the current benchmark output and must be corrected before another quality judgment.
- The current adapter extracts the target speaker embedding directly from the full approved
  reference clip instead of using OpenVoice's intended reference-speaker preprocessing flow.
  That means the benchmark is skipping the model's speech-segmentation/reference-cleanup path.
- The failed baseline did not preserve the processed reference artifact plus the pre-conversion
  Swedish base artifact, which is why it could not isolate setup quality defects fairly.
- The failed baseline also proved the old Torch Hub / Silero path was wrong, which is why the
  corrected rerun had to remove `whisper-timestamped` rather than wire in a legacy cache path.

## Remediation Track

- [x] Correct the sample-rate contract between the Swedish base model and the OpenVoice converter:
  - write base audio at the base model's native sample rate,
  - resample explicitly only when the converter requires a different rate,
  - record both rates in the benchmark report.
- [x] Replace the current simplified reference-speaker setup with the intended OpenVoice
  reference-speaker preprocessing path and preserve the processed reference artifact used for
  embedding extraction.
- [x] Produce paired rerun artifacts so we can compare:
  - processed reference audio,
  - Swedish base output before cloning,
  - Swedish cloned output after tone-color conversion.
- [x] Remove the broken `faster-whisper` / PyAV dependency chain from the OpenVoice sidecar image
  so Hemma can rebuild the benchmark image on Python 3.12.
- [x] Rerun Task 81 on Hemma with the corrected setup and preserve the failed sample as baseline
  evidence rather than overwriting the learning.
- [x] Record whether the corrected setup removes the reported artifacts, improves pacing, and
  materially improves timbre match to the approved teacher voice.
- [x] Make the next corrected rerun atomic:
  - one repo head,
  - one timestamp family,
  - one machine-readable benchmark/evidence status,
  - one deterministic setup-artifact trail.
- [x] Re-prove the earlier export failure on current `HEAD` before changing the export path again.
- [x] Record that the earlier export failure does not reproduce on current `HEAD`.
- [x] Fix the current synthesize-stage Torch Hub / Silero VAD path mismatch so the declared
  `TORCH_HOME` cache path is actually the path used by the runtime assertion logic.
- [x] Remove `whisper-timestamped` from the active reference-preprocessing path and replace it
  with a direct local Silero VAD flow rooted only in the canonical Torch cache.
- [x] Recover setup-artifact collection so the corrected rerun preserves:
  - processed reference artifacts,
  - Swedish base artifacts before cloning,
  - converter-input artifacts for the tone-color conversion step.
- [x] If the corrected rerun is still poor, record OpenVoice as technically feasible but not the
  primary Swedish teacher-voice candidate, then proceed to `T82`.

## Immediate Execution Order

1. Preserve OpenVoice as a technically successful but non-primary benchmark lane.
1. Proceed to `T82` for the next cloning-capable comparison backend.
1. Keep `T83` as the direct Swedish pronunciation control lane.

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
- [x] The task records whether OpenVoice V2 is sufficiently credible to be the default Swedish-
  probable cloning backend for follow-on implementation work.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
- [x] Recommendation recorded
