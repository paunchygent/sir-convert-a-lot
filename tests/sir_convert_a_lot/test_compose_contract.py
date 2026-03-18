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
DOCKERIGNORE = REPO_ROOT / ".dockerignore"


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


def test_compose_declares_single_prod_service_only() -> None:
    compose = _load_compose()
    services_obj = compose.get("services")
    assert isinstance(services_obj, dict)
    assert "sir_convert_a_lot_prod" in services_obj
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
    assert service.get("env_file") == [{"path": ".env", "required": False}]

    env_map = _service_env_map(service)
    assert (
        env_map["SIR_CONVERT_A_LOT_SERVICE_REVISION"]
        == "${SIR_CONVERT_A_LOT_SERVICE_REVISION:-unknown}"
    )
    assert (
        env_map["SIR_CONVERT_A_LOT_EXPECTED_REVISION"]
        == "${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-unknown}"
    )
    assert env_map["SIR_CONVERT_A_LOT_DATA_DIR"] == "/var/lib/sir-convert-a-lot/prod"
    assert "SIR_CONVERT_A_LOT_EVAL_DATA_DIR" not in env_map

    assert service.get("command") == [
        "uvicorn",
        "scripts.sir_convert_a_lot.service:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8085",
    ]
    volumes = service.get("volumes")
    assert volumes == ["sir-convert-a-lot-prod-data:/var/lib/sir-convert-a-lot/prod"]


def test_compose_declares_rocm_build_args_and_gpu_device_passthrough() -> None:
    compose = _load_compose()
    service = _require_service(compose, "sir_convert_a_lot_prod")

    assert service.get("image") == "sir-convert-a-lot-runtime:${SIR_CONVERT_A_LOT_IMAGE_TAG:-local}"

    build_obj = service.get("build")
    assert isinstance(build_obj, dict)
    assert build_obj.get("context") == "."
    assert build_obj.get("dockerfile") == "Dockerfile"
    assert "args" not in build_obj

    assert service.get("devices") == ["/dev/kfd:/dev/kfd", "/dev/dri:/dev/dri"]
    assert service.get("group_add") == ["video", "render"]


def test_dockerignore_limits_build_context_to_service_runtime_contract() -> None:
    dockerignore_rules = _load_dockerignore_rules()

    assert "*" in dockerignore_rules
    assert "scripts/*" in dockerignore_rules
    assert "scripts/sir_convert_a_lot/*" in dockerignore_rules
    assert "scripts/sir_convert_a_lot/devops/*" in dockerignore_rules

    required_file_paths = {
        "pyproject.toml",
        "pdm.lock",
        "scripts/__init__.py",
        "scripts/sir_convert_a_lot/__init__.py",
        "scripts/sir_convert_a_lot/service.py",
        "scripts/sir_convert_a_lot/devops/__init__.py",
        "scripts/sir_convert_a_lot/devops/export_service_requirements.py",
        "scripts/sir_convert_a_lot/devops/service_image_build_contract.py",
    }
    for path in required_file_paths:
        assert f"!{path}" in dockerignore_rules

    required_directory_paths = {
        "scripts/sir_convert_a_lot/application",
        "scripts/sir_convert_a_lot/domain",
        "scripts/sir_convert_a_lot/infrastructure",
        "scripts/sir_convert_a_lot/integrations",
        "scripts/sir_convert_a_lot/interfaces",
        "scripts/sir_convert_a_lot/templates",
    }
    for path in required_directory_paths:
        assert f"!{path}" in dockerignore_rules
        assert f"!{path}/**" in dockerignore_rules

    assert "!docs" not in dockerignore_rules
    assert "!tests" not in dockerignore_rules
    assert "!build" not in dockerignore_rules


def test_compose_declares_only_prod_named_volume() -> None:
    compose = _load_compose()
    volumes_obj = compose.get("volumes")
    assert isinstance(volumes_obj, dict)
    assert "sir-convert-a-lot-prod-data" in volumes_obj
    assert "sir-convert-a-lot-eval-data" not in volumes_obj


def test_dockerfile_uses_supported_runtime_settings_for_single_service() -> None:
    dockerfile_text = DOCKERFILE.read_text(encoding="utf-8")
    assert "FROM python:3.11-slim AS runtime-base" in dockerfile_text
    assert "FROM runtime-base AS dependency-builder" in dockerfile_text
    assert "COPY --from=dependency-builder /app/.venv /app/.venv" in dockerfile_text
    assert "export_service_requirements.py" in dockerfile_text
    assert "service_image_build_contract.py" in dockerfile_text
    assert (
        "python -m pip install --no-cache-dir --no-deps -r /tmp/service-requirements.txt"
        in dockerfile_text
    )
    assert (
        "python -m scripts.sir_convert_a_lot.devops.export_service_requirements" in dockerfile_text
    )
    assert 'load_rocm_runtime_contract(Path("/app")).as_shell_exports()' in dockerfile_text
    assert "torch==${SIR_CONVERT_A_LOT_TORCH_VERSION}" in dockerfile_text
    assert "torchvision==${SIR_CONVERT_A_LOT_TORCHVISION_VERSION}" in dockerfile_text
    assert "torchaudio==${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION}" in dockerfile_text
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
