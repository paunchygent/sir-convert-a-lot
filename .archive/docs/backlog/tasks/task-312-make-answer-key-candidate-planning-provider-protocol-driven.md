---
id: task-312-make-answer-key-candidate-planning-provider-protocol-driven
title: Make answer-key candidate planning provider-protocol driven
type: task
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
labels:
  - answer-key-completion
  - structured-output
  - provider-policy
  - vllm
  - granite
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make DigiExam answer-key candidate planning provider-protocol driven before
Task 309 runs live validation against Granite/vLLM.

The current advisory path builds one JSON Schema-shaped provider request for
choice and gap-fill items. That proves the generic harness, but it is not the
right Task 309 production shape: Granite through vLLM should use bounded
`structured_outputs.choice` for clear candidate-selection rows and JSON Schema
for gap-fill rows. The same provider/model service must therefore support
per-item output contracts without hard-coding Granite/vLLM branches into the
generic answer-key orchestration.

## PR Scope

- Introduce an answer-key candidate planner protocol that returns the
  item-local provider request, the provider profile to use for that item, and a
  decoder from provider-native response content into the stable advisory answer
  payload.
- Add a Granite/vLLM planner selected by endpoint/capability contract, not by
  ad hoc model-name checks. It must use bounded vLLM choice values for
  supported choice and multiple-response rows, and vLLM JSON Schema for
  gap-fill rows.
- Keep a generic JSON Schema planner for provider profiles that do not support
  vLLM structured choice.
- Keep eligibility, budget checks, route policy, manual-follow-up behavior, and
  the `answer_key_completion_report_v1` artifact contract unchanged.
- Keep raw prompt text and raw provider responses out of retained report
  artifacts.
- Preserve advisory-mode immutability: source IR and effective IR are not
  mutated by candidate planning or provider execution.

## Deliverables

- [x] Provider-protocol driven candidate planner interface.
- [x] Granite/vLLM hybrid planner for per-item choice versus gap JSON Schema
  behavior.
- [x] Generic JSON Schema planner for non-vLLM provider profiles.
- [x] Advisory orchestration wired to injected/default planner selection.
- [x] Focused tests proving vLLM choice request construction and decoding for
  choice rows, JSON Schema request construction for gap rows, and unchanged
  report privacy/manual-follow-up behavior.

## Acceptance Criteria

- [x] The answer-key orchestration does not branch on Granite/vLLM details; it
  consumes a planner protocol.
- [x] The planner can select a provider profile/output mode per item while
  keeping the configured provider connection/service stable.
- [x] Granite/vLLM choice rows use `StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE`
  and an output spec with bounded `choice_values`.
- [x] Granite/vLLM gap-fill rows use `StructuredLLMOutputMode.VLLM_JSON_SCHEMA`
  and the existing gap-fill JSON Schema decision object.
- [x] Multiple-response rows are represented as bounded candidate selections
  rather than free JSON whenever the candidate-set enumeration is tractable.
- [x] Provider-native choice responses decode into the stable advisory
  `{"kind": "choice", "correct_alternative_ids": [...]}` answer payload before
  report construction.
- [x] Invalid provider-native choice values become manual follow-up and are not
  counted as valid suggestions.
- [x] Normal production reports still contain no raw prompts, raw provider
  responses, item text, alternative text, or gap text.
- [x] The implementation is suitable for Task 309 live validation and does not
  enable force-eval or service-backed auth/public-edge mirror behavior.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Added `DigiExamAnswerKeyCandidatePlannerProtocol` and response decoders in
  `digiexam_answer_key_completion_candidates.py`.
- Added a Granite/vLLM planner selected by endpoint/capabilities. It derives
  per-item provider profiles: `vllm_structured_choice` for bounded choice and
  multiple-response rows, `vllm_json_schema` for gap-fill rows.
- Kept a generic JSON Schema planner for non-vLLM provider profiles.
- Wired `build_digiexam_answer_key_completion_report` to consume an injected
  planner or select the default planner from the selected provider profile.
- Preserved advisory report shape and metadata-only retention. Provider-native
  choice responses decode into stable answer payloads before report
  construction.

## Validation Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_structured_llm_provider_harness.py tests/sir_convert_a_lot/test_structured_llm_provider_execution.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py tests/sir_convert_a_lot/test_structured_llm_provider_harness.py tests/sir_convert_a_lot/test_structured_llm_provider_execution.py tests/sir_convert_a_lot/test_digiexam_answer_key_live_validation_manifest.py`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
