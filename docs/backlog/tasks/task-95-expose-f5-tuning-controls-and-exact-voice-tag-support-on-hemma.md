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

- [x] Task 85 runner exposes the new F5 tuning flags and file-backed probe-text
  input.
- [x] F5 sidecar runtime writes the expanded TOML surface supported by the
  installed `swedish-tts` CLI.
- [x] Exact upstream voice-tag behavior is documented with code-grounded
  evidence rather than README-level assumptions.
- [x] One fresh Hemma evidence bundle exists for the Christian Hedlund
  reference clip under `build/verification/`.

## Acceptance Criteria

- [x] `benchmark:f5-tts-smoke` accepts and records `speed`, `fix_duration`,
  `cross_fade_duration`, `target_rms`, and `load_vocoder_from_local`.
- [x] The generated F5 TOML can use file-backed prompt text (`gen_file`) while
  preserving the normalized sidecar contract.
- [x] The docs record the exact accepted voice-tag form from the installed CLI:
  `[voice_name]` with names constrained by the upstream regex rather than an
  inferred free-form tag syntax.
- [x] The implementation does not falsely claim support for paralinguistic
  tags, SSML, or IPA unless code-grounded evidence exists in the installed
  upstream runtime.
- [x] One new Hemma sample is generated with the Christian Hedlund reference
  clip and synced locally for listening review.

## Current Evidence

- The Task 85 runner now exposes and records:
  - `speed`
  - `fix_duration`
  - `cross_fade_duration`
  - `target_rms`
  - `load_vocoder_from_local`
  - file-backed `--probe-text-file`
- The F5 sidecar now writes file-backed prompt text through `gen_file` in the
  generated TOML while keeping the normalized ADR-0007 `/synthesize` request
  shape unchanged.
- The exact upstream `infer_cli` voice-tag syntax is now code-grounded:
  - tag form: `[voice_name]`
  - actual parser regex: `\[(\w+)\]`
  - accepted tag-name characters are therefore limited to word characters
    rather than free-form labels,
  - missing or unknown tags fall back to `main`,
  - true multi-speaker generation still requires a richer request surface than
    the current single-reference ADR-0007 sidecar contract.
- Upstream evidence also remains negative on the following claims:
  - no explicit IPA support found,
  - no explicit SSML/paralinguistic-tag support found in the installed CLI,
  - the Gradio “multi-style” examples are still reference-routing examples
    rather than magic built-in emotion tags.
- Live Hemma Christian Hedlund rerun now exists under:
  - `build/verification/task-95-f5-tuning-controls-and-exact-voice-tag-support-on-hemma/`
  - `run_id=20260308T012850Z`
  - `repo_head=ec3d6ebecf9de24de6aab3d8c836ffc4e7aa2254`
  - rebuilt image:
    `sha256:3ab9b7a15f25da99ea677670a3bce217055cf2a06ec4be2d54f1166d7d21327e`
  - synthesized artifact:
    `build/verification/task-95-f5-tuning-controls-and-exact-voice-tag-support-on-hemma/artifacts/sample_sv.wav`
  - artifact SHA256:
    `50b38ad889dbe993668c370d28092c7a3e867052dffe7dc2e1e3c5f7a25117c5`
- The successful Christian run used these quality-first settings:
  - `remove_silence=true`
  - `nfe_step=64`
  - `cfg_strength=2.0`
  - `sway_sampling_coef=-1.0`
  - `speed=1.0`
  - `fix_duration=null`
  - `cross_fade_duration=0.15`
  - `target_rms=0.1`
  - `vocoder_name=vocos`
  - `load_vocoder_from_local=false`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
