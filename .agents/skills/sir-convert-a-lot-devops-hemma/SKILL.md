---
name: sir-convert-a-lot-devops-hemma
description: >
  Repo-specific DevOps skill for running Sir Convert-a-Lot on Hemma with GPU-first
  policy, tunnel-first local development, and cross-repo awareness of HuleEdu and
  Skriptoteket server layout.
---

# Sir Convert-a-Lot DevOps (Hemma + GPU)

## Use This Skill When

- Deploying or troubleshooting Sir Convert-a-Lot on `hemma.hule.education`.
- Verifying GPU/ROCm readiness for conversion workloads.
- Running local-to-remote tunnel workflows for conversion jobs.
- Coordinating coexistence with HuleEdu and Skriptoteket on the same host.

## Source of Truth

- `docs/runbooks/runbook-hemma-devops-and-gpu.md`
- `docs/converters/pdf_to_md_service_api_v1.md`
- `docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md`

Cross-repo operational references:
- `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/operations/hemma-server-operations-huleedu.md`
- `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/operations/gpu-ai-workloads-on-hemma-huleedu.md`
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

## Hemma Repo Topology Awareness

- `~/apps/sir-convert-a-lot`: this service repo.
- `~/apps/huleedu`: HuleEdu stack + NLP offload.
- `~/apps/skriptoteket`: Skriptoteket stack.
- `~/infrastructure`: shared nginx/certbot edge infra.

## GPU-First Guardrails

- Prefer GPU execution path by default for conversion service workloads.
- Never silently switch to CPU fallback when GPU is unavailable.
- If fallback policy changes, require ADR/task updates first.

## Tunnel-First Dev Flow

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
