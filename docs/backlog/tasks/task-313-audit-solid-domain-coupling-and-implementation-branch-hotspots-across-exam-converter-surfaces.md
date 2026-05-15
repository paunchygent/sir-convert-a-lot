---
id: task-313-audit-solid-domain-coupling-and-implementation-branch-hotspots-across-exam-converter-surfaces
title: Audit SOLID domain coupling and implementation-branch hotspots across exam converter surfaces
type: task
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries.md
  - docs/backlog/tasks/task-312-make-answer-key-candidate-planning-provider-protocol-driven.md
  - docs/backlog/tasks/task-315-extract-exam-net-pdf-item-rendering-policy-strategies-from-item-type-branch-ladder.md
  - docs/backlog/tasks/task-316-extract-target-readiness-policy-decisions-from-artifact-availability-and-target-string-branches.md
  - docs/backlog/tasks/task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters.md
  - docs/reference/ref-exam-converter-solid-domain-coupling-audit.md
labels:
  - solid
  - ddd
  - exam-converter
  - audit
  - refactor
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Document a governed audit of SOLID refactoring opportunities where exam
converter business logic is entangled with implementation-specific branch
mechanics.

This task is deliberately separate from completed Task 312. Task 312 is the
provider-protocol implementation slice; this task records the broader audit
surface across exam converter rendering, readiness, answer-key eligibility,
and source-evidence mapping.

## PR Scope

- Remove the misplaced cross-domain audit appendix from Task 312.
- Create a story for SOLID domain-coupling audit and remediation work.
- Create a reference document that records the audit definition, code evidence,
  prioritized findings, non-findings, and suggested refactor boundaries.
- Create PR-sized follow-up tasks for the high-priority findings.
- Do not implement behavior changes in this task.

## Deliverables

- [x] Task 312 restored to its completed provider-planner scope.
- [x] Story 50 created for SOLID domain-coupling audit/remediation.
- [x] Reference audit created at
  `docs/reference/ref-exam-converter-solid-domain-coupling-audit.md`.
- [x] Follow-up tasks created for PDF item policy extraction, target readiness
  policy extraction, and answer-key/source-evidence decision reuse.

## Acceptance Criteria

- [x] The audit scope covers domain business-policy coupling broadly, not only
  model/provider coupling.
- [x] Findings cite concrete code surfaces and distinguish high-priority
  refactors from acceptable local guards or infrastructure adapter branches.
- [x] Each high-priority finding maps to a governed follow-up task with clear
  stop conditions.
- [x] The reference doc gives enough context for the next implementer to pick a
  refactor boundary without rediscovering the audit.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
