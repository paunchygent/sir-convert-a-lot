"""Task 309 Hemma Granite provider preflight and status probes.

Purpose:
    Collect deterministic, redacted operator evidence for the persistent
    Granite/vLLM provider used by Task 309 answer-key live validation.

Relationships:
    - Used by the Task 309 runner to write JSON and Markdown reports before
      long Hemma validation runs.
    - Follows the Hemma GPU runtime runbook contract for ROCm checks,
      scratch-backed Hugging Face cache paths, localhost-only vLLM exposure,
      disabled request logging, and no CPU fallback.
    - Complements the detached Task 116 resource monitor surface without
      stopping or cleaning up the provider container.
"""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task309_granite_provider_contracts import (
    DEFAULT_CACHE_PATHS,
    DEFAULT_PROVIDER_CONTAINER_NAME,
    DEFAULT_PROVIDER_PORT,
    DEFAULT_PROVIDER_URL,
    TASK309_HEMMA_PREFLIGHT_SCHEMA_VERSION,
    TASK309_PROVIDER_PERSISTENT_POLICY,
    TASK309_PROVIDER_STATUS_SCHEMA_VERSION,
    Task309CommandProbe,
    Task309DeviceBinding,
    Task309HemmaPreflight,
    Task309ModelsEndpointProbe,
    Task309MountBinding,
    Task309PathProbe,
    Task309PortBinding,
    Task309ProviderStatus,
)


def build_task309_provider_status(
    *,
    provider_url: str = DEFAULT_PROVIDER_URL,
    container_name: str = DEFAULT_PROVIDER_CONTAINER_NAME,
    port: int = DEFAULT_PROVIDER_PORT,
    timeout_seconds: float = 2.0,
) -> Task309ProviderStatus:
    """Build one persistent provider status report without mutating Docker state."""

    inspect_payload = _docker_inspect(container_name)
    docker_available = inspect_payload.error_kind != "FileNotFoundError"
    container_present = inspect_payload.payload is not None
    container_running = False
    container_image: str | None = None
    container_command: tuple[str, ...] = ()
    port_bindings: tuple[Task309PortBinding, ...] = ()
    mounts: tuple[Task309MountBinding, ...] = ()
    devices: tuple[Task309DeviceBinding, ...] = ()
    if inspect_payload.payload is not None:
        container_running = _container_running(inspect_payload.payload)
        container_image = _container_image(inspect_payload.payload)
        container_command = _container_command(inspect_payload.payload)
        port_bindings = _port_bindings(inspect_payload.payload)
        mounts = _mounts(inspect_payload.payload)
        devices = _devices(inspect_payload.payload)
    tcp_reachable = _tcp_reachable("127.0.0.1", port, timeout_seconds=timeout_seconds)
    models_endpoint = _models_endpoint(provider_url, timeout_seconds=timeout_seconds)
    localhost_only = _localhost_only(port_bindings, port=port)
    request_logging_disabled = "--disable-log-requests" in container_command
    rocm_image = container_image is not None and "rocm" in container_image.lower()
    gpu_devices_mounted = _gpu_devices_mounted(devices)
    no_cpu_fallback_proved = rocm_image and gpu_devices_mounted
    ready = (
        docker_available
        and container_present
        and container_running
        and tcp_reachable
        and models_endpoint.reachable
        and localhost_only
        and request_logging_disabled
        and no_cpu_fallback_proved
    )
    return Task309ProviderStatus(
        schema_version=TASK309_PROVIDER_STATUS_SCHEMA_VERSION,
        checked_at=_utc_now_iso(),
        provider_url=provider_url,
        container_name=container_name,
        persistent_policy=TASK309_PROVIDER_PERSISTENT_POLICY,
        docker_available=docker_available,
        container_present=container_present,
        container_running=container_running,
        container_image=container_image,
        container_command=container_command,
        port_bindings=port_bindings,
        mounts=mounts,
        devices=devices,
        tcp_reachable=tcp_reachable,
        models_endpoint=models_endpoint,
        localhost_only=localhost_only,
        request_logging_disabled=request_logging_disabled,
        rocm_image=rocm_image,
        gpu_devices_mounted=gpu_devices_mounted,
        no_cpu_fallback_proved=no_cpu_fallback_proved,
        ready=ready,
    )


def build_task309_hemma_preflight(
    *,
    manifest_path: Path,
    provider_url: str = DEFAULT_PROVIDER_URL,
    container_name: str = DEFAULT_PROVIDER_CONTAINER_NAME,
    port: int = DEFAULT_PROVIDER_PORT,
    cache_paths: tuple[str, ...] = DEFAULT_CACHE_PATHS,
    timeout_seconds: float = 2.0,
) -> Task309HemmaPreflight:
    """Build one Hemma preflight report for the Task 309 provider lane."""

    command_probes = (
        _command_probe("rocminfo", ("rocminfo",)),
        _command_probe("rocm-smi", ("rocm-smi",)),
    )
    cache_path_probes = tuple(_path_probe(path) for path in cache_paths)
    provider_status = build_task309_provider_status(
        provider_url=provider_url,
        container_name=container_name,
        port=port,
        timeout_seconds=timeout_seconds,
    )
    manifest_sha = _sha256_or_none(manifest_path)
    blockers = _preflight_blockers(
        command_probes=command_probes,
        cache_path_probes=cache_path_probes,
        provider_status=provider_status,
        manifest_sha=manifest_sha,
    )
    return Task309HemmaPreflight(
        schema_version=TASK309_HEMMA_PREFLIGHT_SCHEMA_VERSION,
        checked_at=_utc_now_iso(),
        runtime_lane="hemma-localhost-rocm-vllm-granite",
        repo_revision=_text_command(("git", "rev-parse", "HEAD")),
        repo_branch=_text_command(("git", "rev-parse", "--abbrev-ref", "HEAD")),
        manifest_path=manifest_path.as_posix(),
        manifest_sha256=manifest_sha,
        command_probes=command_probes,
        cache_path_probes=cache_path_probes,
        provider_status=provider_status,
        ready=len(blockers) == 0,
        blockers=blockers,
    )


@dataclass(frozen=True)
class _DockerInspectResult:
    payload: dict[str, object] | None
    error_kind: str | None


def _docker_inspect(container_name: str) -> _DockerInspectResult:
    try:
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return _DockerInspectResult(payload=None, error_kind="FileNotFoundError")
    except subprocess.TimeoutExpired:
        return _DockerInspectResult(payload=None, error_kind="TimeoutExpired")
    if result.returncode != 0:
        return _DockerInspectResult(payload=None, error_kind="DockerInspectFailed")
    loaded = json.loads(result.stdout)
    if not isinstance(loaded, list) or not loaded or not isinstance(loaded[0], dict):
        return _DockerInspectResult(payload=None, error_kind="DockerInspectMalformed")
    return _DockerInspectResult(
        payload={str(key): value for key, value in loaded[0].items()},
        error_kind=None,
    )


def _command_probe(name: str, command: tuple[str, ...]) -> Task309CommandProbe:
    try:
        result = subprocess.run(
            list(command),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=20,
        )
    except FileNotFoundError:
        return Task309CommandProbe(
            name=name, command=command, exit_code=None, ok=False, error_kind="FileNotFoundError"
        )
    except subprocess.TimeoutExpired:
        return Task309CommandProbe(
            name=name, command=command, exit_code=None, ok=False, error_kind="TimeoutExpired"
        )
    return Task309CommandProbe(
        name=name,
        command=command,
        exit_code=result.returncode,
        ok=result.returncode == 0,
        error_kind=None,
    )


def _text_command(command: tuple[str, ...]) -> str | None:
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    return text if text else None


def _path_probe(path: str) -> Task309PathProbe:
    path_obj = Path(path)
    return Task309PathProbe(
        path=path,
        exists=path_obj.exists(),
        is_dir=path_obj.is_dir(),
    )


def _container_running(payload: dict[str, object]) -> bool:
    state = _mapping(payload.get("State"))
    return _bool(state.get("Running")) if state is not None else False


def _container_image(payload: dict[str, object]) -> str | None:
    config = _mapping(payload.get("Config"))
    if config is None:
        return _string(payload.get("Image"))
    return _string(config.get("Image")) or _string(payload.get("Image"))


def _container_command(payload: dict[str, object]) -> tuple[str, ...]:
    config = _mapping(payload.get("Config"))
    args = _string_tuple(payload.get("Args"))
    if config is None:
        return args
    entrypoint = _string_tuple(config.get("Entrypoint"))
    cmd = _string_tuple(config.get("Cmd"))
    return entrypoint + cmd + args


def _port_bindings(payload: dict[str, object]) -> tuple[Task309PortBinding, ...]:
    network_settings = _mapping(payload.get("NetworkSettings"))
    if network_settings is None:
        return ()
    ports = _mapping(network_settings.get("Ports"))
    if ports is None:
        return ()
    bindings: list[Task309PortBinding] = []
    for container_port, raw_bindings in ports.items():
        if not isinstance(raw_bindings, list):
            continue
        for raw_binding in raw_bindings:
            binding = _mapping(raw_binding)
            if binding is None:
                continue
            host_ip = _string(binding.get("HostIp"))
            host_port = _string(binding.get("HostPort"))
            if host_ip is not None and host_port is not None:
                bindings.append(
                    Task309PortBinding(
                        container_port=container_port,
                        host_ip=host_ip,
                        host_port=host_port,
                    )
                )
    return tuple(bindings)


def _mounts(payload: dict[str, object]) -> tuple[Task309MountBinding, ...]:
    raw_mounts = payload.get("Mounts")
    if not isinstance(raw_mounts, list):
        return ()
    mounts: list[Task309MountBinding] = []
    for raw_mount in raw_mounts:
        mount = _mapping(raw_mount)
        if mount is None:
            continue
        source = _string(mount.get("Source"))
        destination = _string(mount.get("Destination"))
        mount_type = _string(mount.get("Type"))
        if source is not None and destination is not None and mount_type is not None:
            mounts.append(
                Task309MountBinding(
                    source=source,
                    destination=destination,
                    mount_type=mount_type,
                )
            )
    return tuple(mounts)


def _devices(payload: dict[str, object]) -> tuple[Task309DeviceBinding, ...]:
    host_config = _mapping(payload.get("HostConfig"))
    if host_config is None:
        return ()
    raw_devices = host_config.get("Devices")
    if not isinstance(raw_devices, list):
        return ()
    devices: list[Task309DeviceBinding] = []
    for raw_device in raw_devices:
        device = _mapping(raw_device)
        if device is None:
            continue
        host_path = _string(device.get("PathOnHost"))
        container_path = _string(device.get("PathInContainer"))
        if host_path is not None and container_path is not None:
            devices.append(Task309DeviceBinding(host_path=host_path, container_path=container_path))
    return tuple(devices)


def _tcp_reachable(host: str, port: int, *, timeout_seconds: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _models_endpoint(provider_url: str, *, timeout_seconds: float) -> Task309ModelsEndpointProbe:
    url = provider_url.rstrip("/") + "/v1/models"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code = response.status
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return Task309ModelsEndpointProbe(
            url=url,
            reachable=False,
            status_code=exc.code,
            model_ids=(),
            error_kind="HTTPError",
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return Task309ModelsEndpointProbe(
            url=url,
            reachable=False,
            status_code=None,
            model_ids=(),
            error_kind=type(exc).__name__,
        )
    model_ids = _model_ids(payload)
    return Task309ModelsEndpointProbe(
        url=url,
        reachable=status_code == 200,
        status_code=status_code,
        model_ids=model_ids,
        error_kind=None if status_code == 200 else "UnexpectedStatusCode",
    )


def _model_ids(payload: object) -> tuple[str, ...]:
    mapping = _mapping(payload)
    if mapping is None:
        return ()
    data = mapping.get("data")
    if not isinstance(data, list):
        return ()
    model_ids: list[str] = []
    for raw_model in data:
        model = _mapping(raw_model)
        if model is None:
            continue
        model_id = _string(model.get("id"))
        if model_id is not None:
            model_ids.append(model_id)
    return tuple(sorted(model_ids))


def _localhost_only(bindings: tuple[Task309PortBinding, ...], *, port: int) -> bool:
    expected_port = str(port)
    relevant = tuple(binding for binding in bindings if binding.host_port == expected_port)
    if not relevant:
        return False
    allowed_hosts = {"127.0.0.1", "::1", "localhost"}
    return all(binding.host_ip in allowed_hosts for binding in relevant)


def _gpu_devices_mounted(devices: tuple[Task309DeviceBinding, ...]) -> bool:
    device_paths = {device.host_path for device in devices} | {
        device.container_path for device in devices
    }
    return "/dev/kfd" in device_paths and any(path.startswith("/dev/dri") for path in device_paths)


def _preflight_blockers(
    *,
    command_probes: tuple[Task309CommandProbe, ...],
    cache_path_probes: tuple[Task309PathProbe, ...],
    provider_status: Task309ProviderStatus,
    manifest_sha: str | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if manifest_sha is None:
        blockers.append("manifest_missing")
    for command_probe in command_probes:
        if not command_probe.ok:
            blockers.append(f"{command_probe.name}_failed")
    for path_probe in cache_path_probes:
        if not path_probe.exists or not path_probe.is_dir:
            blockers.append(f"cache_path_missing:{path_probe.path}")
    if not provider_status.container_running:
        blockers.append("provider_container_not_running")
    if not provider_status.tcp_reachable:
        blockers.append("provider_port_unreachable")
    if not provider_status.models_endpoint.reachable:
        blockers.append("provider_models_endpoint_unreachable")
    if not provider_status.localhost_only:
        blockers.append("provider_not_localhost_only")
    if not provider_status.request_logging_disabled:
        blockers.append("provider_request_logging_not_proved_disabled")
    if not provider_status.no_cpu_fallback_proved:
        blockers.append("provider_no_cpu_fallback_not_proved")
    return tuple(blockers)


def _sha256_or_none(path: Path) -> str | None:
    if not path.exists():
        return None
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): child for key, child in value.items()}


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _bool(value: object) -> bool:
    return value if isinstance(value, bool) else False


def _string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, list):
        return ()
    strings: list[str] = []
    for entry in value:
        if isinstance(entry, str):
            strings.append(entry)
    return tuple(strings)
