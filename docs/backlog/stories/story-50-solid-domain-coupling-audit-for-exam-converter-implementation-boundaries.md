---
id: story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries
title: SOLID domain coupling audit for exam converter implementation boundaries
type: story
status: in_progress
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-312-make-answer-key-candidate-planning-provider-protocol-driven.md
  - docs/backlog/tasks/task-313-audit-solid-domain-coupling-and-implementation-branch-hotspots-across-exam-converter-surfaces.md
  - docs/backlog/tasks/task-315-extract-exam-net-pdf-item-rendering-policy-strategies-from-item-type-branch-ladder.md
  - docs/backlog/tasks/task-316-extract-target-readiness-policy-decisions-from-artifact-availability-and-target-string-branches.md
  - docs/backlog/tasks/task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters.md
  - docs/reference/ref-exam-converter-solid-domain-coupling-audit.md
labels:
  - solid
  - ddd
  - exam-converter
  - refactor
  - target-policy
---

Implementation slice with acceptance-driven scope.

## Objective

Audit and remediate exam-converter places where business rules are coupled to
implementation mechanics through widening branch ladders, source-family string
checks, item-type dispatch, target-specific conditionals, or provider/output
mode details.

The story exists because Task 312 correctly extracted the answer-key candidate
planner behind a protocol, but that task is complete and scoped to provider
planning. Similar SOLID/DDD concerns need their own governed surface instead
of being appended to a completed answer-key task.

## Scope

- Define the audit lens for SOLID domain coupling in exam converter code:
  branches are findings when domain policy, target capability, provenance, or
  implementation construction are entangled so that adding a new item type,
  source family, target, or output mode changes several unrelated functions.
- Treat export policy as a consumer of IR/effective-IR state, never as an owner
  of IR state. Target renderers may read item semantics, provenance, accepted
  authoring corrections, and target-readiness inputs, but layout, target
  support, warning wording, artifact availability, and degraded/manual export
  choices must stay outside parser/source/effective-IR contracts.
- Treat `accept_current_state_for_export` as historical/current runtime behavior
  slated for removal from authoring/correction state by Task 337. Future
  incomplete or best-effort export, if approved, must be represented as
  target-specific export request policy, not as source IR, effective IR,
  ingestion overlay, or correction replay state.
- Document the first audit pass in a reference doc with explicit code evidence,
  priority, non-findings, and recommended protocol or strategy boundaries.
- Refactor high-priority hotspots only through follow-up PR-sized tasks.
- Keep normal validation guards, parser-local extraction checks, and
  infrastructure adapter mechanics out of scope unless they begin making exam
  business-policy decisions.

## Acceptance Criteria

- [x] Task 312 no longer carries the cross-domain audit appendix.
- [x] A separate audit task and reference document define the broader SOLID
  domain-coupling lens beyond model/provider coupling.
- [x] The audit classifies findings by business-policy entanglement, not by
  the mere existence of an `if` statement.
- [x] Follow-up tasks are split by refactor boundary rather than grouped under
  one broad cleanup bucket.
- [ ] Task 315 is the next governed PDF-layout decoupling slice and preserves
  the boundary that export concerns consume IR state without changing, owning,
  or serializing IR/effective-IR state semantics. It must not re-home
  accepted-current-state authoring/correction behavior inside PDF strategies
  except as deleted/historical behavior until a future export-only request
  contract exists.
- [ ] Exam.net PDF item rendering policy is protocol/strategy-driven instead
  of centralized in an item-type branch ladder.
- [ ] Target readiness rows are built from typed readiness decisions rather
  than artifact availability strings and target-name branches.
- [ ] Answer-key eligibility/output-mode and source-evidence provenance
  mappings have one owned domain decision surface per concern.

## Test Requirements

- [x] Audit docs validate through the normal docs-as-code gates.
- [ ] PDF renderer tests prove existing post-Task-337 rendered output,
  warnings, missing-key blockers, and unsupported-item behavior are unchanged
  after policy extraction.
- [ ] PDF renderer strategy tests prove Exam.net target reshaping is isolated
  from the core PDF item protocol and does not mutate source/effective item
  semantics, even when gap/open-cloze items are presented in a target-compatible
  free-text-style shape.
- [ ] Target-readiness tests prove artifact availability, item-specific
  readiness rows, accepted-current-state rows, and unsupported-target-shape
  rows are unchanged after policy extraction.
- [ ] Answer-key manifest and source-evidence tests prove no eligibility,
  output-mode, provenance, or manual-follow-up semantics drift.

## Done Definition

This story is done when the first audit is documented, the highest-priority
business-policy branch hotspots are refactored behind explicit domain
protocols or strategies, and the remaining medium-priority observations are
either converted into governed tasks or deliberately retained with rationale.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
