---
id: task-296-extract-structured-chat-provider-harness-for-local-first-completion
title: Extract structured chat provider harness for local-first completion
type: task
status: completed
priority: high
created: '2026-05-14'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/protocols/llm/chat.py
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py
labels:
  - llm
  - structured-output
  - local-first
  - dishka
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add a Sir Convert structured-chat provider harness that can call local
llama.cpp-compatible and OpenAI-compatible providers with operation-supplied
schemas and strict remote-fallback policy.

## PR Scope

- Add module-level domain docstrings to every new Python module.
- Define protocol and value objects for `StructuredOutputSpec`,
  `StructuredLLMResponse`, provider profiles, provider sets, and route policy.
- Implement payload builders for Chat Completions `response_format`, Responses
  `text.format`, and llama.cpp JSON Schema/GBNF capability paths.
- Add Dishka providers only where they clarify composition and test injection.
- Add token budget resolver and item-local preflight.
- Add metadata-only capture/telemetry decisions without raw prompt/response
  persistence.
- Do not call providers from parser, renderer, or HTTP artifact routes.

## Tranche 1 Implemented Shape

This first implementation slice establishes the pure structured-provider core
without introducing network calls or answer-key advisory orchestration.

Implemented files:

- `scripts/sir_convert_a_lot/domain/structured_llm_contracts.py`
- `scripts/sir_convert_a_lot/infrastructure/structured_llm_payloads.py`
- `tests/sir_convert_a_lot/test_structured_llm_provider_harness.py`

Completed in tranche 1:

- [x] Source-neutral `StructuredChatProviderProtocol`.
- [x] Source-neutral `StructuredOutputSpec`, `StructuredLLMRequest`,
  `StructuredLLMResponse`, provider capabilities, provider profiles, provider
  sets, route policy, token budget, preflight, and metadata-only capture
  models.
- [x] Payload builders for OpenAI Chat Completions
  `response_format.json_schema`, OpenAI Responses `text.format.json_schema`,
  llama.cpp JSON Schema, llama.cpp GBNF, and vLLM `structured_outputs.choice`.
- [x] Local-first routing policy that distinguishes remote policy forbidden,
  explicit remote denial, missing remote consent, and allowed signed/authorized
  remote fallback.
- [x] Token-budget preflight that returns `over_budget` before any provider
  call.
- [x] Capture metadata that excludes raw prompts, raw provider responses, item
  text, result PDF content, raw `.dxe`, student data, owner metadata, and
  artifact paths.

Remaining after tranche 1:

- [ ] Provider adapter execution against configured local/OpenAI-compatible
  endpoints.
- [ ] Config/profile loading and Dishka wiring where it clarifies composition
  and test injection.
- [ ] Route/runtime tests proving defaults make no LLM calls from HTTP artifact
  routes.

## Tranche 2 Implemented Shape

The second implementation slice adds provider endpoint execution and response
parsing while keeping the provider harness disconnected from advisory reports,
parsers, renderers, and HTTP artifact routes.

Implemented files:

- `scripts/sir_convert_a_lot/infrastructure/structured_llm_provider.py`
- `scripts/sir_convert_a_lot/infrastructure/structured_llm_responses.py`
- `tests/sir_convert_a_lot/test_structured_llm_provider_execution.py`

Completed in tranche 2:

- [x] Async HTTP adapter for configured OpenAI-compatible provider endpoints.
- [x] Endpoint selection for Chat Completions, Responses, llama.cpp-compatible
  chat completions, and vLLM-compatible chat completions.
- [x] Connection model with base URL normalization, API-key header injection,
  extra headers, and per-provider timeout.
- [x] Response parsing for Chat Completions JSON-string content, Responses
  direct/object output, Responses text output, and vLLM structured-choice
  content.
- [x] Typed provider failure mapping for missing provider config, request
  errors, HTTP status errors, invalid JSON bodies, non-object responses, empty
  content, non-JSON content, and conservative schema mismatches.
- [x] Provider execution returns parsed `StructuredLLMResponse` only; raw
  upstream payloads are not part of the return or capture contract.

Remaining after tranche 2:

- [x] Config/profile loading from service settings or a governed provider
  config surface.
- [x] Dishka wiring where it clarifies composition and test injection.
- [x] Route/runtime tests proving default HTTP artifact routes make no LLM
  calls.
- [ ] Task 297 advisory candidate builders and report orchestration.

## Tranche 3 Implemented Shape

The final Task 296 slice adds service configuration loading and opt-in
composition without connecting the provider harness to default HTTP artifact
routes.

Implemented files:

- `scripts/sir_convert_a_lot/infrastructure/structured_llm_config.py`
- `scripts/sir_convert_a_lot/infrastructure/structured_llm_di.py`
- `tests/sir_convert_a_lot/test_structured_llm_provider_composition.py`

Completed in tranche 3:

- [x] `ServiceConfig` now carries a disabled-by-default structured LLM runtime
  config.
- [x] Environment loading uses centralized constants for provider env vars and
  JSON provider keys rather than copied literal strings.
- [x] Enabled config requires an explicit local primary provider, explicit
  provider capabilities, endpoint/output modes, connection base URL, timeout,
  and optional API key indirection through a named env var.
- [x] Remote provider availability and remote fallback authorization remain
  explicit service settings; per-request `allow_remote_fallback` is still
  supplied by the operation request.
- [x] Dishka composition creates an opt-in async provider container for
  `HttpStructuredChatProvider` and HTTP client lifecycle/test injection.
- [x] `dishka<2,>=1.7` is a direct runtime dependency and generated service
  dependency manifests include the new provider-composition dependency.
- [x] DigiExam migration artifact-route proof shows default conversion and
  artifact download do not call the structured provider, and the
  `answer_key_completion_report` remains `not_requested`.

Remaining after Task 296:

- [ ] Task 297 advisory candidate builders and report orchestration.

## Tranche 1 Validation Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_structured_llm_provider_harness.py`
  passed with `15 passed`.
- `pdm run format-all` completed after formatting the new tests.
- `pdm run typecheck-all` passed with no issues in `665` source files.
- `pdm run lint-fix` passed after `pdm run docs-sync` refreshed generated
  indexes.
- `pdm run docs-validate` passed with `387` backlog files and `454` docs.
- `pdm run skills-validate` passed.
- `pdm run handoff-validate` passed.
- `pdm run coverage-gate` passed with `1216 passed, 5 skipped`, coverage
  `95.43%`.
- `git diff --check` passed.

## Tranche 2 Validation Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_structured_llm_provider_harness.py tests/sir_convert_a_lot/test_structured_llm_provider_execution.py`
  passed with `26 passed`.
- `pdm run format-all` completed after formatting one provider test file.
- `pdm run lint-fix` passed.
- `pdm run typecheck-all` passed with no issues in `668` source files.
- `pdm run docs-sync` refreshed generated indexes.
- `pdm run docs-validate` passed with `387` backlog files and `454` docs.
- `pdm run skills-validate` passed.
- `pdm run handoff-validate` passed.
- `pdm run coverage-gate` passed with `1232 passed, 5 skipped`, coverage
  `95.43%`.
- `git diff --check` passed.

## Tranche 3 Validation Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_structured_llm_provider_harness.py tests/sir_convert_a_lot/test_structured_llm_provider_execution.py tests/sir_convert_a_lot/test_structured_llm_provider_composition.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_default_artifact_route_does_not_call_structured_llm`
  passed with `32 passed`.
- `pdm run format-all` completed after formatting the new composition test and
  one touched route test.
- `pdm run lint-fix` passed after fixing one import-order/lint issue.
- `pdm run typecheck-all` passed with no issues in `671` source files.
- `pdm run docs-sync` refreshed generated indexes.
- `pdm run docs-validate` passed with `387` backlog files and `454` docs.
- `pdm run skills-validate` passed.
- `pdm run handoff-validate` passed.
- `pdm run coverage-gate` passed with `1238 passed, 5 skipped`, coverage
  `95.43%`.
- `git diff --check` passed.

## Deliverables

- [x] Generic structured provider protocol.
- [x] Provider profile/config model.
- [x] Payload builders for supported endpoint kinds.
- [x] Budget resolver and failover router.
- [x] Unit tests for payloads, routing, budgeting, and capture policy.
- [x] Service settings/config loader.
- [x] Dishka composition root for provider and HTTP client injection.
- [x] Route/runtime proof that default HTTP artifact routes do not call LLMs.

## Acceptance Criteria

- [x] No provider code is specific to editor edit-ops or DigiExam item types.
- [x] Remote fallback is impossible unless policy says remote is allowed and
  the request explicitly opts in.
- [x] Explicit `allow_remote_fallback=false` is treated differently from
  unspecified consent and blocks remote use.
- [x] Provider capability flags drive JSON Schema/GBNF behavior.
- [x] Normal logs/metrics contain only bounded metadata.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
