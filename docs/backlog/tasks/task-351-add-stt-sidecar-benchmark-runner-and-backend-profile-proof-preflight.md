---
id: task-351-add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight
title: Add STT sidecar benchmark runner and backend profile proof preflight
type: task
status: completed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/reviews/review-27-ruthless-review-of-story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
labels:
  - stt
  - audio
  - benchmark
  - hemma
  - sidecar
  - preflight
---

PR-sized execution unit linked to Epic 12's STT runtime-enablement lane.

## Objective

Add the first committed STT sidecar benchmark runner surface that can be run on
Hemma before any `audio -> transcript_bundle` runtime registration. The runner
must record content-safe preflight evidence for the codec toolchain, Python
backend dependencies, Hugging Face cache/token readiness, and the remaining
profile-proof gaps needed to supersede the Story 52 governed
production-profile rejection.

This task does not select a production STT profile. Story 53 remains blocked
until a later live Hemma benchmark run proves Swedish and English fixtures,
diarization speaker hints, and 120-minute batch lifecycle behavior with the
chosen sidecar image/backend profile.

## PR Scope

- Add `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_benchmark.py`
  as the dependency-light preflight/reporting module.
- Add
  `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_benchmark_preflight.py`
  as the CLI entrypoint for the preflight.
- Add a stable PDM command:
  `pdm run benchmark:stt-sidecar-preflight`.
- Add focused tests proving report redaction, deterministic rejection when
  dependencies are missing, and the remaining profile-proof stop condition.
- Keep the runner out of route registration, OpenAPI publication, transcript
  persistence, formatter generation, and production service image dependency
  changes.

## Deliverables

- [x] Content-safe JSON and Markdown preflight report under `build/verification/`.
- [x] Preflight probes for `ffmpeg`, `ffprobe`, `faster_whisper`,
  `pyannote.audio`, `huggingface_hub`, `torch`, Hugging Face cache roots, and
  required secret environment-variable names.
- [x] No secret values, transcript text, private cache paths, raw model
  identifiers, or generated benchmark artifacts written to governed docs.
- [x] Explicit profile-selection rejection until Swedish/English fixtures,
  speaker hint modes, and 120-minute batch lifecycle evidence are produced by a
  later live Hemma benchmark.

## Acceptance Criteria

- [x] `pdm run benchmark:stt-sidecar-preflight` writes sanitized `report.json`
  and `report.md` without importing STT/diarization/model packages.
- [x] Missing `ffmpeg`, `ffprobe`, `faster_whisper`, `pyannote.audio`,
  Hugging Face token, or cache roots is represented as a deterministic
  blocking reason rather than a false selected profile.
- [x] A fully ready preflight still refuses profile selection and names the
  next required live evidence: Swedish fixture, English fixture, exact speaker
  count, min/max speaker range, and 120-minute batch lifecycle.
- [x] Reports do not contain Hugging Face token values or private cache paths.
- [x] Story 53 remains blocked; this task does not register
  `audio -> transcript_bundle`.

## Upstream Docs Checked

- Context7 `/systran/faster-whisper`: current `WhisperModel` loading uses
  model size, `device`, and `compute_type`; transcription is lazy until segment
  iteration, can expose language/duration metadata, and supports batched
  inference through `BatchedInferencePipeline`.
- Context7 `/pyannote/pyannote-audio`: current diarization pipeline loading
  uses `Pipeline.from_pretrained(..., token=...)`, supports GPU placement with
  `pipeline.to(torch.device("cuda"))`, exact `num_speakers`, and
  `min_speakers`/`max_speakers`.
- Context7 `/huggingface/huggingface_hub`: cache roots are governed by
  `HF_HOME`/`HF_HUB_CACHE`; token behavior must be explicit and secret values
  must not be persisted.
- FFmpeg official `ffprobe` documentation: `ffprobe` returns a positive exit
  code for unopenable or unrecognized media and emits machine-readable stream
  information, so the live benchmark must keep probing fail-closed.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
