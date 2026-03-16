"""Tests for shared Qwen storage-tier helpers.

Purpose:
    Verify the common storage helper behavior that underpins scratch-to-storage
    migration and symlink-backed path stability for Hemma remediation flows.

Relationships:
    - Covers `scripts.sir_convert_a_lot.ml.qwen.common.storage`.
    - Protects the symlink fallback used by Task 204 and Task 205 archive paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.common.storage import replace_with_canonical_symlink


def test_replace_with_canonical_symlink_falls_back_to_sudo_when_symlink_creation_is_denied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Storage helpers should retry symlink creation with sudo on protected roots."""
    source_path = tmp_path / "scratch" / "source"
    target_path = tmp_path / "storage" / "target"
    target_path.parent.mkdir(parents=True)
    target_path.write_text("ok", encoding="utf-8")
    seen: list[tuple[list[str], str]] = []

    def fake_symlink_to(self: Path, target: Path, target_is_directory: bool = False) -> None:
        del self, target, target_is_directory
        raise PermissionError("denied")

    def fake_run_checked(command: list[str], *, label: str) -> str:
        seen.append((command, label))
        return "ok"

    monkeypatch.setattr(Path, "symlink_to", fake_symlink_to)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.storage.run_checked",
        fake_run_checked,
    )

    replace_with_canonical_symlink(source_path, target_path)

    assert seen == [
        (
            ["sudo", "-n", "ln", "-s", target_path.as_posix(), source_path.as_posix()],
            "sudo ln symlink",
        )
    ]
