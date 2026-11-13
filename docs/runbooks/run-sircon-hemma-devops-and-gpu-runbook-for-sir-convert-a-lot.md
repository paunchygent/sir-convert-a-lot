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

| Job                                                                 | Read                                                            |
| ------------------------------------------------------------------- | --------------------------------------------------------------- |
| Storage placement, migration, backup and bind-root cutover          | [Storage Placement And Cutover](#storage-placement-and-cutover) |
| Service placement, deploys, tunnels, health checks, prod env mirror | `docs/runbooks/runbook-hemma-service-ops.md`                    |
| GPU checks, cache runtime, vLLM, llama.cpp, Docling GPU validation  | `docs/runbooks/runbook-hemma-gpu-runtime.md`                    |
| Conversion smoke tests, throughput, bottleneck triage               | `docs/runbooks/runbook-hemma-conversion-benchmarks.md`          |
| TTS sidecar and Swedish voice benchmark lanes                       | `docs/runbooks/runbook-hemma-tts-sidecar-benchmarks.md`         |
| Public API or CLI contract behavior                                 | `docs/converters/` and `docs/decisions/`                        |

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
- New storage placement follows [Storage Placement And Cutover](#storage-placement-and-cutover).
- Runtime changes need governing backlog/reference/ADR authority before they are
  treated as product behavior.

### Storage Placement And Cutover

TASK-SIRCON-REP-0033 D01–D04 supersedes the former scratch build/cache and
`/srv/storage` primary corpus/archive guidance. Hot holds persistent Sir build,
proof, model, corpus and legacy archive assets for their required lifetime.
Scratch holds short-lived disposable single-agent operational work of any file
type; promote useful results before retention or inter-agent handoff. Context
and retained evidence remain Hot; `/srv/storage` is backup-only. Retain
historical evidence paths and preserve logical paths
through verified migration. Cache still has a separate legacy default and owner.

Read `skill-repository/docs/runbooks/runbook-hemma-storage-migration-and-research-backups.md`
through the harness's canonical `skill-repository` alias for the single shared
host procedure. The parent owns writer-safe cutover, installation and physical
backing/probe receipts; source-only adapter checks do not prove activation.
Shared weekly `hemma-docker-cleanup` owns Docker cleanup. Sir defaults and
producer protections are in the [Qwen storage section](run-sircon-qwen3-tts-swedish-finetuning-runbook-for-hemma-and-colab-qwen3-tts-swedish-finetuning-runbook-for-hemma-and-colab.md#storage-and-cutover).

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
