---
id: task-95-expose-f5-tuning-controls-and-exact-voice-tag-support-on-hemma
title: Expose F5 tuning controls and exact voice-tag support on Hemma
type: task
status: in_progress
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-94-extract-youtube-reference-audio-for-chatterbox-pipeline.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - tts
  - f5-tts
  - tuning
  - hemma
  - benchmark
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Expose the F5-TTS tuning controls that are already supported by the current
`ChiliOlavi/F5-TTS@swedish-tts` inference CLI, switch the active Hemma
generation lane to the new extracted Christian Hedlund reference clip, and
document the exact upstream voice-tag syntax that is actually accepted by the
installed CLI/runtime.

## PR Scope

- Add bounded Task 85 pass-through controls for the current upstream-supported
  inference knobs:
  - `speed`
  - `fix_duration`
  - `cross_fade_duration`
  - `target_rms`
  - `load_vocoder_from_local`
- Add file-backed probe-text input so longer Swedish prompts and explicit pause
  punctuation can be preserved without fragile inline shell quoting.
- Keep the normalized ADR-0007 `/synthesize` contract stable while improving
  the generated F5 TOML written inside the sidecar.
- Confirm and document the exact multi-voice tag syntax the installed F5 CLI
  accepts, including any regex limits on voice names.
- Record the current contract boundary explicitly:
  - single-reference cloning remains the only normalized sidecar voice mode,
  - true multi-speaker generation is not added unless ADR-0007 and the upload
    surface are expanded to carry multiple reference clips/transcripts.
- Generate and preserve one fresh Hemma sample using:
  - the extracted Christian Hedlund reference clip from `T94`,
  - the provided exact reference transcript,
  - updated quality-first Task 85 defaults.

## Deliverables

- [ ] Task 85 runner exposes the new F5 tuning flags and file-backed probe-text
  input.
- [ ] F5 sidecar runtime writes the expanded TOML surface supported by the
  installed `swedish-tts` CLI.
- [ ] Exact upstream voice-tag behavior is documented with code-grounded
  evidence rather than README-level assumptions.
- [ ] One fresh Hemma evidence bundle exists for the Christian Hedlund
  reference clip under `build/verification/`.

## Acceptance Criteria

- [ ] `benchmark:task-85` accepts and records `speed`, `fix_duration`,
  `cross_fade_duration`, `target_rms`, and `load_vocoder_from_local`.
- [ ] The generated F5 TOML can use file-backed prompt text (`gen_file`) while
  preserving the normalized sidecar contract.
- [ ] The docs record the exact accepted voice-tag form from the installed CLI:
  `[voice_name]` with names constrained by the upstream regex rather than an
  inferred free-form tag syntax.
- [ ] The implementation does not falsely claim support for paralinguistic
  tags, SSML, or IPA unless code-grounded evidence exists in the installed
  upstream runtime.
- [ ] One new Hemma sample is generated with the Christian Hedlund reference
  clip and synced locally for listening review.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
