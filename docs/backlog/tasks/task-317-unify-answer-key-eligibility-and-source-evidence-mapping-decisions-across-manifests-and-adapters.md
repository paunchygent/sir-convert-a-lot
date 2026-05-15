---
id: task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters
title: Unify answer-key eligibility and source-evidence mapping decisions across manifests and adapters
type: task
status: proposed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-312-make-answer-key-candidate-planning-provider-protocol-driven.md
  - docs/backlog/tasks/task-313-audit-solid-domain-coupling-and-implementation-branch-hotspots-across-exam-converter-surfaces.md
  - docs/reference/ref-exam-converter-solid-domain-coupling-audit.md
  - scripts/sir_convert_a_lot/domain/digiexam_answer_key_live_validation_manifest.py
  - scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion_candidates.py
  - scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py
  - scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py
labels:
  - solid
  - ddd
  - exam-converter
  - answer-key-completion
  - provenance
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Unify duplicated answer-key eligibility/output-mode classification and typed
source-evidence provenance mapping so manifests and adapters consume explicit
domain decision surfaces instead of repeating string and item-type checks.

This task follows Task 312 without reopening Task 312. The provider planner now
owns per-item provider request shape; the remaining drift risk is that Task 309
manifest planning and source-evidence adapters can classify the same domain
state through separate branch logic.

## PR Scope

- Expose one answer-key candidate eligibility/output-mode classifier consumed
  by both live execution planning and the Task 309 validation manifest.
- Preserve Task 309 manifest fields and counts while deriving them from the
  shared decision surface.
- Introduce a typed source-evidence family/provenance mapper for DigiExam DXE,
  graded-result PDF correct labels, teacher overlay, and reviewed completion
  evidence.
- Replace scattered source-family string-to-provenance mapping checks in gap
  contracts and DigiExam authoring adapters with the mapper.
- Do not change parser provenance semantics, advisory report privacy,
  effective IR application, or renderer output.

## Deliverables

- [ ] Shared answer-key candidate eligibility/output-mode classifier.
- [ ] Task 309 manifest generation wired to the shared classifier.
- [ ] Typed source-evidence family/provenance mapper.
- [ ] Adapter and gap-contract tests proving existing classifications are
  unchanged.

## Acceptance Criteria

- [ ] Choice, multiple-response, and gap-fill eligibility are classified in
  one domain service or policy object rather than duplicated in manifest code.
- [ ] Task 309 output-mode counts still distinguish vLLM choice from JSON
  Schema exactly as the governed planner policy requires.
- [ ] Adding a new source-evidence family requires changing one mapper, not
  multiple string-check helpers.
- [ ] LLM completion lineage remains candidate metadata and never becomes
  parser/source provenance.
- [ ] No raw prompt, provider response, item text, alternative text, or gap text
  is introduced into retained artifacts.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
