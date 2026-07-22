"""Run public Qwen commands through the isolated nested PDM project.

The root command surface remains stable while dependency ownership, lock
freshness, and the installed environment belong exclusively to ``qwen/``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from packaging.markers import UndefinedComparison, UndefinedEnvironmentName
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

CommandRunner = Callable[[tuple[str, ...], Path], int]
EnvironmentFreshnessChecker = Callable[[Path], bool]
StructuredCommandRunner = Callable[[tuple[str, ...], Path], subprocess.CompletedProcess[str]]
_QWEN_LOCK_EXPORT_COMMAND = (
    "pdm",
    "export",
    "-p",
    "qwen",
    "-G",
    "dev",
    "--without-hashes",
)
_QWEN_INSTALLED_LIST_COMMAND = (
    "pdm",
    "list",
    "-p",
    "qwen",
    "--json",
    "--fields",
    "name,version",
)
_QWEN_MARKER_ENVIRONMENT_MODULE = "scripts.sir_convert_a_lot.devops.qwen_marker_environment"
_MARKER_ENVIRONMENT_KEYS = frozenset(
    {
        "implementation_name",
        "implementation_version",
        "os_name",
        "platform_machine",
        "platform_release",
        "platform_system",
        "platform_version",
        "platform_python_implementation",
        "python_full_version",
        "python_version",
        "sys_platform",
    }
)


def _run_command(command: tuple[str, ...], cwd: Path) -> int:
    completed = subprocess.run(command, cwd=cwd, check=False)
    return completed.returncode


def _run_structured_command(
    command: tuple[str, ...],
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _qwen_marker_environment_command(project_root: Path) -> tuple[str, ...]:
    nested_interpreter = project_root / "qwen" / ".venv" / "bin" / "python"
    return (str(nested_interpreter), "-m", _QWEN_MARKER_ENVIRONMENT_MODULE)


def _marker_environment(marker_environment_json: str) -> dict[str, str] | None:
    try:
        values = json.loads(marker_environment_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(values, dict) or set(values) != _MARKER_ENVIRONMENT_KEYS:
        return None

    marker_environment: dict[str, str] = {}
    for key in _MARKER_ENVIRONMENT_KEYS:
        value = values.get(key)
        if not isinstance(value, str):
            return None
        marker_environment[key] = value
    return marker_environment


def _exported_lock_versions(
    requirements_text: str,
    marker_environment: dict[str, str],
) -> dict[str, Version] | None:
    expected_versions: dict[str, Version] = {}
    for raw_line in requirements_text.splitlines():
        requirement_text = raw_line.strip()
        if not requirement_text or requirement_text.startswith("#"):
            continue
        try:
            requirement = Requirement(requirement_text)
        except InvalidRequirement:
            return None
        if requirement.marker is not None:
            try:
                marker_applies = requirement.marker.evaluate(marker_environment)
            except (UndefinedComparison, UndefinedEnvironmentName):
                return None
            if not marker_applies:
                continue

        specifiers = tuple(requirement.specifier)
        if len(specifiers) != 1:
            return None
        specifier = specifiers[0]
        if specifier.operator != "==" or specifier.version.endswith(".*"):
            return None
        try:
            expected_version = Version(specifier.version)
        except InvalidVersion:
            return None

        name = canonicalize_name(requirement.name)
        existing_version = expected_versions.get(name)
        if existing_version is not None and existing_version != expected_version:
            return None
        expected_versions[name] = expected_version

    return expected_versions or None


def _installed_environment_versions(installed_json: str) -> dict[str, Version] | None:
    try:
        records = json.loads(installed_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(records, list):
        return None

    installed_versions: dict[str, Version] = {}
    for record in records:
        if not isinstance(record, dict):
            return None
        raw_name = record.get("name")
        raw_version = record.get("version")
        if not isinstance(raw_name, str) or not isinstance(raw_version, str):
            return None
        try:
            version = Version(raw_version)
        except InvalidVersion:
            return None

        name = canonicalize_name(raw_name)
        if name in installed_versions:
            return None
        installed_versions[name] = version

    return installed_versions


def _qwen_environment_matches_lock(
    project_root: Path,
    structured_command_runner: StructuredCommandRunner = _run_structured_command,
) -> bool:
    try:
        marker_environment_result = structured_command_runner(
            _qwen_marker_environment_command(project_root),
            project_root,
        )
    except OSError:
        return False
    if marker_environment_result.returncode != 0:
        return False
    marker_environment = _marker_environment(marker_environment_result.stdout)
    if marker_environment is None:
        return False

    try:
        export = structured_command_runner(_QWEN_LOCK_EXPORT_COMMAND, project_root)
    except OSError:
        return False
    if export.returncode != 0:
        return False
    expected_versions = _exported_lock_versions(export.stdout, marker_environment)
    if expected_versions is None:
        return False

    try:
        installed = structured_command_runner(_QWEN_INSTALLED_LIST_COMMAND, project_root)
    except OSError:
        return False
    if installed.returncode != 0:
        return False
    installed_versions = _installed_environment_versions(installed.stdout)
    return installed_versions == expected_versions


def run_qwen_project(
    project_root: Path,
    arguments: Sequence[str],
    command_runner: CommandRunner = _run_command,
    environment_freshness_checker: EnvironmentFreshnessChecker = _qwen_environment_matches_lock,
) -> int:
    """Validate and execute one command through the Qwen-owned environment."""
    qwen_root = project_root / "qwen"
    required_paths = (
        qwen_root / "pyproject.toml",
        qwen_root / "pdm.lock",
        qwen_root / ".venv" / "bin" / "python",
    )
    missing_paths = tuple(path for path in required_paths if not path.exists())
    if missing_paths:
        missing = ", ".join(path.relative_to(project_root).as_posix() for path in missing_paths)
        print(
            f"nested Qwen environment is missing required paths: {missing}; "
            "run `pdm install -p qwen -G dev`",
            file=sys.stderr,
        )
        return 2
    if not arguments:
        print("a nested Qwen command is required", file=sys.stderr)
        return 2

    lock_check = ("pdm", "lock", "-p", "qwen", "--check")
    if command_runner(lock_check, project_root) != 0:
        print(
            "nested Qwen lock is stale; run `pdm lock -p qwen` and reinstall the environment",
            file=sys.stderr,
        )
        return 2

    if not environment_freshness_checker(project_root):
        print(
            "nested Qwen environment does not match qwen/pdm.lock; "
            "run `pdm install -p qwen -G dev` to synchronize it",
            file=sys.stderr,
        )
        return 2

    command = ("pdm", "run", "-p", "qwen", *arguments)
    return command_runner(command, project_root)
