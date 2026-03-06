"""Reporting types and rendering helpers for the Task 81 Hemma OpenVoice benchmark.

Purpose:
    Keep the Task 81 benchmark runner focused on orchestration while
    centralizing typed JSON/Markdown evidence for runtime truth, cache reuse,
    capability snapshots, and synthesized Swedish sample artifacts.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.run_task81_hemma_openvoice_benchmark`.
    - Records evidence for `docs/backlog/tasks/task-81-...` under
      `build/verification/task-81-openvoice-v2-hemma/`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.tts_sidecar.contracts import CapabilityResponse


@dataclass(frozen=True)
class GpuIdentity:
    """Live Hemma GPU identity and utilization evidence."""

    product_name: str
    gfx_architecture: str
    vram_total_bytes: int
    peak_gpu_busy_percent: int
    peak_vram_used_bytes: int


@dataclass(frozen=True)
class CacheEvidence:
    """Resolved persistent-cache paths used by the benchmark."""

    openvoice_host_root: str
    openvoice_container_root: str
    hf_host_root: str
    hf_container_root: str
    openvoice_home_mount_used: bool
    hf_home_mount_used: bool


@dataclass(frozen=True)
class SidecarRuntime:
    """Observed runtime metadata from inside the OpenVoice sidecar container."""

    image: str
    image_id: str
    container_name: str
    python_version: str
    package_versions: dict[str, str | None]
    hf_home: str | None
    hf_hub_cache: str | None
    transformers_cache: str | None
    openvoice_checkpoints_root: str | None


@dataclass(frozen=True)
class InternalProbeEvidence:
    """Evidence that the sidecar is reachable from the Sir service container."""

    host_probe_ok: bool
    service_probe_ok: bool
    service_backend_id: str
    service_ready: bool


@dataclass(frozen=True)
class ReferenceAudioEvidence:
    """Approved reference-audio metadata recorded by the benchmark."""

    input_path: str
    filename: str
    reference_role: str
    duration_seconds: float
    sample_rate_hz: int


@dataclass(frozen=True)
class SetupArtifactEvidence:
    """Intermediate artifacts that explain the OpenVoice setup used for one rerun."""

    processed_reference_dir: str | None
    processed_reference_segment_count: int | None
    base_output_path: str | None
    base_output_sample_rate_hz: int | None
    converter_input_path: str | None
    converter_input_sample_rate_hz: int | None


@dataclass(frozen=True)
class SynthesisProbeResult:
    """Result for one normalized `/synthesize` request."""

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
class BenchmarkReport:
    """Top-level JSON payload for Task 81 Hemma evidence."""

    benchmark_id: str
    generated_at: str
    repo_head: str
    host_base_url: str
    internal_base_url: str
    gpu_identity: GpuIdentity
    cache_evidence: CacheEvidence
    sidecar_runtime: SidecarRuntime
    internal_probe: InternalProbeEvidence
    capabilities: CapabilityResponse
    reference_audio: ReferenceAudioEvidence
    setup_artifacts: SetupArtifactEvidence
    synthesis_result: SynthesisProbeResult
    official_support_summary: list[str]
    listening_notes: str
    pull_performed: bool
    build_performed: bool
    readiness_seconds: float
    cleanup_performed: bool
    docker_logs_path: str


def json_default(value: object) -> object:
    """Serialize dataclasses, pydantic models, and paths for stable JSON output."""
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Path):
        return value.as_posix()
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


def write_json(path: Path, payload: object) -> None:
    """Write deterministic JSON output to disk."""
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=json_default) + "\n",
        encoding="utf-8",
    )


def build_report_markdown(report: BenchmarkReport) -> str:
    """Render one operator-friendly markdown summary for Task 81 evidence."""
    capability_languages = ", ".join(
        f"{entry.code}:{entry.support_level.value}" for entry in report.capabilities.languages
    )
    lines = [
        "# Task 81 Hemma OpenVoice V2 Benchmark",
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
        "## Cache Evidence",
        f"- openvoice_host_root: `{report.cache_evidence.openvoice_host_root}`",
        f"- openvoice_container_root: `{report.cache_evidence.openvoice_container_root}`",
        f"- hf_host_root: `{report.cache_evidence.hf_host_root}`",
        f"- hf_container_root: `{report.cache_evidence.hf_container_root}`",
        f"- openvoice_home_mount_used: `{report.cache_evidence.openvoice_home_mount_used}`",
        f"- hf_home_mount_used: `{report.cache_evidence.hf_home_mount_used}`",
        "",
        "## Sidecar Runtime",
        f"- image: `{report.sidecar_runtime.image}`",
        f"- image_id: `{report.sidecar_runtime.image_id}`",
        f"- container_name: `{report.sidecar_runtime.container_name}`",
        f"- python_version: `{report.sidecar_runtime.python_version}`",
        f"- openvoice_checkpoints_root: `{report.sidecar_runtime.openvoice_checkpoints_root}`",
        f"- hf_home: `{report.sidecar_runtime.hf_home}`",
        f"- hf_hub_cache: `{report.sidecar_runtime.hf_hub_cache}`",
        f"- transformers_cache: `{report.sidecar_runtime.transformers_cache}`",
        "",
        "## Capability Snapshot",
        f"- backend_id: `{report.capabilities.backend_id}`",
        f"- backend_version: `{report.capabilities.backend_version}`",
        f"- backend_profile: `{report.capabilities.backend_profile}`",
        f"- languages: `{capability_languages}`",
        f"- voice_modes: `{[mode.value for mode in report.capabilities.voice.modes]}`",
        (
            "- output_formats: "
            f"`{[fmt.value for fmt in report.capabilities.synthesis.output_formats]}`"
        ),
        "",
        "## Internal Probe",
        f"- host_probe_ok: `{report.internal_probe.host_probe_ok}`",
        f"- service_probe_ok: `{report.internal_probe.service_probe_ok}`",
        f"- service_backend_id: `{report.internal_probe.service_backend_id}`",
        f"- service_ready: `{report.internal_probe.service_ready}`",
        "",
        "## Reference Audio",
        f"- input_path: `{report.reference_audio.input_path}`",
        f"- filename: `{report.reference_audio.filename}`",
        f"- reference_role: `{report.reference_audio.reference_role}`",
        f"- duration_seconds: `{report.reference_audio.duration_seconds}`",
        f"- sample_rate_hz: `{report.reference_audio.sample_rate_hz}`",
        "",
        "## Setup Artifacts",
        f"- processed_reference_dir: `{report.setup_artifacts.processed_reference_dir}`",
        (
            "- processed_reference_segment_count: "
            f"`{report.setup_artifacts.processed_reference_segment_count}`"
        ),
        f"- base_output_path: `{report.setup_artifacts.base_output_path}`",
        f"- base_output_sample_rate_hz: `{report.setup_artifacts.base_output_sample_rate_hz}`",
        f"- converter_input_path: `{report.setup_artifacts.converter_input_path}`",
        (
            "- converter_input_sample_rate_hz: "
            f"`{report.setup_artifacts.converter_input_sample_rate_hz}`"
        ),
        "",
        "## Synthesis Result",
        f"- ok: `{report.synthesis_result.ok}`",
        f"- status_code: `{report.synthesis_result.status_code}`",
        f"- content_type: `{report.synthesis_result.content_type}`",
        f"- byte_count: `{report.synthesis_result.byte_count}`",
        f"- output_path: `{report.synthesis_result.output_path}`",
        f"- elapsed_seconds: `{report.synthesis_result.elapsed_seconds}`",
        f"- sample_rate_hz: `{report.synthesis_result.sample_rate_hz}`",
        f"- duration_seconds: `{report.synthesis_result.duration_seconds}`",
        f"- sha256: `{report.synthesis_result.sha256}`",
        f"- error_message: `{report.synthesis_result.error_message or 'n/a'}`",
        "",
        "## Official Support Summary",
    ]
    for line in report.official_support_summary:
        lines.append(f"- {line}")
    lines.extend(
        [
            "",
            "## Listening Notes",
            report.listening_notes,
            "",
            "## Benchmark Notes",
            f"- pull_performed: `{report.pull_performed}`",
            f"- build_performed: `{report.build_performed}`",
            f"- readiness_seconds: `{report.readiness_seconds}`",
            f"- cleanup_performed: `{report.cleanup_performed}`",
            f"- docker_logs_path: `{report.docker_logs_path}`",
            "",
        ]
    )
    return "\n".join(lines)
