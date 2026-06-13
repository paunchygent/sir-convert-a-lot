---
id: review-47-ruthless-review-of-task-362-batched-fasterwhisper-production-stt-sidecar
title: Ruthless review of Task 362 batched FasterWhisper production STT sidecar
type: review
status: completed
priority: high
created: '2026-06-13'
last_updated: '2026-06-13'
related:
  - docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
labels:
  - review
  - approved
  - task-362
  - stt
  - faster-whisper
  - batch-inference
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Independent ruthless review for Task 362, using the current uncommitted Sir
Convert-a-Lot diff as the implementation under review. This pass did not
implement production fixes, commit, push, deploy, or run a live production
probe. The only intentional mutation from this reviewer is this retained
review artifact plus any generated docs index refreshes required by validation.

Existing retained-review search found no prior Task 362 review under
`docs/backlog/reviews/`, so this artifact uses `review-47`.

Required instructions and references read:

- `AGENTS.md`
- `docs/index.md`
- `.codex/handoff.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/046-docker-compose-v2-and-debugging.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
- Context7 `/systran/faster-whisper` docs for `WhisperModel`,
  `BatchedInferencePipeline`, and `batch_size` transcription usage.

Governing docs:

- `docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md`
- `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
- `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
- `.codex/handoff.md`

Files reviewed:

- `scripts/sir_convert_a_lot/stt_sidecar/settings.py`
- `scripts/sir_convert_a_lot/stt_sidecar/runtime.py`
- `compose.yaml`
- `tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`
- `tests/sir_convert_a_lot/test_compose_contract.py`
- `docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md`
- `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
- `docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
- `.codex/handoff.md`
- `docs/backlog/INDEX.md`
- Formatting-only diffs in Task 360, Task 361, and Review 46 docs.

Public and operational surfaces affected:

- Production STT sidecar startup path.
- Internal sidecar `/capabilities` transcription evidence.
- `SIR_STT_SIDECAR_BATCH_SIZE` environment contract.
- `compose.yaml` service `sir_convert_a_lot_stt_sidecar`.

Compatibility posture:

- This is an intentional production-runtime hardening change. Missing
  FasterWhisper batched-pipeline support must fail closed at startup rather
  than falling back to plain `WhisperModel.transcribe`.
- No public Service API request/response contract change is part of this slice.

## Findings

None.

## Review Notes

The implementation satisfies the Task 362 contract. Context7's current
Faster Whisper examples use `BatchedInferencePipeline(model=WhisperModel(...))`
and call `batched_model.transcribe(..., batch_size=N)`, which matches the local
runtime shape.

`SttSidecarSettings` now has a typed `batch_size: int` field and loads
`SIR_STT_SIDECAR_BATCH_SIZE` through the shared positive-integer helper with
default `8`; non-positive values raise `ValueError`
(`scripts/sir_convert_a_lot/stt_sidecar/settings.py:37`,
`scripts/sir_convert_a_lot/stt_sidecar/settings.py:70`,
`scripts/sir_convert_a_lot/stt_sidecar/settings.py:80`).

Startup imports FasterWhisper, requires `BatchedInferencePipeline`, converts a
missing attribute into a startup `RuntimeError`, creates the base
`WhisperModel`, and stores the batched pipeline as the active STT model. There
is no fallback path to store or use the plain model when the batched pipeline
is unavailable (`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:145`,
`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:147`,
`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:153`,
`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:161`).

Chunk transcription goes through the batched model protocol and passes
`batch_size=self._settings.batch_size`, preserving `beam_size`,
`word_timestamps=True`, and the language override
(`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:64`,
`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:398`).

Capabilities expose sanitized transcription truth as
`backend_family=faster_whisper` and `batch_size` while avoiding raw STT model
ids and secret values. Secret capability output remains limited to required
secret names, presence, and `values_exposed: False`
(`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:209`,
`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:230`).

Production compose explicitly pins `SIR_STT_SIDECAR_BATCH_SIZE=8` for
`sir_convert_a_lot_stt_sidecar`, and the compose contract test fails closed on
missing or drifted value by indexing the env map and asserting exact string
`"8"` (`compose.yaml:190`,
`tests/sir_convert_a_lot/test_compose_contract.py:327`,
`tests/sir_convert_a_lot/test_compose_contract.py:333`).

The tests are behavioral enough for the production failure mode. The startup
test proves the runtime wraps the base model with `BatchedInferencePipeline`;
it would fail if startup reverted to storing the plain `WhisperModel`. The
chunk transcription test exercises probe-issued normalized media through
`transcribe_chunk()` and asserts the actual transcribe call includes
`batch_size=8`, `beam_size=5`, word timestamps, and language behavior. The
compose test proves the production env contract
(`tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py:87`,
`tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py:114`,
`tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py:126`,
`tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py:159`).

Scoped searches found no new `Any`, `typing.cast`, `# type: ignore`, `noqa`,
or broad `except Exception`/`except BaseException` typing or catch-all escape
in the touched STT runtime/settings/test files. The only fallback-named
matches in the touched production runtime are existing segment-parsing
attribute fallbacks, not a batching or runtime-identity fallback.

Docs and handoff are appropriate for a completed implementation slice. They
claim code/config/test remediation and explicitly say the slice does not
deploy. No reviewed doc or capability output retains tokens, private key
material, or raw model identifiers.

Line-count and SRP check:

- `scripts/sir_convert_a_lot/stt_sidecar/settings.py`: 85 lines.
- `scripts/sir_convert_a_lot/stt_sidecar/runtime.py`: 490 lines.
- `tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py`: 336 lines.
- `tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`: 497 lines.
- `tests/sir_convert_a_lot/test_compose_contract.py`: 632 lines, pre-existing
  broad compose contract module touched only for the one env assertion in this
  slice.

## Decision

`approved`.

## Response

Task 362 is approved. The sidecar now requires FasterWhisper batched
inference, passes configured `batch_size=8` during chunk transcription,
exposes sanitized runtime truth, and pins the production compose env contract.
No production remediation is required by this review.

## Follow-up Actions

1. Deploy/runtime owners still need a separate governed deployment and live
   capability/job proof after this code lands. This review did not deploy or
   verify the current production container.
2. A future hardening test could add an explicit missing-`BatchedInferencePipeline`
   negative startup case. The current code fails closed, and the production
   regression itself is covered by the existing startup-wrapper and transcribe
   tests, so this is not an approval blocker.

## Verification

Reviewer inspection:

- Scoped the dirty worktree with `git status --short` and
  `git diff --name-status`.
- Searched retained reviews with `rg --files docs/backlog/reviews` and
  `rg` for Task 362 review terms; no existing Task 362 review was present.
- Inspected final file contents and diffs for runtime, settings, compose,
  tests, task, story, epic, backlog index, and handoff surfaces.
- Used Context7 for current Faster Whisper API documentation and confirmed
  the implementation matches the documented batched inference pattern.
- Ran scoped typing/fallback/secret searches over reviewed code, tests, docs,
  and compose. No slice-local `Any`, `cast`, `type: ignore`, lint ignore,
  broad catch-all exception, secret value leak, raw STT model identifier in
  capabilities, or batching fallback was found.

Reviewer-run commands:

- `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_compose_contract.py -q`
  - passed, `27 passed`.
- `rg -n "except Exception|except BaseException|catch|fallback|fallback_provider|typing\\.Any|\\bAny\\b|cast\\(|type: ignore|noqa|pyright: ignore" scripts/sir_convert_a_lot/stt_sidecar/settings.py scripts/sir_convert_a_lot/stt_sidecar/runtime.py tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_compose_contract.py`
  - only existing segment-parsing fallback labels matched in runtime.
- `rg -n "secret|token|HF_TOKEN|api[_-]?key|private|BEGIN|password|credential|raw model|model id|model_id" docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md .codex/handoff.md scripts/sir_convert_a_lot/stt_sidecar/runtime.py compose.yaml`
  - no secret values or private material found.

Post-artifact validation commands:

- `pdm run docs-sync`
  - passed and refreshed `docs/backlog/INDEX.md`,
    `docs/reference/INDEX.md`, `docs/runbooks/INDEX.md`, and `docs/index.md`.
- `pdm run typecheck-all`
  - passed, `Success: no issues found in 879 source files`.
- `pdm run docs-validate`
  - passed with `Validated 480 backlog files` and
    `Validated docs=555 rules=11`.
- `pdm run skills-validate`
  - passed with `skills-validate: ok`.
- `pdm run handoff-validate`
  - passed with `handoff-validate: ok`.
- `git diff --check`
  - passed with no whitespace errors.

## Completion

Review retained with `approved` on 2026-06-13.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up actions captured
- [x] Review closed
