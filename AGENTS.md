# Sir Convert-a-Lot Agent Entrypoint

Sir Convert-a-Lot is the canonical document-conversion platform for reliable,
LLM-friendly PDF, DOCX, Markdown, HTML, and exam-migration workflows. It is a
Python/PDM repository with Hemma offload, GPU-first runtime governance, and
docs-as-code as planning and contract truth.

This file is a thin router. Keep durable procedure in skills and runbooks, and
keep product facts in references, ADRs, and backlog items.

## Repo Invariants

- Production behavior changes need backlog authority under `docs/backlog/`.
  Externally visible contracts need ADR/API/reference authority.
- Keep command context explicit: local development uses
  `pdm run run-local-pdm ...`; Hemma work uses the environment-aware
  `pdm run run-hemma -- ...` wrapper or a committed command surface.
- From MacBook/client sessions, `run-hemma` SSHes to Hemma; from the canonical
  Hemma Server repo, it executes locally after host/root/skill-repository checks.
- GPU/offload work is GPU-first and decision-governed.

## Session Start

1. Check `handoff.md` for current-state pointers.
2. Use `handoff.md` for active planning pointers and `docs/index.md` as
   the generated durable docs doorway.
3. Use the shared `agent-docs-governance` route for docs topology and lifecycle.

## Repo-Specific Routes

Keep routes here only when they add Sir Convert-a-Lot references, local skills,
product workflow, or command-wrapper context.

| Context                                                                   | Repo-Specific Route                                                                           |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Docs-as-code, backlog contracts, scaffolding, governed docs               | `agent-docs-governance` plus its Sir Convert-a-Lot reference                                  |
| Planning, decomposition, tranche sequencing                               | `agent-planning` plus its Sir Convert-a-Lot reference                                         |
| Next-session or developer handoff messages                                | `agent-session-handoff` plus its Sir Convert-a-Lot reference                                  |
| Local dev, PDM scripts, wrappers, local Docker, dependency workflow       | `local-devops` plus its Sir Convert-a-Lot reference                                           |
| Hemma deploys, remote operations, shared host runtime, GPU/offload lanes  | `hemma-devops` plus `.codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md` when Sir-specific |
| Sir Convert client usage from other repos or operator workflows           | `sir-convert-a-lot-client`                                                                    |
| Qwen3-TTS fine-tuning, preprocessing, evaluation, and promotion decisions | `.codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md`                                    |
| Speech-model fine-tuning beyond Qwen-specific guidance                    | `.codex/skills/speech-model-finetuning-on-hemma/SKILL.md`                                     |
| Colab/Hemma notebook orchestration                                        | `.codex/skills/sir-convert-a-lot-colab-hemma/SKILL.md`                                        |

Shared workflows come from the central package. Repo facts belong in shared-skill
references or repo-local leaf skills, not copied shared-skill bodies.

## Agent Surface

- `.codex/skills/`: truly Sir Convert-specific workflow/domain skills only.
- `handoff.md`: current-state handoff.
- `.codex/long-term-memory/index.md`: durable session-history doorway.
- `.codex/repomix_packages/`: ignored generated AI-review packages.

## Durable Docs

- Generated docs doorway: `docs/index.md`
- Active planning pointer: `handoff.md`
- ADRs and decisions: `docs/decisions/`
- Runbooks: `docs/runbooks/`
- References, contracts, research, and roadmaps: `docs/reference/`

When a backlog item, ADR, reference, runbook, or active decision changes, update
the governing docs and `handoff.md` as needed.

## Authority Transition Guard

Use `agent-docs-governance` for current authority transitions and archive
handling. Do not duplicate the shared transition protocol here.

## Command Policy

Default close-out:

- Docs/governance change: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and `git diff --check`
- Python/backend change: inspect `pdm run check --plan <scope>`, then run only
  the owning named scope with `pdm run check <scope>`
- Docker/runtime change: use the relevant local or Hemma skill/runbook, named
  compose wrappers, health checks, bounded logs, and exact proof artifacts
- Qwen/ML change: use the Qwen/speech skills and governed runbooks before
  launching or interpreting experiments

Use `pdm run run-hemma -- ...` for Sir Hemma commands. Treat
`pdm run run-hemma --shell ...` as exception-only for short probes that cannot
be expressed through the global argv-mode default. Promote non-trivial remote
workflows to committed scripts.

Long-running dev services, Docker volumes, Hemma jobs, and generated artefact
trees should not be stopped, reset, pruned, or deleted unless the user asks or a
governing task explicitly authorizes it.
