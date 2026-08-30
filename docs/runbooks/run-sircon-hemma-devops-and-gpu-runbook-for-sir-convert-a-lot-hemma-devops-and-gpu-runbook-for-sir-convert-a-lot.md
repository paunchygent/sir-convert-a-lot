---
type: runbook
id: RUN-SIRCON-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot
title: Hemma DevOps and GPU Runbook for Sir Convert-a-Lot
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-02'
status: active
summary: Hemma DevOps and GPU Runbook for Sir Convert-a-Lot
system: hemma.hule.education
retired_ids:
  - RUN-hemma-devops-and-gpu
---

## Trigger

## Preconditions

## Steps

## Expected Results

## Stop Conditions

## Rollback

## Historical Source Content

### Purpose

This is the doorway for Sir Convert-a-Lot Hemma operations. It routes to focused
runbooks and holds only the invariants that apply across service, GPU, model,
benchmark, and tunnel work.

### Route By Job

| Job                                                                        | Read                                                    |
| -------------------------------------------------------------------------- | ------------------------------------------------------- |
| Service placement, deploys, tunnels, health checks, prod env mirror        | `docs/runbooks/runbook-hemma-service-ops.md`            |
| GPU checks, scratch-backed caches, vLLM, llama.cpp, Docling GPU validation | `docs/runbooks/runbook-hemma-gpu-runtime.md`            |
| Conversion smoke tests, throughput, bottleneck triage                      | `docs/runbooks/runbook-hemma-conversion-benchmarks.md`  |
| TTS sidecar and Swedish voice benchmark lanes                              | `docs/runbooks/runbook-hemma-tts-sidecar-benchmarks.md` |
| Public API or CLI contract behavior                                        | `docs/converters/` and `docs/decisions/`                |

### Global Invariants

- Canonical remote repo: `/home/paunchygent/apps/sir-convert-a-lot`.
- Canonical Hemma command wrapper: `pdm run run-hemma -- ...`.
- `run-hemma` SSHes from client machines and runs directly when the current
  session is already in the canonical Hemma Server checkout.
- `pdm run run-hemma --shell ...` is for short probes that need shell syntax.
- Long-running Hemma work uses committed detached runners or supervised remote
  surfaces.
- Canonical client tunnel lane: `http://127.0.0.1:28085`.
- Docker work uses BuildKit and Docker Compose v2.
- GPU/offload work is GPU-first; no silent CPU fallback.
- Long-lived Docker state, model caches, and generated active artifacts stay on
  `/srv/scratch`, not the Hemma OS disk.
- Raw corpora and cold completed artifacts belong on `/srv/storage`.
- Runtime changes need governing backlog/reference/ADR authority before they are
  treated as product behavior.

### Closeout

For docs or operational-governance edits, run:

```bash
pdm run docs-sync
pdm run docs-validate
pdm run skills-validate
pdm run handoff-validate
git diff --check
```

If a procedure grows beyond this routing surface, move it into one focused
runbook. If evidence grows beyond a focused runbook, move it into the governing
task or reference document.
