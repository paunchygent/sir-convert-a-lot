---
id: review-02-evidence-03-synchronous-cache-copy
title: 'Evidence: Dangerous Synchronous Cache Copying'
type: review
status: completed
priority: high
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture/README.md
labels: []
---

**Source:** `scripts/sir_convert_a_lot/devops/task100_qwen_finetune_runtime.py`
**Lines:** 203-220

This code illustrates the hardcoded synchronous `for`-loop wrapping `cp -a` to copy potentially massive Hugging Face caches (containing base models, datasets, etc.) when the canonical Hemma cache root is empty.

```python
def _sync_home_cache_into_data_disk(canonical_dir: Path, home_mount: Path) -> None:
    """Copy any existing home-backed cache files into the canonical cache root."""
    if not home_mount.exists():
        return
    for source in sorted(home_mount.iterdir()):
        target = canonical_dir / source.name
        if target.exists():
            continue
        if source.is_dir():
            subprocess.run(
                ["cp", "-a", source.as_posix(), target.as_posix()],
                check=True,
                capture_output=True,
                text=True,
            )
            continue
        target.write_bytes(source.read_bytes())
```

If interrupted, `cp -a` leaves partial files, and this python-level iteration provides no progress output to the user. For a >50GB `HF_HOME`, the runner will appear completely frozen.
