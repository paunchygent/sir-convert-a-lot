---
type: task
id: TASK-SIRCON-REP-0040
title: 'EPIC-SKILL-18: Sir convert-a-lot bounded startup and workload paths use the overlay or start'
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-11-23'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - Given bounded_production_startup and hemma_workload, when they start production services, then an `up` that may recreate passes the overlay through agent-secrets, and a start of existing containers uses `start` and reads no secret.
backlog_document_profile: contract-derived
---

## Implementation Contract

Leaf of skill-repository `EPIC-SKILL-18` (decided terms D3, D6, D7, D8, D13,
D14, D15, D18, D19). Shared rules for every leaf:

- A secret reaches a process only through
  `agent-secrets run --set <set> -- <command>`; the set names below are
  declared in skill-repository `resources/agent-secrets.toml` (D18). Under
  sudo, pass `sudo --preserve-env="$AGENT_SECRETS_VARIABLES" ...`.
- Compose: every secret interpolation moves out of the base compose files into
  one secrets overlay file per project, written `${VAR:?run through <wrapper>}`.
  Only the deploy, recreate, build-with-secrets and one-off `run` paths pass
  the overlay, through the wrapper; `ps`, `logs`, `stop`, `config`, `exec` and
  boot paths use the base files and read no secret (D15). A path that runs
  `up` on existing production containers without the overlay changes to
  `start` (D15, docker docs: `start` never creates containers).
- Host-run code reads secrets from the process environment only; `.env`
  fallbacks for secret names (`load_dotenv`, `dotenv_values`, hand parsers,
  `source .env`) are removed for those names; `.env` keeps configuration.
- This leaf changes code only: no `.env` edit, no deploy, no container
  restart. The live switch is a later step, and production steps need Olof's
  approval (D13).

## Contract Inputs

Files: scripts/sir_convert_a_lot/devops/bounded_production_startup.py, bounded_production_startup_runtime.py, hemma_workload.py, prod-start-bounded.sh. Set: `sir-convert-a-lot-prod`.

## Core Vertical And Performance

One wrapped command per changed path runs on Hemma after the tooling release, with its secret absent from `.env`.

## Validation

Focused tests for changed code (argv and environment of the wrapped commands,
no `.env` secret fallback); lint and typecheck on changed files.

## Stop Conditions

Stop and report a path that needs a secret at boot, or a secret that has to
reach a container this leaf cannot route through the wrapper.

## Decided Contract Terms

| ID  | Decided contract term                                   |
| --- | ------------------------------------------------------- |
| D1  | EPIC-SKILL-18 decided terms apply; this leaf adds none. |
