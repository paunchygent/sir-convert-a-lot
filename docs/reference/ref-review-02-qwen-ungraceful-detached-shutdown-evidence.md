---
type: reference
id: REF-review-02-qwen-ungraceful-detached-shutdown-evidence
title: Review 02 Qwen Ungraceful Detached Shutdown Evidence
status: active
created: '2026-03-09'
owners:
  - platform
updated: '2026-03-09'
related:
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture.md
---

## Purpose

Preserve the code-level evidence behind Review 02's detached shutdown finding
without misclassifying the evidence note as a standalone backlog review.

**Source:** `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py`
**Lines:** `378-390`

This orchestration code uses `docker stop` to terminate the detached pilot.
Docker defaults to sending `SIGTERM` followed by a grace period and then
`SIGKILL`.

```python
def stop_detached_pilot(launch: Task101DetachedLaunch) -> Task101DetachedStop:
    """Stop one detached Task 101 pilot container intentionally."""
    stop_output = docker_checked(
        ["stop", launch.container_name],
        label="docker stop task101 detached pilot",
    )
    return Task101DetachedStop(
        stopped_at=_utc_now_iso(),
        launch_id=launch.launch_id,
        container_name=launch.container_name,
        container_id=launch.container_id,
        stop_output=stop_output.strip(),
    )
```

**Missing handler in:** `scripts/devops/qwen_finetuning_patches/sft_12hz.py`

The underlying PyTorch training script `train_with_args` originally contained a
standard `for epoch in range(...)` loop without any `signal` traps for
`SIGTERM`.

When `docker stop` is invoked, the Python process can terminate without dumping
the current optimizer state or triggering `_save_durable_checkpoint` for
partial progress within the epoch.
