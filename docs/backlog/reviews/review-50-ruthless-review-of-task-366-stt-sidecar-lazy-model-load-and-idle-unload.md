---
id: review-50-ruthless-review-of-task-366-stt-sidecar-lazy-model-load-and-idle-unload
title: Ruthless review of Task 366 STT sidecar lazy model load and idle unload
type: review
status: completed
priority: high
created: '2026-06-27'
last_updated: '2026-06-27'
related:
  - docs/backlog/tasks/task-366-implement-stt-sidecar-lazy-model-load-and-idle-unload.md
  - docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - review
  - approved
  - task-366
  - stt
  - lazy-load
  - idle-unload
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Fixed independent ruthless review for Task 366. This reviewer did not author
the implementation or tests and did not modify production code or tests. The
only intentional mutation from this pass is this retained review artifact plus
generated docs index refresh if validation requires it.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/backlog/tasks/task-366-implement-stt-sidecar-lazy-model-load-and-idle-unload.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`

Implementation and test files reviewed:

- `compose.yaml`
- `scripts/sir_convert_a_lot/stt_sidecar/app_factory.py`
- `scripts/sir_convert_a_lot/stt_sidecar/contracts.py`
- `scripts/sir_convert_a_lot/stt_sidecar/model_lifecycle.py`
- `scripts/sir_convert_a_lot/stt_sidecar/runtime.py`
- `scripts/sir_convert_a_lot/stt_sidecar/settings.py`
- `tests/sir_convert_a_lot/test_compose_contract.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py`
- `tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py`
- task and generated docs index diffs in the current working tree

Public/operator surfaces affected:

- Internal STT sidecar `/health` response.
- Internal STT sidecar `/capabilities.cache` readiness truth.
- Internal STT sidecar `/probe-media`, `/diarize`, and `/transcribe-chunk`
  model residency behavior.
- Docker Compose STT sidecar healthcheck and idle-unload timeout environment.

Compatibility posture:

- Task 366 permits additive residency fields while preserving current endpoint
  compatibility.
- The existing converter contract still defines `cache_roots_ready`,
  `model_artifacts_present`, and `required_secrets_present` as readiness truth
  fields that fail closed before job admission.
- No allocator, quantization, model-family, route, or CPU fallback change is
  authorized in this task.

## Findings

### Blocker: `/capabilities.cache.model_artifacts_present` now equates cache-root existence with model artifacts

`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:145` computes
`cache_ready = cache_root_ready(self._settings.hf_cache_container_root)`, and
`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:149-150` reports both
`cache_roots_ready` and `model_artifacts_present` from that same boolean.
`cache_root_ready` only checks `path.exists()`
(`scripts/sir_convert_a_lot/stt_sidecar/model_lifecycle.py:265-267`).

That is weaker than the accepted contract. The converter contract says missing
model files, inaccessible gated model artifacts, missing secrets, unwritable
cache roots, or GPU unavailability must fail readiness, and explicitly names
`model_artifacts_present` as readiness truth
(`docs/converters/audio-transcription-service-api-artifact-contract.md:406-413`).
The main service readiness evaluator rejects
`model_artifacts_present=false` as `model_artifacts_missing`
(`scripts/sir_convert_a_lot/domain/audio_transcription_policy.py:331-349`).
With this patch, an empty `/cache/huggingface` directory reports
`model_artifacts_present=true`, so the main service can admit audio work that
only fails later during lazy model load. This is deceptive degradation on a
model-evidence readiness path.

Required fix: keep lazy loading, but make the cache readiness fields truthful.
Either compute a bounded artifact-availability check for the configured
approved STT and diarization profiles without exposing raw model ids/secrets,
or, if the intended contract is changing to "remote-loadable with cache root
and secret", update the governed converter contract and readiness policy in the
same slice. Under current Task 366 wording, the compatible fix is artifact
truth, not a semantic downgrade of `model_artifacts_present`.

Proof requirement: add a failing-then-passing capability contract test where the
cache root exists but required model artifacts are absent, and assert
`model_artifacts_present=false` or a governed typed readiness shape that the
main service rejects. Run:
`pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py -q`.

### Medium: idle unload is production-driven only by health/capability polling, but that trigger is not documented or tested as the runtime contract

The unload check runs from `health()` and `capabilities()`
(`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:91-109`) and from the
explicit helper (`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:317-319`).
The production compose service has a `/health` healthcheck every 30 seconds
(`compose.yaml:217-228`), so production likely unloads without user traffic.
However, the task documentation and tests prove the helper behavior directly,
not the production trigger. `tests/sir_convert_a_lot/test_compose_contract.py:360-366`
asserts the healthcheck route exists, while
`tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py:203-214` calls
`runtime.unload_idle_models()` directly. No test ties `/health` or
`/capabilities` to elapsed-time unload through the HTTP/runtime boundary.

Why it matters: operators will reasonably read "idle unload after timeout" as a
self-contained lifecycle guarantee. In the current implementation, disabling
compose healthchecks or changing the health route cadence also changes memory
release behavior.

Required fix: document that compose `/health` polling is the production driver
for idle unload, or add a small internal scheduler if the intended guarantee is
timer-driven. The smaller compatible fix is docs plus proof that `/health`
performs the unload after timeout.

Proof requirement: add a focused HTTP/runtime test that loads models, advances a
controlled clock or uses `idle_unload_seconds=0`, calls `/health` or
`runtime.health()`, and observes `models_resident=false` without calling
`unload_idle_models()` directly. Keep the compose contract test asserting the
healthcheck route and cadence. Run:
`pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_compose_contract.py -q`.

## Decision

changes_requested

## Response

The lazy-startup and active-use accounting direction is sound, and the focused
tests prove startup/probe avoid importing FasterWhisper/pyannote, first
model-using work shares one lazy load under concurrency, active work blocks
idle unload, shutdown drops references, and compose declares the timeout.

Approval is blocked because readiness truth regressed: `model_artifacts_present`
now means "cache root exists" even though the accepted contract and main-service
readiness gate treat it as actual model-artifact availability. That can admit
jobs into a false-ready sidecar and fail only after the first lazy model load.

## Follow-up Actions

1. Worker lane A (`codex/task-0814-stt-lazy-idle-unload`) should fix the two
   findings above and request re-review.
1. Do not mark Task 366 completed until the retained review is updated after
   the capability truth fix.

## Completion

Reviewer-run evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_compose_contract.py -q`
  passed: `33 passed in 1.16s`.
- Static review found no allocator changes in the Task 366 diff.
- Static review found no `Any`, `typing.cast`, `# type: ignore`, `noqa`, or
  lint-ignore escape hatches in the reviewed STT sidecar files/tests.
- Reviewed source modules are under the local 400-500 LoC budget; largest
  production files reviewed are `runtime.py` at 421 lines and
  `model_lifecycle.py` at 267 lines.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed

## Re-review 2026-06-27

Re-review trigger: Worker A remediation for the two retained findings above.
Reviewer remains independent and did not modify production code or tests. This
section is the only intentional review mutation from this pass before generated
index refresh.

Additional files reviewed for the remediation:

- `tests/sir_convert_a_lot/stt_sidecar_lazy_lifecycle_support.py`
- `tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py`

### Prior Finding Closure

The blocker is closed. `/capabilities.cache.model_artifacts_present` no longer
reuses cache-root existence. `SttSidecarRuntime.capabilities()` computes
`cache_roots_ready` from `cache_root_ready(...)` and
`model_artifacts_present` from `model_artifacts_present(self._settings)`
(`scripts/sir_convert_a_lot/stt_sidecar/runtime.py:110-152`). The artifact
helper checks both configured STT and diarization model ids under Hugging Face
cache snapshot candidate roots without importing FasterWhisper or pyannote
(`scripts/sir_convert_a_lot/stt_sidecar/model_lifecycle.py:270-305`).

The regression proof is behaviorally sufficient for the prior false-ready
failure: an empty cache root now reports `cache_roots_ready=true`,
`model_artifacts_present=false`, and the existing main-service readiness policy
rejects the payload with `model_artifacts_missing`
(`tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py:72-92`).
The happy-path startup/probe test writes bounded cached snapshot files for both
configured model ids and still proves `/health`, `/capabilities`, and
`/probe-media` avoid heavyweight model imports
(`tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py:43-69`).

The medium finding is closed. The production idle-unload trigger is now covered
through `runtime.health()` directly: the test loads models, advances a
controlled monotonic clock beyond `idle_unload_seconds`, calls `health()`, and
asserts `models_resident=false` with exactly one fake CTranslate2 unload
(`tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py:232-273`). This
matches the production compose healthcheck path retained at
`compose.yaml:217-228`.

No remaining false-ready/deceptive degradation was found in this re-review
scope. The artifact check is intentionally a bounded cache snapshot presence
check rather than a model load; that matches Task 366's requirement that
health/capability/probe do not instantiate FasterWhisper or pyannote.

### Drift Checks

- No allocator, `malloc_trim`, `MALLOC_ARENA_MAX`, quantization, model
  replacement, concurrency reduction, CPU fallback, or heavy-lane routing change
  was found in the Task 366 reviewed scope.
- No `Any`, `typing.cast`, `# type: ignore`, `noqa`, or lint-ignore escape
  hatch was found in the reviewed STT sidecar production files or new lifecycle
  tests.
- Reviewed modules remain under the local 400-500 LoC budget:
  `model_lifecycle.py` is 305 lines, `runtime.py` is 423 lines,
  `test_stt_sidecar_lazy_lifecycle.py` is 273 lines, and
  `stt_sidecar_lazy_lifecycle_support.py` is 329 lines.

### Re-review Decision

approved

The revised Worker A lane is approved for Task 366. The prior blocker and
medium finding are resolved with focused behavioral proof, and no new findings
were identified in this re-review.

### Re-review Verification

- `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py -q`
  passed: `47 passed in 1.18s`.
- Static scans for forbidden allocator/model/concurrency/heavy-lane drift and
  typing/lint escape hatches passed with no actionable matches.
