"""Tests for narrow service dependency-image input contracts.

Purpose:
    Prove dependency image hashes are keyed by runtime dependency truth and
    runtime pins, not PDM scripts or unrelated pyproject metadata.

Relationships:
    - Covers `scripts.sir_convert_a_lot.devops.service_dependency_inputs`.
    - Supports Task 255 Docker dependency image cache-key invariants.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.service_dependency_inputs import (
    build_project_dependency_input_payload,
)


def _write_pyproject(project_root: Path, *, script_command: str, torch_version: str) -> None:
    """Write a minimal pyproject with dependency pins and unrelated scripts."""
    project_root.joinpath("pyproject.toml").write_text(
        f"""
[project]
name = "hash-fixture"
version = "0.1.0"
dependencies = [
    "fastapi>=0.128.8",
]

[tool.pdm.scripts]
"ops-only" = "{script_command}"

[tool.sir_convert_a_lot.rocm_runtime]
torch_index_url = "https://download.pytorch.org/whl/rocm7.1"
torch_version = "{torch_version}"
torchvision_version = "0.25.0+rocm7.1"
torchaudio_version = "2.10.0+rocm7.1"

[tool.sir_convert_a_lot.cpu_runtime]
torch_version = "2.10.0"
torchvision_version = "0.25.0"
torchaudio_version = "2.10.0"
""".lstrip(),
        encoding="utf-8",
    )


def _dependency_hash(project_root: Path, *, requirements_text: str) -> str:
    """Return the ROCm dependency hash for a temp project fixture."""
    payload = build_project_dependency_input_payload(
        project_root=project_root,
        requirements_text=requirements_text,
        runtime_kind="rocm",
    )
    return str(payload["dependency_hash"])


def test_pdm_script_only_pyproject_change_does_not_change_dependency_hash(
    tmp_path: Path,
) -> None:
    requirements_text = "fastapi==0.135.1\nuvicorn==0.40.0\n"
    _write_pyproject(
        tmp_path,
        script_command="python -m scripts.old",
        torch_version="2.10.0+rocm7.1",
    )
    before_hash = _dependency_hash(tmp_path, requirements_text=requirements_text)

    _write_pyproject(
        tmp_path,
        script_command="python -m scripts.new",
        torch_version="2.10.0+rocm7.1",
    )
    after_hash = _dependency_hash(tmp_path, requirements_text=requirements_text)

    assert after_hash == before_hash


def test_runtime_requirement_change_changes_dependency_hash(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        script_command="python -m scripts.same",
        torch_version="2.10.0+rocm7.1",
    )

    before_hash = _dependency_hash(
        tmp_path,
        requirements_text="fastapi==0.135.1\nuvicorn==0.40.0\n",
    )
    after_hash = _dependency_hash(
        tmp_path,
        requirements_text="fastapi==0.135.1\nuvicorn==0.40.1\n",
    )

    assert after_hash != before_hash


def test_runtime_pin_change_changes_dependency_hash(tmp_path: Path) -> None:
    requirements_text = "fastapi==0.135.1\nuvicorn==0.40.0\n"
    _write_pyproject(
        tmp_path,
        script_command="python -m scripts.same",
        torch_version="2.10.0+rocm7.1",
    )
    before_hash = _dependency_hash(tmp_path, requirements_text=requirements_text)

    _write_pyproject(
        tmp_path,
        script_command="python -m scripts.same",
        torch_version="2.10.1+rocm7.1",
    )
    after_hash = _dependency_hash(tmp_path, requirements_text=requirements_text)

    assert after_hash != before_hash
