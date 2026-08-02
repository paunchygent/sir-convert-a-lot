---
type: story
id: ST-SIRCON-07-03
title: SOLID domain coupling audit for exam converter implementation boundaries
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-07
links:
  decisions: []
acceptance_criteria:
- Task 312 no longer carries the cross-domain audit appendix.
- A separate audit task and reference document define the broader SOLID domain-coupling
  lens beyond model/provider coupling.
- The audit classifies findings by business-policy entanglement, not by the mere existence
  of an `if` statement.
- Follow-up tasks are split by refactor boundary rather than grouped under one broad
  cleanup bucket.
- Task 315 is the next governed PDF-layout decoupling slice and preserves the boundary
  that export concerns consume IR state without changing, owning, or serializing IR/effective-IR
  state semantics. It must not re-home accepted-current-state authoring/correction
  behavior inside PDF strategies except as deleted/historical behavior until a future
  export-only request contract exists.
- Exam.net PDF item rendering policy is protocol/strategy-driven instead of centralized
  in an item-type branch ladder.
- Target readiness rows are built from typed readiness decisions rather than artifact
  availability strings and target-name branches.
- Answer-key eligibility/output-mode and source-evidence provenance mappings have
  one owned domain decision surface per concern.
retired_ids:
- story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries
---

## Context

## Epic Contract Slice

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review

## Historical Source Content

Implementation slice with acceptance-driven scope.

### Objective

Audit and remediate exam-converter places where business rules are coupled to
implementation mechanics through widening branch ladders, source-family string
checks, item-type dispatch, target-specific conditionals, or provider/output
mode details.

The story exists because Task 312 correctly extracted the answer-key candidate
planner behind a protocol, but that task is complete and scoped to provider
planning. Similar SOLID/DDD concerns need their own governed surface instead
of being appended to a completed answer-key task.

### Scope

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

### Acceptance Criteria

- [x] Task 312 no longer carries the cross-domain audit appendix.
- [x] A separate audit task and reference document define the broader SOLID
  domain-coupling lens beyond model/provider coupling.
- [x] The audit classifies findings by business-policy entanglement, not by
  the mere existence of an `if` statement.
- [x] Follow-up tasks are split by refactor boundary rather than grouped under
  one broad cleanup bucket.
- [x] Task 315 is the next governed PDF-layout decoupling slice and preserves
  the boundary that export concerns consume IR state without changing, owning,
  or serializing IR/effective-IR state semantics. It must not re-home
  accepted-current-state authoring/correction behavior inside PDF strategies
  except as deleted/historical behavior until a future export-only request
  contract exists.
- [x] Exam.net PDF item rendering policy is protocol/strategy-driven instead
  of centralized in an item-type branch ladder.
- [ ] Target readiness rows are built from typed readiness decisions rather
  than artifact availability strings and target-name branches.
- [ ] Answer-key eligibility/output-mode and source-evidence provenance
  mappings have one owned domain decision surface per concern.

### Test Requirements

- [x] Audit docs validate through the normal docs-as-code gates.
- [x] PDF renderer tests prove existing post-Task-337 rendered output,
  warnings, missing-key blockers, and unsupported-item behavior are unchanged
  after policy extraction.
- [x] PDF renderer strategy tests prove Exam.net target reshaping is isolated
  from the core PDF item protocol and does not mutate source/effective item
  semantics. Current Exam.net PDF output must not label open-cloze/`Lucktext`
  items as `Fritext`.
- [ ] Target-readiness tests prove artifact availability, item-specific
  readiness rows, removed accepted-current-state rows, and
  unsupported-target-shape rows are unchanged after policy extraction.
- [ ] Answer-key manifest and source-evidence tests prove no eligibility,
  output-mode, provenance, or manual-follow-up semantics drift.

### Done Definition

This story is done when the first audit is documented, the highest-priority
business-policy branch hotspots are refactored behind explicit domain
protocols or strategies, and the remaining medium-priority observations are
either converted into governed tasks or deliberately retained with rationale.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
