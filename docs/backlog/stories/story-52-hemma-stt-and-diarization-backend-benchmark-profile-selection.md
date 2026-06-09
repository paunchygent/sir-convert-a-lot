---
id: story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection
title: Hemma STT and diarization backend benchmark profile selection
type: story
status: proposed
priority: high
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
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

## Acceptance Criteria

- [ ] A bounded `stt_profile` and `diarization_profile` are selected for the
  first runtime slice or explicitly rejected with reasons.
- [ ] Hemma evidence proves GPU execution, cache reuse, readiness failure on
  missing model access, and no silent CPU fallback.
- [ ] Representative Swedish and English recordings transcribe with diarized
  segment output suitable for JSON artifact assembly.
- [ ] Exact speaker count and min/max speaker range hints are tested against
  the selected diarization backend.
- [ ] 120-minute processing feasibility is proven before route registration.
- [ ] Benchmark reports use bounded metadata and redact content/secrets.

## Test Requirements

- [ ] Sidecar capability smoke test on Hemma.
- [ ] Missing-secret/cache readiness failure test.
- [ ] Swedish/English transcription fixture checks with language evidence.
- [ ] Diarization hint and alignment validation checks.
- [ ] 120-minute fixture or synthetic-duration proof through the governed
  benchmark harness.
- [ ] Docs validation: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Done Definition

The story is done when a selected backend profile is proven or rejected with
operator-grade Hemma evidence and the route execution story has clear runtime
profile inputs.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
