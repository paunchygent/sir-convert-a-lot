---
id: task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar
title: Provision pyannote diarization access and replacement decision for STT sidecar
type: task
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md
  - docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md
  - docs/backlog/reviews/review-40-ruthless-review-of-stt-sidecar-hiprtc-live-proof.md
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

After the operator accepted the pyannote gated-model terms for the configured
`HF_TOKEN` account, the access diagnostic and live observation were rerun. The
diagnostic returned ready, proving the token can now fetch the selected pyannote
model family. The deployed failure-stage live observation at
`17f7e265113b184209f01fae14f4700df147fe14` wrote:

- `build/verification/stt-sidecar-live-observation-hemma-failure-stage-17f7e26/live-observation.json`.

The command still returned exit code `2`, but the retained blocker changed to
`failure_code=backend_runtime_blocked`, `exception_class=NameError`, and
`failure_stage=exact_speaker_count`. A bounded sidecar probe showed the installed
TorchCodec `0.14.0` decoder failed under ROCm Torch `2.10.0+rocm7.1` because the
wheel expected CUDA `libnvrtc.so.13`; pyannote then hit `AudioDecoder` as an
undefined name during the first diarization call. This task now owns the
TorchCodec compatibility correction before complete Task 352 proof can pass.

The TorchCodec correction was committed, pushed, and deployed at
`36c8435fe372354f6b591d154338d843364c05ba`. The follow-up live observation
proved the decoder import (`torchcodec_audio_decoder_importable=true`) but still
returned `pyannote_audio_runtime_blocked` at `failure_stage=exact_speaker_count`.
A one-off Hemma diagnostic inside the same benchmark image and GPU lane captured
MIOpen HIPRTC compilation failing in pyannote's LSTM path:
`rocrand/rocrand_xorwow.h` was missing. Installing Debian `librocrand-dev`
moved the failure to missing `math.h`; installing both `librocrand-dev` and
`libc6-dev` allowed exact two-speaker pyannote diarization to complete on the
English fixture and emit 151 exclusive speaker segments. The committed
correction must therefore install those packages and project
`miopen_hiprtc_headers_available=true` in the live observation/profile-proof
chain.

The ROCm JIT header correction was committed at
`fe566bd4a489f46df55d8168ac8a3a13d3dcea30`, pushed to `main`, deployed, and
verified with matching expected, remote, and service revisions. The subsequent
full live proof passed and wrote ignored artifacts:

- `build/verification/stt-sidecar-live-observation-hemma-hiprtc-fe566bd/live-observation.json`;
- `build/verification/stt-sidecar-profile-proof-live-hiprtc-fe566bd/profile-proof.json`;
- `build/verification/stt-sidecar-profile-proof-live-hiprtc-fe566bd/profile-proof.md`.

The proof reports `proof_ready=true`, `observation_failure_reasons=[]`,
`rejection_reasons=[]`, `torchcodec_audio_decoder_importable=true`,
`miopen_hiprtc_headers_available=true`, FasterWhisper ROCm execution with
`cpu_fallback_observed=false`, pyannote diarization on the GPU-required sidecar
lane, exact speaker-count exercised, min/max speaker range exercised, 151
English diarized speaker segments, and 3 Swedish diarized speaker segments.
Human-reviewable ignored transcript artifacts were generated at:

- `build/verification/stt-sidecar-transcript-review-hiprtc-fe566bd/transcript-review.json`;
- `build/verification/stt-sidecar-transcript-review-hiprtc-fe566bd/transcript-review.md`.

Human review accepted these transcript-review artifacts on 2026-06-10. The
acceptance confirms the pyannote diarization output is usable for the live proof
fixtures while keeping transcript text and generated artifacts outside git.

## Upstream Docs Checked

- Context7 `/pyannote/pyannote-audio`: current examples load pretrained
  diarization pipelines with `Pipeline.from_pretrained(..., token=...)`, move
  the pipeline to GPU with `pipeline.to(torch.device("cuda"))`, support exact
  `num_speakers` and `min_speakers`/`max_speakers`, and expose exclusive
  diarization output suitable for transcript alignment.
- Official TorchCodec documentation: TorchCodec is the media-decoding runtime
  used by pyannote for local audio; the published compatibility table maps
  TorchCodec `0.10` to Torch `2.10`, while TorchCodec `0.14` requires Torch
  `>=2.11`.
- Official Torchaudio `torchaudio.load` documentation: as of Torchaudio `2.9`,
  `torchaudio.load` relies on TorchCodec's `AudioDecoder`, so it is not a safe
  workaround for this ROCm decoder failure.
- Official ROCm rocRAND documentation: the Debian `-dev` package variant
  provides rocRAND library files and headers, and the documented package family
  owns the `rocrand/rocrand_xorwow.h` header required by MIOpen HIPRTC kernel
  compilation.
- ROCm MIOpen issue #3314: MIOpen kernels include
  `rocrand/rocrand_xorwow.h`; missing include paths or missing headers surface
  as HIPRTC compilation failures before the model can finish GPU inference.
- Context7 `/huggingface/huggingface_hub`: `HF_TOKEN` is the standard
  environment variable for authenticated Hub access, `whoami(token=...)`
  identifies the authenticated account, and `hf_hub_download(...)` resolves a
  specific repository file through the cache without requiring token values to
  appear in command output.

## Diagnostic Runner Surface

Task 354 adds a purpose-named access diagnostic command:

```bash
pdm run diagnose:stt-sidecar-diarization-access
```

The command writes `diarization-access.json` under
`build/verification/stt-sidecar-diarization-access` by default and returns exit
code `0` only when the configured `HF_TOKEN` can fetch the selected pyannote
pipeline configuration artifact. Blocked reports return exit code `2` and
record one bounded operator action:

- `configure_hf_token_for_stt_sidecar_operator` when `HF_TOKEN` is missing or
  unauthorized;
- `accept_or_request_pyannote_gated_model_access_for_hf_token_account` when the
  Hub returns gated-model denial;
- `verify_pyannote_hugging_face_access_for_hf_token_account` for other bounded
  Hub access errors.

The report records only bounded labels: backend family, profile label, model
family, artifact label, token environment variable name, token presence,
authenticated-account observation, failure code, exception class, and operator
action. It does not retain token values, private cache paths, raw model
identifiers, transcript text, generated media, or model artifacts.

Local red/green implementation evidence:

- red:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`
  failed during collection because the purpose-named diagnostic module did not
  exist;
- green:
  `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`
  passed `8 passed`;
- local fail-closed smoke:
  `env -u HF_TOKEN pdm run diagnose:stt-sidecar-diarization-access --env-file /tmp/sir-convert-a-lot-no-env --output-root build/verification/stt-sidecar-diarization-access-local-missing-token`
  returned exit code `2` and wrote an ignored report with
  `failure_code=hf_token_missing`, `token_env_vars_present=false`, and
  `operator_action=configure_hf_token_for_stt_sidecar_operator`.

## Hemma Access Diagnostic Attempt

The diagnostic runner was committed, pushed, and deployed at
`f7a1eb61f4edbcd9530208d561baf9f59d89cf3d`. Hemma deploy verification passed
with expected, remote, and service revisions all matching that revision.

The remote diagnostic command was then run from the canonical Hemma checkout:

```bash
pdm run run-hemma -- pdm run diagnose:stt-sidecar-diarization-access \
  --output-root build/verification/stt-sidecar-diarization-access-hemma-f7a1eb6
```

The command returned exit code `2` and wrote the ignored artifact:

- `build/verification/stt-sidecar-diarization-access-hemma-f7a1eb6/diarization-access.json`.

The bounded report records:

- `status=blocked`;
- `backend_family=pyannote_audio`;
- `profile_label=diarization_sv_en_primary`;
- `model_family=pyannote_community_diarization`;
- `artifact_label=pipeline_config`;
- `token_env_var_names=[HF_TOKEN]`;
- `token_env_vars_present=true`;
- `authenticated_account_observed=true`;
- `failure_code=gated_model_access_denied`;
- `exception_class=GatedRepoError`;
- `operator_action=accept_or_request_pyannote_gated_model_access_for_hf_token_account`;
- `secret_values_exposed=false`;
- `private_cache_paths_exposed=false`;
- `raw_model_identifiers_exposed=false`.

This evidence confirms the current blocker is not missing token plumbing or a
missing cache root. The Hemma `HF_TOKEN` account must accept or request access
for the selected pyannote gated model family before the full Task 352 live proof
can complete with the current first-choice diarization backend.

## PR Scope

- Verify pyannote gated-model access from the Hemma sidecar lane using the
  existing `HF_TOKEN` environment variable name and the committed
  `benchmark:stt-sidecar-live-observation` surface.
- Pin the benchmark sidecar's pyannote/TorchCodec dependency pair to the
  currently selected pyannote Community-1 runtime and the TorchCodec version
  compatible with the accepted ROCm Torch `2.10` base, then prove
  `torchcodec.decoders.AudioDecoder` importability in sanitized dependency
  evidence.
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

- [x] Pyannote access verification evidence from Hemma using ignored live
  observation/profile-proof artifacts.
- [x] A purpose-named bounded diagnostic command that records the pyannote
  access state without leaking token values, private cache paths, raw model
  identifiers, transcripts, generated media, or model artifacts.
- [x] A bounded Hemma access-denied diagnostic record that names the next
  operator action while preserving the content-safety contract.
- [x] Either accepted pyannote diarization proof with exact and min/max speaker
  hints, or a bounded Hemma access-denied record that names the next
  operator action.
- [x] A TorchCodec-compatible sidecar image that reports
  `torchcodec_audio_decoder_importable=true`, reports
  `miopen_hiprtc_headers_available=true`, and runs pyannote diarization through
  exact speaker-count and min/max speaker-range calls on Hemma.
- [x] Replacement decision not required because pyannote access and GPU live
  proof succeeded with the selected maintained library-backed backend.
- [x] Task 352/353 and `.codex/handoff.md` updated with the resulting next
  state.
- [x] Retained ruthless review artifact accepting either the complete
  diarization proof or the bounded access/replacement decision.

## Acceptance Criteria

- [x] FasterWhisper remains the preferred and accepted STT backend unless a
  separate governed STT task changes that decision; this task only resolves
  diarization.
- [x] Pyannote remains the first diarization option. Replacement work can begin
  only after the access-denied state is recorded as not provisionable for
  the current lane.
- [x] The accepted pyannote path must not hide a broken decoder behind
  `torchaudio.load`, because that surface also depends on TorchCodec in the
  accepted Torchaudio version.
- [x] The accepted pyannote path must include the ROCm JIT header surface needed
  by MIOpen HIPRTC compilation. The benchmark image must install
  `librocrand-dev` for `rocrand/rocrand_xorwow.h` and `libc6-dev` for standard
  C headers, and live observation/profile proof must project
  `miopen_hiprtc_headers_available=true`.
- [x] Live proof succeeds only when diarization runs through the selected
  backend on the GPU-required sidecar lane, exercises exact speaker-count
  and min/max speaker-range hints, provides exclusive speaker segments, and
  produces alignment-suitable evidence for the English and Swedish
  fixtures.
- [x] `HF_TOKEN` is the governed token environment variable. Reports and docs
  may record the key name and bounded readiness status, but never token
  values, private cache paths, raw transcripts, generated media, or model
  artifacts.
- [x] Any replacement candidate is governed before implementation and rejected
  if it lacks maintained-library ownership, GPU execution, exact speaker
  hints, min/max speaker hints, or alignment-suitable segment output.
- [x] Story 53 stayed blocked until Task 352 received Review 40's final
  retained decision accepting complete live proof including diarization.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
