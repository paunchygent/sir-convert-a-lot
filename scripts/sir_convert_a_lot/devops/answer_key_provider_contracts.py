"""answer-key live validation Granite provider preflight report contracts.

Purpose:
    Define the typed JSON-safe contracts for answer-key live validation Hemma Granite/vLLM
    provider status and preflight reports.

Relationships:
    - Used by `answer_key_granite_provider_status` for non-mutating runtime
      probes.
    - Used by `answer_key_provider_reporting` for retained JSON and
      Markdown artifacts.
    - Mirrors the Hemma GPU runtime runbook checks without carrying command
      execution logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

ANSWER_KEY_PROVIDER_STATUS_SCHEMA_VERSION = "answer_key_granite_provider_status_v1"
ANSWER_KEY_HEMMA_PREFLIGHT_SCHEMA_VERSION = "answer_key_granite_hemma_preflight_v1"
ANSWER_KEY_PROVIDER_PERSISTENT_POLICY = "leave_running_until_operator_stop"
ANSWER_KEY_LLAMA_PROVIDER_LAUNCH_SCHEMA_VERSION = "answer_key_llama_provider_launch_v1"
DEFAULT_PROVIDER_URL = "http://127.0.0.1:8017"
DEFAULT_PROVIDER_CONTAINER_NAME = "sir-convert-answer-key-live-validation-granite-vllm"
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
class AnswerKeyCommandProbe:
    """One command-availability probe without persisted stdout or stderr."""

    name: str
    command: tuple[str, ...]
    exit_code: int | None
    ok: bool
    error_kind: str | None


@dataclass(frozen=True)
class AnswerKeyPathProbe:
    """One Hemma path preflight probe."""

    path: str
    exists: bool
    is_dir: bool


@dataclass(frozen=True)
class AnswerKeyPortBinding:
    """One Docker host-port binding relevant to the vLLM provider."""

    container_port: str
    host_ip: str
    host_port: str


@dataclass(frozen=True)
class AnswerKeyMountBinding:
    """One sanitized Docker mount binding."""

    source: str
    destination: str
    mount_type: str


@dataclass(frozen=True)
class AnswerKeyDeviceBinding:
    """One sanitized Docker device binding."""

    host_path: str
    container_path: str


@dataclass(frozen=True)
class AnswerKeyModelsEndpointProbe:
    """One vLLM models endpoint probe."""

    url: str
    reachable: bool
    status_code: int | None
    model_ids: tuple[str, ...]
    error_kind: str | None


@dataclass(frozen=True)
class AnswerKeyProviderStatus:
    """Persistent answer-key live validation provider status report."""

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
    port_bindings: tuple[AnswerKeyPortBinding, ...]
    mounts: tuple[AnswerKeyMountBinding, ...]
    devices: tuple[AnswerKeyDeviceBinding, ...]
    tcp_reachable: bool
    models_endpoint: AnswerKeyModelsEndpointProbe
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
class AnswerKeyHemmaPreflight:
    """Hemma preflight report for answer-key live validation live validation."""

    schema_version: str
    checked_at: str
    runtime_lane: str
    repo_revision: str | None
    repo_branch: str | None
    manifest_path: str
    manifest_sha256: str | None
    command_probes: tuple[AnswerKeyCommandProbe, ...]
    cache_path_probes: tuple[AnswerKeyPathProbe, ...]
    provider_status: AnswerKeyProviderStatus
    ready: bool
    blockers: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the Hemma preflight report."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class AnswerKeyProviderLaunchPlan:
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
class AnswerKeyProviderLaunchResult:
    """Result of a answer-key live validation persistent provider launch attempt."""

    schema_version: str
    launched_at: str
    container_name: str
    dry_run: bool
    exit_code: int | None
    container_id: str | None
    ok: bool
    error_kind: str | None
    plan: AnswerKeyProviderLaunchPlan

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the provider launch result."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class AnswerKeyLlamaProviderLaunchPlan:
    """Persistent llama.cpp launch command and policy for answer-key live validation."""

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
class AnswerKeyLlamaProviderLaunchResult:
    """Result of a answer-key live validation persistent llama.cpp launch attempt."""

    schema_version: str
    launched_at: str
    provider_profile: str
    dry_run: bool
    exit_code: int | None
    pid: int | None
    ok: bool
    error_kind: str | None
    plan: AnswerKeyLlamaProviderLaunchPlan

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the llama.cpp launch result."""

        return _json_object(asdict(self))


def _json_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(
            "answer-key live validation provider report must serialize to a JSON object."
        )
    return {str(key): _json_value(child) for key, child in value.items()}


def _json_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(
        f"Unsupported answer-key live validation provider JSON value: {type(value).__name__}"
    )
