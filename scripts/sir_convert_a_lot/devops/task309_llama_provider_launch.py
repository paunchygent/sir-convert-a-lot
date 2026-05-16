"""Task 309 llama.cpp provider launch helpers.

Purpose:
    Build and execute the Hemma-local llama.cpp server command used for the
    Qwen3.6 Task 309 answer-key validation lane.

Relationships:
    - Complements the Granite/vLLM Docker launch surface without replacing it.
    - Writes persistent pid/log artifacts under the governed Task 309 output
      root so the provider remains observable after the CLI exits.
    - Uses the named provider defaults from `task309_structured_provider_profiles`.
"""

from __future__ import annotations

import os
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task309_granite_provider_contracts import (
    TASK309_LLAMA_PROVIDER_LAUNCH_SCHEMA_VERSION,
    TASK309_PROVIDER_PERSISTENT_POLICY,
    Task309LlamaProviderLaunchPlan,
    Task309LlamaProviderLaunchResult,
)
from scripts.sir_convert_a_lot.devops.task309_structured_provider_profiles import (
    QWEN36_LLAMA_CPP_HF_FILE,
    QWEN36_LLAMA_CPP_HF_REPO,
    QWEN36_LLAMA_CPP_PROVIDER_URL,
    QWEN36_LLAMA_CPP_REQUIRED_PROCESS_ARGS,
    QWEN36_LLAMA_CPP_SERVER_BINARY,
    Task309ProviderProfileName,
)

LLAMA_PROVIDER_HOST = "127.0.0.1"
LLAMA_PROVIDER_CONTEXT_TOKENS = "32768"
LLAMA_PROVIDER_TEMPERATURE = "0.15"


def build_task309_llama_provider_launch_plan(
    *,
    provider_profile: Task309ProviderProfileName,
    provider_url: str = QWEN36_LLAMA_CPP_PROVIDER_URL,
    model: str,
    port: int,
    output_root: Path,
    server_binary: str = QWEN36_LLAMA_CPP_SERVER_BINARY,
    hf_repo: str = QWEN36_LLAMA_CPP_HF_REPO,
    hf_file: str = QWEN36_LLAMA_CPP_HF_FILE,
    llama_cache_path: str,
    dry_run: bool,
) -> Task309LlamaProviderLaunchPlan:
    """Build the persistent llama.cpp launch plan for Task 309."""

    log_path = output_root / f"{model}-llama-server.log"
    pid_path = output_root / f"{model}-llama-server.pid"
    media_path = output_root / "vision-assets"
    command = (
        server_binary,
        "-hf",
        hf_repo,
        "-hff",
        hf_file,
        "--alias",
        model,
        "--host",
        LLAMA_PROVIDER_HOST,
        "--port",
        str(port),
        "--ctx-size",
        LLAMA_PROVIDER_CONTEXT_TOKENS,
        "--n-gpu-layers",
        "all",
        "--fit",
        "off",
        "--flash-attn",
        "on",
        "--jinja",
        "--reasoning",
        "off",
        "--temp",
        LLAMA_PROVIDER_TEMPERATURE,
        "--offline",
        "--media-path",
        media_path.as_posix(),
        "--log-file",
        log_path.as_posix(),
    )
    return Task309LlamaProviderLaunchPlan(
        schema_version=TASK309_LLAMA_PROVIDER_LAUNCH_SCHEMA_VERSION,
        generated_at=_utc_now_iso(),
        provider_profile=provider_profile.value,
        provider_url=provider_url,
        model=model,
        host=LLAMA_PROVIDER_HOST,
        port=port,
        server_binary=server_binary,
        hf_repo=hf_repo,
        hf_file=hf_file,
        llama_cache_path=llama_cache_path,
        xdg_cache_home=llama_cache_path,
        media_path=media_path.as_posix(),
        output_root=output_root.as_posix(),
        log_path=log_path.as_posix(),
        pid_path=pid_path.as_posix(),
        persistent_policy=TASK309_PROVIDER_PERSISTENT_POLICY,
        command=command,
        dry_run=dry_run,
    )


def launch_task309_llama_provider(
    plan: Task309LlamaProviderLaunchPlan,
) -> Task309LlamaProviderLaunchResult:
    """Launch the persistent llama.cpp provider or return a dry-run result."""

    if plan.dry_run:
        return _result(plan=plan, exit_code=None, pid=None, ok=True, error_kind=None)
    if _tcp_reachable(plan.host, plan.port, timeout_seconds=0.2):
        return _result(
            plan=plan,
            exit_code=None,
            pid=None,
            ok=False,
            error_kind="PortAlreadyInUse",
        )
    output_root = Path(plan.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    log_path = Path(plan.log_path)
    env = dict(os.environ)
    env["LLAMA_CACHE"] = plan.llama_cache_path
    env["XDG_CACHE_HOME"] = plan.xdg_cache_home
    try:
        with log_path.open("ab") as log_handle:
            process = subprocess.Popen(
                list(plan.command),
                cwd=output_root,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except FileNotFoundError:
        return _result(
            plan=plan,
            exit_code=None,
            pid=None,
            ok=False,
            error_kind="FileNotFoundError",
        )
    except OSError as exc:
        return _result(
            plan=plan,
            exit_code=None,
            pid=None,
            ok=False,
            error_kind=type(exc).__name__,
        )
    Path(plan.pid_path).write_text(f"{process.pid}\n", encoding="utf-8")
    return _result(plan=plan, exit_code=None, pid=process.pid, ok=True, error_kind=None)


def qwen36_llama_required_process_args() -> tuple[str, ...]:
    """Return process args required for the Qwen3.6 llama.cpp status gate."""

    return QWEN36_LLAMA_CPP_REQUIRED_PROCESS_ARGS


def _result(
    *,
    plan: Task309LlamaProviderLaunchPlan,
    exit_code: int | None,
    pid: int | None,
    ok: bool,
    error_kind: str | None,
) -> Task309LlamaProviderLaunchResult:
    return Task309LlamaProviderLaunchResult(
        schema_version=TASK309_LLAMA_PROVIDER_LAUNCH_SCHEMA_VERSION,
        launched_at=_utc_now_iso(),
        provider_profile=plan.provider_profile,
        dry_run=plan.dry_run,
        exit_code=exit_code,
        pid=pid,
        ok=ok,
        error_kind=error_kind,
        plan=plan,
    )


def _tcp_reachable(host: str, port: int, *, timeout_seconds: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
