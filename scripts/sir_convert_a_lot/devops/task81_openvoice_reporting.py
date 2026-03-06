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
from enum import Enum, StrEnum
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


class BenchmarkStatus(StrEnum):
    """Top-level outcome for one benchmark attempt."""

    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class EvidenceStatus(StrEnum):
    """Completeness classification for emitted evidence artifacts."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"


class BenchmarkStep(StrEnum):
    """Named benchmark stages for machine-readable failure reporting."""

    PRECONDITIONS = "preconditions"
    GPU_IDENTITY = "gpu_identity"
    REFERENCE_AUDIO = "reference_audio"
    CACHE_RESOLUTION = "cache_resolution"
    PREFETCH_OPENVOICE = "prefetch_openvoice"
    PREFETCH_HF = "prefetch_huggingface"
    PREFETCH_VAD = "prefetch_vad"
    START_SIDECAR = "start_sidecar"
    WAIT_READY = "wait_ready"
    INTERNAL_PROBE = "internal_probe"
    INSPECT_RUNTIME = "inspect_runtime"
    SYNTHESIZE = "synthesize"
    EXPORT_SETUP_ARTIFACTS = "export_setup_artifacts"
    COLLECT_SETUP_ARTIFACTS = "collect_setup_artifacts"
    WRITE_REPORT = "write_report"


@dataclass(frozen=True)
class CacheEvidence:
    """Resolved persistent-cache paths used by the benchmark."""

    openvoice_host_root: str
    openvoice_container_root: str
    hf_host_root: str
    hf_container_root: str
    torch_host_root: str
    torch_container_root: str
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
    torch_home: str | None
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
    sha256: str
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
class FailureEvidence:
    """Machine-readable benchmark failure details."""

    message: str


@dataclass(frozen=True)
class BenchmarkReport:
    """Top-level JSON payload for Task 81 Hemma evidence."""

    benchmark_id: str
    run_id: str
    generated_at: str
    repo_head: str
    benchmark_status: BenchmarkStatus
    evidence_status: EvidenceStatus
    blocking_step: BenchmarkStep | None
    failure: FailureEvidence | None
    host_base_url: str
    internal_base_url: str
    gpu_identity: GpuIdentity | None
    cache_evidence: CacheEvidence | None
    sidecar_runtime: SidecarRuntime | None
    internal_probe: InternalProbeEvidence | None
    capabilities: CapabilityResponse | None
    reference_audio: ReferenceAudioEvidence | None
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
    if isinstance(value, Enum):
        return value.value
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

    def _render(value: object | None) -> str:
        return "n/a" if value is None else str(value)

    gpu = report.gpu_identity
    cache = report.cache_evidence
    runtime = report.sidecar_runtime
    probe = report.internal_probe
    reference = report.reference_audio
    capabilities = report.capabilities
    capability_languages = "n/a"
    voice_modes = "n/a"
    output_formats = "n/a"
    if capabilities is not None:
        capability_languages = ", ".join(
            f"{entry.code}:{entry.support_level.value}" for entry in capabilities.languages
        )
        voice_modes = str([mode.value for mode in capabilities.voice.modes])
        output_formats = str([fmt.value for fmt in capabilities.synthesis.output_formats])
    blocking_step = report.blocking_step.value if report.blocking_step is not None else None
    failure_message = report.failure.message if report.failure is not None else None
    lines = [
        "# Task 81 Hemma OpenVoice V2 Benchmark",
        "",
        f"- run_id: `{report.run_id}`",
        f"- generated_at: `{report.generated_at}`",
        f"- repo_head: `{report.repo_head}`",
        f"- benchmark_status: `{report.benchmark_status.value}`",
        f"- evidence_status: `{report.evidence_status.value}`",
        f"- blocking_step: `{_render(blocking_step)}`",
        f"- failure: `{_render(failure_message)}`",
        f"- host_base_url: `{report.host_base_url}`",
        f"- internal_base_url: `{report.internal_base_url}`",
        "",
        "## GPU Identity",
        f"- product_name: `{_render(gpu.product_name if gpu else None)}`",
        f"- gfx_architecture: `{_render(gpu.gfx_architecture if gpu else None)}`",
        f"- vram_total_bytes: `{_render(gpu.vram_total_bytes if gpu else None)}`",
        f"- peak_gpu_busy_percent: `{_render(gpu.peak_gpu_busy_percent if gpu else None)}`",
        f"- peak_vram_used_bytes: `{_render(gpu.peak_vram_used_bytes if gpu else None)}`",
        "",
        "## Cache Evidence",
        f"- openvoice_host_root: `{_render(cache.openvoice_host_root if cache else None)}`",
        (
            "- openvoice_container_root: "
            f"`{_render(cache.openvoice_container_root if cache else None)}`"
        ),
        f"- hf_host_root: `{_render(cache.hf_host_root if cache else None)}`",
        f"- hf_container_root: `{_render(cache.hf_container_root if cache else None)}`",
        f"- torch_host_root: `{_render(cache.torch_host_root if cache else None)}`",
        f"- torch_container_root: `{_render(cache.torch_container_root if cache else None)}`",
        (
            "- openvoice_home_mount_used: "
            f"`{_render(cache.openvoice_home_mount_used if cache else None)}`"
        ),
        f"- hf_home_mount_used: `{_render(cache.hf_home_mount_used if cache else None)}`",
        "",
        "## Sidecar Runtime",
        f"- image: `{_render(runtime.image if runtime else None)}`",
        f"- image_id: `{_render(runtime.image_id if runtime else None)}`",
        f"- container_name: `{_render(runtime.container_name if runtime else None)}`",
        f"- python_version: `{_render(runtime.python_version if runtime else None)}`",
        (
            "- openvoice_checkpoints_root: "
            f"`{_render(runtime.openvoice_checkpoints_root if runtime else None)}`"
        ),
        f"- hf_home: `{_render(runtime.hf_home if runtime else None)}`",
        f"- hf_hub_cache: `{_render(runtime.hf_hub_cache if runtime else None)}`",
        f"- transformers_cache: `{_render(runtime.transformers_cache if runtime else None)}`",
        f"- torch_home: `{_render(runtime.torch_home if runtime else None)}`",
        "",
        "## Capability Snapshot",
        f"- backend_id: `{_render(capabilities.backend_id if capabilities else None)}`",
        f"- backend_version: `{_render(capabilities.backend_version if capabilities else None)}`",
        f"- backend_profile: `{_render(capabilities.backend_profile if capabilities else None)}`",
        f"- languages: `{capability_languages}`",
        f"- voice_modes: `{voice_modes}`",
        f"- output_formats: `{output_formats}`",
        "",
        "## Internal Probe",
        f"- host_probe_ok: `{_render(probe.host_probe_ok if probe else None)}`",
        f"- service_probe_ok: `{_render(probe.service_probe_ok if probe else None)}`",
        f"- service_backend_id: `{_render(probe.service_backend_id if probe else None)}`",
        f"- service_ready: `{_render(probe.service_ready if probe else None)}`",
        "",
        "## Reference Audio",
        f"- input_path: `{_render(reference.input_path if reference else None)}`",
        f"- filename: `{_render(reference.filename if reference else None)}`",
        f"- sha256: `{_render(reference.sha256 if reference else None)}`",
        f"- reference_role: `{_render(reference.reference_role if reference else None)}`",
        f"- duration_seconds: `{_render(reference.duration_seconds if reference else None)}`",
        f"- sample_rate_hz: `{_render(reference.sample_rate_hz if reference else None)}`",
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
