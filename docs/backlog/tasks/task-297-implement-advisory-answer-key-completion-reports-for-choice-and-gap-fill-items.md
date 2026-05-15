---
id: task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items
title: Implement advisory answer-key completion reports for choice and gap-fill items
type: task
status: completed
priority: high
created: '2026-05-14'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
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
- Consume Task 305's gapped/open-cloze accepted-value contract for gap-fill
  candidate/report shape; do not invent a provider-only answer-key structure.
- Validate model output strictly and convert invalid output to manual follow-up.
- Emit `answer_key_completion_report` with bounded metadata and per-item
  decisions.
- Encode LLM output as candidate lineage metadata, not answer-key provenance.
  Advisory report entries must identify candidate IDs, candidate payload
  digests, provider profile, schema version, prompt-template version, backend
  status, and validation state without storing raw prompts, raw provider
  responses, or source/parser provenance claims.
- Compute candidate payload digests from the canonical backend-validated
  candidate payload only. Do not digest raw provider responses, raw prompts, or
  pre-validation payloads for the public report contract.
- Preserve a shared downstream contract for reviewed application: teacher
  acceptance unchanged can later apply a reviewed effective key with lineage to
  the candidate; teacher edits can later apply a teacher-provided effective key
  with lineage noting the candidate as the starting point.
- Do not emit `effective_ir_json` changes from LLM completion in this slice.

## Deliverables

- [x] Candidate builders for choice and gap-fill.
- [x] Output specs and validators.
- [x] Completion orchestrator for advisory mode.
- [x] Completion report artifact and manifest wiring with candidate lineage
  metadata.
- [x] Focused tests with mock provider responses.

## Acceptance Criteria

- [x] Source IR, effective IR, Exam.net PDF, and QTI package remain unchanged by
  advisory completion.
- [x] Reports never contain raw prompts, raw provider responses, student data,
  raw `.dxe`, result PDF content, or owner metadata.
- [x] Reports never classify model output as `source_provided`,
  `teacher_provided`, `reviewed`, parser evidence, or aggregate `mixed`
  matching provenance. They expose only advisory candidate lineage and backend
  validation state.
- [x] The aggregate `mixed` prohibition in this task is matching-specific:
  gapped/open-cloze application may later derive a `mixed` summary from
  per-accepted-value provenance under Task 305/306, but Task 297 still emits
  only advisory candidates and no answer-key provenance.
- [x] Candidate lineage is sufficient for Task 306 to distinguish accepted
  unchanged LLM candidates from teacher-edited candidates without changing
  source/parser provenance.
- [x] Unsupported or ambiguous items produce manual follow-up.
- [x] Existing manual follow-up semantics remain visible to Skriptoteket.
- [x] Route defaults still make no LLM calls.

## Implementation Evidence

Implemented in:

- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion_candidates.py`
- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion.py`
- `scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion_contracts.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py`
- `scripts/sir_convert_a_lot/application/openapi_contracts_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_openapi_contract_v2.py`

The advisory mode now accepts
`local_llm_suggest_missing_machine_marked`, builds item-local structured
requests for missing choice and gap-fill keys, and writes
`answer-key-completion-report.json` only when requested. It does not apply
candidate output to source IR, effective IR, Exam.net PDF, or QTI. The bundle
manifest marks `answer_key_completion_report` as `not_requested` on default
`source_evidence_only` requests.

Report items carry candidate lineage fields only: candidate ID, canonical
candidate payload digest, provider profile, model profile, output schema,
prompt-template version, backend status, backend failure code, and validation
state. Raw prompts, raw provider responses, source/parser provenance claims,
student data, owner metadata, raw `.dxe`, and result-PDF content are excluded.

Generated OpenAPI v2 now publishes
`DigiExamAnswerKeyCompletionReportV1` and the
`answer_key_completion_report` contract component mapping. Consumer tests assert
against centralized schema-version constants rather than copied literals.

Validation evidence:

- `pdm run openapi-export-v2`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_advisory_completion_report_does_not_mutate_artifacts tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_default_artifact_route_does_not_call_structured_llm tests/sir_convert_a_lot/test_openapi_contract_v2.py`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
