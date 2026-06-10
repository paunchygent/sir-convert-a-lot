---
id: task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof
title: Build live Hemma STT sidecar benchmark profile proof
type: task
status: in_progress
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-351-add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight.md
  - docs/backlog/reviews/review-27-ruthless-review-of-story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - stt
  - audio
  - diarization
  - benchmark
  - hemma
  - sidecar
  - gpu
---

PR-sized execution unit linked to Epic 12's speech-to-text runtime-enablement
lane.

## Objective

Build the first governed live Hemma STT sidecar benchmark/profile-proof
surface that can supersede Story 52's production-profile rejection. The proof
must demonstrate the codec boundary, selected transcription and diarization
runtime, model/cache/token readiness, Swedish and English fixture handling,
speaker-hint behavior, GPU-required execution, and 120-minute batch lifecycle
shape before Story 53 can register `audio -> transcript_bundle`.

This task still does not register the route, publish OpenAPI runtime fields,
persist transcript artifacts, or implement formatter outputs. Story 53 remains
blocked until this task and its retained review accept the live benchmark
evidence.

## PR Scope

- Extend the STT benchmark proof contract beyond Task 351 preflight-only
  readiness.
- Add a committed benchmark runner surface that can run locally in deterministic
  dry-run/projection mode and on Hemma in live-proof mode.
- Add a sidecar image/build contract or launch contract for a benchmark-only
  STT runtime containing FFmpeg/ffprobe, `faster-whisper`, `pyannote.audio`,
  `huggingface_hub`, and GPU-aware Torch support without adding those runtime
  dependencies to the main Sir Convert service image.
- Record sanitized benchmark evidence for:
  - FFmpeg/ffprobe media probing and fail-closed bad-media behavior;
  - selected bounded STT and diarization profile labels;
  - GPU-required backend execution and no silent CPU fallback;
  - Hugging Face cache roots and token-name readiness without secret/path
    leakage;
  - Swedish and English language fixture execution without transcript text in
    retained docs;
  - exact speaker-count and min/max speaker-range diarization hints;
  - 120-minute batch lifecycle, using a governed fixture or synthetic-duration
    proof that exercises detached/status-capable long-job assumptions.
- Keep generated benchmark artifacts under `build/verification/` or a
  governed Hemma artifact root; do not commit media, transcripts, model files,
  tokens, private cache paths, or raw backend model identifiers.

## Deliverables

- [x] Purpose-named benchmark proof module(s) and CLI/PDM command surface.
- [x] Focused red/green tests for profile-proof acceptance and rejection.
- [x] Content-safe JSON and Markdown evidence schema for live proof results.
- [x] Hemma live-proof instructions and command evidence recorded here after
  execution.
- [x] Retained ruthless review artifact that either accepts the live proof or
  records concrete changes requested.

## Acceptance Criteria

- [ ] The benchmark proof refuses profile selection unless all required live
  evidence exists: codec boundary, STT backend, diarization backend, GPU
  execution, cache/token readiness, Swedish fixture, English fixture, exact
  speaker count, min/max speaker range, and 120-minute lifecycle.
- [ ] FFmpeg/ffprobe probing emits bounded metadata and fails closed for
  corrupt/no-audio/unsupported media without leaking source content.
- [ ] `faster-whisper` execution is represented through bounded profile labels,
  GPU-required device policy, language evidence, duration evidence, segment
  count, and word-timestamp availability; transcript text is not retained
  in governed docs.
- [ ] `pyannote.audio` execution is represented through bounded profile labels,
  GPU-required device policy, exact and min/max speaker-hint evidence,
  exclusive diarization availability, and alignment-suitable segment shape.
- [ ] Hugging Face readiness records only token env-var names, cache-root
  readiness classes, and bounded model-access status; no token values,
  private cache paths, or raw model identifiers are persisted.
- [ ] The 120-minute proof is detached/status-capable or otherwise exercises
  the long-job lifecycle assumptions required by ADR-0013.
- [ ] Successful proof updates Story 52/Epic 12 state enough to unblock a later
  Story 53 implementation task; failed proof records concrete blockers and
  keeps Story 53 blocked.
- [ ] No `audio -> transcript_bundle` runtime route registration, OpenAPI
  publication, transcript persistence, formatter generation, or main-image
  STT dependency change occurs in this task.

## Upstream Docs Checked

- Context7 `/systran/faster-whisper`: current `WhisperModel` examples use
  explicit model size, `device`, and `compute_type`; transcription is lazy until
  segment iteration; language probability, duration, word timestamps, and
  `BatchedInferencePipeline` are available surfaces for bounded evidence.
- Context7 `/pyannote/pyannote-audio`: current diarization examples load
  `Pipeline.from_pretrained(..., token=...)`, move the pipeline to GPU with
  `pipeline.to(torch.device("cuda"))`, support exact `num_speakers`,
  `min_speakers`/`max_speakers`, and expose exclusive diarization output.
- Context7 `/huggingface/huggingface_hub`: `HF_HOME`, `HF_HUB_CACHE`, and
  `HF_TOKEN` govern cache/token readiness; deprecated token/cache aliases do
  not take precedence over the standard variables.
- Official FFmpeg `ffprobe` documentation: `ffprobe` gathers multimedia stream
  information, can print machine-readable JSON, supports audio stream
  selection with `-select_streams a`, and returns a positive exit code for
  unopenable or unrecognized media.

## Local Fixture Smoke Proof

On 2026-06-10, the two user-provided recordings were copied into the ignored
generated fixture root
`build/verification/stt-sidecar-live-fixtures/source-media/` with
purpose-labeled filenames. The source locations are not retained in this task,
and no transcript text was generated or persisted.

- `english-dialogue-two-speakers.mp3`: `ffprobe` detected one audio stream,
  codec `mp3`, format `mp3`, 44.1 kHz sample rate, 2 channels, 675.250667
  seconds, and 16,311,853 bytes.
- `swedish-monologue-one-speaker.m4a`: `ffprobe` detected one audio stream,
  codec `aac`, format `mov,mp4,m4a,3gp,3g2,mj2`, 48 kHz sample rate, 1 channel,
  18.474667 seconds, and 161,184 bytes.
- `git check-ignore -v` confirmed both copied fixture files are ignored through
  the repo `build/` ignore rule.

This is codec/admission smoke proof only. It is not STT output, diarization
output, profile-selection proof, or 120-minute lifecycle proof.

## Runner Surface

Task 352 now has a purpose-named runner command:

```bash
pdm run benchmark:stt-sidecar-profile-proof
```

The command writes content-safe `profile-proof.json` and `profile-proof.md`
artifacts under `build/verification/stt-sidecar-profile-proof` by default.
Projection mode is deterministic and intentionally keeps profile selection
blocked with `live_hemma_evidence_missing`; it is suitable for local contract
checks only and does not supersede Story 52's profile rejection.

Live mode accepts a sanitized sidecar observation JSON envelope:

```bash
pdm run benchmark:stt-sidecar-profile-proof --mode live --live-observation-json <path>
```

The live observation must include bounded sidecar launch/build metadata,
codec-boundary observations, backend dependency observations, Hugging Face
token/cache readiness by environment variable name only, Swedish and English
fixture summaries, exact and min/max speaker-hint summaries, GPU-required
runtime evidence, content-safety flags, and 120-minute lifecycle status. Missing
or partial live observations fail closed and return exit code `2`.

The sidecar launch contract currently records only bounded values:

- image name `sir-convert-a-lot-stt-sidecar` and tag `benchmark`;
- compose service `stt-sidecar-benchmark`;
- BuildKit build contract;
- observed sidecar launch flag, required before profile selection;
- required tools `ffmpeg` and `ffprobe`;
- required packages `faster-whisper`, `pyannote.audio`, `huggingface_hub`, and
  `torch`;
- GPU-required execution;
- Hugging Face environment variable names `HF_TOKEN`, `HF_HOME`, and
  `HF_HUB_CACHE`.

No raw transcript text, token values, private cache paths, raw model
identifiers, fixture source paths, generated artifact paths, route registration,
OpenAPI publication, transcript persistence, or formatter output is produced by
this runner. Live Hemma execution remains open until a sanitized observation is
generated by the benchmark-only sidecar runtime and recorded here.

Task 352 now also has a purpose-named live-observation producer command:

```bash
pdm run benchmark:stt-sidecar-live-observation \
  --runtime-mode docker \
  --sidecar-launch-observed \
  --english-fixture build/verification/stt-sidecar-live-fixtures/source-media/english-dialogue-two-speakers.mp3 \
  --swedish-fixture build/verification/stt-sidecar-live-fixtures/source-media/swedish-monologue-one-speaker.m4a \
  --output-root build/verification/stt-sidecar-live-observation-hemma
```

The command builds or reuses the isolated `sir-convert-a-lot-stt-sidecar:benchmark`
image with BuildKit, probes the codec boundary through the sidecar image,
resolves the Docker-visible Hugging Face cache mount while preserving the
canonical scratch-backed cache root, runs the committed runtime probe module,
and writes sanitized `live-observation.json` without transcript text, fixture
paths, token values, private cache paths, or raw model identifiers.

## Hemma Live Observation Attempt

On 2026-06-10, the live-observation producer was run from the deployed Hemma
checkout against the two ignored purpose-labeled fixtures under
`build/verification/stt-sidecar-live-fixtures/source-media/`. No code was
synced to Hemma for the final attempts; fixes were committed to `main`, pushed,
and redeployed before rerunning the live proof.

Three implementation defects were found and corrected before the latest
retained live observation:

- the operator environment loaded from `.env` was not forwarded to subprocess
  commands;
- `sudo docker run -e HF_TOKEN` stripped the token before Docker received it,
  so the runtime probe now preserves the `HF_TOKEN` environment name across the
  sudo boundary without putting the secret value in argv;
- the benchmark image installed `huggingface_hub` 1.x, which is incompatible
  with `pyannote.audio`, so the sidecar now pins `huggingface-hub==0.34.4`;
- third-party backend guidance polluted the runtime probe stdout stream, so the
  probe now keeps only the final sanitized JSON on stdout.

The latest deployed revision for this attempt was
`5e63c9ce1bf2dbd7fc96d3525b9abb85294a4145`. Hemma deploy verification passed:

- expected, remote, and service revisions matched
  `5e63c9ce1bf2dbd7fc96d3525b9abb85294a4145`;
- service URL `http://127.0.0.1:28085`;
- structured LLM reachability and microprobe passed;
- metrics scan, public reserved host, TLS, nginx proxy registration, and
  default-host placeholder checks passed.

Focused validation before redeploying the fixes:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py -q
pdm run format-all
pdm run lint-fix
pdm run typecheck-all
git diff --check
```

Results:

- focused pytest: `7 passed`;
- format: `881 files left unchanged`;
- lint/docs validation: `All checks passed!`, `Validated docs=529 rules=11`,
  `Validated 454 backlog files`;
- typecheck: `Success: no issues found in 832 source files`;
- whitespace: clean.

The post-deploy live observation command returned exit code `2` and wrote:

- `build/verification/stt-sidecar-live-observation-hemma-post-stdout-fix/live-observation.json`.

The observation proves these live Hemma surfaces:

- sidecar launch/build contract: `sir-convert-a-lot-stt-sidecar:benchmark`,
  BuildKit, isolated runtime marker, required tools/packages, and GPU-required
  policy;
- codec boundary: `ffmpeg` and `ffprobe` available inside the sidecar image,
  valid MP3/M4A fixture probes exercised, and bad/no-audio/unsupported media
  fail closed;
- isolated backend dependencies: `faster-whisper`, `pyannote.audio`,
  `huggingface_hub`, and ROCm Torch importable inside the benchmark image;
- Hugging Face token/cache readiness: `HF_TOKEN` present by environment-variable
  name only, scratch-backed cache roots ready, no token value or private path
  retained;
- GPU execution policy: ROCm acceleration family with GPU execution confirmed
  and no CPU fallback observed by the runtime probe;
- 120-minute lifecycle shape: 12 chunks of 600 seconds with progress,
  checkpoint, detached-status, cancel, and retry semantics exercised;
- content safety: no transcript text, raw model ids, secret values, private
  paths, generated committed artifacts, fixture names, or original source paths
  in the retained observation.

The observation is intentionally blocked, not accepted. Remaining blocker
codes:

- `faster_whisper_runtime_blocked`;
- `pyannote_audio_runtime_blocked`.

Sanitized backend diagnostics from the same benchmark image identify the root
causes:

- `faster-whisper` model loading fails with `RuntimeError`: `CUDA failed with
  error CUDA driver version is insufficient for CUDA runtime version`. Current
  upstream `faster-whisper`/CTranslate2 documentation remains CUDA/NVIDIA
  oriented; this is not an accepted ROCm GPU proof.
- `pyannote.audio` pipeline loading fails with `GatedRepoError` after the
  Hub-version pin. The token is present and the container can authenticate, but
  the pretrained diarization pipeline still requires accepted Hugging Face
  gated-model access for the account/token before it can run.

The blocked observation was ingested through the approved profile-proof runner:

```bash
pdm run run-hemma -- pdm run benchmark:stt-sidecar-profile-proof \
  --mode live \
  --live-observation-json build/verification/stt-sidecar-live-observation-hemma-post-stdout-fix/live-observation.json \
  --output-root build/verification/stt-sidecar-profile-proof-live-post-stdout-fix
```

The profile-proof runner returned exit code `2` and wrote:

- `build/verification/stt-sidecar-profile-proof-live-post-stdout-fix/profile-proof.json`;
- `build/verification/stt-sidecar-profile-proof-live-post-stdout-fix/profile-proof.md`.

The profile proof has `proof_ready=false`. Its required evidence is true for
live Hemma mode, sidecar launch, codec boundary, backend dependencies,
GPU-required execution, 120-minute lifecycle, content safety, and route
unregistered. It remains false for Hugging Face readiness, Swedish fixture,
English fixture, exact speaker count, and min/max speaker range because neither
backend completed runtime execution.

Story 53 remains blocked. The next governed decision is either to provide
pyannote gated-model access and replace/re-govern the STT backend for Hemma
ROCm, or move the faster-whisper proof to a CUDA/NVIDIA lane that satisfies the
GPU-required no-CPU-fallback policy.

`git check-ignore -v` confirmed the generated live-observation and profile-proof
artifacts are ignored under the repo `build/` rule.

## Test Requirements

- [x] Red-first focused tests for accepted proof and each missing-evidence
  rejection.
- [x] Report-redaction tests proving no transcript text, secret values, private
  cache paths, raw model identifiers, or generated artifact paths are
  projected into retained docs.
- [x] CLI/reporting tests for deterministic output paths and non-registration
  of the Service API v2 audio route.
- [x] Hemma live proof or concrete live blocker evidence recorded in this task.
- [x] Docs validation: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Stop Conditions

- Stop before adding STT, diarization, FFmpeg, or model dependencies to the main
  service image.
- Stop before exposing the STT sidecar on a public port or Gateway route.
- Stop before committing fixture media, transcript text, model artifacts,
  generated audio, secret values, private paths, or raw backend model ids.
- Stop before treating dry-run/preflight evidence as production profile proof.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [x] Docs updated
