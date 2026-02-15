# Sir Convert-a-Lot Agent Guidelines

## Purpose

This repository is the canonical home for **Sir Convert-a-Lot**. It is designed for
reliable, LLM-friendly document conversion workflows with Hemma offloading and GPU-first governance.

## Golden Rules

1. No behavior change without docs-as-code planning.
1. Contract-first delivery: docs/API/ADR are normative.
1. Preserve SRP and split modules before ~500 LoC.
1. No typing shortcuts (`Any`, casts, `# type: ignore`, lint ignores) in new code.
1. Use canonical wrappers for local vs remote command context.

## Session Start (Mandatory)

1. Read `.agents/rules/000-rule-index.md`.
1. Read task-relevant rules from the index.
1. Read `.agents/session/readme-first.md` and `.agents/session/handoff.md`.
1. Confirm active planning context in `docs/backlog/current.md`.
1. Validate docs-as-code state before implementation:
   - `pdm run validate-tasks`
   - `pdm run validate-docs`

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
pdm run validate-tasks
pdm run validate-docs
pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing
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

Repo-specific DevOps skill:

- `.agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md`
- `.agents/skills/sir-convert-a-lot-docs-governance/SKILL.md`
- `.agents/skills/sir-convert-a-lot-session-handoff/SKILL.md`

Cross-repo topology awareness on Hemma:

- `~/apps/sir-convert-a-lot`
- `~/apps/huleedu`
- `~/apps/skriptoteket`
- `~/infrastructure`

Policy:

- GPU-first execution is default and decision-governed.
- No silent CPU fallback.
- Use tunnels for local dev access by default.

## Do Not

- Do not create ad hoc converter scripts outside canonical service/CLI surfaces.
- Do not bypass docs contract or task hierarchy.
- Do not use `scp` for tracked repo code sync to Hemma (use `git pull` on host repo).
- Do not execute multiline or heavily quoted payloads through `pdm run run-hemma --shell`; promote them to committed scripts.
- Do not use raw `ssh hemma ...` for normal repo operations when `run-hemma` wrappers are available.

## Key Paths

- Rules: `.agents/rules/`
- Session context: `.agents/session/`
- Skills: `.agents/skills/`
- Global skills registry: `~/.codex/skills/` (repo skills must be symlinked there)
- Planning: `docs/backlog/`
- Product/ops docs: `docs/`
