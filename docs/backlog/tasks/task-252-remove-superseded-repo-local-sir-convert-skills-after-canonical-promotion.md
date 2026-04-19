---
id: task-252-remove-superseded-repo-local-sir-convert-skills-after-canonical-promotion
title: Remove superseded repo-local Sir Convert skills after canonical promotion
type: task
status: completed
priority: high
created: '2026-04-18'
last_updated: '2026-04-18'
related:
  - AGENTS.md
  - .codex/skills/README.md
  - /Users/olofs_mba/Documents/Repos/skill-repository/docs/backlog/tasks/task-0050-audit-and-promote-sir-convert-skill-scopes-into-branched-canonical-skills.md
labels:
  - skills
  - codex
  - governance
---

PR-sized execution unit; may be linked to a story or standalone.

## Context

`skill-repository` `TASK-0050` promoted the cross-repo Sir Convert client
workflow into a canonical global skill and folded Sir Convert docs, planning,
and handoff guidance into shared action-skill references. This task is the
Sir Convert repo-side cleanup so the local skill folder no longer preserves
superseded duplicates or instructions to globally symlink repo-local skills.

## Objective

Remove Sir Convert-a-Lot repo-local skill folders that are now covered by
canonical `skill-repository` skills, without deleting repo-local Qwen, Colab,
Hemma, or speech-training guidance that remains local.

## PR Scope

- Remove local duplicates for the promoted cross-repo conversion client and
  the folded PDF-to-Markdown route skill.
- Remove local docs-governance and session-handoff action skills now covered
  by shared global action skills with Sir Convert references.
- Update repo entrypoint and local skill index only enough to prevent agents
  from recreating repo-local global symlink shims.

## Deliverables

- [x] Superseded local skill folders removed.
- [x] `AGENTS.md` distinguishes retained local skills from canonical global
  shared skills.
- [x] `.codex/skills/README.md` records local-only skill ownership and the
  no-global-symlink policy for repo-local skills.

## Acceptance Criteria

- [x] `.codex/skills/sir-convert-a-lot-client` is absent locally because the
  canonical global skill lives in `skill-repository`.
- [x] `.codex/skills/sir-convert-a-lot-pdf-to-md` is absent locally because it
  is folded into the canonical client skill.
- [x] `.codex/skills/sir-convert-a-lot-docs-governance` and
  `.codex/skills/sir-convert-a-lot-session-handoff` are absent locally
  because shared action skills carry Sir Convert references.
- [x] Remaining local skills pass `pdm run skills-validate`.
- [x] No global symlink points to `sir-convert-a-lot/.codex/skills`.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- `pdm run skills-validate`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- local `.codex/skills` symlink audit found no symlinks
- global symlink audit for `sir-convert-a-lot/.codex/skills` targets
- `git diff --check`
