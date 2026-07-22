"""Architecture guard tests for the Qwen training control plane.

Purpose:
    Enforce Qwen training control-plane boundaries so CLI, runtime, and
    reporting responsibilities stay separated.

Relationships:
    - Guards the public CLI composition root and extracted runtime packages.
    - Fails fast if broad orchestration modules are reintroduced.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _line_count(path: Path) -> int:
    """Return the total line count for one source file."""
    return len(path.read_text(encoding="utf-8").splitlines())


def test_broad_qwen_orchestration_modules_stay_absent() -> None:
    """Broad orchestrator and reporting modules should stay absent."""
    assert not (REPO_ROOT / "scripts/sir_convert_a_lot/ml/qwen/training/orchestrator.py").exists()
    assert not (REPO_ROOT / "scripts/sir_convert_a_lot/ml/qwen/training/reporting.py").exists()


def test_hot_path_modules_stay_under_architecture_line_caps() -> None:
    """Hot-path Qwen modules should stay below the enforced Qwen architecture boundary caps."""
    assert _line_count(REPO_ROOT / "scripts/sir_convert_a_lot/cli/ml/qwen_train.py") <= 250
    assert _line_count(REPO_ROOT / "scripts/devops/qwen_finetuning_patches/sft_12hz_loop.py") <= 400
    assert (
        _line_count(
            REPO_ROOT
            / "scripts/sir_convert_a_lot/ml/qwen/training/control_plane/launch_use_case.py"
        )
        <= 400
    )
    assert (
        _line_count(
            REPO_ROOT
            / "scripts/sir_convert_a_lot/ml/qwen/training/detached_runtime/launch_service.py"
        )
        <= 400
    )


def test_qwen_train_py_stays_a_true_composition_root() -> None:
    """The public CLI file should only define `main` and delegate everything else."""
    cli_path = REPO_ROOT / "scripts/sir_convert_a_lot/cli/ml/qwen_train.py"
    module = ast.parse(cli_path.read_text(encoding="utf-8"))

    function_defs = [
        node.name
        for node in module.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert function_defs == ["main"]
