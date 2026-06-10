---
id: task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers
title: Resolve Hemma STT sidecar live proof backend blockers
type: task
status: in_progress
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/reviews/review-33-ruthless-review-of-task-352-post-deploy-stt-sidecar-live-proof-blocker.md
  - docs/backlog/reviews/review-34-ruthless-review-of-task-353-stt-sidecar-backend-failure-classification.md
  - docs/backlog/reviews/review-35-ruthless-review-of-stt-sidecar-ctranslate2-rocm-image-contract.md
  - docs/backlog/reviews/review-36-ruthless-review-of-stt-sidecar-ctranslate2-rocm-rpath-image-correction.md
  - docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - stt
  - diarization
  - hemma
  - rocm
  - sidecar
  - benchmark
  - gpu
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Resolve the two backend runtime blockers that prevent Task 352 from producing
accepted live Hemma STT sidecar evidence: `faster-whisper` cannot currently
load on the Hemma ROCm lane without a CUDA runtime/driver failure, and
`pyannote.audio` cannot load the selected diarization pipeline because the
Hugging Face token/account lacks gated-model access. FasterWhisper remains the
preferred first STT backend, but the invariant is GPU-backed Whisper-family
execution with no CPU fallback. If no governed GPU-backed Whisper-family profile
can be proven on the execution lane, Task 352 and Story 53 stay blocked.

Story 53 remains blocked throughout this task. No `audio -> transcript_bundle`
route registration, transcript persistence, formatter output, Gateway
publication, or main-service STT dependency promotion is in scope.

## PR Scope

- Investigate and prove the Hemma STT backend profile:
  - `faster-whisper` is the preferred first STT option;
  - accepted proof requires GPU-required no-CPU-fallback Whisper-family
    execution for both fixtures;
  - on Hemma's current ROCm lane this requires a governed CTranslate2 HIP/ROCm
    wheel or source-build proof for FasterWhisper, or a governed GPU-backed
    Whisper-family replacement proof before Task 352 can unblock Story 53.
- Investigate and decide the diarization profile:
  - provision/verify gated-model access for
    `pyannote/speaker-diarization-community-1`; or
  - select an alternative library-backed diarization profile that supports
    exact speaker count and min/max speaker ranges without handrolled toy
    diarization.
- Add bounded backend failure classification to the live observation or a
  governed diagnostic artifact so future live-proof reviews do not depend on
  ad hoc diagnostic scripts.
- Rerun the benchmark-only sidecar live observation against the ignored English
  two-speaker and Swedish one-speaker fixtures after remediation.
- Ingest the accepted or rejected observation with
  `pdm run benchmark:stt-sidecar-profile-proof --mode live --live-observation-json <path>`.
- Record the ignored observation/profile-proof paths and retained review
  decision in Task 352.

## Current Evidence

Review 33 accepts the current blocker record as truthful and requires changes
before Task 352 can complete:

- live sidecar launch, codec boundary, backend imports, `HF_TOKEN` presence,
  scratch-backed cache roots, ROCm GPU/no CPU fallback, content safety, and
  120-minute lifecycle are proven;
- `faster-whisper` model load fails with `RuntimeError`: `CUDA failed with error CUDA driver version is insufficient for CUDA runtime version`;
- `pyannote.audio` pipeline loading fails with `GatedRepoError`;
- the profile-proof artifact has `proof_ready=false`;
- Story 53 remains blocked.

## Research Evidence

Read-only subagent research on 2026-06-10 split the two blockers:

- `faster-whisper`/CTranslate2 is not accepted on the current Hemma ROCm lane.
  The live sidecar proves ROCm Torch, but the Dockerfile installs the normal
  pip path for `faster-whisper`/CTranslate2. Upstream `faster-whisper`
  documentation remains CUDA/NVIDIA oriented, while CTranslate2 now has an AMD
  HIP/ROCm path through specific release wheels or source builds with
  `WITH_HIP=ON`. Therefore the preferred first STT remediation path is a
  governed GPU-backed FasterWhisper proof through CTranslate2 HIP/ROCm on Hemma.
  If that path is not viable, a different Whisper-family backend can be governed
  and proven, but non-Whisper STT replacement and CPU fallback are not acceptable
  substitutes for this product lane.
- `pyannote.audio` is blocked by account/model access, not import, cache, or
  token-forwarding plumbing. The token is present in the sidecar and the
  selected pipeline call uses `Pipeline.from_pretrained(..., token=token)`, but
  the selected `pyannote/speaker-diarization-community-1` model returns
  `GatedRepoError`. Hugging Face gated access is per account/token; accepting or
  requesting access for that exact account is required before this profile can
  produce speaker-hint evidence.

The governed next-choice matrix is:

| Area | Keep Current Profile If | Otherwise |
|---|---|---|
| STT | CTranslate2 HIP/ROCm wheel or source-build proof runs `faster-whisper` on Hemma GPU with no CPU fallback. | Govern and prove a different GPU-backed Whisper-family backend, or keep Task 352 and Story 53 blocked; do not accept non-Whisper STT or CPU fallback. |
| Diarization | The Hemma `HF_TOKEN` account receives gated access and pyannote runs exact and min/max speaker hints. | Govern a different library-backed diarization profile that supports the speaker-hint contract; keep Story 53 blocked until proven. |

## Overseer Loop

This task uses the shared `overseer-implementation-review-loop` skill:

1. The overseer owns scope, docs authority, commits, deploys, and final state.
1. Implementation specialists work against this task, with red behavior tests
   first where feasible.
1. A fixed ruthless reviewer writes retained review artifacts and either
   approves or requests changes.
1. On changes requested, implementation adds red tests that would have caught
   each accepted finding, makes them green, and returns for another review pass.
1. A backend profile change is not accepted until the retained review approves
   the live-proof evidence.

## Implementation Notes

The first Task 353 implementation slice adds bounded backend failure
classification to the live observation. This resolves Review 33's medium
finding without claiming Task 352 is accepted:

- the runtime probe classifies exceptions as stable codes such as
  `gpu_backend_runtime_unavailable`, `gated_model_access_denied`,
  `backend_dependency_incompatible`, or `backend_runtime_blocked`;
- the live observation projects `backend_failures` with only
  `backend_family`, `status`, `failure_code`, and `exception_class`;
- raw exception messages, backend-native guidance, token values, private paths,
  fixture source paths, raw model identifiers, and transcript text remain out of
  retained JSON.

Review 34 approved this bounded diagnostic slice on 2026-06-10. That approval
does not accept live STT or diarization backend execution and does not unblock
Story 53.

The slice was deployed at `14cd0da321e95ecd9644d8766b850b99feb4dc95` and rerun
against the Hemma benchmark sidecar. The ignored live-observation artifact is:

- `build/verification/stt-sidecar-live-observation-hemma-backend-failures/live-observation.json`.

It records bounded backend failures without raw messages, private paths, model
ids, token values, or transcript text:

- STT: `backend_family=faster_whisper`,
  `failure_code=gpu_backend_runtime_unavailable`,
  `exception_class=RuntimeError`;
- diarization: `backend_family=pyannote_audio`,
  `failure_code=gated_model_access_denied`, `exception_class=GatedRepoError`.

The ignored profile-proof artifacts are:

- `build/verification/stt-sidecar-profile-proof-live-backend-failures/profile-proof.json`;
- `build/verification/stt-sidecar-profile-proof-live-backend-failures/profile-proof.md`.

Profile-proof ingestion still returns exit code `2` with `proof_ready=false`.
The remaining product blockers are unchanged: GPU-backed Whisper-family STT
execution and live diarization execution are still not accepted.

The second Task 353 implementation slice updates only the benchmark sidecar
image contract for the preferred FasterWhisper path:

- the image downloads the official CTranslate2 `4.8.0` ROCm wheel archive from
  OpenNMT's release artifacts and verifies SHA256
  `9ec6d82e5682b27af6c535f56525665c949cc63fbef14a9028c47b0164717143`;
- the image installs the exact Python 3.11 CTranslate2 ROCm wheel after
  `faster-whisper`, `pyannote.audio`, and `huggingface-hub==0.34.4`;
- the initially reviewed image registered the full Torch ROCm library directory
  with the system dynamic linker so the CTranslate2 ROCm extension could
  resolve the HIP sonames already declared by the Torch ROCm wheel;
- the slice does not add CPU fallback, route registration, transcript
  persistence, formatter output, Gateway publication, main-service STT
  dependencies, or diarization replacement behavior.

Review 35 approved this bounded image-contract slice on 2026-06-10. That
approval did not accept Task 352 live proof. The slice was committed, pushed,
and deployed at `1b1576450d56eb16429ed1696e59c9f3ae504183`. The post-deploy
live observation returned exit code `2` and wrote:

- `build/verification/stt-sidecar-live-observation-hemma-ctranslate2-rocm-1b15764/live-observation.json`.

The deployed image improved the STT backend evidence: FasterWhisper no longer
records an STT backend failure, the runtime confirms ROCm acceleration with no
CPU fallback, both fixtures detect the expected `en` and `sv` languages, and
word timestamps are present. The same observation invalidated the global
dynamic-linker approach because the codec boundary regressed:
`ffmpeg_available=false`, `ffprobe_available=false`, and
`valid_audio_probe_exercised=false`. A direct Hemma probe traced the failure to
global registration of the full Torch library directory, which made FFmpeg and
FFprobe load Torch's bundled `libtinfo.so.6`.

The corrective implementation slice keeps the official CTranslate2 ROCm wheel
and FasterWhisper-first path, but replaces global linker registration with a
CTranslate2-owned ROCm runtime library directory:

- the image installs `patchelf`;
- the image links Torch ROCm runtime libraries into
  `/opt/ctranslate2-rocm-libraries` while excluding `libtinfo.so*`;
- the image adds the required versioned HIP soname links for `libhiprand.so.1`,
  `libhipblas.so.3`, and `libamdhip64.so.7`;
- the image patches only CTranslate2 wheel binaries with RPATHs pointing at
  the wheel-local CTranslate2 libraries and
  `/opt/ctranslate2-rocm-libraries`;
- the image does not use `LD_LIBRARY_PATH`, `ldconfig`, or
  `/etc/ld.so.conf.d` for this lane.

Review 36 approved this corrective pre-deploy image slice on 2026-06-10. The
slice was committed, pushed, and deployed at
`bcde92a04ce23a60aa88ac3bcb354cf5c9051b7a`. Hemma deploy verification passed
with expected, remote, and service revisions all matching
`bcde92a04ce23a60aa88ac3bcb354cf5c9051b7a`.

The post-deploy live observation returned exit code `2` and wrote:

- `build/verification/stt-sidecar-live-observation-hemma-ctranslate2-rpath-bcde92a/live-observation.json`.

The post-deploy profile-proof ingestion returned exit code `2` and wrote:

- `build/verification/stt-sidecar-profile-proof-live-ctranslate2-rpath-bcde92a/profile-proof.json`;
- `build/verification/stt-sidecar-profile-proof-live-ctranslate2-rpath-bcde92a/profile-proof.md`.

This deployed evidence removes the prior FasterWhisper and codec blockers:

- codec boundary is proven: `ffmpeg_available=true`,
  `ffprobe_available=true`, `valid_audio_probe_exercised=true`,
  `bounded_metadata_projected=true`, and corrupt/no-audio/unsupported media all
  fail closed;
- FasterWhisper is importable and executes on ROCm with
  `gpu_execution_confirmed=true`, `cpu_fallback_observed=false`, expected
  `en`/`sv` language detection, and word timestamps present for both fixtures;
- sidecar isolation, backend imports, scratch-backed Hugging Face cache roots,
  120-minute lifecycle, and content safety remain proven.

Review 37 approved this bounded post-deploy evidence as sufficient for the
STT/codec blockers only. Task 352 still is not accepted as complete live proof
because pyannote remains blocked by gated model access. The only
live-observation failure reason is `pyannote_audio_runtime_blocked`; the
retained backend failure is `diarization=gated_model_access_denied`. Profile
proof remains `proof_ready=false` because diarized segments, exclusive
diarization, alignment-suitable evidence, exact speaker-count hints, min/max
speaker-range hints, and Hugging Face model access are not ready.

## Deliverables

- [x] Current upstream/backend feasibility notes for FasterWhisper/CTranslate2
  on ROCm and pyannote gated-model access are recorded here or in Task 352.
- [x] The live observation schema or retained diagnostic artifact records
  bounded backend failure classifications without transcript text, token values,
  private paths, or raw model identifiers.
- [x] GPU-backed Whisper-family execution is proven through FasterWhisper on
  the deployed ROCm sidecar lane without CPU fallback.
- [ ] Diarization backend access is proven or explicitly rejected with governed
  replacement follow-up.
- [x] Post-remediation live observation and profile-proof artifacts are
  generated on Hemma from committed/pushed/deployed code.
- [x] Retained review accepts the post-deploy evidence as sufficient for the
  STT/codec blockers while recording concrete remaining diarization blockers
  and keeping Story 53 blocked.

## Acceptance Criteria

- [x] The task does not promote dry-run, projection, or partial sidecar evidence
  as accepted live proof.
- [x] Live evidence proves a Whisper-family STT backend executes on a
  GPU-required no-CPU-fallback lane for both fixtures and records bounded
  language/duration/segment/word-timestamp evidence.
- [ ] If GPU-backed FasterWhisper cannot be proven, any alternative STT backend
  is governed as a Whisper-family replacement and proven on GPU before Task 352
  can unblock Story 53.
- [ ] If `pyannote.audio` remains selected, live evidence proves exact speaker
  count and min/max speaker range hints run through the backend for the fixtures.
- [ ] If pyannote gated access cannot be provisioned, the rejection is recorded
  with a governed replacement decision that preserves library-backed diarization.
- [x] The live observation and profile proof remain content-safe: no transcript
  text, token values, private cache paths, fixture source paths, raw model ids,
  generated media, or model artifacts are committed.
- [ ] Story 53 remains blocked unless Task 352 receives a final retained review
  decision of accepted live-proof evidence.

## Test Requirements

- [x] Red-first tests cover backend failure-class projection before any schema
  or diagnostic artifact implementation.
- [x] Focused sidecar observation/profile-proof tests pass.
- [x] Docs validation passes:
  `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.
- [x] Runtime change validation includes focused `format-all`, `lint-fix`,
  `typecheck-all`, and focused `pytest-root` commands.
- [x] Red-first image contract validation covers the corrected
  CTranslate2-owned ROCm runtime library directory, wheel-local RPATHs, and the
  absence of `LD_LIBRARY_PATH`, `ldconfig`, and global Torch library
  registration.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
