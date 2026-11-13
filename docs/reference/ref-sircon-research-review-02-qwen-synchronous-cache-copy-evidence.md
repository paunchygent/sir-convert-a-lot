---
type: reference
id: REF-SIRCON-RESEARCH-review-02-qwen-synchronous-cache-copy-evidence
title: Review 02 Qwen Synchronous Cache Copy Evidence
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: research
summary: Review 02 Qwen Synchronous Cache Copy Evidence
retired_ids:
- REF-review-02-qwen-synchronous-cache-copy-evidence
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

## Historical Source Content

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
