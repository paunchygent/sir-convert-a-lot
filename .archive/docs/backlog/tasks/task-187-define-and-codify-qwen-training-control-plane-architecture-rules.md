---
id: task-187-define-and-codify-qwen-training-control-plane-architecture-rules
title: Define and codify Qwen training control-plane architecture rules
type: task
status: completed
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - .codex/rules/095-qwen-training-architecture-boundaries.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - .codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md
labels:
  - qwen
  - architecture
  - rules
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make the Qwen training control-plane architecture policy explicit and
non-optional so future changes cannot silently reintroduce god files or mixed
concerns.

## PR Scope

- Add one dedicated repo rule for Qwen training/control-plane architecture.
- Update Story 28, Story 26, `T186`, Epic 08, the runbook, the Qwen skill, and
  `current.md` so architecture hardening is tracked as a first-class blocker.
- Define the stricter `400` LoC cap and DRY/SOLID/SRP/DDD expectations for this
  lane.

## Deliverables

- [x] `RULE-095` exists and is indexed from `000-rule-index.md`.
- [x] Story 28 and `T187-T191` are fully linked from the active Qwen backlog.
- [x] Operator/docs surfaces explicitly say new feature work must not grow the
  current god files further.

## Acceptance Criteria

- [x] The backlog and repo rules agree on the new architecture lane and
  sequencing.
- [x] The runbook and skill mention the canonical control-plane architecture
  path and the no-shim/no-compat-wrapper rule.
- [x] `current.md` records Story 28 as the architecture blocker for future Task
  101 control-plane work.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
