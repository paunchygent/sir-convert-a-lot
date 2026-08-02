---
id: task-335-replace-deepseek-v4-flash-answer-key-provider-with-v4-pro
title: Replace DeepSeek v4 flash answer-key provider with v4 pro
type: task
status: completed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-334-add-deepseek-v4-flash-json-output-provider-for-answer-key-completion.md
  - docs/backlog/tasks/task-326-run-openai-mini-nano-answer-key-evaluation-gate-before-provider-promotion.md
  - docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md
labels:
  - answer-key-completion
  - structured-llm
  - deepseek
  - provider-routing
  - evaluation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the guarded DeepSeek answer-key provider profile introduced by Task 334
with the selected `deepseek-v4-pro` non-thinking JSON Output route, then rerun
the same full advisory-corpus evaluation before any promotion decision.

## PR Scope

- Remove the flash profile from current code/test surfaces and expose only
  `deepseek-v4-pro-non-thinking`.
- Keep DeepSeek on OpenAI-compatible Chat Completions with
  `response_format: {"type": "json_object"}` and `thinking.type=disabled`.
- Keep the profile text-only for Sir Convert because the DeepSeek API/provider
  surface documents `supportsImages=false` and the live image probe rejects
  `image_url` content parts.
- Do not change the production provider default away from OpenAI mini in this
  slice unless a later explicit override bypasses the promotion gate.
- Rerun the full DigiExam advisory-corpus eval using the pro profile and record
  the result.

## Deliverables

- [x] DeepSeek profile constants, enum value, rendered provider JSON, and tests
  use `deepseek-v4-pro`.
- [x] Runtime profile rendering accepts `deepseek-v4-pro-non-thinking` and no
  longer exposes the flash profile.
- [x] Full advisory-corpus eval evidence for the pro profile is retained under
  `build/verification/`.
- [x] Promotion decision is recorded from the pro eval result.

## Acceptance Criteria

- [x] `answer_key_deepseek_provider_profile_values()` returns only
  `deepseek-v4-pro-non-thinking`.
- [x] Rendered provider JSON uses model `deepseek-v4-pro`, output mode
  `json_object`, `thinking_mode=disabled`, and
  `supports_multimodal_vision=false`.
- [x] Focused provider/runtime tests pass after the flash replacement.
- [x] Full eval reports pro-model counts for supported eligible items, correct
  suggestions, wrong-but-valid suggestions, manual follow-up, malformed
  success, and provider failures.
- [x] No raw DeepSeek API key, prompt text, raw provider payload, or raw
  response is committed.

## Validation Evidence

- Focused profile/runtime tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_answer_key_deepseek_model_profiles.py tests/sir_convert_a_lot/test_answer_key_provider_runtime_config.py`
  passed locally.
- Render check:
  `pdm run python -m scripts.sir_convert_a_lot.devops.render_answer_key_provider_env --profile deepseek-v4-pro-non-thinking --lane hemma-prod-compose`
  rendered primary provider `deepseek-v4-pro-non-thinking`, model
  `deepseek-v4-pro`, output mode `json_object`, and
  `thinking_mode=disabled`.
- Full advisory-corpus eval artifact:
  `build/verification/task-335-deepseek-v4-pro-full-eval-2026-05-18/advisory-golden-evaluation.md`.
  Result: 23 reports, 44 golden items, 42 supported eligible text items, 42
  suggestions, 39 correct suggestions, 3 wrong-but-valid suggestions, 2 manual
  follow-up image/asset skips, and 0 malformed successes.
- Live pro image-input probe against
  `https://api.deepseek.com/v1/chat/completions` with JSON Output and
  `thinking.type=disabled` returned HTTP 400
  `unknown variant image_url, expected text`, matching the documented
  text-only provider surface.
- Promotion decision: do not promote DeepSeek v4 pro non-thinking to the
  production default from this eval. It is selectable and transport-valid for
  text-only JSON Output, but the full gate still has non-zero
  wrong-but-valid rows and no DeepSeek API image-input support.

## Full-Eval Failure Rows

- `item-001` in `1776888013-ak7-lag-och-ratt.dxe`: one gap expected `polis`,
  model returned `åklagare`.
- `item-002` in `1776888013-ak7-lag-och-ratt.dxe`: multiple-response expected
  `[2,3,5,6,8,9]`, model returned `[2,3,5,6,8]`.
- `item-004` in `1821017157-prov-biologi-genetik-v2.dxe`: single choice
  expected `[1]`, model returned `[2]`.
- Image/asset rows remain manual-follow-up for this profile because DeepSeek's
  API provider surface rejects `image_url` request parts.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
