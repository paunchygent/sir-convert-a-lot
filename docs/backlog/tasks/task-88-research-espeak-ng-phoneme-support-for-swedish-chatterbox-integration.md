---
id: 'task-88-research-espeak-ng-phoneme-support-for-swedish-chatterbox-integration'
title: 'Research eSpeak NG phoneme support for Swedish Chatterbox integration'
type: 'task'
status: 'in_progress'
priority: 'high'
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-87-run-chatterbox-multilingual-tuning-sweep-on-hemma.md
  - docs/reference/ref-espeak-ng-swedish-phoneme-integration-for-chatterbox.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
labels:
  - research
  - chatterbox
  - espeak-ng
  - phonemes
  - swedish
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Research whether eSpeak NG should be incorporated into the Swedish Chatterbox
pipeline, and if so, identify the safest repo-aligned integration boundary,
licensing posture, and benchmark discipline before any implementation work
starts.

## PR Scope

- Research only; no production code integration in this task.
- Verify the official Chatterbox input surface that the current repo uses:
  - `text`
  - `language_id`
  - `audio_prompt_path`
  - `exaggeration`
  - `cfg_weight`
- Verify whether direct phoneme-string input is documented by the Chatterbox
  maintainers for the current multilingual API.
- Verify the official eSpeak NG capability surface relevant to this repo:
  - text-to-phoneme conversion
  - language coverage and Swedish verification steps
  - CLI/runtime packaging expectations
  - license
- Verify the licensing posture of likely helper tooling such as `phonemizer`
  before proposing it as a pipeline dependency.
- Produce one reference note that compares possible integration boundaries:
  - offline preprocessing tool
  - benchmark-only sidecar/helper container
  - in-process runtime dependency
  - optional text-normalization experiment only
- End with a doc-first recommendation for the next implementation slice.

## Deliverables

- [ ] Reference note with official-source findings and incorporation options.
- [ ] Explicit statement of whether direct phoneme input is documented for the
  current Chatterbox multilingual API.
- [ ] Explicit licensing note for eSpeak NG and any proposed helper library.
- [ ] Recommended docs-as-code follow-on task sequence for implementation, if
  the research outcome is positive.

## Acceptance Criteria

- [ ] The research note is grounded in official upstream sources only:
  - `resemble-ai/chatterbox`
  - `espeak-ng/espeak-ng`
  - any proposed helper library's official repo/docs
- [ ] The task records whether the current Chatterbox API used by this repo can
  accept phoneme strings without undocumented internals.
- [ ] The task records that Swedish phoneme support must be benchmarked on Hemma
  rather than assumed from generic multilingual marketing copy.
- [ ] The task records whether GPL-licensed phoneme tooling can be placed inside
  the main runtime image or should remain outside the production service
  boundary pending review.
- [ ] The task ends with a recommended task setup for the next slices rather
  than jumping directly to implementation.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
