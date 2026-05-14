---
id: 'task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items'
title: 'Implement advisory answer-key completion reports for choice and gap-fill items'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
labels:
  - llm
  - advisory
  - answer-key-completion
  - choice
  - gap-fill
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first safe completion mode:
`local_llm_suggest_missing_machine_marked`, producing advisory reports for
missing choice and gap-fill answer keys without changing renderer input.

## PR Scope

- Build item-local candidate inputs for single choice, multiple choice,
  multiple response, and gap-fill items after source parse and optional teacher
  overlay.
- Skip items with source-bound answer keys, unreliable structure, unsupported
  assets, unsupported item types, or budget overflow.
- Add item-type-specific output schemas for choice and gap-fill decisions.
- Validate model output strictly and convert invalid output to manual follow-up.
- Emit `answer_key_completion_report` with bounded metadata and per-item
  decisions.
- Do not emit `effective_ir_json` changes from LLM completion in this slice.

## Deliverables

- [ ] Candidate builders for choice and gap-fill.
- [ ] Output specs and validators.
- [ ] Completion orchestrator for advisory mode.
- [ ] Completion report artifact and manifest wiring.
- [ ] Focused tests with mock provider responses.

## Acceptance Criteria

- [ ] Source IR, effective IR, Exam.net PDF, and QTI package remain unchanged by
  advisory completion.
- [ ] Reports never contain raw prompts, raw provider responses, student data,
  raw `.dxe`, result PDF content, or owner metadata.
- [ ] Unsupported or ambiguous items produce manual follow-up.
- [ ] Existing manual follow-up semantics remain visible to Skriptoteket.
- [ ] Route defaults still make no LLM calls.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
