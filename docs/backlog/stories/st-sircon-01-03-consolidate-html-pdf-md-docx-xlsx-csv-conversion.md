---
type: story
id: ST-SIRCON-01-03
title: Consolidate html/pdf/md/docx/xlsx/csv conversion capabilities
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-01
links:
  decisions: []
acceptance_criteria:
- Capability matrix exists and maps all listed formats to canonical operations.
- Each existing converter script is classified as a platform implementation, compatibility
  wrapper, or deprecated/removed.
- Consumer repositories use canonical CLI/API and stop adding ad hoc converter ownership.
- Migration notes exist for renamed or replaced commands.
- Post-stabilization cleanup is executed per gate in task 002 phase 6.
retired_ids:
- 003d-multi-format-converter-consolidation-story
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

### Objective

Subsume current conversion scripts into one cohesive and versioned service/CLI surface that supports html, pdf, md, docx, xlsx, and csv workflows without repo-specific ad hoc implementations.

### Scope

- Define canonical command/API coverage map for all in-scope formats.
- Migrate existing scripts to platform-owned implementations or thin compatibility wrappers.
- Define deprecation/removal plan for redundant scripts after stabilization.

### Acceptance Criteria

1. Capability matrix exists and maps all listed formats to canonical operations.
1. Each existing converter script is classified as:

- platform implementation,
- compatibility wrapper,
- deprecated/removed.

3. Consumer repositories use canonical CLI/API and stop adding ad hoc converter ownership.
1. Migration notes exist for renamed/replaced commands.
1. Post-stabilization cleanup is executed per gate in task 002 phase 6.

### Test Requirements

- Format-specific regression tests for all in-scope formats.
- Backward compatibility tests for retained wrapper commands.
- Negative tests for unsupported/invalid conversion route requests.

### Done Definition

- Canonical platform owns conversion behavior for all in-scope formats.
- Redundant implementations are removed or reduced to wrappers with explicit deprecation timeline.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
