---
id: 'task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar'
title: 'Provision pyannote diarization access and replacement decision for STT sidecar'
type: 'task'
status: 'in_progress'
priority: 'high'
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md
  - docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - stt
  - audio
  - diarization
  - pyannote
  - hugging-face
  - hemma
  - gpu
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Resolve the remaining Task 352 live-proof blocker for diarization while keeping
FasterWhisper as the preferred and already proven STT backend on the Hemma ROCm
sidecar lane. The first option is to provision or verify the required Hugging
Face gated-model access for the Hemma `HF_TOKEN` account so the selected
`pyannote.audio` pipeline can execute exact speaker-count and min/max
speaker-range hints. A replacement diarization backend is only in scope if
pyannote access cannot be obtained, and any replacement must be governed,
library-backed, GPU-required, and compatible with the audio transcript bundle
contract.

This task does not register `audio -> transcript_bundle`, publish Gateway or
OpenAPI fields, persist transcript artifacts, generate formatter outputs, or
change the accepted FasterWhisper/CTranslate2 ROCm image path.

## Current Evidence

Review 37 accepts the bounded post-deploy evidence that the prior
FasterWhisper/CTranslate2 ROCm and codec-boundary blockers are resolved. The
remaining live-observation failure reason is `pyannote_audio_runtime_blocked`,
with retained backend failure `diarization=gated_model_access_denied`.

On 2026-06-10, the live observation was rerun from the current `main` state
against the ignored English two-speaker and Swedish one-speaker fixtures:

```bash
pdm run run-hemma -- pdm run benchmark:stt-sidecar-live-observation \
  --runtime-mode docker \
  --sidecar-launch-observed \
  --english-fixture build/verification/stt-sidecar-live-fixtures/source-media/english-dialogue-two-speakers.mp3 \
  --swedish-fixture build/verification/stt-sidecar-live-fixtures/source-media/swedish-monologue-one-speaker.m4a \
  --output-root build/verification/stt-sidecar-live-observation-hemma-pyannote-access-recheck-33c0593
```

The command returned exit code `2` and wrote the ignored artifact:

- `build/verification/stt-sidecar-live-observation-hemma-pyannote-access-recheck-33c0593/live-observation.json`.

The sanitized evidence remained unchanged in the important ways:

- `HF_TOKEN` is present by environment variable name only;
- Hugging Face cache roots are ready and scratch-backed;
- codec boundary evidence remains true for FFmpeg/FFprobe and fail-closed bad
  media;
- FasterWhisper still executes on ROCm with no CPU fallback, expected `en`/`sv`
  language evidence, and word timestamps;
- content safety flags remain false for transcript text, secret values, private
  cache paths, raw model identifiers, and generated committed artifacts;
- pyannote still fails with `GatedRepoError` classified as
  `gated_model_access_denied`;
- exact speaker-count and min/max speaker-range hints remain supported by
  contract but unexercised in live proof because diarization cannot load.

The same observation was ingested through profile proof:

```bash
pdm run run-hemma -- pdm run benchmark:stt-sidecar-profile-proof \
  --mode live \
  --live-observation-json build/verification/stt-sidecar-live-observation-hemma-pyannote-access-recheck-33c0593/live-observation.json \
  --output-root build/verification/stt-sidecar-profile-proof-live-pyannote-access-recheck-33c0593
```

The profile-proof command returned exit code `2` and wrote:

- `build/verification/stt-sidecar-profile-proof-live-pyannote-access-recheck-33c0593/profile-proof.json`;
- `build/verification/stt-sidecar-profile-proof-live-pyannote-access-recheck-33c0593/profile-proof.md`.

Required evidence remains true for live Hemma mode, sidecar launch, backend
dependencies, codec boundary, GPU-required execution, batch lifecycle, content
safety, and route-unregistered state. It remains false for Hugging Face model
access, English and Swedish diarized fixture completion, exact speaker-count
hints, and min/max speaker-range hints.

## Upstream Docs Checked

- Context7 `/pyannote/pyannote-audio`: current examples load pretrained
  diarization pipelines with `Pipeline.from_pretrained(..., token=...)`, move
  the pipeline to GPU with `pipeline.to(torch.device("cuda"))`, support exact
  `num_speakers` and `min_speakers`/`max_speakers`, and expose exclusive
  diarization output suitable for transcript alignment.

## PR Scope

- Verify pyannote gated-model access from the Hemma sidecar lane using the
  existing `HF_TOKEN` environment variable name and the committed
  `benchmark:stt-sidecar-live-observation` surface.
- If access is available, rerun live observation and profile-proof ingestion
  against the two ignored fixtures, then record the sanitized ignored artifact
  paths in Task 352/353 and request retained review for complete Task 352
  acceptance.
- If access remains denied, record the operator action required to accept or
  request access for the selected pyannote model family without exposing token
  values, private cache paths, transcript text, fixture source paths, or model
  artifacts.
- If pyannote access cannot be provisioned for this product lane, create or
  update a governed decision/reference that selects a replacement real
  diarization backend before implementation. The replacement must be a
  maintained library-backed profile, not a handrolled clustering or toy
  diarization implementation.
- Preserve the accepted FasterWhisper/CTranslate2 ROCm sidecar path. No
  non-Whisper STT backend, CPU fallback, main-service STT dependency promotion,
  route registration, Gateway publication, transcript persistence, or formatter
  output belongs in this task.

## Deliverables

- [ ] Pyannote access verification evidence from Hemma using ignored live
      observation/profile-proof artifacts.
- [ ] Either accepted pyannote diarization proof with exact and min/max speaker
      hints, or a bounded access-denied record that names the next operator
      action.
- [ ] If access cannot be provisioned, a governed replacement decision or
      reference that preserves library-backed diarization, GPU-required
      execution, exact speaker-count hints, min/max speaker-range hints, and
      alignment-suitable exclusive segments.
- [ ] Task 352/353 and `.codex/handoff.md` updated with the resulting next
      state.
- [ ] Retained ruthless review artifact accepting either the complete
      diarization proof or the bounded access/replacement decision.

## Acceptance Criteria

- [ ] FasterWhisper remains the preferred and accepted STT backend unless a
      separate governed STT task changes that decision; this task only resolves
      diarization.
- [ ] Pyannote remains the first diarization option. Replacement work can begin
      only after the access-denied state is recorded as not provisionable for
      the current lane.
- [ ] Live proof succeeds only when diarization runs through the selected
      backend on the GPU-required sidecar lane, exercises exact speaker-count
      and min/max speaker-range hints, provides exclusive speaker segments, and
      produces alignment-suitable evidence for the English and Swedish
      fixtures.
- [ ] `HF_TOKEN` is the governed token environment variable. Reports and docs
      may record the key name and bounded readiness status, but never token
      values, private cache paths, raw transcripts, generated media, or model
      artifacts.
- [ ] Any replacement candidate is governed before implementation and rejected
      if it lacks maintained-library ownership, GPU execution, exact speaker
      hints, min/max speaker hints, or alignment-suitable segment output.
- [ ] Story 53 remains blocked until Task 352 receives a final retained review
      decision accepting complete live proof including diarization.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
