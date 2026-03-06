"""Reporting types and rendering helpers for the Task 79 Hemma TTS benchmark.

Purpose:
    Keep the live Hemma benchmark entrypoint focused on orchestration while
    centralizing typed report payloads plus deterministic JSON/Markdown output.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.run_task79_hemma_tts_sidecar_benchmark`.
    - Produces the `report.json` and `report.md` artifacts under
      `build/verification/task-79-hemma-tts-sidecar/`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path


@dataclass(frozen=True)
class GpuIdentity:
    """Live GPU identity and runtime truth observed on Hemma."""

    product_name: str
    gfx_architecture: str
    vram_total_bytes: int
    peak_gpu_busy_percent: int
    peak_vram_used_bytes: int


@dataclass(frozen=True)
class SidecarRuntime:
    """Observed sidecar runtime metadata from inside the benchmark container."""

    image: str
    image_id: str
    container_name: str
    python_version: str
    package_versions: dict[str, str | None]
    stage_config_path: str


@dataclass(frozen=True)
class VoicesEvidence:
    """Observed voices endpoint evidence from host and service-container probes."""

    host_probe_ok: bool
    service_probe_ok: bool
    host_voice_count: int
    service_voice_count: int
    voice_names: list[str]


@dataclass(frozen=True)
class AudioProbeResult:
    """Result for one `/v1/audio/speech` response-format probe."""

    response_format: str
    ok: bool
    status_code: int
    content_type: str | None
    byte_count: int
    sha256: str | None
    output_path: str | None
    elapsed_seconds: float
    sample_rate_hz: int | None
    duration_seconds: float | None
    error_message: str | None


@dataclass(frozen=True)
class PythonRecommendation:
    """Recommendation emitted from the live Task 79 runtime evidence."""

    highest_proven_version: str
    recommended_minor: str
    python_3_14_supported: bool
    rationale: str


@dataclass(frozen=True)
class BenchmarkReport:
    """Top-level JSON report payload for Task 79 evidence."""

    benchmark_id: str
    generated_at: str
    repo_head: str
    host_base_url: str
    internal_base_url: str
    gpu_identity: GpuIdentity
    sidecar_runtime: SidecarRuntime
    voices_evidence: VoicesEvidence
    audio_results: list[AudioProbeResult]
    python_recommendation: PythonRecommendation
    pull_performed: bool
    readiness_seconds: float
    cleanup_performed: bool
    docker_logs_path: str


def json_default(value: object) -> object:
    """Serialize dataclasses and paths for deterministic JSON output."""
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


def write_json(path: Path, payload: object) -> None:
    """Write stable JSON output to disk."""
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=json_default) + "\n",
        encoding="utf-8",
    )


def build_report_markdown(report: BenchmarkReport) -> str:
    """Render a human-readable markdown summary for Task 79 evidence."""
    lines = [
        "# Task 79 Hemma TTS Sidecar Benchmark",
        "",
        f"- generated_at: `{report.generated_at}`",
        f"- repo_head: `{report.repo_head}`",
        f"- host_base_url: `{report.host_base_url}`",
        f"- internal_base_url: `{report.internal_base_url}`",
        "",
        "## GPU Identity",
        f"- product_name: `{report.gpu_identity.product_name}`",
        f"- gfx_architecture: `{report.gpu_identity.gfx_architecture}`",
        f"- vram_total_bytes: `{report.gpu_identity.vram_total_bytes}`",
        f"- peak_gpu_busy_percent: `{report.gpu_identity.peak_gpu_busy_percent}`",
        f"- peak_vram_used_bytes: `{report.gpu_identity.peak_vram_used_bytes}`",
        "",
        "## Sidecar Runtime",
        f"- image: `{report.sidecar_runtime.image}`",
        f"- image_id: `{report.sidecar_runtime.image_id}`",
        f"- container_name: `{report.sidecar_runtime.container_name}`",
        f"- python_version: `{report.sidecar_runtime.python_version}`",
        f"- stage_config_path: `{report.sidecar_runtime.stage_config_path}`",
        "",
        "## Voices",
        f"- host_probe_ok: `{report.voices_evidence.host_probe_ok}`",
        f"- service_probe_ok: `{report.voices_evidence.service_probe_ok}`",
        f"- host_voice_count: `{report.voices_evidence.host_voice_count}`",
        f"- service_voice_count: `{report.voices_evidence.service_voice_count}`",
        f"- voice_names: `{report.voices_evidence.voice_names}`",
        "",
        "## Audio Probes",
    ]
    for result in report.audio_results:
        lines.extend(
            [
                f"- format `{result.response_format}`:",
                f"  - ok: `{result.ok}`",
                f"  - status_code: `{result.status_code}`",
                f"  - content_type: `{result.content_type}`",
                f"  - byte_count: `{result.byte_count}`",
                f"  - elapsed_seconds: `{result.elapsed_seconds}`",
                f"  - output_path: `{result.output_path or 'n/a'}`",
                f"  - sha256: `{result.sha256 or 'n/a'}`",
                f"  - sample_rate_hz: `{result.sample_rate_hz}`",
                f"  - duration_seconds: `{result.duration_seconds}`",
                f"  - error_message: `{result.error_message or 'n/a'}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Python Recommendation",
            f"- highest_proven_version: `{report.python_recommendation.highest_proven_version}`",
            f"- recommended_minor: `{report.python_recommendation.recommended_minor}`",
            f"- python_3_14_supported: `{report.python_recommendation.python_3_14_supported}`",
            f"- rationale: {report.python_recommendation.rationale}",
            "",
            "## Benchmark Notes",
            f"- pull_performed: `{report.pull_performed}`",
            f"- readiness_seconds: `{report.readiness_seconds}`",
            f"- cleanup_performed: `{report.cleanup_performed}`",
            f"- docker_logs_path: `{report.docker_logs_path}`",
            "",
        ]
    )
    return "\n".join(lines)
