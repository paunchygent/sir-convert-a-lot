---
id: 'story-47-structured-llm-provider-harness-for-answer-key-completion'
title: 'Structured LLM provider harness for answer-key completion'
type: 'story'
status: 'proposed'
priority: 'high'
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-298-implement-reviewed-answer-key-completion-application-and-matching-ir-v3-gate.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
labels:
  - llm
  - structured-output
  - local-first
  - answer-key-completion
  - provider-policy
---
Implementation slice with acceptance-driven scope.

## Objective

Create a generic structured-output provider harness for item-local answer-key
completion while reusing the shape of Skriptoteket's local-first provider set,
budgeting, Dishka wiring, and remote fallback policy where appropriate.

## Scope

- Introduce `StructuredChatProviderProtocol`, `StructuredOutputSpec`,
  `StructuredLLMResponse`, and `StructuredChatProviderSet` separate from
  editor edit-ops.
- Support configured endpoint kinds for Chat Completions, Responses, and local
  llama.cpp-compatible chat completions.
- Keep provider capabilities explicit: JSON Schema, GBNF, remote/local, context
  window, output-token budget, parser profile, and health.
- Define item-type-specific output schemas for choice, gap-fill, and matching.
- Reuse Skriptoteket's budgeting idea: context window minus max output tokens
  minus safety margin, with conservative fallback for unknown/local tokenizers.
- Implement route policy where remote provider fallback is forbidden by default
  and explicit false is terminal.
- Keep production capture metadata-only unless a separate governed evaluation
  mode is added.

## Acceptance Criteria

- [ ] Provider code is generic structured output, not edit-op-specific.
- [ ] Chat Completions and Responses payload builders keep their schema shapes
  separate.
- [ ] Local llama.cpp support is capability-configured and does not infer GBNF
  or JSON Schema support from host/port.
- [ ] The completion prompt is single-turn and item-local with no full exam,
  result PDF, raw `.dxe`, student data, owner metadata, or artifact paths.
- [ ] Over-budget items are not sent to a provider and produce
  `manual_follow_up_required` with backend failure code `over_budget`.
- [ ] Provider failure, invalid JSON, schema mismatch, unknown IDs, duplicate
  IDs, or invalid answer payloads become manual follow-up with backend-owned
  failure codes.
- [ ] Remote fallback is attempted only when authenticated/signed policy allows
  it and the request explicitly opts in.

## Test Requirements

- [ ] Unit tests cover Chat Completions, Responses, and llama.cpp payload
  construction for the same output spec.
- [ ] Budget tests cover OpenAI-family, Mistral/Devstral-family, and unknown
  tokenizer resolver paths.
- [ ] Routing tests cover local primary success, local unavailable with local
  fallback, remote fallback forbidden, explicit false, missing consent, and
  allowed signed consent.
- [ ] Capture tests prove raw prompts/responses and item text are not persisted
  in normal production mode.

## Done Definition

This story is done when Sir Convert has a reusable structured provider harness
that can serve answer-key completion without binding provider mechanics to the
DigiExam parser, renderers, or artifact routes.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
