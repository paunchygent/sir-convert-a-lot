---
type: task
id: TASK-SIRCON-REP-0039
title: 'EPIC-SKILL-18: Sir convert-a-lot compose secrets overlay and wrapper'
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-11-23'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-11-23T21:30:29Z'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: "TASK-SIRCON-REP-0039#closeout; whole review 322590fc changes_requested; first rereview e7f337f1 changes_requested; second rereview 9358f055 approved."
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

## Closeout

Implementation is complete and independently approved.

- Whole review `322590fc` (independent ruthless reviewer, 2026-11-23T20:41:21Z,
  `changes_requested`) reviewed all three merged leaves at `f14832aa` and
  returned eight findings. For this task, finding 1: the remote-proof deploy
  could not run from its named set alone, its diagnostic verbs still wrapped
  the store, and the base file still bound the legacy alias; and the
  wrapper-elevation part of finding 4: entrypoints put the store lookup on the
  root side of sudo although the wrapper owns Docker elevation.
- First rereview `e7f337f1` (2026-11-23T21:18:10Z, `changes_requested`): the
  remote-proof overlay repair at `a975a8f` was confirmed — `ps`, `logs`,
  `stop`, `config` and `check` no longer open Bitwarden or render the key as a
  service binding — but the default remote-proof env file still carries the
  legacy key line into diagnostics (finding 1 not resolved), and the deploy
  coordinator still retried `prod-recreate` under outer sudo (finding 4 not
  resolved).
- Second rereview `9358f055` (2026-11-23T21:30:29Z, `approved` at `70b2b88`):
  `prod-compose.sh` is the single owner of Docker elevation and
  `compose-actions.sh` opens the operator store before applying sudo, so the
  coordinator's retry was removed. Finding 1's remaining env-file line was not
  reopened: ST-SKILL-18-02 records the legacy remote-proof credential line for
  removal and a name-only check at cutover.
- The one wrapped command per changed path on Hemma is a cutover step after
  the `agent-secrets --set` tooling release and D13 approval; it is not part
  of this closeout.
