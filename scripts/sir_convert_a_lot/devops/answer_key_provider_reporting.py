"""answer-key live validation Granite provider report artifact rendering.

Purpose:
    Render redacted JSON and Markdown artifacts for answer-key live validation Hemma preflight
    and persistent Granite/vLLM provider status reports.

Relationships:
    - Consumes contracts from `answer_key_provider_contracts`.
    - Writes through the answer-key live validation manifest JSON helper so report formatting is
      deterministic across corpus, golden, and provider evidence.
    - Keeps artifact rendering separate from non-mutating Docker/ROCm probes.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.answer_key_provider_contracts import (
    AnswerKeyHemmaPreflight,
    AnswerKeyLlamaProviderLaunchResult,
    AnswerKeyProviderLaunchResult,
    AnswerKeyProviderStatus,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_manifest import (
    write_answer_key_json,
)


def write_answer_key_provider_status_artifacts(
    *,
    output_root: Path,
    status: AnswerKeyProviderStatus,
) -> tuple[Path, Path]:
    """Write JSON and Markdown provider-status artifacts."""

    json_path = output_root / "provider-status.json"
    markdown_path = output_root / "provider-status.md"
    write_answer_key_json(status.to_payload(), json_path)
    _write_markdown(markdown_path, _provider_status_markdown(status))
    return json_path, markdown_path


def write_answer_key_hemma_preflight_artifacts(
    *,
    output_root: Path,
    preflight: AnswerKeyHemmaPreflight,
) -> tuple[Path, Path]:
    """Write JSON and Markdown Hemma preflight artifacts."""

    json_path = output_root / "hemma-preflight.json"
    markdown_path = output_root / "hemma-preflight.md"
    write_answer_key_json(preflight.to_payload(), json_path)
    _write_markdown(markdown_path, _hemma_preflight_markdown(preflight))
    return json_path, markdown_path


def write_answer_key_provider_launch_artifacts(
    *,
    output_root: Path,
    result: AnswerKeyProviderLaunchResult,
) -> tuple[Path, Path]:
    """Write JSON and Markdown provider-launch artifacts."""

    json_path = output_root / "provider-launch.json"
    markdown_path = output_root / "provider-launch.md"
    write_answer_key_json(result.to_payload(), json_path)
    _write_markdown(markdown_path, _provider_launch_markdown(result))
    return json_path, markdown_path


def write_answer_key_llama_provider_launch_artifacts(
    *,
    output_root: Path,
    result: AnswerKeyLlamaProviderLaunchResult,
) -> tuple[Path, Path]:
    """Write JSON and Markdown llama.cpp provider-launch artifacts."""

    json_path = output_root / "llama-provider-launch.json"
    markdown_path = output_root / "llama-provider-launch.md"
    write_answer_key_json(result.to_payload(), json_path)
    _write_markdown(markdown_path, _llama_provider_launch_markdown(result))
    return json_path, markdown_path


def _provider_status_markdown(status: AnswerKeyProviderStatus) -> str:
    model_ids = ", ".join(f"`{model_id}`" for model_id in status.models_endpoint.model_ids)
    lines = [
        "# answer-key live validation Granite Provider Status",
        "",
        f"- checked_at: `{status.checked_at}`",
        f"- provider_url: `{status.provider_url}`",
        f"- container_name: `{status.container_name}`",
        f"- persistent_policy: `{status.persistent_policy}`",
        f"- container_present: `{status.container_present}`",
        f"- container_running: `{status.container_running}`",
        f"- container_image: `{status.container_image}`",
        f"- tcp_reachable: `{status.tcp_reachable}`",
        f"- models_endpoint_reachable: `{status.models_endpoint.reachable}`",
        f"- model_ids: {model_ids if model_ids else '`none`'}",
        f"- localhost_only: `{status.localhost_only}`",
        f"- localhost_tcp_listener: `{status.localhost_tcp_listener}`",
        f"- request_logging_disabled: `{status.request_logging_disabled}`",
        f"- no_cpu_fallback_proved: `{status.no_cpu_fallback_proved}`",
        f"- expected_model_id: `{status.expected_model_id}`",
        f"- expected_model_present: `{status.expected_model_present}`",
        f"- llama_process_present: `{status.llama_process_present}`",
        f"- llama_required_args_present: `{status.llama_required_args_present}`",
        f"- ready: `{status.ready}`",
    ]
    return "\n".join(lines)


def _hemma_preflight_markdown(preflight: AnswerKeyHemmaPreflight) -> str:
    blockers = ", ".join(f"`{blocker}`" for blocker in preflight.blockers)
    lines = [
        "# answer-key live validation Hemma Preflight",
        "",
        f"- checked_at: `{preflight.checked_at}`",
        f"- runtime_lane: `{preflight.runtime_lane}`",
        f"- repo_revision: `{preflight.repo_revision}`",
        f"- repo_branch: `{preflight.repo_branch}`",
        f"- manifest_path: `{preflight.manifest_path}`",
        f"- manifest_sha256: `{preflight.manifest_sha256}`",
        f"- ready: `{preflight.ready}`",
        f"- blockers: {blockers if blockers else '`none`'}",
        "",
        "## Command Probes",
    ]
    for command_probe in preflight.command_probes:
        lines.append(
            f"- {command_probe.name}: ok=`{command_probe.ok}` exit_code=`{command_probe.exit_code}`"
        )
    lines.append("")
    lines.append("## Cache Paths")
    for path_probe in preflight.cache_path_probes:
        lines.append(
            f"- `{path_probe.path}`: exists=`{path_probe.exists}` is_dir=`{path_probe.is_dir}`"
        )
    lines.append("")
    lines.append("## Provider")
    lines.extend(_provider_status_markdown(preflight.provider_status).splitlines()[2:])
    return "\n".join(lines)


def _provider_launch_markdown(result: AnswerKeyProviderLaunchResult) -> str:
    lines = [
        "# answer-key live validation Granite Provider Launch",
        "",
        f"- launched_at: `{result.launched_at}`",
        f"- container_name: `{result.container_name}`",
        f"- dry_run: `{result.dry_run}`",
        f"- ok: `{result.ok}`",
        f"- exit_code: `{result.exit_code}`",
        f"- error_kind: `{result.error_kind}`",
        f"- container_id: `{result.container_id}`",
        f"- image: `{result.plan.image}`",
        f"- model: `{result.plan.model}`",
        f"- host_port: `{result.plan.host_port}`",
        f"- persistent_policy: `{result.plan.persistent_policy}`",
        f"- request_logging_disabled: `{'--disable-log-requests' in result.plan.command}`",
        f"- localhost_host_bind: `127.0.0.1:{result.plan.host_port}`",
        f"- host_cache_path: `{result.plan.host_cache_path}`",
    ]
    return "\n".join(lines)


def _llama_provider_launch_markdown(result: AnswerKeyLlamaProviderLaunchResult) -> str:
    lines = [
        "# answer-key live validation llama.cpp Provider Launch",
        "",
        f"- launched_at: `{result.launched_at}`",
        f"- provider_profile: `{result.provider_profile}`",
        f"- dry_run: `{result.dry_run}`",
        f"- ok: `{result.ok}`",
        f"- exit_code: `{result.exit_code}`",
        f"- error_kind: `{result.error_kind}`",
        f"- pid: `{result.pid}`",
        f"- provider_url: `{result.plan.provider_url}`",
        f"- model: `{result.plan.model}`",
        f"- host_port: `{result.plan.host}:{result.plan.port}`",
        f"- persistent_policy: `{result.plan.persistent_policy}`",
        f"- hf_repo: `{result.plan.hf_repo}`",
        f"- hf_file: `{result.plan.hf_file}`",
        f"- llama_cache_path: `{result.plan.llama_cache_path}`",
        f"- media_path: `{result.plan.media_path}`",
        f"- log_path: `{result.plan.log_path}`",
        f"- pid_path: `{result.plan.pid_path}`",
    ]
    return "\n".join(lines)


def _write_markdown(path: Path, markdown: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
