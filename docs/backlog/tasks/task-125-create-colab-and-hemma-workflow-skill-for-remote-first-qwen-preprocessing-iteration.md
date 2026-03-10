---
id: 'task-125-create-colab-and-hemma-workflow-skill-for-remote-first-qwen-preprocessing-iteration'
title: 'Create Colab and Hemma workflow skill for remote-first Qwen preprocessing iteration'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-10'
last_updated: '2026-03-10'
related:
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - skills
  - qwen
  - colab
  - hemma
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add a repo-local workflow skill that makes Colab notebook orchestration and
Hemma-first repo iteration explicit for the Qwen preprocessing lane, so future
sessions default to editing, committing, and pushing from Hemma when the
execution environment is Hemma-backed.

## PR Scope

- Create one repo-local skill for Sir Convert-a-Lot Colab/Hemma workflow
  decisions.
- Encode the Hemma-first edit/commit/push rule for Hemma-backed execution
  slices.
- Cross-link the new skill from the existing skill/runbook surfaces that govern
  Qwen Colab work.
- Make the skill globally visible through the local Codex skill registry.

## Deliverables

- [x] One repo-local skill that covers Colab orchestration and Hemma-backed
      repo iteration.
- [x] One completed task doc describing the workflow rule and expected use.
- [x] One repo docs/skill update that points future Qwen Colab work at the new
      workflow rule.
- [x] One global-symlink registration step for future skill discovery.

## Acceptance Criteria

- [x] Future sessions have one named skill to use for Colab notebook and
      Hemma-backed workflow decisions.
- [x] The skill explicitly states that Hemma-backed execution lanes should be
      edited, committed, and pushed from Hemma.
- [x] The skill keeps Colab positioned as an orchestrator around committed
      repo-owned commands.
- [x] The skill is visible from the local repo and eligible for global skill
      discovery.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
