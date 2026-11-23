---
type: task
id: TASK-SIRCON-REP-0039
title: 'EPIC-SKILL-18: Sir convert-a-lot compose secrets overlay and wrapper'
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
  - Given compose.yaml, when the leaf closes, then SIR_CONVERT_A_LOT_V2_API_KEY and HF_TOKEN are interpolated only in compose.secrets.yaml with required guards (no dev-only-key default), and scripts/devops/compose-actions.sh passes the overlay through `agent-secrets run --set sir-convert-a-lot-prod -- sudo --preserve-env=...` for start, recreate and build, while ps, logs, stop and config use the base file.
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

Files: compose.yaml, new compose.secrets.yaml, scripts/devops/compose-actions.sh, prod-compose.sh (no more .env snapshot for secrets), dev-compose.sh, remote-proof-compose.sh with compose.remote-proof.yaml (set `sir-convert-a-lot-remote-proof`). Set: `sir-convert-a-lot-prod`.

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
