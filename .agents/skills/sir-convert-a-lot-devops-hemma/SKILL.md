---
name: sir-convert-a-lot-devops-hemma
description: >-
  Repo-specific DevOps skill for running Sir Convert-a-Lot on Hemma with
  GPU-first policy, tunnel-or-internet client access policy, and cross-repo
  awareness of HuleEdu and Skriptoteket server layout.
---

# Sir Convert-a-Lot DevOps (Hemma + GPU)

## Use This Skill When

- Deploying or troubleshooting Sir Convert-a-Lot on `hemma.hule.education`.
- Verifying GPU/ROCm readiness for conversion workloads.
- Running local-to-remote tunnel workflows for conversion jobs.
- Coordinating coexistence with HuleEdu and Skriptoteket on the same host.

## Source of Truth

- `docs/runbooks/runbook-hemma-devops-and-gpu.md`
- `docs/converters/sir_convert_a_lot.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/decisions/0002-multi-format-service-api-v2.md`

Cross-repo operational references:

- `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/runbooks/hemma-server-operations-huleedu.md`
- `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/runbooks/gpu-ai-workloads-on-hemma-huleedu.md`
- `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/runbooks/runbook-home-server.md`
- `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/runbooks/runbook-gpu-ai-workloads.md`

## Canonical Command Surfaces

Local wrapper (loads `.env`, enforces repo root):

```bash
pdm run run-local-pdm <script> [args]
```

Remote Hemma wrapper (enforces remote repo root):

```bash
pdm run run-hemma -- <command> [args]
pdm run run-hemma --shell "<command with shell operators>"
```

Detached execution policy:

- Use attached `run-hemma` only for short probes, validation commands, and fast
  status checks.
- Any long-running Hemma work must be launched through a detached remote
  surface so the job survives local client disconnects, tunnel drops, or
  session resets.
- Prefer committed detached runners, named background containers, or remote
  `tmux`/supervised surfaces over foreground client-attached execution.

Deploy parity gate (one-command deploy + verify):

```bash
pdm run hemma-deploy-and-verify \
  --expected-revision <sha> \
  --lane host \
  --api-key <key>
```

Deploy verification evidence path (deterministic):

- Use `--output-root` for deterministic evidence output and include:
  - `report.json`
  - `report.md`
  - `readyz.json`
  - `metrics.prom`
  - `remote_head.txt`

Wrapper behavior is deterministic:

- validates `SIR_CONVERT_A_LOT_HEMMA_ROOT` exists and is a git repo before command execution.
- asserts effective remote cwd equals configured root.
- runs commands in `bash --noprofile --norc`.
- streams the prepared script over stdin to avoid SSH quoting/argv ambiguity.
- fails with explicit exit codes:
  - `66` root missing
  - `67` root is not a git repo
  - `68` cwd mismatch

## Hemma Repo Topology Awareness

- `~/apps/sir-convert-a-lot`: this service repo.
- `~/apps/huleedu`: HuleEdu stack + NLP offload.
- `~/apps/skriptoteket`: Skriptoteket stack.
- `~/infrastructure`: shared nginx/certbot edge infra.

## Mandatory First Step (Path Guard)

Before any deployment/smoke actions:

1. Verify repo location is under `~/apps`:

```bash
pdm run run-hemma --shell 'find /home/paunchygent -maxdepth 4 -type d -name "sir-convert-a-lot" 2>/dev/null | sort'
```

2. If missing, bootstrap canonical path:

```bash
ssh hemma "/bin/bash -lc 'mkdir -p /home/paunchygent/apps && cd /home/paunchygent/apps && git clone git@github.com:paunchygent/sir-convert-a-lot.git'"
```

3. If multiple copies exist, standardize on:

- `/home/paunchygent/apps/sir-convert-a-lot`
- set `SIR_CONVERT_A_LOT_HEMMA_ROOT` accordingly for wrappers.

## GPU-First Guardrails

- Prefer GPU execution path by default for conversion service workloads.
- Never silently switch to CPU fallback when GPU is unavailable.
- If fallback policy changes, require ADR/backlog updates first.

## Tunnel-First Dev Flow

Canonical client access lanes (no superseded local lanes):

- Tunnel lane: `http://127.0.0.1:28085`
- Internet lane: `https://convert.hule.education`
- Do not guide clients to `127.0.0.1:8085` or `127.0.0.1:18085`.

Verification lane policy:

- host lane (`28085`) is canonical for deploy/live verification.
- docker lane (`8085`) is internal-only container validation and must not be
  documented as a client access lane.

API key policy for deploy/live verification:

- precedence: `--api-key` > `SIR_CONVERT_A_LOT_API_KEY` > error.
- implicit `dev-only-key` is rejected unless explicitly passed via
  `--api-key dev-only-key` or `--allow-dev-key`.
- API keys must never be persisted in reports/logs/artifacts.

Canonical Hemma prod env mirror/symlink command:

```bash
pdm run run-hemma -- pdm run hemma-sync-prod-env-mirror
```

```bash
ssh hemma -L 28085:127.0.0.1:28085 -N
curl -fsS http://127.0.0.1:28085/healthz
pdm run convert-a-lot convert ./pdfs --output-dir ./research --service-url http://127.0.0.1:28085
```

## Minimal Triage Commands

```bash
pdm run run-hemma -- /bin/bash -lc 'sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
pdm run run-hemma -- rocminfo
pdm run run-hemma -- rocm-smi
```
