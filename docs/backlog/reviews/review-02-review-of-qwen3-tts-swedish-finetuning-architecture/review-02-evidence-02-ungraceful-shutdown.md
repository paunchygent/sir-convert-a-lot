---
id: review-02-evidence-02-ungraceful-shutdown
title: 'Evidence: Ungraceful Detached Shutdown'
type: review
status: completed
priority: high
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture/README.md
labels: []
---

**Source:** `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py`
**Lines:** 378-390

This orchestration code uses `docker stop` to terminate the detached pilot. Docker defaults to sending `SIGTERM` followed by a 10-second wait, and then `SIGKILL`.

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

**Missing Handler in:** `scripts/devops/qwen_finetuning_patches/sft_12hz.py`

The underlying PyTorch training script `train_with_args` contains a standard `for epoch in range(...)` loop without any `signal` module imports or traps for `SIGTERM`.

When `docker stop` is invoked, the Python process is immediately terminated by `SIGTERM`, failing to dump the current optimizer state or trigger `_save_durable_checkpoint` for partial progress within the epoch.
