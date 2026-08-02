---
type: reference
id: REF-SIRCON-RESEARCH-review-02-qwen-ungraceful-detached-shutdown-evidence
title: Review 02 Qwen Ungraceful Detached Shutdown Evidence
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: research
summary: Review 02 Qwen Ungraceful Detached Shutdown Evidence
retired_ids:
- REF-review-02-qwen-ungraceful-detached-shutdown-evidence
---


## Research Purpose And Boundary

State the question, the later decision or contract this research may inform,
the evidence boundary, and explicit exclusions.

## Evidence And Sources

List each repository source, retained artifact, experiment, external source, or
observation with enough provenance to verify it. Distinguish observed,
inherited, inferred, and unresolved evidence.

## Findings And Interpretation

Record findings supported by the evidence, their practical meaning, conflicts,
and limitations. Keep facts separate from interpretation.

## Evidence Gaps And Follow-Up

State missing evidence, why it matters, and the owning research, decision,
backlog, ADR, or runbook follow-up. Do not use this section as implementation
status or authority.

## Source Body Preservation

## Purpose
Preserve the code-level evidence behind Review 02's detached shutdown finding without misclassifying the evidence note as a standalone backlog review.
**Source:** `scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/launch_service.py`
**Lines:** `378-390`
This orchestration code uses `docker stop` to terminate the detached pilot. Docker defaults to sending `SIGTERM` followed by a grace period and then `SIGKILL`.
`def stop_detached_pilot(launch: Task101DetachedLaunch) -> Task101DetachedStop: """Stop one detached Task 101 pilot container intentionally.""" stop_output = docker_checked( ["stop", launch.container_name], label="docker stop qwen detached pilot", ) return Task101DetachedStop( stopped_at=_utc_now_iso(), launch_id=launch.launch_id, container_name=launch.container_name, container_id=launch.container_id, stop_output=stop_output.strip(), )`
**Missing handler in:** `scripts/devops/qwen_finetuning_patches/sft_12hz.py`
The underlying PyTorch training script `train_with_args` originally contained a standard `for epoch in range(...)` loop without any `signal` traps for `SIGTERM`.
When `docker stop` is invoked, the Python process can terminate without dumping the current optimizer state or triggering `_save_durable_checkpoint` for partial progress within the epoch.

