---
type: runbook
id: RUN-hemma-devops-and-gpu
title: Hemma DevOps and GPU Runbook for Sir Convert-a-Lot
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
system: hemma.hule.education
tags:
  - devops
  - hemma
  - gpu
  - sir-convert-a-lot
links:
  - .agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md
  - /Users/olofs_mba/Documents/Repos/huledu-reboot/docs/operations/hemma-server-operations-huleedu.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/runbooks/runbook-home-server.md
---

## Purpose

Standardize how `sir-convert-a-lot` is operated on Hemma with GPU-first behavior, while
remaining aligned with existing HuleEdu and Skriptoteket server patterns.

## Canonical Hemma Repo Map

- `~/apps/sir-convert-a-lot`: canonical repo path for this service.
- `~/apps/huleedu`: HuleEdu stack + ML offload services.
- `~/apps/skriptoteket`: Skriptoteket stack.
- `~/infrastructure`: nginx-proxy/certbot and shared edge infra.
- `~/apps/shared-postgres` (container-level service): shared DB host via Docker network.
- `/home/paunchygent/llama.cpp-rocm`: ROCm llama.cpp build context (shared GPU tooling).

## Repo Placement Policy (`~/apps`)

- Sir Convert-a-Lot must be hosted at:
  - `/home/paunchygent/apps/sir-convert-a-lot`
- Do not run production/devops commands from ad hoc copies in `/home/paunchygent` root.
- If the repo is missing from `~/apps`, create/repair it first:

```bash
ssh hemma "/bin/bash -lc 'mkdir -p /home/paunchygent/apps && cd /home/paunchygent/apps && git clone git@github.com:paunchygent/sir-convert-a-lot.git'"
```

- If a misplaced copy exists outside `~/apps`, prefer reclone or clean move to `~/apps` and
  then set:

```bash
export SIR_CONVERT_A_LOT_HEMMA_ROOT=/home/paunchygent/apps/sir-convert-a-lot
```

- Verification command:

```bash
ssh hemma "/bin/bash -lc 'find /home/paunchygent -maxdepth 4 -type d -name sir-convert-a-lot 2>/dev/null | sort'"
```

## Command Context Rules

- Local PDM wrappers:
  - `pdm run run-local-pdm <script> [args]`
- Remote Hemma commands:
  - `pdm run run-hemma -- <command> [args]`
  - `pdm run run-hemma --shell "<command with operators>"`

Default remote context is:

- host: `hemma`
- repo root: `/home/paunchygent/apps/sir-convert-a-lot`

Overrides:

- `SIR_CONVERT_A_LOT_HEMMA_HOST`
- `SIR_CONVERT_A_LOT_HEMMA_ROOT`

Wrapper guarantees:

- Remote root is validated before execution (directory exists and is a git repo).
- Effective remote cwd is asserted to match the configured root.
- Wrapper fails fast on context mismatch:
  - `66`: remote root missing
  - `67`: remote root is not a git repo
  - `68`: remote cwd mismatch
- Commands run in deterministic shell mode (`bash --noprofile --norc`).
- Remote script is streamed over stdin to avoid quoting drift across SSH command parsing.

## SSH and Service Health

```bash
pdm run run-hemma -- pwd
pdm run run-hemma --shell 'command -v docker && docker --version'
pdm run run-hemma --shell 'sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

## GPU Verification (ROCm/HIP)

```bash
pdm run run-hemma -- rocminfo
pdm run run-hemma -- rocm-smi
pdm run run-hemma --shell 'sudo docker exec -it <container_name> python -c "import torch; print(torch.cuda.is_available()); print(getattr(torch.version, \"hip\", None))"'
```

## GPU Runtime Compliance Gate (Task 12+)

Use deterministic compliance checks before GPU-governed conversion workloads:

```bash
pdm run run-local-pdm hemma-verify-gpu-runtime
```

If verification fails due a non-ROCm torch runtime in the project environment:

```bash
pdm run run-local-pdm hemma-repair-rocm-runtime
pdm run run-local-pdm hemma-verify-gpu-runtime
```

Compliance pass conditions:

- `/healthz` reports deterministic service metadata:
  - `service_revision` equals Hemma repo `HEAD`,
  - `started_at` is newer than current `HEAD` commit timestamp.
- `rocm-smi` detects the GPU.
- `probe_torch_gpu_runtime()` reports `runtime_kind="rocm"` and `is_available=true`.
- Live `gpu_required` conversion succeeds with `conversion_metadata.acceleration_used="cuda"`.
- No `docling_cuda_unavailable_fallback_cpu` warning.
- `rocm-smi` observes non-zero GPU busy during conversion.

## Tunnel Workflow (Local Dev from Any Repo)

Use a dedicated local-only service port to avoid collisions with other stacks.
Recommended first assignment for Sir Convert-a-Lot: `28085`.

```bash
ssh hemma -L 28085:127.0.0.1:28085 -N
curl -fsS http://127.0.0.1:28085/healthz
```

Then run conversion from any repository:

```bash
pdm run convert-a-lot convert ./pdfs \
  --output-dir ./research \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_API_KEY"
```

## Canonical Live Docling GPU Validation

Run the committed live-runner surface (argv mode, no inline shell payloads):

```bash
pdm run run-hemma -- pdm run validate:docling-gpu-live \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_API_KEY" \
  --output-root build/manual-validation-quality-control
```

## Deployment Pattern

- Pull tracked changes on Hemma with `git pull`.
- Do not use `scp` for tracked repository files.
- Keep service internal-only (localhost bind + tunnel) until public exposure is explicitly decided.
- Keep GPU as default execution policy; CPU fallback requires documented decision update.

## Cross-Repo Coexistence Notes

- Reserve unique service ports per app to avoid collisions:
  - Skriptoteket web/proxy stack (existing compose)
  - HuleEdu LanguageTool/offload stack (existing compose)
  - Sir Convert-a-Lot conversion service (new compose)
- Keep this service on shared operational conventions (SSH alias, Docker commands, logs, health checks)
  so assistants can execute the same mental model across repos.
