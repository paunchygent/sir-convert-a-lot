---
type: reference
id: REF-dockerized-hemma-gpu-passthrough-gap-2026-02-16
title: 'Reference: Dockerized Hemma GPU passthrough gap (2026-02-16)'
status: active
created: '2026-02-16'
updated: '2026-02-16'
owners:
  - platform
tags:
  - hemma
  - docker
  - gpu
  - rocm
links:
  - docs/backlog/tasks/task-27-dockerized-hemma-rocm-gpu-passthrough-and-runtime-wheel-pinning.md
---

## Purpose

Capture the concrete pre-fix gap between dockerized service readiness and actual
GPU usability on Hemma.

## Observed State (Before Task 27)

- Git revision deployed: `aadab112f48679fad5c94380a80f7c57e0813f7d`.
- Dockerized services:
  - `http://127.0.0.1:8085/readyz` -> ready (revision matches `aadab11`).
  - `http://127.0.0.1:8086/readyz` -> ready (revision matches `aadab11`).
- In-container torch probe (prod container):
  - `torch_version="2.10.0+cu128"`
  - `runtime_kind="cuda"`
  - `is_available=false`
  - `device_count=0`
- Device nodes inside container:
  - `/dev/kfd` missing
  - `/dev/dri` missing

## Impact

- Dockerized lane is operational from readiness perspective, but cannot satisfy
  GPU-required conversion invariants.
- GPU verification success on host-process lane (`28085/28086`) does not prove
  dockerized GPU correctness.

## Task Direction

Task 27 must close this gap by enforcing ROCm wheel pinning in image build and
explicit GPU passthrough in compose runtime, then re-verifying on `8085/8086`.
