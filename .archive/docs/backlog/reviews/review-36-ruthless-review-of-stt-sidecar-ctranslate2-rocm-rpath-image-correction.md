---
id: review-36-ruthless-review-of-stt-sidecar-ctranslate2-rocm-rpath-image-correction
title: Ruthless review of STT sidecar CTranslate2 ROCm RPATH image correction
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/reviews/review-35-ruthless-review-of-stt-sidecar-ctranslate2-rocm-image-contract.md
  - docs/backlog/reviews/review-33-ruthless-review-of-task-352-post-deploy-stt-sidecar-live-proof-blocker.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - review
  - approved
  - stt
  - sidecar
  - rocm
  - ctranslate2
  - faster-whisper
  - rpath
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless implementation review of the corrective STT sidecar
  CTranslate2 ROCm RPATH image slice.
- Governing authority:
  - `AGENTS.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/046-docker-compose-v2-and-debugging.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/reviews/review-35-ruthless-review-of-stt-sidecar-ctranslate2-rocm-image-contract.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
- Files reviewed:
  - `containers/stt-sidecar-benchmark/Dockerfile`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py`
  - `docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md`
  - `docs/backlog/reviews/review-35-ruthless-review-of-stt-sidecar-ctranslate2-rocm-image-contract.md`
  - `.codex/handoff.md`
- Scope under review:
  - keep FasterWhisper as the first STT backend by keeping the official pinned
    CTranslate2 `4.8.0` ROCm wheel;
  - replace the invalidated global Torch library registration from Review 35
    with a contained CTranslate2 ROCm runtime library directory;
  - patch only CTranslate2 wheel binaries with RPATHs that resolve wheel-local
    CTranslate2 libraries and `/opt/ctranslate2-rocm-libraries`;
  - keep FFmpeg/FFprobe out of global Torch linker state by avoiding
    `LD_LIBRARY_PATH`, `ldconfig`, and `/etc/ld.so.conf.d`;
  - preserve the GPU-backed/no-CPU-fallback product invariant.
- Public or operational surfaces affected:
  - benchmark-only STT sidecar image construction;
  - no Service API v2 route registration;
  - no OpenAPI publication;
  - no transcript artifact persistence;
  - no main-service STT, diarization, FFmpeg, or model dependency promotion.
- Compatibility posture:
  - clean image-construction correction inside the benchmark sidecar only.
  - no legacy route, command, import, provider, output, or file contract is
    preserved.
  - the private ROCm runtime library directory is accepted as image packaging for
    ELF dependency resolution, not an application shim, alias, or wrapper. The
    versioned HIP SONAME links are private dynamic-linker artifacts used only by
    CTranslate2 RPATHs; they do not expose a compatibility surface to service
    code or clients.

## Review Evidence

- Context7 `/opennmt/ctranslate2` confirms CTranslate2 has a HIP/ROCm build path
  that depends on HIP runtime libraries such as `hiprand` and `hipblas`.
- Context7 `/systran/faster-whisper` confirms FasterWhisper uses CTranslate2 and
  the GPU path is selected with `WhisperModel(..., device="cuda", compute_type="float16")`; on Hemma ROCm, CTranslate2 is therefore the package
  that must provide the ROCm-backed GPU implementation.
- Context7 `/pyannote/pyannote-audio` confirms pyannote diarization remains a
  real library-backed profile with token-gated model loading, GPU transfer, and
  exact/min/max speaker hints. This corrective slice does not resolve gated
  diarization access.
- The current Dockerfile starts with the BuildKit syntax directive, pins
  CTranslate2 `4.8.0`, verifies the official ROCm wheel archive SHA256, and
  installs the exact `cp311` ROCm wheel after `faster-whisper`,
  `pyannote.audio`, and `huggingface-hub==0.34.4`.
- The correction installs `patchelf`, creates
  `/opt/ctranslate2-rocm-libraries`, links Torch ROCm libraries from
  `/app/.venv/lib/python3.11/site-packages/torch/lib` while excluding
  `libtinfo.so*`, creates the required `libhiprand.so.1`,
  `libhipblas.so.3`, and `libamdhip64.so.7` SONAME links, and patches only:
  - `ctranslate2/_ext*.so` with `$ORIGIN/../ctranslate2.libs` plus the contained
    ROCm runtime directory;
  - `ctranslate2.libs/libctranslate2*.so*` with `$ORIGIN` plus the contained
    ROCm runtime directory.
- The current Dockerfile no longer contains `LD_LIBRARY_PATH`, `ldconfig`, or
  `/etc/ld.so.conf`, so FFmpeg/FFprobe should no longer inherit Torch's bundled
  `libtinfo.so.6` through global linker state.
- The new image contract test is purpose-named, not story/task-number named, and
  its module docstring describes the image contract domain without meta comments
  or refactoring narration.
- Red-first evidence from the implementation specialist is credible for this
  bounded slice: the image contract test failed before the Dockerfile patch
  because `CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR` was absent, then passed after
  the RPATH correction.
- The parent reported a throwaway Hemma GPU probe matching the current
  Dockerfile shape before this review: FFmpeg and FFprobe version checks passed,
  and CTranslate2 compute-type discovery returned GPU compute types including
  `float16`.
- This reviewer read the deployed invalidation artifact at
  `build/verification/stt-sidecar-live-observation-hemma-ctranslate2-rocm-1b15764/live-observation.json`.
  It confirms Review 35's deployed image improved FasterWhisper to ROCm-backed
  `en`/`sv` language evidence with word timestamps and no CPU fallback, but
  failed the codec boundary with `ffmpeg_available=false`,
  `ffprobe_available=false`, and `valid_audio_probe_exercised=false`.
- A read-only Hemma probe against the currently deployed
  `sir-convert-a-lot-stt-sidecar:benchmark` tag still reproduced the known
  pre-correction `libtinfo.so.6` FFmpeg/FFprobe failure. That command is not
  evidence against the uncommitted corrective Dockerfile; it confirms the next
  required step is commit, push, redeploy, then live observation/profile-proof
  ingestion from the corrected image.

## Findings

No blocking findings remain.

The corrective image slice is accepted as a bounded static image-contract fix.
It preserves FasterWhisper as the preferred STT option, keeps GPU-backed
CTranslate2 ROCm execution as the target, removes the global dynamic-linker
contamination that broke FFmpeg/FFprobe, and does not add CPU fallback, route
registration, transcript persistence, formatter output, Gateway publication, or
main-service STT dependencies.

The contained runtime library directory does not violate the repo's no-shim,
no-alias, no-wrapper rule because it is not a service-level compatibility
surface. It is private container packaging for dynamic-linker resolution,
reachable only through CTranslate2 wheel RPATHs, and it deliberately excludes
the library that caused the codec-boundary regression.

This approval does not accept Task 352 as complete live proof and does not
unblock Story 53. The corrected image must still be committed, pushed, deployed
to Hemma, exercised through the live observation command, and ingested through
`benchmark:stt-sidecar-profile-proof`. Pyannote gated access or a governed
library-backed diarization replacement remains unresolved.

## Decision

approved

## Response

Accept the corrective CTranslate2 ROCm RPATH image slice. The implementation
specialist can be closed for this bounded slice after the overseer records this
review and continues with the normal commit/push/deploy/live-proof workflow.

Task 352 remains in progress. Story 53 remains blocked until a later retained
review accepts post-deploy live Hemma evidence for both GPU-backed
FasterWhisper execution and real diarization execution.

## Follow-up Actions

1. Commit, push, and redeploy the accepted corrective slice.
1. Rerun the Hemma live observation against the English two-speaker and Swedish
   one-speaker fixtures from the committed/deployed code.
1. Ingest the new live observation through
   `pdm run benchmark:stt-sidecar-profile-proof --mode live`.
1. Record the ignored live-observation/profile-proof paths in Task 352 or Task
   353 and request a retained review of the post-deploy live evidence.
1. Keep Story 53 blocked until live proof includes both GPU-backed FasterWhisper
   and real diarization execution. If pyannote gated access remains unavailable,
   govern a library-backed diarization replacement before route work begins.

## Completion

Review completed on 2026-06-10. Decision is `approved` for the corrective
pre-deploy STT sidecar CTranslate2 ROCm RPATH image slice only.

Validation run during review:

- `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py -q`
  -> `10 passed`.
- `pdm run ruff format --check tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py`
  -> `1 file already formatted`.
- `pdm run ruff check tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py`
  -> `All checks passed!`.
- `pdm run mypy --no-incremental --config-file pyproject.toml tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py`
  -> `Success: no issues found in 1 source file`.
- `pdm run run-hemma -- jq '{runtime: .runtime, codec_boundary: .codec_boundary, backend_failures: .backend_failures, language_evidence: .language_evidence}' build/verification/stt-sidecar-live-observation-hemma-ctranslate2-rocm-1b15764/live-observation.json`
  -> confirmed deployed Review 35 invalidation: ROCm/no CPU fallback and `en`/`sv`
  word-timestamp evidence were present, while FFmpeg/FFprobe codec availability
  was false.
- `pdm run run-hemma -- sudo -n docker run --rm --entrypoint ffmpeg sir-convert-a-lot-stt-sidecar:benchmark -version`
  -> failed against the still-deployed pre-correction image with Torch
  `libtinfo.so.6` loading.
- `pdm run run-hemma -- sudo -n docker run --rm --entrypoint ffprobe sir-convert-a-lot-stt-sidecar:benchmark -version`
  -> failed against the still-deployed pre-correction image with Torch
  `libtinfo.so.6` loading.
- `pdm run run-hemma -- sudo -n docker run --rm --entrypoint /app/.venv/bin/python sir-convert-a-lot-stt-sidecar:benchmark -c 'print(sorted(__import__("ctranslate2").get_supported_compute_types("cuda")))'`
  -> did not test the corrective Dockerfile because the deployed tag was still
  pre-correction.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
