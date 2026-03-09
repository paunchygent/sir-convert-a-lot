---
type: reference
id: REF-review-02-qwen-synchronous-cache-copy-evidence
title: Review 02 Qwen Synchronous Cache Copy Evidence
status: active
created: '2026-03-09'
owners:
  - platform
updated: '2026-03-09'
related:
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture.md
---

## Purpose

Preserve the code-level evidence behind Review 02's cache-sync finding without
turning the evidence note into an invalid nested review.

**Source:** `scripts/sir_convert_a_lot/devops/task100_qwen_finetune_runtime.py`
**Lines:** `203-220`

This code illustrates the old synchronous `for`-loop wrapping `cp -a` to copy
potentially massive Hugging Face caches when the canonical Hemma cache root is
empty.

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

If interrupted, `cp -a` can leave partial files, and this python-level
iteration provides no progress output to the user. For a very large `HF_HOME`,
the runner can appear completely frozen.
