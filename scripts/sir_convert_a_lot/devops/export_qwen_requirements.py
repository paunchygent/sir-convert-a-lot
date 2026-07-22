"""Generate Hemma Qwen requirements from the nested lock.

The Hemma image installs its governed ROCm GPU packages from the AMD-compatible
index before installing the remaining lock-derived dependencies.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

GPU_RUNTIME_PACKAGES = frozenset({"torch", "torchaudio", "torchvision", "triton"})
GPU_RUNTIME_PREFIXES = ("cuda-", "nvidia-", "triton-")
REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalized_requirement_name(line: str) -> str | None:
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    match = REQUIREMENT_NAME.match(line)
    if match is None:
        return None
    return re.sub(r"[-_.]+", "-", match.group(1)).lower()


def filter_container_requirements(exported: str) -> str:
    """Remove dependencies installed by the image's governed GPU runtime lane."""
    retained: list[str] = []
    for line in exported.splitlines():
        name = _normalized_requirement_name(line)
        if name in GPU_RUNTIME_PACKAGES:
            continue
        if name is not None and name.startswith(GPU_RUNTIME_PREFIXES):
            continue
        retained.append(line)
    return "\n".join(retained).rstrip() + "\n"


def export_qwen_requirements(project_root: Path) -> int:
    """Export the Qwen lock and write the filtered Hemma requirement set."""
    completed = subprocess.run(
        ("pdm", "export", "-p", "qwen", "--prod", "--without-hashes"),
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        return completed.returncode

    output_path = project_root / "containers" / "qwen-finetune-hemma" / "requirements.txt"
    output_path.write_text(filter_container_requirements(completed.stdout), encoding="utf-8")
    print(output_path.relative_to(project_root).as_posix())
    return 0


def main() -> int:
    """Generate the Qwen container requirements from the repository root."""
    project_root = Path(__file__).resolve().parents[3]
    return export_qwen_requirements(project_root)


if __name__ == "__main__":
    raise SystemExit(main())
