---
type: runbook
id: RUN-hemma-service-ops
title: Hemma Service Operations Runbook for Sir Convert-a-Lot
status: active
created: '2026-05-14'
updated: '2026-05-14'
owners:
  - platform
system: hemma.hule.education
tags:
  - devops
  - hemma
  - deploy
  - tunnel
links:
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/converters/sir_convert_a_lot.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/runbooks/runbook-v2-async-push-delivery.md
---

## Purpose

Operate Sir Convert-a-Lot on Hemma without duplicating HuleEdu or Skriptoteket
runtime guidance.

## Host Map

- Sir Convert-a-Lot: `/home/paunchygent/apps/sir-convert-a-lot`
- HuleEdu: `/home/paunchygent/apps/huleedu`
- Skriptoteket: `/home/paunchygent/apps/skriptoteket`
- Shared edge infrastructure: `/home/paunchygent/infrastructure`
- Shared Postgres runs as shared container infrastructure, not as a Sir-local
  database.

## Command Surfaces

- Local wrapper: `pdm run run-local-pdm <script> [args]`
- Hemma wrapper: `pdm run run-hemma -- <command> [args]`
- Short shell probe: `pdm run run-hemma --shell "<command>"`
- Deploy and live verify: `pdm run hemma-deploy-and-verify --expected-revision <sha> --lane host --api-key <key>`

`hemma-deploy-and-verify` gates deploy success on revision/readiness parity,
structured LLM provider verification, metrics safety, and public-edge reserved
state. The legacy V2 conversion smoke is evidence only; `gpu_not_available`
there is a conversion-worker finding, not a deploy failure.

Use the wrapper from the local repo root. It is environment-aware: from a
client machine it SSHes to Hemma; from the canonical Hemma Server checkout it
runs directly after checking the hostname, repo root, and shared skill
repository path. Set `SIR_CONVERT_A_LOT_FORCE_REMOTE_HEMMA=1` only when an
operator deliberately needs the SSH path despite local Hemma detection.

Direct production and ROCm helpers such as `prod-*`,
`prod-deps-rocm-build`, and `hemma-sync-prod-env-mirror` are Hemma
Server-only. They fail before Docker or host env mutation when the session does
not prove the canonical Hemma hostname, repo root, and shared skill repository.

## Repo Placement Check

Before deploy, smoke, or destructive maintenance:

```bash
pdm run run-hemma --shell 'find /home/paunchygent -maxdepth 4 -type d -name "sir-convert-a-lot" 2>/dev/null | sort'
```

If the canonical repo is missing, repair the `~/apps` checkout before continuing.
Do not run operational commands from ad hoc root-level copies.

## Client Access

Canonical lanes:

- Tunnel lane: `http://127.0.0.1:28085`
- Gateway/public lane: disabled until the Gateway cutover explicitly re-enables
  the intended public edge.

Do not document `127.0.0.1:8085` or `127.0.0.1:18085` as client access lanes.
Port `8085` is container-internal validation only.

Tunnel check:

```bash
ssh hemma -L 28085:127.0.0.1:28085 -N
curl -fsS http://127.0.0.1:28085/healthz
```

## API Key Handling

Deploy/live verification key precedence:

1. `--api-key`
1. `SIR_CONVERT_A_LOT_API_KEY`
1. explicit failure

The implicit development key is rejected unless passed deliberately. Never write
API keys into reports, logs, or retained artifacts.

API-provider credentials used by structured answer-key completion live in the
canonical prod env mirror by key reference only. The OpenAI provider reads
`SIR_CONVERT_A_LOT_OPENAI_API_KEY`; the mirror also preserves the generic
`OPENAI_API_KEY`, `OPENROUTER_API_KEY`, and `DEEPSEEK_API_KEY` names plus
Sir-prefixed aliases for follow-on provider profiles. Verify presence by key
name only and redact values in any retained output.

The unified exam-authoring correction route requires
`SIR_CONVERT_A_LOT_EXAM_AUTHORING_SOURCE_STATE_SIGNATURE_SECRET` so producer
source states can be signed and later verified before readiness or artifact
availability is projected. Verify only that the key is present; never print the
secret value.

## Production Env Mirror

Use the committed mirror command:

```bash
pdm run run-hemma -- pdm run hemma-sync-prod-env-mirror
```

Do not hand-copy `.env` files between products or repos.

## Detached Work

Use attached remote commands only for fast probes and validation. Long jobs must
survive local client disconnects through committed detached runners, named
containers, `tmux`, or a supervised remote service.

## Minimal Service Triage

```bash
pdm run run-hemma -- /bin/bash -lc 'sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
pdm run run-hemma -- curl -fsS http://127.0.0.1:28085/healthz
```
