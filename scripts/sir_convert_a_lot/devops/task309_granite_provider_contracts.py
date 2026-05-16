"""Task 309 Granite provider preflight report contracts.

Purpose:
    Define the typed JSON-safe contracts for Task 309 Hemma Granite/vLLM
    provider status and preflight reports.

Relationships:
    - Used by `task309_granite_provider_status` for non-mutating runtime
      probes.
    - Used by `task309_granite_provider_reporting` for retained JSON and
      Markdown artifacts.
    - Mirrors the Hemma GPU runtime runbook checks without carrying command
      execution logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

TASK309_PROVIDER_STATUS_SCHEMA_VERSION = "task309_granite_provider_status_v1"
TASK309_HEMMA_PREFLIGHT_SCHEMA_VERSION = "task309_granite_hemma_preflight_v1"
TASK309_PROVIDER_PERSISTENT_POLICY = "leave_running_until_operator_stop"
TASK309_LLAMA_PROVIDER_LAUNCH_SCHEMA_VERSION = "task309_llama_provider_launch_v1"
DEFAULT_PROVIDER_URL = "http://127.0.0.1:8017"
DEFAULT_PROVIDER_CONTAINER_NAME = "sir-convert-task309-granite-vllm"
DEFAULT_PROVIDER_PORT = 8017
DEFAULT_CACHE_PATHS = (
    "/srv/scratch/sir-convert-a-lot/cache/huggingface",
    "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
)
DEFAULT_PROVIDER_IMAGE = (
    "rocm/vllm:rocm7.12.0_gfx120X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0"
)
DEFAULT_PROVIDER_MODEL = "ibm-granite/granite-4.1-8b-fp8"
DEFAULT_PROVIDER_HOST_CACHE = "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"
DEFAULT_PROVIDER_CONTAINER_CACHE = "/cache/huggingface"
DEFAULT_PROVIDER_MAX_MODEL_LEN = 16384
DEFAULT_PROVIDER_GPU_MEMORY_UTILIZATION = "0.80"


@dataclass(frozen=True)
class Task309CommandProbe:
    """One command-availability probe without persisted stdout or stderr."""

    name: str
    command: tuple[str, ...]
    exit_code: int | None
    ok: bool
    error_kind: str | None


@dataclass(frozen=True)
class Task309PathProbe:
    """One Hemma path preflight probe."""

    path: str
    exists: bool
    is_dir: bool


@dataclass(frozen=True)
class Task309PortBinding:
    """One Docker host-port binding relevant to the vLLM provider."""

    container_port: str
    host_ip: str
    host_port: str


@dataclass(frozen=True)
class Task309MountBinding:
    """One sanitized Docker mount binding."""

    source: str
    destination: str
    mount_type: str


@dataclass(frozen=True)
class Task309DeviceBinding:
    """One sanitized Docker device binding."""

    host_path: str
    container_path: str


@dataclass(frozen=True)
class Task309ModelsEndpointProbe:
    """One vLLM models endpoint probe."""

    url: str
    reachable: bool
    status_code: int | None
    model_ids: tuple[str, ...]
    error_kind: str | None


@dataclass(frozen=True)
class Task309ProviderStatus:
    """Persistent Task 309 provider status report."""

    schema_version: str
    checked_at: str
    provider_url: str
    container_name: str
    persistent_policy: str
    docker_available: bool
    container_present: bool
    container_running: bool
    container_image: str | None
    container_command: tuple[str, ...]
    port_bindings: tuple[Task309PortBinding, ...]
    mounts: tuple[Task309MountBinding, ...]
    devices: tuple[Task309DeviceBinding, ...]
    tcp_reachable: bool
    models_endpoint: Task309ModelsEndpointProbe
    localhost_only: bool
    localhost_tcp_listener: bool
    request_logging_disabled: bool
    rocm_image: bool
    gpu_devices_mounted: bool
    no_cpu_fallback_proved: bool
    expected_model_id: str | None
    expected_model_present: bool
    llama_process_present: bool
    llama_process_command: tuple[str, ...]
    llama_required_args_present: bool
    llama_required_args: tuple[str, ...]
    ready: bool

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the provider status report."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class Task309HemmaPreflight:
    """Hemma preflight report for Task 309 live validation."""

    schema_version: str
    checked_at: str
    runtime_lane: str
    repo_revision: str | None
    repo_branch: str | None
    manifest_path: str
    manifest_sha256: str | None
    command_probes: tuple[Task309CommandProbe, ...]
    cache_path_probes: tuple[Task309PathProbe, ...]
    provider_status: Task309ProviderStatus
    ready: bool
    blockers: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the Hemma preflight report."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class Task309ProviderLaunchPlan:
    """Persistent Granite/vLLM Docker launch command and policy."""

    schema_version: str
    generated_at: str
    container_name: str
    image: str
    model: str
    host_port: int
    container_port: int
    host_cache_path: str
    container_cache_path: str
    persistent_policy: str
    command: tuple[str, ...]
    dry_run: bool

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the provider launch plan."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class Task309ProviderLaunchResult:
    """Result of a Task 309 persistent provider launch attempt."""

    schema_version: str
    launched_at: str
    container_name: str
    dry_run: bool
    exit_code: int | None
    container_id: str | None
    ok: bool
    error_kind: str | None
    plan: Task309ProviderLaunchPlan

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the provider launch result."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class Task309LlamaProviderLaunchPlan:
    """Persistent llama.cpp launch command and policy for Task 309."""

    schema_version: str
    generated_at: str
    provider_profile: str
    provider_url: str
    model: str
    host: str
    port: int
    server_binary: str
    hf_repo: str
    hf_file: str
    llama_cache_path: str
    xdg_cache_home: str
    media_path: str
    output_root: str
    log_path: str
    pid_path: str
    persistent_policy: str
    command: tuple[str, ...]
    dry_run: bool

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the llama.cpp launch plan."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class Task309LlamaProviderLaunchResult:
    """Result of a Task 309 persistent llama.cpp launch attempt."""

    schema_version: str
    launched_at: str
    provider_profile: str
    dry_run: bool
    exit_code: int | None
    pid: int | None
    ok: bool
    error_kind: str | None
    plan: Task309LlamaProviderLaunchPlan

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the llama.cpp launch result."""

        return _json_object(asdict(self))


def _json_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("Task 309 provider report must serialize to a JSON object.")
    return {str(key): _json_value(child) for key, child in value.items()}


def _json_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported Task 309 provider JSON value: {type(value).__name__}")
