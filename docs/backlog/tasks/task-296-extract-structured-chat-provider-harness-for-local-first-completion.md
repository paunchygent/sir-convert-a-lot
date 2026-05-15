---
id: task-296-extract-structured-chat-provider-harness-for-local-first-completion
title: Extract structured chat provider harness for local-first completion
type: task
status: proposed
priority: high
created: '2026-05-14'
last_updated: '2026-05-14'
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

## Deliverables

- [ ] Generic structured provider protocol.
- [ ] Provider profile/config model.
- [ ] Payload builders for supported endpoint kinds.
- [ ] Budget resolver and failover router.
- [ ] Unit tests for payloads, routing, budgeting, and capture policy.

## Acceptance Criteria

- [ ] No provider code is specific to editor edit-ops or DigiExam item types.
- [ ] Remote fallback is impossible unless policy says remote is allowed and
  the request explicitly opts in.
- [ ] Explicit `allow_remote_fallback=false` is treated differently from
  unspecified consent and blocks remote use.
- [ ] Provider capability flags drive JSON Schema/GBNF behavior.
- [ ] Normal logs/metrics contain only bounded metadata.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
