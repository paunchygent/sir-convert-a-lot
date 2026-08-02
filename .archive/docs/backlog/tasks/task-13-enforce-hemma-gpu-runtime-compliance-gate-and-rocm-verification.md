---
id: task-13-enforce-hemma-gpu-runtime-compliance-gate-and-rocm-verification
title: Enforce Hemma GPU runtime compliance gate and ROCm verification
type: task
status: completed
priority: high
created: '2026-02-15'
last_updated: '2026-02-15'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - gpu
  - hemma
  - rocm
  - runtime
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Ensure GPU-required Docling execution is fail-closed unless a real ROCm/CUDA runtime is
available, and provide deterministic Hemma verification/remediation workflows so Task 12
acceptance/evaluation runs are trustworthy.

## PR Scope

1. Add typed GPU runtime probe in infrastructure.
1. Enforce fail-closed backend behavior for `gpu_available=True` when probe is unavailable.
1. Map backend GPU runtime unavailability to deterministic API/runtime `503 gpu_not_available`.
1. Add Hemma verify/repair scripts and PDM script surfaces.
1. Update Task 12 and converter/runbook docs with the compliance gate.
1. Add/adjust tests for probe classification and fail-closed mapping.

## Deliverables

- [x] `scripts/sir_convert_a_lot/infrastructure/gpu_runtime_probe.py`
- [x] Updated backend/runtime mapping for GPU-runtime unavailability
- [x] `scripts/devops/verify-hemma-gpu-runtime.sh`
- [x] `scripts/devops/repair-hemma-rocm-runtime.sh`
- [x] Updated docs in task/runbook/converter/API references
- [x] Updated targeted tests for probe + fail-closed behavior

## Acceptance Criteria

- [x] GPU-required Docling requests do not silently execute on CPU when GPU runtime probe is unavailable.
- [x] Runtime/API returns deterministic `503 gpu_not_available` with
  `details.reason=backend_gpu_runtime_unavailable`.
- [x] Hemma verification command proves `conversion_metadata.acceleration_used == "cuda"` on
  a real PDF conversion and records non-zero GPU busy during conversion.
- [x] Validation gates pass for code + docs.

## Checklist

- [x] Docs kickoff and context updates complete
- [x] Implementation complete
- [x] Hemma verification/remediation scripts validated
- [x] Validation complete
- [x] Docs updated
