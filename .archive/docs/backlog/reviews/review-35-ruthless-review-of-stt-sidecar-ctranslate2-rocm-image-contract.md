---
id: review-35-ruthless-review-of-stt-sidecar-ctranslate2-rocm-image-contract
title: Ruthless review of STT sidecar CTranslate2 ROCm image contract
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/reviews/review-33-ruthless-review-of-task-352-post-deploy-stt-sidecar-live-proof-blocker.md
  - docs/backlog/reviews/review-34-ruthless-review-of-task-353-stt-sidecar-backend-failure-classification.md
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
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless implementation review of the bounded STT sidecar image
  contract slice.
- Governing authority:
  - `AGENTS.md`
  - `docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/reviews/review-33-ruthless-review-of-task-352-post-deploy-stt-sidecar-live-proof-blocker.md`
  - `docs/backlog/reviews/review-34-ruthless-review-of-task-353-stt-sidecar-backend-failure-classification.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
- Scope under review:
  - replace the failed normal CTranslate2 CUDA wheel path in the benchmark-only
    sidecar image with the official CTranslate2 ROCm release wheel;
  - register Torch ROCm libraries through the dynamic linker so
    FasterWhisper can use the GPU-backed CTranslate2 lane on Hemma, which was
    later invalidated by post-deploy live codec evidence recorded below;
  - retain the existing no-CPU-fallback invariant and FasterWhisper-first
    product preference;
  - clean docstrings away from task/story/meta wording in touched tests.
- Files reviewed:
  - `containers/stt-sidecar-benchmark/Dockerfile`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py`
- Public or operational surfaces affected:
  - benchmark-only STT sidecar image construction;
  - no Service API v2 route registration;
  - no OpenAPI publication;
  - no transcript artifact persistence;
  - no main-service STT, diarization, or codec dependency promotion.
- Compatibility posture:
  - clean replacement inside the benchmark sidecar image only.
  - no legacy command, route, file, import, or provider contract is preserved.
  - the dynamic-linker registration is system library configuration for the
    selected ROCm runtime in the reviewed slice, but is no longer accepted as
    the current implementation approach after post-deploy live observation.

## Review Evidence

- Current diff includes the Dockerfile change, the new purpose-named benchmark
  image contract test, and docstring-only cleanup in two existing test modules.
- Context7 `/opennmt/ctranslate2` confirms CTranslate2 has an AMD HIP/ROCm
  build path and requires HIP libraries such as `hiprand` and `hipblas`.
- Context7 `/systran/faster-whisper` confirms GPU-backed FasterWhisper uses
  `WhisperModel(..., device="cuda", compute_type=...)` through CTranslate2.
  On the Hemma ROCm lane, the CTranslate2 backend implementation is therefore
  the runtime identity that must become ROCm-capable.
- Context7 `/pyannote/pyannote-audio` confirms the selected diarization family
  remains token-gated and supports GPU transfer plus exact and min/max speaker
  hints once gated artifacts are accessible. This slice does not resolve the
  diarization blocker.
- The Dockerfile starts with the BuildKit syntax directive at
  `containers/stt-sidecar-benchmark/Dockerfile:1`.
- The Dockerfile pins CTranslate2 `4.8.0`, the official ROCm wheel archive, the
  exact `cp311` wheel filename, and SHA256
  `9ec6d82e5682b27af6c535f56525665c949cc63fbef14a9028c47b0164717143` at
  `containers/stt-sidecar-benchmark/Dockerfile:18`.
- The Dockerfile verifies the release archive with `sha256sum --check` before
  installing the ROCm wheel with `python -m pip install --force-reinstall --no-deps`
  at `containers/stt-sidecar-benchmark/Dockerfile:49` and
  `containers/stt-sidecar-benchmark/Dockerfile:54`.
- The Dockerfile installs the FasterWhisper/pyannote/Hugging Face dependencies
  before replacing the transitive CTranslate2 package with the pinned ROCm wheel
  at `containers/stt-sidecar-benchmark/Dockerfile:37`.
- A Hemma read-only container probe confirmed `ldconfig` against
  `/app/.venv/lib/python3.11/site-packages/torch/lib` creates the required
  versioned HIP soname links for `libhiprand.so.1`, `libhipblas.so.3`, and
  `libamdhip64.so.7`. This supported the pre-deploy static review only; the
  post-deploy live observation recorded below invalidated using global
  dynamic-linker registration for the benchmark image.
- Static review found no task/story-number filenames in the new test file and
  no task/story/meta wording in the changed module docstrings.
- Forbidden-pattern review found no application shim, alias, wrapper, hidden
  CPU fallback, lint bypass, `typing.cast`, `type: ignore`, or `Any` shortcut in
  the scoped diff.

## Findings

No blocking findings remained for the pre-deploy static image-contract slice.

The scoped implementation is accepted because it keeps FasterWhisper as the
first STT backend, replaces only the failed CTranslate2 package path inside the
benchmark sidecar image, pins and verifies the official ROCm wheel, registers
Torch ROCm libraries through the system dynamic linker, and does not weaken the
GPU-required/no-CPU-fallback contract.

This review does not accept Task 352 as complete live proof. The image change
still must be committed, pushed, deployed to Hemma, and exercised by the live
observation/profile-proof commands before Story 53 can move.

## Post-Deploy Correction

The reviewed slice was later committed, pushed, and deployed at
`1b1576450d56eb16429ed1696e59c9f3ae504183`. The live Hemma observation wrote:

- `build/verification/stt-sidecar-live-observation-hemma-ctranslate2-rocm-1b15764/live-observation.json`.

That observation improved the STT backend state but invalidated this review's
dynamic-linker implementation approach. FasterWhisper no longer recorded an STT
backend failure, ROCm execution remained active with no CPU fallback, the
fixtures detected `en` and `sv`, and word timestamps were present. The codec
boundary failed in the same deployed image with `ffmpeg_available=false`,
`ffprobe_available=false`, and `valid_audio_probe_exercised=false`.

A direct Hemma probe traced the codec failure to global registration of the
full Torch library directory, which made FFmpeg and FFprobe load Torch's bundled
`libtinfo.so.6`. The corrective implementation direction is therefore to keep
the official CTranslate2 ROCm wheel but contain ROCm runtime discovery to
CTranslate2 wheel binaries by using a CTranslate2-owned runtime library
directory and wheel-local RPATHs. That corrected implementation requires a
separate retained review and live Hemma proof before Task 352 can be accepted.

## Decision

approved

## Response

Accept the bounded CTranslate2 ROCm image-contract slice. The implementation
specialist can be closed for this slice after the overseer records this review
and performs the normal commit/push/deploy workflow.

Task 352 remains in progress. Story 53 remains blocked until a later retained
review accepts post-deploy live Hemma evidence for both GPU-backed
FasterWhisper execution and real diarization execution.

## Follow-up Actions

1. After commit, push, and deploy, rerun the live Hemma observation against the
   English two-speaker and Swedish one-speaker fixtures and ingest it through
   `pdm run benchmark:stt-sidecar-profile-proof --mode live`.
1. Record the ignored live-observation/profile-proof paths in Task 352 or Task
   353 and request a separate retained review of the post-deploy evidence.
1. Keep pyannote gated access or a governed replacement diarization backend as
   the remaining live-proof blocker; do not register `audio -> transcript_bundle`
   while that evidence is missing.

## Completion

Review completed on 2026-06-10. Decision is `approved` for the bounded
pre-deploy STT sidecar CTranslate2 ROCm image-contract slice only. The
post-deploy codec failure recorded above means the dynamic-linker approach is
not accepted as current implementation guidance.

Validation run during review:

- `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py -q`
  -> `10 passed`.
- `pdm run ruff format --check tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py`
  -> `3 files already formatted`.
- `pdm run ruff check tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py`
  -> `All checks passed!`.
- `pdm run mypy --no-incremental --config-file pyproject.toml tests/sir_convert_a_lot/test_audio_transcription_sidecar_benchmark_image_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_live_observation_runtime.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_runtime_probe_output.py`
  -> `Success: no issues found in 3 source files`.
- `pdm run run-hemma -- sudo -n docker run --rm --entrypoint /bin/bash sir-convert-a-lot-stt-sidecar:benchmark -lc 'set -e; printf "%s\n" /app/.venv/lib/python3.11/site-packages/torch/lib > /etc/ld.so.conf.d/torch-rocm-review.conf; ldconfig; ls -l /app/.venv/lib/python3.11/site-packages/torch/lib/libhiprand.so* /app/.venv/lib/python3.11/site-packages/torch/lib/libhipblas.so* /app/.venv/lib/python3.11/site-packages/torch/lib/libamdhip64.so*'`
  -> confirmed `ldconfig` creates the versioned HIP soname links required by
  the CTranslate2 ROCm wheel.
- `pdm run docs-sync` -> refreshed generated docs indexes.
- `pdm run docs-validate` -> `Validated 458 backlog files`;
  `Validated docs=533 rules=11`.
- `pdm run skills-validate` -> `skills-validate: ok`.
- `pdm run handoff-validate` -> `handoff-validate: ok`.
- `git diff --check` -> passed.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
