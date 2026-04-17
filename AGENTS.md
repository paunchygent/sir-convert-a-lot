# Sir Convert-a-Lot Agent Guidelines

## Purpose

This repository is the canonical home for **Sir Convert-a-Lot**. It is designed for
reliable, LLM-friendly document conversion workflows with Hemma offloading and GPU-first governance.

## Golden Rules (Mandatory)

1. No behavior change without docs-as-code planning.
1. Contract-first delivery: docs/API/ADR are normative.
1. Strict DRY and SOLID code only - no duplication, no god objects \<400 LoC.
1. No typing shortcuts (`Any`, casts, `# type: ignore`, lint ignores) in new code.
1. Use canonical wrappers for local vs remote command context.

## Session Start (Mandatory)

1. Read this file.
1. Check `.codex/handoff.md` only for volatile current-state pointers.
1. Read `.codex/rules/000-rule-index.md` when repo rules are needed.
1. Read task-relevant rules from the index.
1. Confirm active planning context in `docs/backlog/current.md`.
1. Validate docs-as-code state before implementation:
   - `pdm run docs-validate`

## Planning and Docs Taxonomy (Invariant)

### Planning hierarchy

`programme -> epic -> story -> task`

Canonical location:

- `docs/backlog/`

Task policy:

- Tasks are small PR-sized execution units.
- A task may be linked to a story, or exist independently when the change is scoped and coherent.

### Documentation classes

- Runbooks (operational instructions): `docs/runbooks/`
- Reference docs (research/reports/reviews/future plans): `docs/reference/`
- ADRs (decisions): `docs/decisions/`
- PDRs (high-level product value/features): `docs/pdr/`
- Converter/API docs: `docs/converters/`
- Docs contract metadata: `docs/_meta/docs-contract.yaml`

All docs and rules must include YAML frontmatter and satisfy contract validation.

## Canonical Scripts and Command Context

### Local wrappers

Use for repo-root execution with `.env` loading:

```bash
pdm run run-local-pdm <script> [args]
```

### Remote Hemma wrappers

Use for explicit remote execution in Hemma repo root:

```bash
pdm run run-hemma -- <command> [args]
pdm run run-hemma --shell "<command with operators>"
```

Strict execution policy:

- Default to argv mode: `pdm run run-hemma -- <command> [args]`.
- Treat `--shell` as exception-only; use it only for short operator usage that cannot be expressed in argv mode.
- For any non-trivial remote workflow (multi-step checks, probes, reports, loops, JSON parsing), commit a script in this repo and invoke that script via argv mode.
- Never run inline heredoc Python/Bash payloads through `run-hemma --shell` for routine operations.
- Never use `run-hemma --shell` as an ad hoc command transport layer when a committed script surface exists or should exist.
- Detached execution is the default for long-running Hemma work.
- Any Hemma job that may outlive the local client session or tunnel must be launched through a detached remote surface and observed separately through committed logs, reports, or status commands.
- Attached `run-hemma` execution is short-probe-only.

Environment overrides:

- `SIR_CONVERT_A_LOT_HEMMA_HOST`
- `SIR_CONVERT_A_LOT_HEMMA_ROOT`

### Planning scaffolds

- `pdm run new-programme "<title>"`
- `pdm run new-epic "<title>"`
- `pdm run new-story "<title>"`
- `pdm run new-task "<title>"`
- `pdm run new-review "<title>"`

## Quality Gates (Mandatory)

```bash
pdm run format-all
pdm run lint-fix
pdm run typecheck-all
pdm run pytest-root <path-or-nodeid>
```

Docs gates:

```bash
pdm run docs-validate
```

Skill-surface gate:

```bash
pdm run skills-validate
```

Handoff gate:

```bash
pdm run handoff-validate
```

## Docker v2 Standards (Greatest Hits)

- Use `docker compose` (v2), never `docker-compose`.
- Keep compose commands explicit and reproducible.
- For debugging capture: `docker compose ps`, `docker compose logs`, `docker compose config`.
- Use health endpoints for readiness, not sleep-based startup assumptions.

## PostgreSQL Standards (Greatest Hits)

- PostgreSQL is canonical relational database.
- Migration files are immutable once applied.
- Add forward migrations for changes; avoid editing history.
- Validate schema changes with integration tests.

## PDM Standards (Greatest Hits)

- Run PDM from repository root.
- Keep dependency and lockfile changes synchronized.
- Prefer named PDM scripts for repeatable workflows.

## Hemma Operations and GPU (Greatest Hits)

Canonical runbook:

- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

Repo-local skills retained for Sir Convert-specific operations:

- `.codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md`
- `.codex/skills/sir-convert-a-lot-colab-hemma/SKILL.md`
- `.codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md`
- `.codex/skills/speech-model-finetuning-on-hemma/SKILL.md`

Shared/global skills used from `~/.codex/skills`, not duplicated locally:

- `sir-convert-a-lot-client`
- `agent-docs-governance`
- `agent-planning`
- `agent-session-handoff`

Cross-repo topology awareness on Hemma:

- `~/apps/sir-convert-a-lot`
- `~/apps/huleedu`
- `~/apps/skriptoteket`
- `~/infrastructure`

Policy:

- GPU-first execution is default and decision-governed.
- No silent CPU fallback.
- Use tunnels for local dev access by default.
- Long-running Hemma work must not depend on the stability of the local client, tunnel, or attached SSH session.
- Hemma storage tiers are explicit and mandatory:
  - `/srv/scratch` is the fast SSD work tier for Docker root/BuildKit cache,
    HF/model caches, and active generated artifacts.
  - `/srv/storage` is the large HDD bulk-data tier for raw corpora and colder
    retained datasets.
  - The Hemma OS disk (`/`) must not be the long-term home for Docker
    persistent state or large ML artifact trees.

## Do Not

- Do not create ad hoc converter scripts outside canonical service/CLI surfaces.
- Do not bypass docs contract or task hierarchy.
- Do not use `scp` for tracked repo code sync to Hemma (use `git pull` on host repo).
- Do not execute multiline or heavily quoted payloads through `pdm run run-hemma --shell`; promote them to committed scripts.
- Do not use raw `ssh hemma ...` for normal repo operations when `run-hemma` wrappers are available.

## Key Paths

- Rules: `.codex/rules/`
- Session handoff: `.codex/handoff.md`
- Long-term memory: `.codex/long-term-memory/index.md`
- Skills: `.codex/skills/`
- Global skills registry: `~/.codex/skills/` for canonical shared skills
- Planning: `docs/backlog/`
- Product/ops docs: `docs/`
