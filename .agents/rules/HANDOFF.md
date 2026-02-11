---
trigger: model_decision
rule_id: RULE-HANDOFF
title: Rules Handoff Notes
status: active
created: 2026-02-11
updated: 2026-02-11
owners:
  - platform
tags:
  - handoff
scope: repo
---
# Rule Handoff Notes

## 2026-02-11

- Migrated Sir Convert-a-Lot from monorepo context to standalone repository.
- Rehomed agent process artifacts from `.claude`/`.windsurf` style to `.agents/`.
- Established canonical rules index and docs-as-code standards for standalone operation.
- Added contract enforcement for YAML frontmatter across `docs/` and `.agents/rules/`.
- Added repo-specific Hemma/GPU DevOps runbook and skill.
