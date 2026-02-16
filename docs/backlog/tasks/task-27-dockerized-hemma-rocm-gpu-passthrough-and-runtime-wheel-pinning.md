---
id: task-27-dockerized-hemma-rocm-gpu-passthrough-and-runtime-wheel-pinning
title: Dockerized Hemma ROCm GPU passthrough and runtime wheel pinning
type: task
status: completed
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

- [x] Docker image build uses decided ROCm torch wheel pins.
- [x] Compose runtime maps required GPU devices/groups for ROCm workloads.
- [x] Verification surface passes on docker lane with GPU proof.
- [x] Docs/runbook updated with canonical docker GPU verification commands.

## Acceptance Criteria

- [x] In-container probe reports `runtime_kind="rocm"` and `is_available=true`.
- [x] Dockerized `readyz` on `8085`/`8086` is `ready=true` with current `HEAD` revision.
- [x] Live conversion through dockerized lane reports
  `conversion_metadata.acceleration_used="cuda"`.
- [x] No CPU fallback warning appears for GPU-required run.
- [x] `rocm-smi` shows non-zero utilization during docker-lane conversion.
- [x] `format-all`, `lint-fix`, `typecheck-all`, targeted pytest,
  `validate-tasks`, `validate-docs`, and index pass.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation and Evidence

- Initial baseline gap (documented in reference):
  - dockerized `8085/8086` was revision-ready but not GPU-ready,
  - runtime probe reported `torch==2.10.0+cu128`, `is_available=false`,
  - no `/dev/kfd` or `/dev/dri` in container.
- Implementation:
  - pinned ROCm torch build args in `Dockerfile`/`compose.yaml`,
  - added compose ROCm device passthrough mappings,
  - made verifier lane-aware (`host|docker`) and fixed readiness-contract script bug,
  - fixed docker runtime gaps discovered in validation:
    - bootstrap `pip` inside PDM venv before torch wheel replacement,
    - create required `video`/`render` groups in image,
    - install Docling shared libs (`libxcb1` and related X/GL runtime libs),
  - optimized compose topology to use one shared runtime image for prod+eval lanes
    (runtime overlays only, no duplicate image build by default).
- Hemma docker-lane evidence (`99e736e`):
  - `pdm run run-local-pdm run-hemma -- sudo docker exec sir_convert_a_lot_prod pdm run python -c "...torch probe..."`
    reported `2.10.0+rocm7.1`, HIP `7.1.25424`, `torch.cuda.is_available() == True`,
  - `curl -fsS http://127.0.0.1:8085/readyz` and `:8086/readyz` returned
    `ready=true` with revision `99e736e...`,
  - `SIR_CONVERT_A_LOT_VERIFY_LANE=docker pdm run run-local-pdm hemma-verify-gpu-runtime`
    passed with:
    - `{"acceleration_used":"cuda","gpu_busy_peak":99,...}`,
    - no CPU fallback warning.
