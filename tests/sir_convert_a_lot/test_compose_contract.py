"""Compose contract tests for single-runtime startup semantics.

Purpose:
    Verify `compose.yaml` and `Dockerfile` encode deterministic single-runtime
    startup and readiness-gated health checks.

Relationships:
    - Validates compose/runtime expectations after eval-lane removal.
    - Protects runbook/task assumptions for docker compose command surfaces.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "compose.yaml"
DOCKERFILE = REPO_ROOT / "Dockerfile"
DOCKERFILE_QWEN_PROVIDER = REPO_ROOT / "Dockerfile.qwen-provider"
DOCKERFILE_DEPS = REPO_ROOT / "Dockerfile.deps"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
PROD_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "prod-compose.sh"
COMPOSE_ACTIONS_SCRIPT = REPO_ROOT / "scripts" / "devops" / "compose-actions.sh"
SERVICE_DEPS_IMAGE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "service-deps-image.sh"
PYPROJECT_FILE = REPO_ROOT / "pyproject.toml"


def _load_compose() -> dict[str, object]:
    raw = COMPOSE_FILE.read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)
    if not isinstance(loaded, dict):
        raise AssertionError("compose.yaml did not parse into a mapping")
    return loaded


def _load_dockerignore_rules() -> set[str]:
    raw_rules = DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    return {
        line.strip()
        for line in raw_rules
        if line.strip() != "" and not line.lstrip().startswith("#")
    }


def _service_env_map(service: dict[str, object]) -> dict[str, str]:
    env_obj = service.get("environment")
    if isinstance(env_obj, dict):
        env_map: dict[str, str] = {}
        for key, value in env_obj.items():
            if isinstance(key, str) and isinstance(value, str):
                env_map[key] = value
        return env_map
    if not isinstance(env_obj, list):
        return {}
    parsed_env_map: dict[str, str] = {}
    for item in env_obj:
        if not isinstance(item, str) or "=" not in item:
            continue
        key, value = item.split("=", maxsplit=1)
        parsed_env_map[key] = value
    return parsed_env_map


def _require_service(compose: dict[str, object], service_name: str) -> dict[str, object]:
    services_obj = compose.get("services")
    if not isinstance(services_obj, dict):
        raise AssertionError("compose services section missing")
    service_obj = services_obj.get(service_name)
    if not isinstance(service_obj, dict):
        raise AssertionError(f"compose service missing: {service_name}")
    return service_obj


def test_compose_declares_prod_runtime_and_private_qwen_provider_services() -> None:
    compose = _load_compose()
    services_obj = compose.get("services")
    assert isinstance(services_obj, dict)
    assert "sir_convert_a_lot_prod" in services_obj
    assert "sir_convert_a_lot_gpu_worker" in services_obj
    assert "sir_convert_a_lot_stt_sidecar" in services_obj
    assert "sir_convert_qwen_answer_key" in services_obj
    assert "sir_convert_a_lot_public_reserved" in services_obj
    assert "sir_convert_a_lot_eval" not in services_obj


def test_compose_uses_readyz_healthcheck_with_deterministic_timing() -> None:
    compose = _load_compose()
    service = _require_service(compose, "sir_convert_a_lot_prod")
    health_obj = service.get("healthcheck")
    assert isinstance(health_obj, dict)
    test_obj = health_obj.get("test")
    assert isinstance(test_obj, list)
    joined = " ".join(str(item) for item in test_obj)
    assert "http://localhost:8085/readyz" in joined
    assert "8086" not in joined
    assert health_obj.get("interval") == "30s"
    assert health_obj.get("timeout") == "10s"
    assert health_obj.get("retries") == 3
    assert health_obj.get("start_period") == "15s"


def test_compose_enforces_single_runtime_restart_env_and_command() -> None:
    compose = _load_compose()
    service = _require_service(compose, "sir_convert_a_lot_prod")

    assert service.get("restart") == "unless-stopped"
    assert service.get("container_name") == "sir_convert_a_lot_prod"
    assert service.get("env_file") is None

    env_map = _service_env_map(service)
    assert (
        env_map["SIR_CONVERT_A_LOT_V2_API_KEY"] == "${SIR_CONVERT_A_LOT_V2_API_KEY:-dev-only-key}"
    )
    assert env_map["SIR_CONVERT_A_LOT_EXAM_AUTHORING_SOURCE_STATE_SIGNATURE_SECRET"] == (
        "${SIR_CONVERT_A_LOT_EXAM_AUTHORING_SOURCE_STATE_SIGNATURE_SECRET:-}"
    )
    assert (
        env_map["SIR_CONVERT_A_LOT_SERVICE_REVISION"]
        == "${SIR_CONVERT_A_LOT_SERVICE_REVISION:-unknown}"
    )
    assert (
        env_map["SIR_CONVERT_A_LOT_EXPECTED_REVISION"]
        == "${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-unknown}"
    )
    assert env_map["SIR_CONVERT_A_LOT_DATA_DIR"] == "/var/lib/sir-convert-a-lot/prod"
    assert env_map["SIR_CONVERT_A_LOT_GPU_AVAILABLE"] == "0"
    assert env_map["SIR_CONVERT_A_LOT_ENABLE_SUPERVISOR"] == "0"
    assert env_map["SIR_CONVERT_A_LOT_RUN_JOBS_ON_SUBMIT"] == "0"
    assert "SIR_CONVERT_A_LOT_EVAL_DATA_DIR" not in env_map
    assert "VIRTUAL_HOST" not in env_map
    assert "VIRTUAL_PORT" not in env_map
    assert "LETSENCRYPT_HOST" not in env_map
    assert env_map["SIR_CONVERT_A_LOT_ENABLE_SSE_STREAM"] == (
        "${SIR_CONVERT_A_LOT_ENABLE_SSE_STREAM:-0}"
    )
    assert env_map["SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_ONBOARDING"] == (
        "${SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_ONBOARDING:-0}"
    )
    assert env_map["SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_DELIVERY"] == (
        "${SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_DELIVERY:-0}"
    )
    assert (
        env_map["SIR_CONVERT_A_LOT_STT_SIDECAR_BASE_URL"]
        == "http://sir_convert_a_lot_stt_sidecar:8095"
    )
    assert env_map["SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL"] == (
        "${SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL:-docling_layout_egret_large}"
    )
    assert env_map["MIOPEN_FIND_MODE"] == "${MIOPEN_FIND_MODE:-FAST}"
    assert env_map["MIOPEN_USER_DB_PATH"] == (
        "${MIOPEN_USER_DB_PATH:-/srv/scratch/sir-convert-a-lot/cache/miopen/user-db}"
    )
    assert env_map["MIOPEN_CUSTOM_CACHE_DIR"] == (
        "${MIOPEN_CUSTOM_CACHE_DIR:-/srv/scratch/sir-convert-a-lot/cache/miopen/kernel-cache}"
    )
    assert env_map["HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH"] == (
        "/run/secrets/huleedu-gateway-internal-identity-public-key.pem"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_ENABLED"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_ENABLED:-0}"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDER_PROFILE"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDER_PROFILE:-}"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_RUNTIME_LANE"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_RUNTIME_LANE:-local-compose}"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDERS_JSON"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDERS_JSON:-}"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_PRIMARY_PROVIDER_ID"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_PRIMARY_PROVIDER_ID:-}"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_FALLBACK_PROVIDER_ID"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_FALLBACK_PROVIDER_ID:-}"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED:-0}"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED:-0}"
    )
    assert env_map["SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_PATH"] == (
        "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_PATH:-"
        "/srv/scratch/sir-convert-a-lot/build/verification/"
        "answer-key-qwen-provider/vision-assets}"
    )
    assert env_map["SIR_CONVERT_A_LOT_OPENAI_API_KEY"] == ("${SIR_CONVERT_A_LOT_OPENAI_API_KEY:-}")

    assert service.get("command") == [
        "uvicorn",
        "scripts.sir_convert_a_lot.service:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8085",
    ]
    volumes = service.get("volumes")
    assert volumes == [
        "sir-convert-a-lot-prod-data:/var/lib/sir-convert-a-lot/prod",
        (
            "${SIR_CONVERT_A_LOT_MIOPEN_CACHE_HOST_DIR:-"
            "/home/paunchygent/.data/sir-convert-a-lot/cache/miopen}:"
            "/srv/scratch/sir-convert-a-lot/cache/miopen"
        ),
        (
            "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_HOST_PATH:-"
            "/home/paunchygent/.data/sir-convert-a-lot/build/verification/"
            "answer-key-qwen-provider/vision-assets}:"
            "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_PATH:-"
            "/srv/scratch/sir-convert-a-lot/build/verification/"
            "answer-key-qwen-provider/vision-assets}"
        ),
        (
            "${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH:-"
            "/home/paunchygent/apps/huleedu/secrets/hemma-runtime/internal-identity/"
            "gateway-internal-identity-public-key.pem}:"
            "/run/secrets/huleedu-gateway-internal-identity-public-key.pem:ro"
        ),
    ]
    assert service.get("depends_on") is None
    assert service.get("devices") is None
    assert service.get("group_add") is None


def test_compose_declares_gpu_worker_as_private_execution_lane() -> None:
    compose = _load_compose()
    service = _require_service(compose, "sir_convert_a_lot_gpu_worker")

    assert service.get("image") == "sir-convert-a-lot-runtime:${SIR_CONVERT_A_LOT_IMAGE_TAG:-local}"
    assert service.get("container_name") == "sir_convert_a_lot_gpu_worker"
    assert service.get("restart") == "unless-stopped"
    assert service.get("ports") is None
    assert service.get("expose") == ["8085"]

    build_obj = service.get("build")
    assert isinstance(build_obj, dict)
    assert build_obj.get("context") == "."
    assert build_obj.get("dockerfile") == "Dockerfile"
    assert build_obj.get("args") == {
        "DEPS_IMAGE": "${SIR_CONVERT_A_LOT_DEPS_IMAGE:-sir-convert-a-lot-deps-rocm:local}"
    }

    env_map = _service_env_map(service)
    assert env_map["SIR_CONVERT_A_LOT_DATA_DIR"] == "/var/lib/sir-convert-a-lot/prod"
    assert env_map["SIR_CONVERT_A_LOT_GPU_AVAILABLE"] == "${SIR_CONVERT_A_LOT_GPU_AVAILABLE:-1}"
    assert env_map["SIR_CONVERT_A_LOT_ENABLE_SUPERVISOR"] == "1"
    assert env_map["SIR_CONVERT_A_LOT_RUN_JOBS_ON_SUBMIT"] == "0"
    assert env_map["SIR_CONVERT_A_LOT_ENABLE_SSE_STREAM"] == "0"
    assert (
        env_map["SIR_CONVERT_A_LOT_STT_SIDECAR_BASE_URL"]
        == "http://sir_convert_a_lot_stt_sidecar:8095"
    )
    assert env_map["SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE"] == "easyocr"
    assert env_map["SIR_CONVERT_A_LOT_OPENAI_API_KEY"] == ("${SIR_CONVERT_A_LOT_OPENAI_API_KEY:-}")

    assert service.get("devices") == ["/dev/kfd:/dev/kfd", "/dev/dri:/dev/dri"]
    assert service.get("group_add") == [
        "${SIR_CONVERT_A_LOT_GPU_VIDEO_GROUP_ID:-44}",
        "${SIR_CONVERT_A_LOT_GPU_RENDER_GROUP_ID:-993}",
    ]
    assert service.get("depends_on") == {
        "sir_convert_a_lot_stt_sidecar": {"condition": "service_healthy"}
    }
    assert service.get("volumes") == [
        "sir-convert-a-lot-prod-data:/var/lib/sir-convert-a-lot/prod",
        (
            "${SIR_CONVERT_A_LOT_MIOPEN_CACHE_HOST_DIR:-"
            "/home/paunchygent/.data/sir-convert-a-lot/cache/miopen}:"
            "/srv/scratch/sir-convert-a-lot/cache/miopen"
        ),
        (
            "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_HOST_PATH:-"
            "/home/paunchygent/.data/sir-convert-a-lot/build/verification/"
            "answer-key-qwen-provider/vision-assets}:"
            "${SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_PATH:-"
            "/srv/scratch/sir-convert-a-lot/build/verification/"
            "answer-key-qwen-provider/vision-assets}"
        ),
        (
            "${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH:-"
            "/home/paunchygent/apps/huleedu/secrets/hemma-runtime/internal-identity/"
            "gateway-internal-identity-public-key.pem}:"
            "/run/secrets/huleedu-gateway-internal-identity-public-key.pem:ro"
        ),
    ]


def test_compose_declares_private_stt_sidecar_runtime() -> None:
    compose = _load_compose()
    service = _require_service(compose, "sir_convert_a_lot_stt_sidecar")

    assert service.get("image") == (
        "sir-convert-a-lot-stt-sidecar:${SIR_CONVERT_A_LOT_STT_SIDECAR_IMAGE_TAG:-local}"
    )
    assert service.get("container_name") == "sir_convert_a_lot_stt_sidecar"
    assert service.get("restart") == "unless-stopped"
    assert service.get("ports") is None
    assert service.get("expose") == ["8095"]
    assert service.get("command") == [
        "uvicorn",
        "scripts.sir_convert_a_lot.stt_sidecar.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8095",
    ]

    build_obj = service.get("build")
    assert isinstance(build_obj, dict)
    assert build_obj.get("context") == "."
    assert build_obj.get("dockerfile") == "containers/stt-sidecar-benchmark/Dockerfile"
    assert build_obj.get("args") == {
        "BASE_IMAGE": "${SIR_CONVERT_A_LOT_DEPS_IMAGE:-sir-convert-a-lot-deps-rocm:local}"
    }

    env_map = _service_env_map(service)
    assert env_map["HF_HOME"] == "/cache/huggingface"
    assert env_map["HF_TOKEN"] == "${HF_TOKEN:-}"
    assert env_map["SIR_STT_SIDECAR_STT_PROFILE_LABEL"] == "stt_sv_en_primary"
    assert env_map["SIR_STT_SIDECAR_DIARIZATION_PROFILE_LABEL"] == "diarization_sv_en_primary"
    assert env_map["SIR_STT_SIDECAR_ACCELERATION_FAMILY"] == "rocm"

    assert service.get("devices") == ["/dev/kfd:/dev/kfd", "/dev/dri:/dev/dri"]
    assert service.get("group_add") == [
        "${SIR_CONVERT_A_LOT_GPU_VIDEO_GROUP_ID:-44}",
        "${SIR_CONVERT_A_LOT_GPU_RENDER_GROUP_ID:-993}",
    ]
    assert service.get("volumes") == [
        "sir-convert-a-lot-prod-data:/var/lib/sir-convert-a-lot/prod",
        (
            "${SIR_CONVERT_A_LOT_HF_CACHE_HOST_DIR:-"
            "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface}:"
            "/cache/huggingface"
        ),
    ]
    assert service.get("networks") == ["hule-network"]
    health_obj = service.get("healthcheck")
    assert isinstance(health_obj, dict)
    assert "http://localhost:8095/health" in " ".join(
        str(item) for item in health_obj.get("test", [])
    )
    assert health_obj.get("retries") == 20
    assert health_obj.get("start_period") == "120s"


def test_compose_declares_private_qwen_provider_runtime() -> None:
    compose = _load_compose()
    service = _require_service(compose, "sir_convert_qwen_answer_key")

    assert service.get("image") == (
        "sir-convert-qwen-llama-runtime:${SIR_CONVERT_A_LOT_QWEN_PROVIDER_IMAGE_TAG:-local}"
    )
    assert service.get("container_name") == "sir_convert_qwen_answer_key"
    assert service.get("restart") == "unless-stopped"
    assert service.get("ports") is None
    assert service.get("expose") == ["8082"]
    env_map = _service_env_map(service)
    assert env_map["LD_LIBRARY_PATH"] == (
        "${SIR_CONVERT_A_LOT_QWEN_ROCM_LIBRARY_PATH:-"
        "/opt/python/lib/python3.12/site-packages/_rocm_sdk_devel/lib:"
        "/opt/python/lib/python3.12/site-packages/_rocm_sdk_libraries_gfx120X_all/lib:"
        "/opt/python/lib/python3.12/site-packages/_rocm_sdk_core/lib:"
        "/usr/lib/x86_64-linux-gnu}"
    )

    build_obj = service.get("build")
    assert isinstance(build_obj, dict)
    assert build_obj.get("context") == "."
    assert build_obj.get("dockerfile") == "Dockerfile.qwen-provider"

    command = service.get("command")
    assert isinstance(command, list)
    joined_command = " ".join(str(item) for item in command)
    assert "/srv/scratch/sir-convert-a-lot/bin/llama-server" in command
    assert "-hf ${SIR_CONVERT_A_LOT_QWEN36_HF_REPO:-unsloth/Qwen3.6-27B-MTP-GGUF}" in (
        joined_command
    )
    assert "-hff ${SIR_CONVERT_A_LOT_QWEN36_HF_FILE:-Qwen3.6-27B-Q6_K.gguf}" in joined_command
    assert "--alias ${SIR_CONVERT_A_LOT_QWEN36_MODEL:-qwen3.6-27b-q6k-mtp}" in joined_command
    assert "--host 0.0.0.0 --port 8082" in joined_command
    assert "--ctx-size 16384" in joined_command
    assert "--parallel 1" in joined_command
    assert "--n-gpu-layers all" in joined_command
    assert "--fit off" in joined_command
    assert "--flash-attn on" in joined_command
    assert "--jinja" in command
    assert "--reasoning off" in joined_command
    assert "--temp ${SIR_CONVERT_A_LOT_QWEN36_TEMPERATURE:-0.15}" in joined_command
    assert "--offline" in command
    assert "--spec-type draft-mtp" in joined_command
    assert "--spec-draft-n-max 2" in joined_command
    assert "--top-p" not in command
    assert "--top-k" not in command

    assert service.get("devices") == ["/dev/kfd:/dev/kfd", "/dev/dri:/dev/dri"]
    assert service.get("group_add") == [
        "${SIR_CONVERT_A_LOT_GPU_VIDEO_GROUP_ID:-44}",
        "${SIR_CONVERT_A_LOT_GPU_RENDER_GROUP_ID:-993}",
    ]
    assert service.get("networks") == ["hule-network"]
    volumes = service.get("volumes")
    assert isinstance(volumes, list)
    assert volumes == [
        (
            "${SIR_CONVERT_A_LOT_QWEN_LLAMA_SERVER_HOST_PATH:-"
            "/home/paunchygent/.data/sir-convert-a-lot/build/"
            "llama.cpp-qwen35/build-hip/bin/llama-server}:"
            "/srv/scratch/sir-convert-a-lot/bin/llama-server:ro"
        ),
        (
            "${SIR_CONVERT_A_LOT_QWEN_DOCKER_BUILD_HOST_PATH:-"
            "/home/paunchygent/.data/sir-convert-a-lot/build}:"
            "/srv/scratch/sir-convert-a-lot/build"
        ),
        (
            "${SIR_CONVERT_A_LOT_QWEN_DOCKER_CACHE_HOST_PATH:-"
            "/home/paunchygent/.data/sir-convert-a-lot/cache}:"
            "/srv/scratch/sir-convert-a-lot/cache"
        ),
    ]
    assert all("/opt/rocm" not in str(volume) for volume in volumes)
    assert all("/opt/amdgpu" not in str(volume) for volume in volumes)

    health_obj = service.get("healthcheck")
    assert isinstance(health_obj, dict)
    assert "http://localhost:8082/v1/models" in " ".join(
        str(item) for item in health_obj.get("test", [])
    )
    assert health_obj.get("retries") == 20
    assert health_obj.get("start_period") == "120s"


def test_compose_routes_public_host_to_reserved_edge_not_app() -> None:
    compose = _load_compose()
    reserved_service = _require_service(compose, "sir_convert_a_lot_public_reserved")

    assert reserved_service.get("image") == "nginx:1.27-alpine"
    assert reserved_service.get("container_name") == "sir_convert_a_lot_public_reserved"
    assert reserved_service.get("restart") == "unless-stopped"
    assert reserved_service.get("volumes") == [
        "./docker/public-edge/reserved-default.conf:/etc/nginx/conf.d/default.conf:ro"
    ]
    assert reserved_service.get("expose") == ["8080"]

    env_map = _service_env_map(reserved_service)
    assert env_map["VIRTUAL_HOST"] == "${SIR_CONVERT_A_LOT_PUBLIC_HOST:-convert.hule.education}"
    assert env_map["VIRTUAL_PORT"] == "8080"
    assert env_map["LETSENCRYPT_HOST"] == "${SIR_CONVERT_A_LOT_PUBLIC_HOST:-convert.hule.education}"

    reserved_config = (REPO_ROOT / "docker" / "public-edge" / "reserved-default.conf").read_text(
        encoding="utf-8"
    )
    assert "return 421" in reserved_config
    assert "sir-convert-a-lot-public-edge-reserved" in reserved_config


def test_compose_declares_rocm_build_args_without_api_gpu_passthrough() -> None:
    compose = _load_compose()
    service = _require_service(compose, "sir_convert_a_lot_prod")

    assert service.get("image") == "sir-convert-a-lot-runtime:${SIR_CONVERT_A_LOT_IMAGE_TAG:-local}"

    build_obj = service.get("build")
    assert isinstance(build_obj, dict)
    assert build_obj.get("context") == "."
    assert build_obj.get("dockerfile") == "Dockerfile"
    assert build_obj.get("args") == {
        "DEPS_IMAGE": "${SIR_CONVERT_A_LOT_DEPS_IMAGE:-sir-convert-a-lot-deps-rocm:local}"
    }

    assert service.get("devices") is None
    assert service.get("group_add") is None


def test_dockerignore_limits_build_context_to_service_runtime_contract() -> None:
    dockerignore_rules = _load_dockerignore_rules()

    assert "*" in dockerignore_rules
    assert "scripts/*" in dockerignore_rules
    assert "scripts/sir_convert_a_lot/*" in dockerignore_rules
    assert "scripts/sir_convert_a_lot/devops/*" in dockerignore_rules

    required_file_paths = {
        "docker/service-deps",
        "docker/service-deps/**",
        "scripts/__init__.py",
        "scripts/sir_convert_a_lot/__init__.py",
        "scripts/sir_convert_a_lot/service.py",
    }
    for path in required_file_paths:
        assert f"!{path}" in dockerignore_rules

    required_directory_paths = {
        "scripts/sir_convert_a_lot/application",
        "scripts/sir_convert_a_lot/domain",
        "scripts/sir_convert_a_lot/infrastructure",
        "scripts/sir_convert_a_lot/integrations",
        "scripts/sir_convert_a_lot/interfaces",
        "scripts/sir_convert_a_lot/stt_sidecar",
        "scripts/sir_convert_a_lot/templates",
    }
    for path in required_directory_paths:
        assert f"!{path}" in dockerignore_rules
        assert f"!{path}/**" in dockerignore_rules

    assert "!docs" not in dockerignore_rules
    assert "!tests" not in dockerignore_rules
    assert "!build" not in dockerignore_rules
    assert "!pyproject.toml" not in dockerignore_rules
    assert "!pdm.lock" not in dockerignore_rules
    assert "!scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_runtime_probe.py" in (
        dockerignore_rules
    )


def test_compose_declares_only_prod_named_volume() -> None:
    compose = _load_compose()
    volumes_obj = compose.get("volumes")
    assert isinstance(volumes_obj, dict)
    assert "sir-convert-a-lot-prod-data" in volumes_obj
    assert "sir-convert-a-lot-eval-data" not in volumes_obj


def test_prod_compose_helper_targets_production_compose_surface() -> None:
    script_text = PROD_COMPOSE_SCRIPT.read_text(encoding="utf-8")
    assert 'SIR_CONVERT_A_LOT_COMPOSE_FILE="${REPO_ROOT}/compose.yaml"' in script_text
    assert 'SIR_CONVERT_A_LOT_DEPS_RUNTIME="rocm"' in script_text


def test_prod_pdm_scripts_expose_dependency_image_lane() -> None:
    pyproject_text = PYPROJECT_FILE.read_text(encoding="utf-8")
    assert (
        '"prod-deps-rocm-build" = "bash scripts/devops/service-deps-image.sh rocm build"'
        in pyproject_text
    )
    assert (
        '"prod-deps-rocm-build-clean" = '
        '"bash scripts/devops/service-deps-image.sh rocm build-clean"' in pyproject_text
    )
    assert '"prod-build" = "bash scripts/devops/prod-compose.sh build"' in pyproject_text
    assert '"prod-recreate" = "bash scripts/devops/prod-compose.sh recreate"' in pyproject_text


def test_compose_actions_ensures_dependency_image_before_app_builds() -> None:
    script_text = COMPOSE_ACTIONS_SCRIPT.read_text(encoding="utf-8")
    assert "service-deps-image.sh" in script_text
    assert 'export SIR_CONVERT_A_LOT_DEPS_IMAGE="${value}"' in script_text
    assert "ensure_dependency_image" in script_text


def test_dependency_image_helper_writes_runtime_identity_to_ignored_output() -> None:
    script_text = SERVICE_DEPS_IMAGE_SCRIPT.read_text(encoding="utf-8")
    assert 'CONTRACT_DIR="${REPO_ROOT}/docker/service-deps"' in script_text
    assert "IDENTITY_OUTPUT_DIR=" in script_text
    assert "--identity-output-dir" in script_text
    assert "build/verification/service-deps" in script_text


def test_dockerfile_consumes_explicit_rocm_dependency_image_for_single_service() -> None:
    dockerfile_text = DOCKERFILE.read_text(encoding="utf-8")
    assert "ARG DEPS_IMAGE=sir-convert-a-lot-deps-rocm:local" in dockerfile_text
    assert "FROM ${DEPS_IMAGE} AS runtime" in dockerfile_text
    assert "FROM runtime-base AS dependency-builder" not in dockerfile_text
    assert "COPY pyproject.toml" not in dockerfile_text
    assert "pdm.lock" not in dockerfile_text
    assert "--no-cache-dir" not in dockerfile_text
    assert "COPY scripts ./scripts" not in dockerfile_text
    assert (
        "COPY scripts/sir_convert_a_lot/application ./scripts/sir_convert_a_lot/application"
        in dockerfile_text
    )
    assert (
        "COPY scripts/sir_convert_a_lot/domain ./scripts/sir_convert_a_lot/domain"
        in dockerfile_text
    )
    assert (
        "COPY scripts/sir_convert_a_lot/infrastructure ./scripts/sir_convert_a_lot/infrastructure"
        in dockerfile_text
    )
    assert (
        "COPY scripts/sir_convert_a_lot/interfaces ./scripts/sir_convert_a_lot/interfaces"
        in dockerfile_text
    )
    assert (
        "COPY scripts/sir_convert_a_lot/integrations ./scripts/sir_convert_a_lot/integrations"
        in dockerfile_text
    )
    assert (
        "COPY scripts/sir_convert_a_lot/templates ./scripts/sir_convert_a_lot/templates"
        in dockerfile_text
    )
    assert 'CMD ["uvicorn", "scripts.sir_convert_a_lot.service:app"' in dockerfile_text
    assert "EXPOSE 8085" in dockerfile_text
    assert "EXPOSE 8086" not in dockerfile_text
    assert "/var/lib/sir-convert-a-lot/eval" not in dockerfile_text


def test_dependency_dockerfile_uses_generated_inputs_and_buildkit_pip_cache() -> None:
    dockerfile_text = DOCKERFILE_DEPS.read_text(encoding="utf-8")
    assert "COPY pyproject.toml" not in dockerfile_text
    assert "pdm.lock" not in dockerfile_text
    assert "COPY docker/service-deps/service-requirements.txt" in dockerfile_text
    assert "COPY docker/service-deps/rocm-runtime.env" in dockerfile_text
    assert "ARG SERVICE_DEPENDENCY_HASH=unknown" in dockerfile_text
    assert "ARG SERVICE_RECIPE_HASH=unknown" in dockerfile_text
    assert "ARG SERVICE_DEPENDENCY_IMAGE_HASH=unknown" in dockerfile_text
    assert "--mount=type=cache,id=sir-convert-a-lot-pip" in dockerfile_text
    assert "--mount=type=cache,id=sir-convert-a-lot-pip-rocm" in dockerfile_text
    assert 'LABEL sir-convert-a-lot.dependency-hash="${SERVICE_DEPENDENCY_HASH}"' in dockerfile_text
    assert 'LABEL sir-convert-a-lot.recipe-hash="${SERVICE_RECIPE_HASH}"' in dockerfile_text
    assert (
        'LABEL sir-convert-a-lot.dependency-image-hash="${SERVICE_DEPENDENCY_IMAGE_HASH}"'
        in dockerfile_text
    )
    assert "--no-cache-dir" not in dockerfile_text
    assert "torch==${SIR_CONVERT_A_LOT_TORCH_VERSION}" in dockerfile_text
    assert "torchvision==${SIR_CONVERT_A_LOT_TORCHVISION_VERSION}" in dockerfile_text
    assert "torchaudio==${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION}" in dockerfile_text
    assert "easyocr.Reader" in dockerfile_text
