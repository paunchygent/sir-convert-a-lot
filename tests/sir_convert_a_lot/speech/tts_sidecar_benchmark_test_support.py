"""Shared settings fixture for TTS sidecar benchmark tests.

Purpose:
    Give the Docker launch/readiness and cache/measurement/report test
    modules one normalized `BenchmarkSettings` builder so each file stays
    focused on its own responsibility.

Relationships:
    - Used by `test_tts_sidecar_hemma_benchmark` and
      `test_tts_sidecar_benchmark_probes`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_runtime import (
    BenchmarkSettings,
)


def build_settings(
    tmp_path: Path,
    *,
    output_root: Path | None = None,
    image: str = "vllm/vllm-omni-rocm:v0.16.0",
    model: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    task_type: str = "CustomVoice",
    language: str = "Auto",
    tokenizer_model: str = "Qwen/Qwen3-TTS-Tokenizer-12Hz",
    hf_cache_home_mount: Path | None = None,
    network: str = "hule-network",
    network_alias: str = "sir-convert-a-lot-tts-tts-sidecar",
    container_name: str = "sir_convert_a_lot_tts_tts-sidecar",
    service_container: str = "sir_convert_a_lot_prod",
    container_port: int = 8091,
    host_port: int = 38091,
    voice: str = "ryan",
    response_formats: tuple[str, ...] = ("wav",),
    startup_timeout_seconds: float = 600.0,
    hf_cache_dir: Path | None = None,
    probe_text: str = "hello",
    instructions: str | None = None,
    reference_audio: Path | None = None,
    reference_transcript: str | None = None,
    hf_token_present: bool = False,
    pull_image: bool = False,
    retain_container: bool = False,
    stage_config_path: Path | None = None,
    use_triton_flash_attn: bool = True,
) -> BenchmarkSettings:
    """Return one TTS sidecar benchmark settings fixture with sensible defaults."""
    return BenchmarkSettings(
        output_root=tmp_path / "output" if output_root is None else output_root,
        image=image,
        model=model,
        task_type=task_type,
        language=language,
        tokenizer_model=tokenizer_model,
        hf_cache_home_mount=(
            tmp_path / "hf-cache-home" if hf_cache_home_mount is None else hf_cache_home_mount
        ),
        network=network,
        network_alias=network_alias,
        container_name=container_name,
        service_container=service_container,
        container_port=container_port,
        host_port=host_port,
        voice=voice,
        response_formats=response_formats,
        startup_timeout_seconds=startup_timeout_seconds,
        hf_cache_dir=tmp_path / "hf-cache" if hf_cache_dir is None else hf_cache_dir,
        probe_text=probe_text,
        instructions=instructions,
        reference_audio=reference_audio,
        reference_transcript=reference_transcript,
        hf_token_present=hf_token_present,
        pull_image=pull_image,
        retain_container=retain_container,
        stage_config_path=(
            tmp_path / "tts-sidecar-stage-config.yaml"
            if stage_config_path is None
            else stage_config_path
        ),
        use_triton_flash_attn=use_triton_flash_attn,
    )
