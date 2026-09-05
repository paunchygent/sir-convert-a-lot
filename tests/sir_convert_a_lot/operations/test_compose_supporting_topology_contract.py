"""Compose contracts for services outside the bounded startup selection.

Purpose:
    Verify supporting service and public-edge topology remains stable while
    the production API and GPU worker use bounded startup semantics.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "compose.yaml"
STT_INPUT_VOLUME = "sir-convert-a-lot-stt-sidecar-inputs"
STT_INPUT_DIR = "/var/lib/sir-convert-a-lot/stt-sidecar-inputs"
STT_INPUT_VOLUME_MOUNT = f"{STT_INPUT_VOLUME}:{STT_INPUT_DIR}"

type YamlScalar = str | int | float | bool | None
type YamlValue = YamlScalar | list[YamlValue] | dict[str, YamlValue]
type YamlMapping = dict[str, YamlValue]


def _load_compose() -> YamlMapping:
    raw = COMPOSE_FILE.read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)
    if not isinstance(loaded, dict):
        raise AssertionError("compose.yaml did not parse into a mapping")
    return loaded


def _service_env_map(service: YamlMapping) -> dict[str, str]:
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


def _require_service(compose: YamlMapping, service_name: str) -> YamlMapping:
    services_obj = compose.get("services")
    if not isinstance(services_obj, dict):
        raise AssertionError("compose services section missing")
    service_obj = services_obj.get(service_name)
    if not isinstance(service_obj, dict):
        raise AssertionError(f"compose service missing: {service_name}")
    return service_obj


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
    assert env_map["SIR_STT_SIDECAR_BATCH_SIZE"] == "8"
    assert env_map["SIR_STT_SIDECAR_IDLE_UNLOAD_SECONDS"] == (
        "${SIR_STT_SIDECAR_IDLE_UNLOAD_SECONDS:-900}"
    )

    assert service.get("devices") == ["/dev/kfd:/dev/kfd", "/dev/dri:/dev/dri"]
    assert service.get("group_add") == [
        "${SIR_CONVERT_A_LOT_GPU_VIDEO_GROUP_ID:-44}",
        "${SIR_CONVERT_A_LOT_GPU_RENDER_GROUP_ID:-993}",
    ]
    assert service.get("volumes") == [
        "sir-convert-a-lot-prod-data:/var/lib/sir-convert-a-lot/prod",
        STT_INPUT_VOLUME_MOUNT,
        (
            "${SIR_CONVERT_A_LOT_HF_CACHE_HOST_DIR:-"
            "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface}:"
            "/cache/huggingface"
        ),
    ]
    assert service.get("networks") == ["hule-network"]
    health_obj = service.get("healthcheck")
    assert isinstance(health_obj, dict)
    health_test = health_obj.get("test")
    assert isinstance(health_test, list)
    assert "http://localhost:8095/health" in " ".join(str(item) for item in health_test)
    assert health_obj.get("retries") == 20
    assert health_obj.get("start_period") == "120s"


def test_compose_has_no_answer_key_sidecar() -> None:
    compose = _load_compose()
    services_obj = compose.get("services")
    assert isinstance(services_obj, dict)
    assert "sir_convert_qwen_answer_key" not in services_obj
    for service_name, service_obj in services_obj.items():
        assert isinstance(service_obj, dict)
        assert service_obj.get("profiles") != ["qwen-answer-key"]
        assert "sir-convert-qwen-llama-runtime" not in str(service_obj.get("image"))
        build_obj = service_obj.get("build")
        if isinstance(build_obj, dict):
            assert build_obj.get("dockerfile") != "Dockerfile.qwen-provider"
        expose = service_obj.get("expose", [])
        assert isinstance(expose, list)
        assert "8082" not in [str(item) for item in expose], service_name


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
