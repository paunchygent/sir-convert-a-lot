---
type: agent_session_long_term_memory_entry
id: sir-convert-a-lot-session-2026-04-16-agent-governance-cutover
status: active
created: '2026-04-16'
last_updated: '2026-04-16'
---

# Agent Governance Cutover Progress

## Scope

Sir Convert-a-Lot began the direct cutover from `.agents/` governance paths to
the shared `.codex/` shape.

Completed unambiguous moves:

- `.agents/rules/` to `.codex/rules/`
- `.agents/skills/` to `.codex/skills/`
- `.agents/session/handoff.md` to `.codex/handoff.md`
- `.agents/repomix_packages/` to `.codex/repomix_packages/`

The former `.agents/session/readme-first.md` duplicated router/onboarding
guidance now owned by `AGENTS.md`, `.codex/handoff.md`, and governed docs, so
it was removed.

## Input Lane Resolution

The ignored, untracked PDF source inputs moved from `.agents/input/` to
`data/conversion-inputs/`. This keeps local reproducibility inputs out of the
agent-governance tree without turning them into committed fixtures or generated
artifacts.

The active Docling references now point at the new non-agent path for
`Prövning i litteraturhistoria 2024.pdf`.

## Validation

Cutover validation passed:

- `pdm run validate-tasks`
- `pdm run validate-docs`
- `git diff --check`

At governance cutover closeout, no `skills-validate` or `handoff-validate` command was
exposed by this repo. `TASK-0045` later added `skills-validate`, and
`TASK-0046` added `handoff-validate`.
