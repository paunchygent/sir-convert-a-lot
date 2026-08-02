---
id: story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection
title: Hemma STT and diarization backend benchmark profile selection
type: story
status: completed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/backlog/tasks/task-351-add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight.md
labels:
  - stt
  - diarization
  - benchmark
  - hemma
  - gpu
  - audio
---

Implementation slice with acceptance-driven scope.

## Objective

Select and prove the first Hemma STT/diarization backend profile that can
support ADR-0013's Swedish/English, diarized, 120-minute batch-processing route
without moving model/runtime dependencies into the main Sir Convert image.

## Scope

- Benchmark candidate transcription and diarization stacks through the
  Sir-owned sidecar capability contract rather than backend-native calls only.
- Validate model/cache/secret governance:
  - configured cache roots;
  - cold/warm cache behavior;
  - missing-token or missing-model readiness failure;
  - bounded public profile labels;
  - no raw model id/token/path leakage.
- Prove day-one product behavior:
  - Swedish and English language detection/transcription;
  - exact speaker count hints;
  - min/max speaker hints;
  - exclusive or otherwise alignment-suitable diarization output;
  - fail-closed diarization and alignment failure.
- Produce 120-minute proof through a governed Hemma fixture or synthetic
  duration test that exercises the real job lifecycle assumptions.
- Record benchmark evidence without transcript text, student PII, secrets, or
  generated model artifacts in repo docs.

## Implementation Evidence

The first implementation slice adds a local, typed benchmark evidence and
profile-selection contract without importing STT, diarization, Hugging Face,
FFmpeg, or sidecar runtime dependencies into the main service.

Implemented boundary:

- `scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_types.py`
  defines immutable evidence objects for bounded profile labels, GPU/cache/token
  readiness, Swedish/English language fixture evidence, diarization speaker
  hints, 120-minute feasibility shape, and content-safety assertions.
- `scripts/sir_convert_a_lot/domain/audio_transcription_benchmark_profiles.py`
  selects `stt_sv_en_primary` and `diarization_sv_en_primary` only when the
  evidence bundle is complete, otherwise rejects with deterministic reasons.
- `build_content_safe_audio_benchmark_report(...)` projects bounded metadata
  and excludes transcript text samples, raw model identifiers, secret values,
  private cache paths, and generated artifact paths.

Bounded upstream research used for this slice:

- `faster-whisper` current Context7 documentation, sourced from the official
  repository README, supports explicit `device` and `compute_type` wiring,
  language detection, transcription metadata, and word timestamps; the
  profile-selection contract treats CPU execution as a rejection rather than a
  fallback.
- `pyannote.audio` current Context7 documentation, sourced from the official
  repository/tutorial material, supports diarization pipelines, explicit GPU
  placement, exact speaker-count hints, min/max speaker-range hints, gated
  Hugging Face access, and exclusive diarization output suitable for later
  transcript alignment.
- `huggingface_hub` current Context7 documentation, sourced from the official
  cache and environment-variable docs, supports cache-root configuration,
  offline/cache-only readiness checks, and token-governed model access. Token
  values are never recorded in public evidence.
- Official FFmpeg/ffprobe documentation records that `ffprobe` inspects
  multimedia streams, can emit JSON, supports audio stream selection, and exits
  non-zero for unopenable/unrecognized media. Story 52 therefore requires a
  governed FFmpeg/ffprobe boundary before any STT profile can be selected.

Red/green evidence:

- Red: `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_profile_selection.py`
  failed during collection with `ModuleNotFoundError` for the missing benchmark
  profile module.
- Green: the same focused command passes with `7 passed`.
- Focused static checks pass for the new profile/type modules and test.

Live Hemma evidence from 2026-06-09:

- Evidence path: this governed story document. No transcript text, token values,
  raw backend model identifiers, private cache paths, generated audio, or model
  artifacts were written to repo artifacts.
- `pdm run run-hemma -- pwd` proved the sanctioned remote checkout:
  `/home/paunchygent/apps/sir-convert-a-lot`.
- `pdm run run-hemma -- git rev-parse HEAD` recorded runtime revision
  `fe195ba440c727ad081dee58a9a5d3525f7fe022`.
- `pdm run run-hemma -- rocm-smi --showproductname --showdriverversion --showmeminfo vram`
  proved the host GPU is visible as AMD Radeon AI PRO R9700 / `gfx1201`, ROCm
  driver `6.16.13`, with 32 GB class VRAM.
- `pdm run run-hemma -- ffprobe -version` and
  `pdm run run-hemma -- ffmpeg -version` both failed with command-not-found.
- `pdm run run-hemma -- pdm run python -m pip show faster-whisper pyannote.audio huggingface-hub torch`
  proved `faster-whisper` and `pyannote.audio` are not installed in the remote
  repo virtualenv; `huggingface-hub 0.34.4` and `torch 2.10.0+rocm7.1` are
  present.
- `pdm run run-hemma --shell '...HF token presence probe...'` reported
  `hf_token_missing`; the probe printed only presence/absence and no secret
  values.
- `pdm run run-hemma --shell '...canonical HF cache root readiness probe...'`
  reported the canonical Hugging Face cache root exists and is writable.
- `pdm run run-hemma -- sudo docker ps --format ...` found the existing Sir
  runtime containers, shared infrastructure, Skriptoteket, and unrelated OCR/VLM
  images, but no STT sidecar container.
- `pdm run run-hemma -- sudo docker images --format ...` found no STT sidecar
  image.
- `pdm run run-hemma -- sudo docker exec sir_convert_a_lot_gpu_worker ...` and
  the same probe against `sir_convert_a_lot_prod` proved both Sir runtime
  containers are missing `ffmpeg`, `ffprobe`, `faster-whisper`, and
  `pyannote.audio`; their GPU-aware Torch/Hugging Face libraries are present.
- `pdm run run-hemma -- rg --files build/verification | rg 'audio|stt|transcri|diari|whisper|pyannote|story-52|task-52'`
  found no existing governed STT/diarization benchmark artifact.
- `pdm run run-hemma -- rg --files | rg '\.(wav|mp3|m4a|flac|ogg|opus|aac)$'`
  found no governed audio fixture in the remote checkout.

Current profile decision:

- Local fixture evidence can select bounded labels `stt_sv_en_primary` and
  `diarization_sv_en_primary` only as a typed contract proof.
- Production `stt_profile` and `diarization_profile` are explicitly
  **rejected** for the first runtime slice because the sanctioned Hemma runtime
  does not yet provide the codec boundary, backend libraries, gated model-access
  readiness, Swedish/English fixture evidence, speaker-hint evidence, or
  120-minute benchmark harness required by ADR-0013.
- Story 53 runtime route registration remains blocked. The next implementation
  slice must first create a governed STT sidecar benchmark image/runner with
  FFmpeg/ffprobe, backend dependencies, token/cache readiness checks,
  content-safe Swedish/English fixture handling, speaker-hint probes, and a
  detached/status-capable 120-minute synthetic-duration benchmark.

Rejection matrix:

| Criterion | Live outcome | Decision |
|---|---|---|
| GPU execution | Host GPU is visible, but no STT/diarization backend or sidecar exists to execute on it. | Rejected until a benchmark runner proves backend GPU execution. |
| Cache reuse/readiness | Canonical Hugging Face cache root exists and is writable, but no selected model files or cold/warm backend run exists. | Rejected until the runner proves cold/warm cache behavior without leaking paths. |
| Missing model access/token failure | HF token is absent from the probed host/container surfaces. | Rejected until readiness fails deterministically with sanitized `audio_model_access_denied` evidence. |
| No silent CPU fallback | No backend execution occurred because required backend packages are absent. | Rejected until the runner proves GPU-required execution and fails closed on CPU fallback. |
| Swedish/English diarized fixtures | No governed audio fixtures or STT/diarization artifacts exist in the Hemma checkout. | Rejected until content-safe fixture evidence is produced without transcript text in docs. |
| Speaker hints | `pyannote.audio` supports the required hint modes in current docs, but it is absent from the runtime. | Rejected until exact and min/max hints are tested through the selected backend. |
| 120-minute feasibility | No committed detached/status-capable benchmark harness exists for STT. | Rejected until synthetic or fixture-duration proof exercises the real lifecycle assumptions. |
| Content safety | Local report projection tests prove redaction; live evidence was recorded as bounded command outcomes only. | Accepted for this rejection slice. |

## Acceptance Criteria

- [x] A bounded `stt_profile` and `diarization_profile` are selected for the
  first runtime slice or explicitly rejected with reasons.
- [x] Hemma evidence proves GPU execution, cache reuse, readiness failure on
  missing model access, and no silent CPU fallback, or records concrete
  rejection blockers for each requirement.
- [x] Representative Swedish and English recordings transcribe with diarized
  segment output suitable for JSON artifact assembly, or are blocked by concrete
  fixture/runtime evidence.
- [x] Exact speaker count and min/max speaker range hints are tested against
  the selected diarization backend, or blocked by concrete backend-runtime
  evidence.
- [x] 120-minute processing feasibility is proven before route registration, or
  route registration is blocked by concrete benchmark-harness evidence.
- [x] Benchmark reports use bounded metadata and redact content/secrets.

## Test Requirements

- [x] Sidecar capability smoke test on Hemma, or deterministic evidence that no
  governed sidecar exists yet.
- [x] Missing-secret/cache readiness failure test, or deterministic evidence
  that token access is absent and cache root readiness alone is insufficient.
- [x] Swedish/English transcription fixture checks with language evidence, or
  deterministic evidence that fixtures/backend execution are absent.
- [x] Diarization hint and alignment validation checks, or deterministic
  evidence that the selected backend is absent.
- [x] 120-minute fixture or synthetic-duration proof through the governed
  benchmark harness, or deterministic evidence that no such harness exists yet.
- [x] Docs validation: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Done Definition

The story is done when a selected backend profile is proven or rejected with
operator-grade Hemma evidence and the route execution story has clear runtime
profile inputs.

## Follow-Up Runtime Task

Task 351 adds the first STT sidecar benchmark preflight runner after this
story's governed production-profile rejection. The preflight runner records
codec, runtime-package, Hugging Face cache, and token-name readiness, while the
production `stt_profile` and `diarization_profile` remain rejected until live
Swedish/English fixture, speaker-hint, and 120-minute lifecycle evidence exists.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
