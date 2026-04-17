______________________________________________________________________

type: meta
id: META-agents-skills-readme
title: Agent Skills Index
status: active
created: 2026-02-11
updated: 2026-02-14
owners:

- platform
  tags: [skills, codex]
  links: []

______________________________________________________________________

## Purpose

Index repo-local skills for Sir Convert-a-Lot.

## Retained Repo-Local Skills

- `.codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md`
- `.codex/skills/sir-convert-a-lot-colab-hemma/SKILL.md`
- `.codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md`
- `.codex/skills/speech-model-finetuning-on-hemma/SKILL.md`

## Policy

Do not create global symlinks that point directly to
`sir-convert-a-lot/.codex/skills`. If a local skill becomes cross-repo guidance,
promote it into `skill-repository` first and expose only that canonical target
through `~/.codex/skills`.
