"""Reporting helpers for the Task 86 Hemma Chatterbox benchmark.

Purpose:
    Keep Task 86 evidence models and markdown rendering separate from the
    orchestration script so the benchmark runner stays small and discoverable.

Relationships:
    - Consumed by `run_task86_hemma_chatterbox_benchmark`.
    - Paired with the runtime helpers in `task86_chatterbox_runtime`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProbeResult:
    """One synthesized artifact plus timing and GPU evidence."""

    ok: bool
    output_path: str
    sha256: str
    content_type: str | None
    duration_seconds: float
    peak_gpu_busy_percent: int
    peak_vram_used_bytes: int


@dataclass(frozen=True)
class BenchmarkReport:
    """Top-level JSON payload for Task 86 Hemma evidence."""

    benchmark_id: str
    run_id: str
    generated_at: str
    repo_head: str
    host_base_url: str
    internal_base_url: str
    image: str
    image_id: str
    build_performed: bool
    package_versions_path: str
    model_snapshot_path: str | None
    model_snapshot_present_before_start: bool
    model_snapshot_downloaded_during_first_start: bool
    first_startup_seconds: float
    cold_start_seconds: float | None
    warm_restart_seconds: float
    service_probe_ok: bool
    service_backend_id: str
    service_ready: bool
    capability_backend_id: str
    capability_reference_transcript_required: bool
    capability_language_support_sv: str
    voices_count: int
    smoke_text: str
    smoke_probe: ProbeResult
    probe_text: str
    probe_language: str
    primary_clone_probe: ProbeResult
    cross_language_probe: ProbeResult | None
    reference_audio_path: str
    reference_audio_duration_seconds: float
    reference_audio_sample_rate_hz: int
    english_reference_audio_path: str | None
    english_reference_audio_duration_seconds: float | None
    english_reference_audio_sample_rate_hz: int | None
    exaggeration: float
    cfg_weight: float
    segment_text: bool
    segment_max_chars: int
    segment_cross_fade_ms: int
    segment_stitch_mode: str
    segment_debug_dir: str | None
    hf_cache_host_root: str
    gpu_product_name: str
    gpu_gfx_architecture: str
    gpu_before_path: str
    gpu_after_path: str
    docker_logs_path: str


def build_report_markdown(report: BenchmarkReport) -> str:
    """Render one operator-friendly markdown summary for Task 86 evidence."""
    lines = [
        "# Task 86 Hemma Chatterbox Benchmark",
        "",
        f"- run_id: `{report.run_id}`",
        f"- repo_head: `{report.repo_head}`",
        f"- image: `{report.image}`",
        f"- image_id: `{report.image_id}`",
        f"- build_performed: `{report.build_performed}`",
        f"- model_snapshot_path: `{report.model_snapshot_path}`",
        (f"- model_snapshot_present_before_start: `{report.model_snapshot_present_before_start}`"),
        (
            "- model_snapshot_downloaded_during_first_start: "
            f"`{report.model_snapshot_downloaded_during_first_start}`"
        ),
        f"- first_startup_seconds: `{report.first_startup_seconds}`",
        f"- cold_start_seconds: `{report.cold_start_seconds}`",
        f"- warm_restart_seconds: `{report.warm_restart_seconds}`",
        f"- service_probe_ok: `{report.service_probe_ok}`",
        f"- capability_backend_id: `{report.capability_backend_id}`",
        (
            "- capability_reference_transcript_required: "
            f"`{report.capability_reference_transcript_required}`"
        ),
        f"- capability_language_support_sv: `{report.capability_language_support_sv}`",
        f"- voices_count: `{report.voices_count}`",
        f"- exaggeration: `{report.exaggeration}`",
        f"- cfg_weight: `{report.cfg_weight}`",
        f"- segment_text: `{report.segment_text}`",
        f"- segment_max_chars: `{report.segment_max_chars}`",
        f"- segment_cross_fade_ms: `{report.segment_cross_fade_ms}`",
        f"- segment_stitch_mode: `{report.segment_stitch_mode}`",
        f"- segment_debug_dir: `{report.segment_debug_dir}`",
        f"- gpu_product_name: `{report.gpu_product_name}`",
        f"- gpu_gfx_architecture: `{report.gpu_gfx_architecture}`",
        "",
        "## Smoke Probe",
        f"- text: `{report.smoke_text}`",
        f"- output_path: `{report.smoke_probe.output_path}`",
        f"- duration_seconds: `{report.smoke_probe.duration_seconds}`",
        f"- peak_gpu_busy_percent: `{report.smoke_probe.peak_gpu_busy_percent}`",
        f"- peak_vram_used_bytes: `{report.smoke_probe.peak_vram_used_bytes}`",
        "",
        "## Primary Clone Probe",
        f"- text: `{report.probe_text}`",
        f"- language: `{report.probe_language}`",
        f"- output_path: `{report.primary_clone_probe.output_path}`",
        f"- duration_seconds: `{report.primary_clone_probe.duration_seconds}`",
        f"- peak_gpu_busy_percent: `{report.primary_clone_probe.peak_gpu_busy_percent}`",
        f"- peak_vram_used_bytes: `{report.primary_clone_probe.peak_vram_used_bytes}`",
        "",
        "## Evidence",
        f"- package_versions_path: `{report.package_versions_path}`",
        f"- gpu_before_path: `{report.gpu_before_path}`",
        f"- gpu_after_path: `{report.gpu_after_path}`",
        f"- docker_logs_path: `{report.docker_logs_path}`",
    ]
    if report.cross_language_probe is not None:
        lines.extend(
            [
                "",
                "## Cross-Language Clone Probe",
                f"- output_path: `{report.cross_language_probe.output_path}`",
                f"- duration_seconds: `{report.cross_language_probe.duration_seconds}`",
            ]
        )
    return "\n".join(lines) + "\n"
