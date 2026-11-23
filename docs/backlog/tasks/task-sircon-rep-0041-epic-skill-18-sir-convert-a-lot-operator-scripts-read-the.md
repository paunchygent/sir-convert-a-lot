---
type: task
id: TASK-SIRCON-REP-0041
title: 'EPIC-SKILL-18: Sir convert-a-lot operator scripts read the key and HF_TOKEN from agent-secrets, and the env mirror is removed'
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
  approval_evidence: "TASK-SIRCON-REP-0041#closeout; whole review 322590fc changes_requested; first rereview e7f337f1 changes_requested; second rereview 9358f055 approved."
task_kind: repository
acceptance_criteria:
  - Given each Sir convert-a-lot devops script that reads SIR_CONVERT_A_LOT_V2_API_KEY or HF_TOKEN, when it runs, then its pdm script runs it through `agent-secrets run --set sir-convert-a-lot-operator`, no code reads those names from a .env file, no HF_TOKEN value is put on a command line, and scripts/devops/sync-prod-env-mirror.sh and its calls are removed.
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

Files: scripts/devops/run-hemma.sh, verify-hemma-gpu-runtime.sh, verify-hemma-v2-conversions.sh, scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar\_\*.py, audio_transcription_sidecar_operator_environment.py, run_tts_sidecar_hemma_benchmark.py with tts_sidecar_benchmark_runtime.py (pass `-e HF_TOKEN` by name), run_pdf_throughput_hemma_benchmark.py (stop parsing the canonical env file), sync-prod-env-mirror.sh (removed), pdm scripts. Set: `sir-convert-a-lot-operator`.

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
  returned eight findings. For this task, finding 5: the TTS `HF_TOKEN` was
  lost across sudo before Docker saw it; finding 6: the STT environment merge
  still fell back to file credentials and the PDF launch preloaded the whole
  `.env`; and finding 7: the deployed verification and PDF benchmark marshaled
  the fetched key back into argv.
- First rereview `e7f337f1` (2026-11-23T21:18:10Z, `changes_requested`):
  finding 6 was not reopened after the process-only read repair at `434ed58`,
  but findings 5 and 7 were not resolved — the required prefetch container
  still dropped the token, and the deployed PDF CLI still accepted and
  recommended a credential on argv.
- Second rereview `9358f055` (2026-11-23T21:30:29Z, `approved` at `70b2b88`):
  finding 5 resolved at `e36f7ee` — prefetch and serve both forward `HF_TOKEN`
  by name only across sudo and `-e`; finding 7 resolved at `a4ccaa6` —
  production PDF mode reads only `SIR_CONVERT_A_LOT_V2_API_KEY`, refuses a
  nonblank `--api-key` without echoing it, and points the missing-key error at
  the existing Hemma wrapper.
- The one wrapped command per changed path on Hemma is a cutover step after
  the `agent-secrets --set` tooling release and D13 approval; it is not part
  of this closeout.
