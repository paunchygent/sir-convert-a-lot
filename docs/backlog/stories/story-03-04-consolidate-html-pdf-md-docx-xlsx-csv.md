---
id: 003d-multi-format-converter-consolidation-story
title: Consolidate html/pdf/md/docx/xlsx/csv conversion capabilities
type: story
status: proposed
priority: high
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md
labels:
  - consolidation
  - multi-format
  - platform
---

## Objective

Subsume current conversion scripts into one cohesive and versioned service/CLI surface that supports html, pdf, md, docx, xlsx, and csv workflows without repo-specific ad hoc implementations.

## Scope

- Define canonical command/API coverage map for all in-scope formats.
- Migrate existing scripts to platform-owned implementations or thin compatibility wrappers.
- Define deprecation/removal plan for redundant scripts after stabilization.

## Acceptance Criteria

1. Capability matrix exists and maps all listed formats to canonical operations.
1. Each existing converter script is classified as:

- platform implementation,
- compatibility wrapper,
- deprecated/removed.

3. Consumer repositories use canonical CLI/API and stop adding ad hoc converter ownership.
1. Migration notes exist for renamed/replaced commands.
1. Post-stabilization cleanup is executed per gate in task 002 phase 6.

## Test Requirements

- Format-specific regression tests for all in-scope formats.
- Backward compatibility tests for retained wrapper commands.
- Negative tests for unsupported/invalid conversion route requests.

## Done Definition

- Canonical platform owns conversion behavior for all in-scope formats.
- Redundant implementations are removed or reduced to wrappers with explicit deprecation timeline.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
