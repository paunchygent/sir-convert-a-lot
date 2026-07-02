# Sir Convert-a-Lot Agent Entrypoint

Sir Convert-a-Lot is the canonical document-conversion platform for reliable,
LLM-friendly PDF, DOCX, Markdown, HTML, and exam-migration workflows. It is a
Python/PDM repository with Hemma offload, GPU-first runtime governance, and
docs-as-code as the source of planning and contract truth.

This file is a thin router. Keep durable procedure in skills, rules, runbooks,
reference docs, ADRs, and backlog items rather than expanding this root context.

## Non-Negotiables

- Use skills before planning or implementation. Start with the global skill
  registry, then use repo-owned skills under `.codex/skills/` when they are
  specifically relevant.
- Use docs-as-code for planning and structural changes. Every production
  behavior change needs backlog authority under `docs/backlog/`; externally
  visible contracts need ADR/API/reference authority.
- Follow `.codex/rules/000-rule-index.md` for targeted repo rules. Do not
  bulk-load the rules directory.
- Do not revert, overwrite, or delete changes you did not make without explicit
  approval.
- Keep implementation DRY and SOLID. Preserve DDD/Clean boundaries, use Dishka
  DI where it clarifies composition, keep modules under roughly 400-500 lines,
  and refactor before files become broad catch-alls.
- Do not introduce typing shortcuts in new code: no `Any`, `typing.cast`,
  `# type: ignore`, lint ignores, or compatibility shims to bypass gates.
- Add a Google-style module docstring at the top of new or materially changed
  Python modules describing purpose and relationships.
- Use Context7 or primary upstream docs before changing third-party dependency
  usage or complex external workflows.
- Keep command context explicit: local development uses
  `pdm run run-local-pdm ...`; Hemma work uses the environment-aware
  `pdm run run-hemma -- ...` wrapper or a committed detached command surface.
  From MacBook/client sessions the wrapper SSHes to Hemma; from the canonical
  Hemma Server repo it executes locally after host/root/skill-repository checks.
- Git workflow is merge-only: never rebase, amend, force-push, or hide conflict
  resolution in history.
- Use BuildKit for Docker builds and Docker Compose v2 (`docker compose`), never
  plain `docker build` or `docker-compose`.
- GPU/offload work is GPU-first and decision-governed. Do not introduce silent
  CPU fallback.
- Never commit secrets, local `.env` files, or `.artifacts`. Generated model,
  conversion, benchmark, review, and research artefacts stay ignored unless a
  task explicitly promotes part of them.

## Session Start

1. Read this file.
1. Check `.codex/handoff.md` only for volatile current-state pointers.
1. Select the task-relevant skill before planning or implementation.
1. Load `.codex/rules/000-rule-index.md` only when repo rules are needed, then
   open the specific rule files the task requires.
1. Use `.codex/handoff.md` for active planning pointers and `docs/index.md` as
   the generated durable docs doorway.
1. Use `docs/DOCS_STRUCTURE_SPEC.md`, `docs/backlog/README.md`, and
   `docs/_meta/docs-contract.yaml` for durable docs topology and validation
   rules.

## Skill Router

| Task | Start Here |
|---|---|
| Docs-as-code, backlog contracts, scaffolding, governed docs | `agent-docs-governance` plus its Sir Convert-a-Lot reference |
| Planning, decomposition, tranche sequencing | `agent-planning` plus its Sir Convert-a-Lot reference |
| Next-session or developer handoff messages | `agent-session-handoff` plus its Sir Convert-a-Lot reference |
| Local dev, PDM scripts, wrappers, local Docker, dependency workflow | `local-devops` plus any Sir Convert-a-Lot reference |
| Hemma deploys, remote operations, shared host runtime, GPU/offload lanes | `hemma-devops` plus `.codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md` when Sir-specific |
| Sir Convert client usage from other repos or operator workflows | `sir-convert-a-lot-client` |
| Qwen3-TTS fine-tuning, preprocessing, evaluation, and promotion decisions | `.codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md` |
| Speech-model fine-tuning beyond Qwen-specific guidance | `.codex/skills/speech-model-finetuning-on-hemma/SKILL.md` |
| Colab/Hemma notebook orchestration | `.codex/skills/sir-convert-a-lot-colab-hemma/SKILL.md` |
| Testing strategy, test implementation, test repair, or test-quality audits | `testing` |
| Code review | `ruthless-code-review` |
| Review/context packages | `repomix-package-builder` |
| Logs, metrics, traces, dashboards, public-edge logging policy | `observability-stack` |
| Browser automation, screenshots, Playwright proof | `playwright-testing` |
| PDM metadata migration | `pdm`, explicit use only |

Shared skills are authored in
`/Users/olofs_mba/Documents/Repos/skill-repository/skills/` first. Repo facts
belong in shared-skill references or repo-local leaf skills, not in copied
shared-skill bodies.

- For any skill creation or update, use the global `skill-creator` skill first.
  Keep `SKILL.md` concise; route examples, rationale, and detailed procedure to
  referenced resources.

## Agent Surface

- `.codex/skills/`: truly Sir Convert-specific workflow/domain skills only.
- `.codex/rules/`: targeted repo invariants and discovery rules.
- `.codex/handoff.md`: volatile current-state handoff; keep durable doctrine
  out of it.
- `.codex/long-term-memory/index.md`: durable session-history doorway.
- `.codex/repomix_packages/`: ignored generated AI-review packages.

Do not recreate retired `.agents/` compatibility shims or local duplicates of
shared/global skills.

## Durable Docs

- Generated docs doorway: `docs/index.md`
- Active planning pointer: `.codex/handoff.md`
- Backlog guide and hierarchy: `docs/backlog/README.md`
- Docs topology: `docs/DOCS_STRUCTURE_SPEC.md`
- Docs contract: `docs/_meta/docs-contract.yaml`
- Converter/API contracts: `docs/converters/`
- ADRs and decisions: `docs/decisions/`
- Product direction: `docs/pdr/`
- Runbooks: `docs/runbooks/`
- References, research, reviews, and roadmaps: `docs/reference/`

When a backlog item, ADR, reference, runbook, or active decision changes, update
the governing docs and `.codex/handoff.md` as needed, then refresh generated
indexes with `pdm run docs-sync`. Promote policy, procedure, acceptance
criteria, and implementation doctrine to governed docs instead of burying them
in handoff or memory.

## Command Policy

Run commands from the repository root and prefer named `pdm run ...` scripts.
Do not invent ad hoc command strings when a script exists.

Default close-out:

- Docs/governance change: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and `git diff --check`
- Python/backend change: `pdm run format-all`, `pdm run lint-fix`,
  `pdm run typecheck-all`, focused `pdm run pytest-root <path-or-nodeid>`, and
  `pdm run coverage-gate` where conversion-core coverage applies
- Docker/runtime change: use the relevant local or Hemma skill/runbook, named
  compose wrappers, health checks, bounded logs, and exact proof artifacts
- Qwen/ML change: use the Qwen/speech skills and the governed runbooks before
  launching or interpreting experiments

Use `pdm run run-hemma -- ...` in argv mode by default. Treat
`pdm run run-hemma --shell ...` as exception-only for short probes that cannot
be expressed in argv mode. The wrapper is environment-aware: it SSHes from
client machines and runs directly on Hemma when the current session is already
the canonical Hemma Server checkout. Promote non-trivial remote workflows to
committed scripts and run long Hemma jobs through detached surfaces with
separately observable logs, reports, or status commands.

Long-running dev services, Docker volumes, Hemma jobs, and generated artefact
trees should not be stopped, reset, pruned, or deleted unless the user asks or a
governing task explicitly authorizes it.
