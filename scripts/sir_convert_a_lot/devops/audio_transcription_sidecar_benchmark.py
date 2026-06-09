"""Audio transcription sidecar benchmark preflight evidence.

Purpose:
    Build content-safe readiness reports for the governed Hemma speech-to-text
    sidecar benchmark before route registration consumes backend-profile data.

Relationships:
    - Supplies STT benchmark planning with operator evidence for codec tools, Python runtime
      packages, Hugging Face cache roots, and token-name readiness.
    - Complements audio-transcription profile selection profile-selection policy by separating
      environment
      readiness from later Swedish/English fixture, diarization, and 120-minute
      lifecycle proof.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.util import find_spec
from pathlib import Path
from typing import Mapping, TypedDict

from scripts.sir_convert_a_lot.benchmarking.output_policy import (
    enforce_generated_output_path,
)

REQUIRED_COMMANDS: tuple[str, ...] = ("ffmpeg", "ffprobe")
REQUIRED_PYTHON_MODULES: tuple[str, ...] = (
    "faster_whisper",
    "pyannote.audio",
    "huggingface_hub",
    "torch",
)
REQUIRED_SECRET_ENV_VARS: tuple[str, ...] = ("HF_TOKEN",)
PROFILE_PROOF_REJECTION_REASONS: tuple[str, ...] = (
    "sv_language_fixture_missing",
    "en_language_fixture_missing",
    "exact_speaker_count_not_exercised",
    "min_max_speaker_range_not_exercised",
    "duration_target_not_met",
    "duration_lifecycle_not_exercised",
)
NEXT_REQUIRED_EVIDENCE: tuple[str, ...] = (
    "run_swedish_fixture_with_language_detection",
    "run_english_fixture_with_language_detection",
    "exercise_exact_speaker_count_hint",
    "exercise_min_max_speaker_range_hint",
    "exercise_120_minute_batch_lifecycle",
)
DEFAULT_OUTPUT_ROOT = Path("build/verification/stt-sidecar-benchmark-preflight")
DEFAULT_HF_HOME = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_HUB_CACHE = DEFAULT_HF_HOME / "hub"


class CommandProbeReport(TypedDict):
    """Content-safe command availability report."""

    found: bool
    version_line: str


class PythonModuleProbeReport(TypedDict):
    """Content-safe Python module availability report."""

    importable: bool


class CacheProbeReport(TypedDict):
    """Content-safe cache-root readiness report."""

    hf_home: str
    hf_hub_cache: str
    roots_ready: bool


class SecretProbeReport(TypedDict):
    """Secret-name-only environment readiness report."""

    required_env_vars: tuple[str, ...]
    present_env_vars: tuple[str, ...]
    secret_values_exposed: bool


class ProfileSelectionPreflightReport(TypedDict):
    """Profile-selection status for preflight-only evidence."""

    selected: bool
    rejection_reasons: tuple[str, ...]


class BenchmarkPreflightReport(TypedDict):
    """Content-safe STT benchmark preflight report."""

    schema_version: str
    generated_at_utc: str
    preflight_ready: bool
    commands: dict[str, CommandProbeReport]
    python_modules: dict[str, PythonModuleProbeReport]
    cache: CacheProbeReport
    secrets: SecretProbeReport
    blocking_reasons: tuple[str, ...]
    next_required_evidence: tuple[str, ...]
    profile_selection: ProfileSelectionPreflightReport


@dataclass(frozen=True, slots=True)
class BenchmarkPreflightSettings:
    """Normalized settings for one STT sidecar benchmark preflight."""

    output_root: Path
    hf_home: Path
    hf_hub_cache: Path
    secret_env_var_names: tuple[str, ...]
    environment: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class CommandProbeResult:
    """Raw command-probe result before content-safe projection."""

    command_name: str
    found: bool
    version_line: str


@dataclass(frozen=True, slots=True)
class PythonModuleProbeResult:
    """Raw module-probe result before content-safe projection."""

    module_name: str
    importable: bool


def default_preflight_settings(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> BenchmarkPreflightSettings:
    """Build default settings for the Hemma STT benchmark preflight."""

    return BenchmarkPreflightSettings(
        output_root=output_root,
        hf_home=DEFAULT_HF_HOME,
        hf_hub_cache=DEFAULT_HF_HUB_CACHE,
        secret_env_var_names=REQUIRED_SECRET_ENV_VARS,
        environment={},
    )


def probe_command(command_name: str) -> CommandProbeResult:
    """Probe one command with `--version` and capture a sanitized first line."""

    try:
        result = subprocess.run(
            [command_name, "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10.0,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CommandProbeResult(command_name=command_name, found=False, version_line="")
    output = result.stdout.strip() or result.stderr.strip()
    version_line = output.splitlines()[0].strip() if output else ""
    return CommandProbeResult(
        command_name=command_name,
        found=result.returncode == 0,
        version_line=version_line,
    )


def probe_python_module(module_name: str) -> PythonModuleProbeResult:
    """Return whether one Python module name is available to the benchmark environment."""

    try:
        importable = find_spec(module_name) is not None
    except ModuleNotFoundError:
        importable = False
    return PythonModuleProbeResult(module_name=module_name, importable=importable)


def build_preflight_report(
    *,
    settings: BenchmarkPreflightSettings,
    command_probe_results: Mapping[str, CommandProbeResult] | None = None,
    python_module_probe_results: Mapping[str, PythonModuleProbeResult] | None = None,
) -> BenchmarkPreflightReport:
    """Build a content-safe STT benchmark preflight report."""

    commands = command_probe_results or {
        command_name: probe_command(command_name) for command_name in REQUIRED_COMMANDS
    }
    python_modules = python_module_probe_results or {
        module_name: probe_python_module(module_name) for module_name in REQUIRED_PYTHON_MODULES
    }
    blocking_reasons = tuple(_blocking_reasons(settings, commands, python_modules))
    preflight_ready = len(blocking_reasons) == 0
    return {
        "schema_version": "audio_transcription_sidecar_benchmark_preflight_v1",
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "preflight_ready": preflight_ready,
        "commands": {
            name: {"found": result.found, "version_line": result.version_line}
            for name, result in sorted(commands.items())
        },
        "python_modules": {
            name: {"importable": result.importable}
            for name, result in sorted(python_modules.items())
        },
        "cache": {
            "hf_home": "configured",
            "hf_hub_cache": "configured",
            "roots_ready": _cache_roots_ready(settings),
        },
        "secrets": {
            "required_env_vars": settings.secret_env_var_names,
            "present_env_vars": tuple(
                name
                for name in settings.secret_env_var_names
                if settings.environment.get(name, "").strip() != ""
            ),
            "secret_values_exposed": False,
        },
        "blocking_reasons": blocking_reasons,
        "next_required_evidence": NEXT_REQUIRED_EVIDENCE,
        "profile_selection": {
            "selected": False,
            "rejection_reasons": (
                blocking_reasons if not preflight_ready else PROFILE_PROOF_REJECTION_REASONS
            ),
        },
    }


def write_preflight_report(
    report: BenchmarkPreflightReport,
    *,
    output_root: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown preflight reports under a governed output root."""

    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    report_json_path = output_root / "report.json"
    report_markdown_path = output_root / "report.md"
    report_json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_markdown_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return report_json_path, report_markdown_path


def _blocking_reasons(
    settings: BenchmarkPreflightSettings,
    commands: Mapping[str, CommandProbeResult],
    python_modules: Mapping[str, PythonModuleProbeResult],
) -> list[str]:
    reasons: list[str] = []
    for command_name in REQUIRED_COMMANDS:
        if not commands.get(
            command_name,
            CommandProbeResult(command_name=command_name, found=False, version_line=""),
        ).found:
            reasons.append(f"{command_name}_missing")
    module_reason_labels = {
        "faster_whisper": "faster_whisper_missing",
        "pyannote.audio": "pyannote_audio_missing",
        "huggingface_hub": "huggingface_hub_missing",
        "torch": "torch_missing",
    }
    for module_name in REQUIRED_PYTHON_MODULES:
        if not python_modules.get(
            module_name,
            PythonModuleProbeResult(module_name=module_name, importable=False),
        ).importable:
            reasons.append(module_reason_labels[module_name])
    missing_secrets = tuple(
        name
        for name in settings.secret_env_var_names
        if settings.environment.get(name, "").strip() == ""
    )
    for secret_name in missing_secrets:
        reasons.append(f"{secret_name.lower()}_missing")
    if not _cache_roots_ready(settings):
        reasons.append("huggingface_cache_roots_not_ready")
    return reasons


def _cache_roots_ready(settings: BenchmarkPreflightSettings) -> bool:
    """Return whether the configured cache roots exist as directories."""

    return settings.hf_home.is_dir() and settings.hf_hub_cache.is_dir()


def _render_markdown_report(report: BenchmarkPreflightReport) -> str:
    """Render a concise operator-readable Markdown report."""

    blocking = ", ".join(report["blocking_reasons"]) or "none"
    next_evidence = "\n".join(f"- `{item}`" for item in report["next_required_evidence"])
    return (
        "# STT Sidecar Benchmark Preflight\n\n"
        f"- Schema: `{report['schema_version']}`\n"
        f"- Generated: `{report['generated_at_utc']}`\n"
        f"- Preflight ready: `{report['preflight_ready']}`\n"
        f"- Profile selected: `{report['profile_selection']['selected']}`\n"
        f"- Blocking reasons: `{blocking}`\n\n"
        "## Next Required Evidence\n\n"
        f"{next_evidence}\n"
    )
