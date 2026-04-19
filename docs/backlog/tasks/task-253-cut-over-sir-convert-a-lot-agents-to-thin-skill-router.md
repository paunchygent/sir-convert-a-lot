---
id: task-253-cut-over-sir-convert-a-lot-agents-to-thin-skill-router
title: Cut over Sir Convert-a-Lot AGENTS to thin skill router
type: task
status: proposed
priority: high
created: '2026-04-18'
last_updated: '2026-04-18'
related: []
labels:
  - agents
  - docs-as-code
  - skills
  - governance
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Cut root `AGENTS.md` over to the HuleEdu-style thin skill router: keep stable
repo identity, non-negotiables, skill routing, docs authority, command-context
principles, and validation defaults in root; route detailed workflow into
shared/global skills, Sir Convert repo references, runbooks, rules, and
governed backlog docs.

## PR Scope

- Classify current `AGENTS.md` sections as keep, route-to-skill,
  route-to-reference, route-to-runbook, route-to-backlog, or remove.
- Add a compact skill router modeled on HuleEdu's `AGENTS.md`.
- Route docs/backlog governance to `agent-docs-governance` plus the Sir
  Convert-a-Lot reference.
- Route local dev, Hemma, conversion-client, Qwen/ML, speech, handoff, and
  review work through the appropriate shared or repo-local skills.
- Keep Sir Convert-specific command names and safety facts in repo references,
  runbooks, `.codex/rules/`, or governed docs rather than duplicated root prose.
- Update `.codex/handoff.md` and `.codex/skills/README.md` only where they
  reference root-entrypoint behavior.

## Deliverables

- [ ] Root `AGENTS.md` is slim and router-shaped.
- [ ] Docs/backlog governance points to `agent-docs-governance` plus the Sir
  Convert-a-Lot reference.
- [ ] Retained local skills and shared/global skills remain clearly separated.
- [ ] No retired `.agents/` or local shared-skill duplicate guidance is
  reintroduced.

## Acceptance Criteria

- [ ] `AGENTS.md` keeps stable repo identity, hard invariants, command-context
  principles, skill router, docs authority, and validation defaults.
- [ ] Detailed procedure for docs, local dev, Hemma, conversion, Qwen/ML,
  speech, reviews, and handoff routes to skills/references/runbooks/docs.
- [ ] Existing shared/global skill list is replaced or reduced to a router that
  names task lanes and start-here skills.
- [ ] Validation evidence includes `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
