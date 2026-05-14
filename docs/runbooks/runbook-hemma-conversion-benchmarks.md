---
type: runbook
id: RUN-hemma-conversion-benchmarks
title: Hemma Conversion Benchmark Runbook for Sir Convert-a-Lot
status: active
created: '2026-05-14'
updated: '2026-05-14'
owners:
  - platform
system: hemma.hule.education
tags:
  - benchmark
  - conversion
  - throughput
  - smoke
links:
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-hemma-service-ops.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
---

## Purpose

Run conversion smoke, throughput, and bottleneck checks without turning the
general Hemma runbook into a historical benchmark log.

## Scope

Use this runbook for:

- v2 conversion smoke verification;
- local parallel throughput fixtures;
- Hemma throughput benchmark harnesses;
- bottleneck triage after runtime or parser changes.

Do not store full benchmark reports here. Retain deterministic JSON/Markdown
outputs under the governing task or ignored artifact root, then summarize only
the decision-relevant result in docs.

## Preconditions

- Governing task identifies the artifact set, expected lane, and evidence root.
- Remote repo is `/home/paunchygent/apps/sir-convert-a-lot`.
- GPU/cache preflight has passed when the benchmark depends on GPU.
- The service lane is reachable through `http://127.0.0.1:28085` when the test
  is service-backed.

## Execution Rules

- Prefer named `pdm run ...` wrappers over ad hoc shell.
- Use detached surfaces for long benchmark runs.
- Keep generated artifacts out of git unless a sanitized summary is explicitly
  promoted by the task.
- Record runtime revision, input manifest, command surface, and output root.
- Compare output correctness before throughput. A faster wrong conversion is a
  failed benchmark.

## Evidence Checklist

- [ ] Repo revision recorded.
- [ ] Input artifact manifest recorded.
- [ ] Runtime lane recorded: local, host, container, tunnel, or public.
- [ ] GPU/offload state recorded when relevant.
- [ ] Structured report retained outside governed docs.
- [ ] Governed task/reference updated with a concise result and next action.

## Triage Order

1. Confirm service health and route.
1. Confirm artifact intake and manifest.
1. Confirm parser/OCR/runtime logs.
1. Confirm CPU/GPU utilization and memory pressure.
1. Confirm output contract, manifest, and manual-follow-up semantics.

If a repeated benchmark needs a stable command, promote it to a committed script
before the next run.
