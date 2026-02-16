---
id: task-27-dockerized-hemma-rocm-gpu-passthrough-and-runtime-wheel-pinning
title: Dockerized Hemma ROCm GPU passthrough and runtime wheel pinning
type: task
status: in_progress
priority: critical
created: '2026-02-16'
last_updated: '2026-02-16'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-22-docker-compose-service-packaging-and-readiness-gated-startup.md
  - docs/backlog/tasks/task-26-docling-form-cluster-ordering-source-patch-with-deterministic-quality-gate-and-fallback.md
  - docs/reference/ref-dockerized-hemma-gpu-passthrough-gap-2026-02-16.md
labels:
  - docker
  - hemma
  - rocm
  - gpu
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make the dockerized Hemma service lane (`8085/8086`) GPU-capable and
deterministic by enforcing the decided ROCm torch wheel pins and explicit
device passthrough, then verify live conversion uses GPU.

## PR Scope

- Enforce ROCm wheel pinning in container image build:
  - `torch==2.10.0+rocm7.1`
  - `torchvision==0.25.0+rocm7.1`
  - `torchaudio==2.10.0+rocm7.1`
- Add deterministic compose runtime GPU device passthrough for AMD/ROCm on Hemma.
- Fix Hemma GPU verification script reliability (current shell quoting bug causing
  `NameError` in readiness contract check).
- Add a docker-lane GPU verification surface for `8085/8086` that validates:
  - readiness revision contract,
  - in-container torch probe,
  - live conversion metadata and host GPU activity.
- Update operational docs for the docker GPU lane.

Out of scope:

- Non-Hemma infrastructure migration.
- New API contract fields.

## Deliverables

- [ ] Docker image build uses decided ROCm torch wheel pins.
- [ ] Compose runtime maps required GPU devices/groups for ROCm workloads.
- [ ] Verification surface passes on docker lane with GPU proof.
- [ ] Docs/runbook updated with canonical docker GPU verification commands.

## Acceptance Criteria

- [ ] In-container probe reports `runtime_kind="rocm"` and `is_available=true`.
- [ ] Dockerized `readyz` on `8085`/`8086` is `ready=true` with current `HEAD` revision.
- [ ] Live conversion through dockerized lane reports
  `conversion_metadata.acceleration_used="cuda"`.
- [ ] No CPU fallback warning appears for GPU-required run.
- [ ] `rocm-smi` shows non-zero utilization during docker-lane conversion.
- [ ] `format-all`, `lint-fix`, `typecheck-all`, targeted pytest,
  `validate-tasks`, `validate-docs`, and index pass.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Implementation and Evidence (planning kickoff)

- Baseline gap (current state before this task):
  - Dockerized services on `8085/8086` are healthy and revision-correct.
  - In-container torch probe currently reports `2.10.0+cu128`,
    `runtime_kind="cuda"`, `is_available=false`.
  - `/dev/kfd` and `/dev/dri` are absent in running containers.
- Separate host-process lane (`28085/28086`) currently has verified ROCm GPU,
  but that does not satisfy dockerized lane acceptance.
