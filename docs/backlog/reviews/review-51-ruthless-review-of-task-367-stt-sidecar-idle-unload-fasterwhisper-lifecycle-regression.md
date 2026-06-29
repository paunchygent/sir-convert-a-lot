---
id: review-51-ruthless-review-of-task-367-stt-sidecar-idle-unload-fasterwhisper-lifecycle-regression
title: Ruthless review of Task 367 STT sidecar idle unload FasterWhisper lifecycle regression
type: review
status: completed
priority: high
created: '2026-06-28'
last_updated: '2026-06-28'
related:
  - docs/backlog/tasks/task-367-remediate-stt-sidecar-idle-unload-fasterwhisper-lifecycle-regression.md
  - docs/backlog/tasks/task-366-implement-stt-sidecar-lazy-model-load-and-idle-unload.md
  - docs/backlog/reviews/review-50-ruthless-review-of-task-366-stt-sidecar-lazy-model-load-and-idle-unload.md
  - docs/reference/ref-stt-proof-lanes-and-admission-operations.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
labels:
  - review
  - approved
  - task-367
  - stt
  - sidecar
  - idle-unload
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Fixed independent ruthless review for Task 367. This reviewer did not author
the implementation or tests and did not modify production or test files. The
only intentional mutation from this pass is this retained review artifact plus
generated docs index refresh.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/index.md`
- `docs/backlog/tasks/task-367-remediate-stt-sidecar-idle-unload-fasterwhisper-lifecycle-regression.md`
- `docs/backlog/tasks/task-366-implement-stt-sidecar-lazy-model-load-and-idle-unload.md`
- `docs/backlog/reviews/review-50-ruthless-review-of-task-366-stt-sidecar-lazy-model-load-and-idle-unload.md`
- `docs/reference/ref-stt-proof-lanes-and-admission-operations.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`

Implementation and test files reviewed:

- `scripts/sir_convert_a_lot/stt_sidecar/model_lifecycle.py`
- `scripts/sir_convert_a_lot/stt_sidecar/runtime.py`
- `scripts/sir_convert_a_lot/stt_sidecar/app_factory.py`
- `tests/sir_convert_a_lot/stt_sidecar_lazy_lifecycle_support.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py`
- `tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`
- task, handoff, and generated docs index diffs in the current working tree

Public/operator surfaces affected:

- Internal STT sidecar `/health` and `/capabilities` residency behavior.
- Internal STT sidecar idle-unload and shutdown cleanup.
- First-use lazy load, active-use protection, and batched FasterWhisper runtime
  behavior.
- Main-service sidecar readiness interpretation is preserved; no public Service
  API v2 request/response contract change was found.

Compatibility posture:

- Task 367 is a clean remediation of a production regression, not a compatibility
  bridge. It removes reliance on a non-existent `WhisperModel.unload_model()`
  method while preserving Task 366 lazy-load/idle-unload semantics.
- FasterWhisper public docs reviewed through Context7 show `WhisperModel`
  construction and transcription but no documented `unload_model()` API.
  CTranslate2 docs separately document `unload_model()` for CTranslate2
  translator-style objects and deletion of model objects for releasing
  resources; that does not justify calling `unload_model()` on the
  FasterWhisper `WhisperModel` wrapper.

## Findings

No findings.

The patch removes the single backend-native unload call from
`LoadedSttModels`/`SttModelLifecycle._drop_models_locked()` and now drops the
resident bundle references directly (`scripts/sir_convert_a_lot/stt_sidecar/model_lifecycle.py:92`,
`scripts/sir_convert_a_lot/stt_sidecar/model_lifecycle.py:238`). That matches
the real production failure class: the sidecar health path triggers
`runtime.unload_idle_models()` before returning readiness
(`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:92`), and before this patch
that path could raise `AttributeError` from an undocumented FasterWhisper
method.

The test remediation is truthful enough for the incident: the shared fake
FasterWhisper model no longer exposes `unload_model()`
(`tests/sir_convert_a_lot/stt_sidecar_lazy_lifecycle_support.py:149`), and the
health-triggered idle-unload test now proves post-timeout `runtime.health()`
drops residency and remains ready (`tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py:231`).
The shutdown test proves active work still blocks idle unload, later idle
unload drops residency, the next model-using call lazy-loads again, and
shutdown is idempotent without relying on fake unload counters
(`tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py:161`).

The adjacent runtime tests preserve the Task 362/366 behavior: batched
FasterWhisper wrapping still happens on first model use
(`tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py:131`), media
probing and normalized-handle checks still behave before/around model work
(`tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py:131`), and the
readiness policy still fails closed for missing model artifacts
(`tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py:72`).

Static review found no `typing.Any`, `typing.cast`, `# type: ignore`, `noqa`,
lint-ignore escape hatches, compatibility shims, false fallback, CPU fallback,
model-family change, quantization change, proxy-timeout change, trust-key
change, or admission-policy change in the reviewed scope. Reviewed modules are
within the repo size budget: `model_lifecycle.py` is 297 lines, `runtime.py` is
423 lines, `test_stt_sidecar_lazy_lifecycle.py` is 272 lines, and the largest
reviewed test module is exactly 500 lines.

## Decision

approved

## Response

Task 367 is approved for the local remediation slice. The implementation fixes
the production lifecycle regression by removing the unsupported
FasterWhisper-wrapper unload call, keeps idle unload fail-closed for real
precondition failures, preserves lazy first-use loading and active-use
protection, and adds a fake surface that would have caught the Task 366
production mismatch.

This approval does not close the task's live production acceptance. Hemma
deployment and post-idle live proof remain required before the task can be
marked terminal.

## Follow-up Actions

1. Overseer must run the governed Hemma deployment and live proof required by
   Task 367: post-idle sidecar `/health` returns `200`, Docker health is
   healthy, a real production `audio -> transcript_bundle` job reaches
   `succeeded`, result and `transcript_json` artifact fetches succeed, and no
   new `audio_sidecar_unavailable` or `unload_model` errors appear in the proof
   interval.
1. After live proof, update Task 367 and `.codex/handoff.md` with exact
   deployment/live-proof evidence before marking validation complete.

## Completion

Reviewer-run evidence:

- Context7 `/systran/faster-whisper` query for `WhisperModel` lifecycle:
  documented model construction and transcription, with no documented
  `WhisperModel.unload_model()` API found.

- Context7 `/opennmt/ctranslate2` query for memory management:
  documented `unload_model()` for CTranslate2 translator-style objects and
  deletion of model objects as a resource-release path.

- `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py -q`
  passed: `47 passed in 0.62s`.

- `pdm run typecheck-all` passed:
  `Success: no issues found in 894 source files`.

- Static scan for `unload_model`, `Any`, `typing.Any`, `cast(`,
  `type: ignore`, `noqa`, lint ignores, pyright, and mypy escape hatches in the
  reviewed STT sidecar files returned no matches.

- `wc -l` confirmed reviewed production/test modules stay within the repo
  400-500 line budget.

- `pdm run docs-sync` refreshed generated docs indexes:
  `docs/backlog/INDEX.md`, `docs/reference/INDEX.md`,
  `docs/runbooks/INDEX.md`, and `docs/index.md`.

- `pdm run docs-validate` passed: `Validated 489 backlog files` and
  `Validated docs=565 rules=11`.

- `pdm run skills-validate` passed: `skills-validate: ok`.

- `pdm run handoff-validate` passed: `handoff-validate: ok`.

- `git diff --check` passed.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
