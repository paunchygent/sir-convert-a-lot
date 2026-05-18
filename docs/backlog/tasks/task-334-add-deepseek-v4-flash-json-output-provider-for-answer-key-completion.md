---
id: task-334-add-deepseek-v4-flash-json-output-provider-for-answer-key-completion
title: Add DeepSeek v4 flash JSON Output provider for answer-key completion
type: task
status: completed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-325-add-openai-responses-provider-and-hot-swappable-operator-routing-for-answer-key-completion.md
  - docs/backlog/tasks/task-326-run-openai-mini-nano-answer-key-evaluation-gate-before-provider-promotion.md
  - docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
labels:
  - answer-key-completion
  - structured-llm
  - deepseek
  - json-output
  - provider-routing
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add the first guarded DeepSeek structured-provider profile for advisory
answer-key completion: `deepseek-v4-flash` through DeepSeek's
OpenAI-compatible Chat Completions API, JSON Output mode, and explicit
non-thinking behavior.

This task implements the provider plumbing only. It does not promote DeepSeek
as the production default, does not change public job-spec provider selection,
and does not bypass Sir Convert's admitted-route/hot-settings boundary.

## PR Scope

- Add a DeepSeek answer-key profile manifest for
  `deepseek-v4-flash-non-thinking`.
- Represent DeepSeek JSON Output as JSON-object provider capability, not strict
  JSON Schema capability. Backend schema validation remains mandatory after
  parsing provider JSON.
- Send DeepSeek requests through OpenAI-compatible Chat Completions with
  `response_format: {"type": "json_object"}`.
- Disable thinking for the DeepSeek profile with `thinking.type=disabled`.
- Keep the DeepSeek API provider profile text-only in this slice; do not
  advertise multimodal vision for the Sir Convert route.
- Keep credentials secret-indirected through an operator-provided DeepSeek
  API-key environment variable; never persist raw DeepSeek API keys.
- Make the profile selectable through existing runtime profile rendering and
  hot-settings/provider-config paths.
- Preserve public/grant remote-provider fail-closed behavior.

## Deliverables

- [x] DeepSeek v4 flash profile manifest and provider JSON rendering.
- [x] Source-neutral JSON-object output mode and capability.
- [x] Chat Completions JSON Output payload shape with thinking disabled.
- [x] Runtime env rendering and config parsing for the DeepSeek profile.
- [x] Focused tests for profile, payload, parsing, and runtime config.
- [x] Docs and validation evidence.

## Acceptance Criteria

- [x] `deepseek-v4-flash-non-thinking` renders as a remote Chat Completions
  provider using model `deepseek-v4-flash`, output mode `json_object`,
  `thinking_mode=disabled`, and base URL `https://api.deepseek.com`.
- [x] The profile declares `supports_json_object=true` and
  `supports_json_schema=false`, so Sir Convert does not claim strict JSON
  Schema support for DeepSeek.
- [x] Provider payloads include `response_format: {"type": "json_object"}`,
  `thinking: {"type": "disabled"}`, bounded `max_tokens`, and no JSON Schema
  object sent to DeepSeek.
- [x] Parsed DeepSeek JSON content is still validated against Sir Convert's
  operation-supplied schema and mapped to the same typed backend failures as
  other providers.
- [x] Runtime profile rendering can select DeepSeek without changing the
  production default away from OpenAI mini.
- [x] Public/grant jobs remain unable to use remote providers unless the
  admitted route is operator-authorized.
- [x] No raw DeepSeek API key, prompt text, item text, raw provider payload, or
  raw provider response is committed.

## Test Requirements

- Manifest tests for the DeepSeek model ID, JSON-object output mode, text-only
  capabilities, secret indirection, and non-thinking setting.
- Payload tests for Chat Completions JSON Output and `thinking.type=disabled`.
- Runtime-config tests proving the selected DeepSeek API-key environment name is
  resolved by indirection and missing credentials fail closed.
- Provider adapter tests proving JSON-object Chat Completions responses are
  parsed and backend schema validation still applies.
- Focused docs validation plus normal Python gates for touched modules.

## Source Notes

- DeepSeek documentation checked on 2026-05-18 through Context7
  `/websites/api-docs_deepseek`: Chat Completions supports
  `deepseek-v4-flash`; JSON Output uses
  `response_format: {"type": "json_object"}` and requires JSON guidance in the
  prompt; thinking mode defaults to enabled and can be disabled with
  `thinking.type=disabled`; v4 flash is documented as supporting non-thinking
  mode, JSON Output, text-only input, and large context/output limits.
- The same documentation lists `deepseek-v4-flash` with text input and
  `supportsImages=false`. A live 2026-05-18 image probe against
  `https://api.deepseek.com/v1/chat/completions` with JSON Output,
  `thinking.type=disabled`, and an OpenAI-style `image_url` data URL failed
  with HTTP 400 `unknown variant image_url, expected text`, so this profile must
  keep `supports_multimodal_vision=false` until DeepSeek publishes and proves a
  compatible image-input route. This is a claim about the DeepSeek API/provider
  surface Sir Convert can use, not a claim about any unavailable model-weight
  deployment outside that API.

## Validation Evidence

- Focused provider tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_answer_key_deepseek_model_profiles.py tests/sir_convert_a_lot/test_answer_key_provider_runtime_config.py tests/sir_convert_a_lot/test_structured_llm_provider_harness.py::test_chat_completions_payload_can_use_json_object_without_schema_format tests/sir_convert_a_lot/test_structured_llm_provider_execution.py::test_http_provider_executes_json_object_chat_and_validates_content`
  passed locally before the corpus eval closeout.
- DeepSeek toy transport probe returned valid JSON Object content through
  `deepseek-v4-flash-non-thinking`.
- Full advisory-corpus eval artifact:
  `build/verification/task-334-deepseek-v4-flash-full-eval-2026-05-18/advisory-golden-evaluation.md`.
  Result: 23 reports, 44 golden items, 42 supported eligible text items, 42
  suggestions, 39 correct suggestions, 3 wrong-but-valid suggestions, 2 manual
  follow-up image/asset skips, and 0 malformed successes.
- Promotion decision: do not promote DeepSeek v4 flash non-thinking to a valid
  answer-key provider option yet. It is transport-valid for text-only JSON
  Output, but the current full gate has non-zero wrong-but-valid rows and no
  DeepSeek API image-input support for the embedded-asset lane.

## Full-Eval Failure Rows

- `item-005` in `1776888013-ak7-lag-och-ratt.dxe`: one gap expected `15`,
  model returned `18`.
- `item-009` in `1813537086-25c-manniskokroppen-prov-eca.dxe`: question asks
  for numbers, model returned surrounding row letters instead.
- `item-016` in `1821017157-prov-biologi-genetik-v2.dxe`: two gaps expected
  `baspar`, model returned `nukleotider`.
- Image/asset rows, including the earlier ekologiprov item 13 image case, are
  correctly manual-follow-up for this profile because DeepSeek rejects
  `image_url` request parts.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
