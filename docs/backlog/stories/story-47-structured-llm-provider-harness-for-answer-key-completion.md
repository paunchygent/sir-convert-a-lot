---
id: story-47-structured-llm-provider-harness-for-answer-key-completion
title: Structured LLM provider harness for answer-key completion
type: story
status: in_progress
priority: high
created: '2026-05-14'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-310-add-validation-only-force-eval-mode-for-source-keyed-answer-key-live-validation.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/backlog/tasks/task-312-make-answer-key-candidate-planning-provider-protocol-driven.md
  - docs/backlog/tasks/task-318-make-task-309-eval-provider-metadata-profile-driven.md
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
- Define item-type-specific output schemas for choice, gap-fill, and matching,
  consuming Task 298 and Task 305 contract shapes for matching pairs and
  gapped/open-cloze accepted values rather than inventing provider-only
  structures.
- Reuse Skriptoteket's budgeting idea: context window minus max output tokens
  minus safety margin, with conservative fallback for unknown/local tokenizers.
- Implement route policy where remote provider fallback is forbidden by default
  and explicit false is terminal.
- Keep production capture metadata-only unless a separate governed evaluation
  mode is added.

## Current Implementation State

Task 296 is completed. Sir Convert now has the reusable structured provider
core: source-neutral contracts, provider profiles/capabilities, local-first
routing policy, token-budget preflight, metadata-only capture, payload builders
for Chat Completions, Responses, llama.cpp JSON Schema/GBNF, and vLLM
structured choice, async HTTP provider execution, response
parsing/failure-mapping, service settings loading, and opt-in Dishka
composition.

Task 297 is completed. The DigiExam migration bundle route now supports the
opt-in `local_llm_suggest_missing_machine_marked` completion mode for advisory
choice and gap-fill answer-key candidates. The default `source_evidence_only`
route still makes no structured LLM calls and keeps
`answer_key_completion_report` as `not_requested`. Advisory mode writes a
candidate-lineage `answer-key-completion-report.json` artifact only when
requested, validates backend output strictly, and leaves source IR, effective
IR, Exam.net PDF, and QTI unchanged.

Task 312 is the provider-protocol correction required before Task 309 live
validation. It keeps answer-key orchestration provider-neutral by injecting a
candidate planner. The Granite/vLLM planner selects bounded
`structured_outputs.choice` for choice and multiple-response rows, while using
vLLM JSON Schema for gap-fill rows. Generic providers keep the JSON
Schema-backed planner.

Task 309 is the proposed live-validation checkpoint for the completed harness
and advisory path. It validates the interim Granite FP8/vLLM provider on Hemma
against a versioned pure DigiExam DXE corpus before the deferred Task 300
comparative model bake-off. MCQ/MCW live requests should prefer vLLM `choice`
values when candidate selection is clear and bounded; JSON Schema remains part
of provider microprobes and gap-fill object validation. Task 310 and Task 311
then separate validation-only force-eval from the strict service-backed
auth/public-edge mirror.

Task 318 is the follow-up for eval evidence alignment after the Qwen3.6
llama.cpp validation exposed that `evaluate-advisory-corpus` still reconstructed
Granite metadata from defaults. Provider-run metadata must be profile-driven
from the selected provider/default object so model changes inject runtime,
sampling, output-mode, capability, and vision media-path settings without
model-name branches in the evaluator.

## Acceptance Criteria

- [x] Provider code is generic structured output, not edit-op-specific.
- [x] Chat Completions and Responses payload builders keep their schema shapes
  separate.
- [x] Local llama.cpp support is capability-configured and does not infer GBNF
  or JSON Schema support from host/port.
- [x] The completion prompt is single-turn and item-local with no full exam,
  result PDF, raw `.dxe`, student data, owner metadata, or artifact paths.
- [x] Over-budget items are not sent to a provider and produce
  `manual_follow_up_required` with backend failure code `over_budget`.
- [x] Provider failure, invalid JSON, schema mismatch, unknown IDs, duplicate
  IDs, or invalid answer payloads become manual follow-up with backend-owned
  failure codes.
- [x] Remote fallback is attempted only when authenticated/signed policy allows
  it and the request explicitly opts in.

## Test Requirements

- [x] Unit tests cover Chat Completions, Responses, and llama.cpp payload
  construction for the same output spec.
- [ ] Budget tests cover OpenAI-family, Mistral/Devstral-family, and unknown
  tokenizer resolver paths.
- [x] Routing tests cover local primary success, local unavailable with local
  fallback, remote fallback forbidden, explicit false, missing consent, and
  allowed signed consent.
- [x] Capture tests prove raw prompts/responses and item text are not persisted
  in normal production mode.

## Done Definition

This story is done when Sir Convert has a reusable structured provider harness
that can serve answer-key completion without binding provider mechanics to the
DigiExam parser, renderers, or artifact routes.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
