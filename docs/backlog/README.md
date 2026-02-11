---
id: 'backlog-readme'
title: 'Backlog Guide'
type: 'reference'
status: 'active'
priority: 'medium'
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - 'docs/_meta/docs-contract.yaml'
  - 'docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md'
labels:
  - 'planning'
  - 'guide'
---
# Backlog Guide

## Purpose

`docs/backlog/` is the canonical planning source of truth for Sir Convert-a-Lot.

## Planning Hierarchy Invariant

- `programme` for cross-cutting work.
- `epic` for major capability increments.
- `story` for implementation slices.
- `task` for PR-sized execution units that may be linked to a story or standalone.

## Directory Layout

- `docs/backlog/programmes/`
- `docs/backlog/epics/`
- `docs/backlog/stories/`
- `docs/backlog/tasks/`
- `docs/backlog/reviews/`
- `docs/backlog/current.md`

## Commands

- `pdm run new-programme "<title>"`
- `pdm run new-epic "<title>"`
- `pdm run new-story "<title>"`
- `pdm run new-task "<title>"`
- `pdm run new-review "<title>"`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
