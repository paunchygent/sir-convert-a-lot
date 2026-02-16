"""Compose contract tests for Task 22 dockerized startup semantics.

Purpose:
    Verify that compose.yaml encodes deterministic prod/eval lane startup and
    readiness-gated health checks aligned with task contracts.

Relationships:
    - Validates compose.yaml created by Task 22.
    - Protects runbook/task assumptions for docker compose command surfaces.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "compose.yaml"
DOCKERFILE = REPO_ROOT / "Dockerfile"


def _load_compose() -> dict[str, object]:
    raw = COMPOSE_FILE.read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)
    if not isinstance(loaded, dict):
        raise AssertionError("compose.yaml did not parse into a mapping")
    return loaded


def _service_env_map(service: dict[str, object]) -> dict[str, str]:
    env_obj = service.get("environment")
    if isinstance(env_obj, dict):
        env_map: dict[str, str] = {}
        for key, value in env_obj.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
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


def test_compose_declares_prod_and_eval_services() -> None:
    compose = _load_compose()
    _require_service(compose, "sir_convert_a_lot_prod")
    _require_service(compose, "sir_convert_a_lot_eval")


def test_compose_uses_readyz_healthchecks_with_deterministic_timing() -> None:
    compose = _load_compose()
    expected_ports = {
        "sir_convert_a_lot_prod": "8085",
        "sir_convert_a_lot_eval": "8086",
    }
    for service_name, port in expected_ports.items():
        service = _require_service(compose, service_name)
        health_obj = service.get("healthcheck")
        assert isinstance(health_obj, dict)
        test_obj = health_obj.get("test")
        assert isinstance(test_obj, list)
        joined = " ".join(str(item) for item in test_obj)
        assert f"http://localhost:{port}/readyz" in joined
        assert health_obj.get("interval") == "30s"
        assert health_obj.get("timeout") == "10s"
        assert health_obj.get("retries") == 3
        assert health_obj.get("start_period") == "15s"


def test_compose_enforces_lane_isolation_and_restart_policy() -> None:
    compose = _load_compose()
    prod_service = _require_service(compose, "sir_convert_a_lot_prod")
    eval_service = _require_service(compose, "sir_convert_a_lot_eval")

    assert prod_service.get("restart") == "unless-stopped"
    assert eval_service.get("restart") == "unless-stopped"
    assert prod_service.get("container_name") == "sir_convert_a_lot_prod"
    assert eval_service.get("container_name") == "sir_convert_a_lot_eval"

    prod_env = _service_env_map(prod_service)
    eval_env = _service_env_map(eval_service)
    assert prod_service.get("env_file") == [{"path": ".env", "required": False}]
    assert eval_service.get("env_file") == [{"path": ".env", "required": False}]
    assert (
        prod_env["SIR_CONVERT_A_LOT_SERVICE_REVISION"]
        == "${SIR_CONVERT_A_LOT_SERVICE_REVISION:-unknown}"
    )
    assert (
        eval_env["SIR_CONVERT_A_LOT_SERVICE_REVISION"]
        == "${SIR_CONVERT_A_LOT_SERVICE_REVISION:-unknown}"
    )
    assert (
        prod_env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"]
        == "${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-unknown}"
    )
    assert (
        eval_env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"]
        == "${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-unknown}"
    )
    assert prod_env["SIR_CONVERT_A_LOT_DATA_DIR"] == "/var/lib/sir-convert-a-lot/prod"
    assert prod_env["SIR_CONVERT_A_LOT_EVAL_DATA_DIR"] == "/var/lib/sir-convert-a-lot/eval"
    assert eval_env["SIR_CONVERT_A_LOT_DATA_DIR"] == "/var/lib/sir-convert-a-lot/prod"
    assert eval_env["SIR_CONVERT_A_LOT_EVAL_DATA_DIR"] == "/var/lib/sir-convert-a-lot/eval"

    prod_volumes = prod_service.get("volumes")
    eval_volumes = eval_service.get("volumes")
    assert prod_volumes == ["sir-convert-a-lot-prod-data:/var/lib/sir-convert-a-lot/prod"]
    assert eval_volumes == ["sir-convert-a-lot-eval-data:/var/lib/sir-convert-a-lot/eval"]

    prod_command = prod_service.get("command")
    eval_command = eval_service.get("command")
    assert prod_command == ["pdm", "run", "serve:sir-convert-a-lot"]
    assert eval_command == ["pdm", "run", "serve:sir-convert-a-lot-eval"]


def test_compose_declares_rocm_build_args_and_gpu_device_passthrough() -> None:
    compose = _load_compose()
    prod_service = _require_service(compose, "sir_convert_a_lot_prod")
    eval_service = _require_service(compose, "sir_convert_a_lot_eval")

    assert (
        prod_service.get("image")
        == "sir-convert-a-lot-runtime:${SIR_CONVERT_A_LOT_IMAGE_TAG:-local}"
    )
    assert (
        eval_service.get("image")
        == "sir-convert-a-lot-runtime:${SIR_CONVERT_A_LOT_IMAGE_TAG:-local}"
    )
    assert eval_service.get("build") is None

    build_obj = prod_service.get("build")
    assert isinstance(build_obj, dict)
    args_obj = build_obj.get("args")
    assert isinstance(args_obj, list)
    assert (
        "SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL=${SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL:-https://download.pytorch.org/whl/rocm7.1}"
        in args_obj
    )
    assert (
        "SIR_CONVERT_A_LOT_TORCH_VERSION=${SIR_CONVERT_A_LOT_TORCH_VERSION:-2.10.0+rocm7.1}"
        in args_obj
    )
    assert (
        "SIR_CONVERT_A_LOT_TORCHVISION_VERSION=${SIR_CONVERT_A_LOT_TORCHVISION_VERSION:-0.25.0+rocm7.1}"
        in args_obj
    )
    assert (
        "SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION=${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION:-2.10.0+rocm7.1}"
        in args_obj
    )

    assert prod_service.get("devices") == ["/dev/kfd:/dev/kfd", "/dev/dri:/dev/dri"]
    assert prod_service.get("group_add") == ["video", "render"]
    assert eval_service.get("devices") == ["/dev/kfd:/dev/kfd", "/dev/dri:/dev/dri"]
    assert eval_service.get("group_add") == ["video", "render"]


def test_compose_declares_named_volumes_for_prod_and_eval_lanes() -> None:
    compose = _load_compose()
    volumes_obj = compose.get("volumes")
    assert isinstance(volumes_obj, dict)
    assert "sir-convert-a-lot-prod-data" in volumes_obj
    assert "sir-convert-a-lot-eval-data" in volumes_obj


def test_dockerfile_uses_supported_pdm_sync_arguments() -> None:
    dockerfile_text = DOCKERFILE.read_text(encoding="utf-8")
    assert "pdm sync --prod --no-editable --no-self" in dockerfile_text
    assert "--frozen-lockfile" not in dockerfile_text
    assert "SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL" in dockerfile_text
    assert "torch==${SIR_CONVERT_A_LOT_TORCH_VERSION}" in dockerfile_text
    assert "torchvision==${SIR_CONVERT_A_LOT_TORCHVISION_VERSION}" in dockerfile_text
    assert "torchaudio==${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION}" in dockerfile_text
