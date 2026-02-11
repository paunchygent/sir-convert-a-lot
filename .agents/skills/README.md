______________________________________________________________________

type: meta
id: META-agents-skills-readme
title: Agent Skills Index
status: active
created: 2026-02-11
updated: 2026-02-11
owners:

- platform
  tags: [skills, codex]
  links: []

______________________________________________________________________

## Purpose

Index repo-local skills for Sir Convert-a-Lot and document global visibility via symlink.

## Local Skills

- `.agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md`
- `.agents/skills/sir-convert-a-lot-docs-governance/SKILL.md`
- `.agents/skills/sir-convert-a-lot-session-handoff/SKILL.md`
- `.agents/skills/docs-as-code/SKILL.md`

## Global Visibility

Create symlinks in `~/.codex/skills` pointing to repo-local skills:

```bash
ln -s "$(pwd)/.agents/skills/sir-convert-a-lot-devops-hemma" ~/.codex/skills/sir-convert-a-lot-devops-hemma
ln -s "$(pwd)/.agents/skills/sir-convert-a-lot-docs-governance" ~/.codex/skills/sir-convert-a-lot-docs-governance
ln -s "$(pwd)/.agents/skills/sir-convert-a-lot-session-handoff" ~/.codex/skills/sir-convert-a-lot-session-handoff
```
