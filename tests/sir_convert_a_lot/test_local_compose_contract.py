"""Compose contract tests for the CPU-only local Docker development lane.

Purpose:
    Verify `compose.local.yaml`, `Dockerfile.local`, and the local dev compose
    helper encode the explicit CPU-only laptop debug profile without leaking
    Hemma ROCm production assumptions into that lane.

Relationships:
    - Protects the opt-in local `:8085` Docker debug surface.
    - Keeps `compose.yaml` free to remain the Hemma/prod contract.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_LOCAL_FILE = REPO_ROOT / "compose.local.yaml"
DOCKERFILE_LOCAL = REPO_ROOT / "Dockerfile.local"
DEV_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "dev-compose.sh"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
PYPROJECT_FILE = REPO_ROOT / "pyproject.toml"


def _load_local_compose() -> dict[str, object]:
    raw = COMPOSE_LOCAL_FILE.read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)
    if not isinstance(loaded, dict):
        raise AssertionError("compose.local.yaml did not parse into a mapping")
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
    if not isinstance(env_obj, list):
        return {}
    parsed_env_map: dict[str, str] = {}
    for item in env_obj:
        if not isinstance(item, str) or "=" not in item:
            continue
        key, value = item.split("=", maxsplit=1)
        parsed_env_map[key] = value
    return parsed_env_map


def test_local_compose_declares_one_cpu_only_dev_service() -> None:
    compose = _load_local_compose()
    services_obj = compose.get("services")
    assert isinstance(services_obj, dict)
    assert set(services_obj.keys()) == {"sir_convert_a_lot_dev"}


def test_local_compose_uses_cpu_only_local_service_contract() -> None:
    compose = _load_local_compose()
    services_obj = compose["services"]
    assert isinstance(services_obj, dict)
    service = services_obj["sir_convert_a_lot_dev"]
    assert isinstance(service, dict)

    assert service.get("container_name") == "sir_convert_a_lot_dev"
    assert service.get("restart") == "unless-stopped"

    build_obj = service.get("build")
    assert isinstance(build_obj, dict)
    assert build_obj.get("context") == "."
    assert build_obj.get("dockerfile") == "Dockerfile.local"
    assert build_obj.get("args") == {
        "DEPS_IMAGE": "${SIR_CONVERT_A_LOT_DEPS_IMAGE:-sir-convert-a-lot-deps-cpu:local}",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION": ("${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-unknown}"),
        "SIR_CONVERT_A_LOT_SERVICE_REVISION": ("${SIR_CONVERT_A_LOT_SERVICE_REVISION:-unknown}"),
    }

    env_map = _service_env_map(service)
    assert env_map["SIR_CONVERT_A_LOT_DATA_DIR"] == "/var/lib/sir-convert-a-lot/local"
    assert env_map["SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE"] == "tesseract_cli"
    assert env_map["SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES"] == "sv,en"
    assert env_map["HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH"] == (
        "/run/huleedu/internal-identity/gateway-internal-identity-public-key.pem"
    )
    assert "VIRTUAL_HOST" not in env_map
    assert "LETSENCRYPT_HOST" not in env_map

    assert service.get("command") == [
        "uvicorn",
        "scripts.sir_convert_a_lot.service_local:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8085",
    ]
    assert service.get("devices") is None
    assert service.get("group_add") is None
    assert service.get("ports") == ["${SIR_CONVERT_A_LOT_LOCAL_PORT:-8085}:8085"]
    assert service.get("volumes") == [
        "sir-convert-a-lot-local-data:/var/lib/sir-convert-a-lot/local",
        (
            "${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH:-"
            "../huleedu/secrets/local-runtime/internal-identity/"
            "gateway-internal-identity-public-key.pem}:"
            "/run/huleedu/internal-identity/gateway-internal-identity-public-key.pem:ro"
        ),
    ]


def test_local_compose_uses_readyz_healthcheck_with_deterministic_timing() -> None:
    compose = _load_local_compose()
    services_obj = compose["services"]
    assert isinstance(services_obj, dict)
    service = services_obj["sir_convert_a_lot_dev"]
    assert isinstance(service, dict)
    health_obj = service.get("healthcheck")
    assert isinstance(health_obj, dict)
    test_obj = health_obj.get("test")
    assert isinstance(test_obj, list)
    joined = " ".join(str(item) for item in test_obj)
    assert "http://localhost:8085/readyz" in joined
    assert health_obj.get("interval") == "30s"
    assert health_obj.get("timeout") == "10s"
    assert health_obj.get("retries") == 3
    assert health_obj.get("start_period") == "15s"


def test_dockerfile_local_uses_cpu_runtime_contract_and_local_entrypoint() -> None:
    dockerfile_text = DOCKERFILE_LOCAL.read_text(encoding="utf-8")
    assert "ARG DEPS_IMAGE=sir-convert-a-lot-deps-cpu:local" in dockerfile_text
    assert "FROM ${DEPS_IMAGE} AS runtime" in dockerfile_text
    assert "COPY .git /tmp/sir-convert-build-git" in dockerfile_text
    assert "SIR_CONVERT_A_LOT_SERVICE_REVISION=unknown" in dockerfile_text
    assert "/opt/sir-convert-a-lot/service_revision" in dockerfile_text
    assert "/opt/sir-convert-a-lot/expected_revision" in dockerfile_text
    assert "COPY pyproject.toml" not in dockerfile_text
    assert "pdm.lock" not in dockerfile_text
    assert "--no-cache-dir" not in dockerfile_text
    assert "scripts.sir_convert_a_lot.service_local:app" in dockerfile_text
    assert "/dev/kfd" not in dockerfile_text
    assert "/dev/dri" not in dockerfile_text


def test_dev_compose_helper_targets_local_compose_surface() -> None:
    script_text = DEV_COMPOSE_SCRIPT.read_text(encoding="utf-8")
    assert 'SIR_CONVERT_A_LOT_COMPOSE_FILE="${REPO_ROOT}/compose.local.yaml"' in script_text
    assert 'SIR_CONVERT_A_LOT_DEPS_RUNTIME="cpu"' in script_text


def test_dev_pdm_scripts_expose_cpu_dependency_image_lane() -> None:
    pyproject_text = PYPROJECT_FILE.read_text(encoding="utf-8")
    assert (
        '"dev-deps-cpu-build" = "bash scripts/devops/service-deps-image.sh cpu build"'
        in pyproject_text
    )
    assert '"dev-build" = "bash scripts/devops/dev-compose.sh build"' in pyproject_text


def test_dockerignore_whitelists_local_service_entrypoint() -> None:
    dockerignore_rules = _load_dockerignore_rules()
    assert "!.git/HEAD" in dockerignore_rules
    assert "!.git/refs/**" in dockerignore_rules
    assert "!.git/packed-refs" in dockerignore_rules
    assert "!scripts/sir_convert_a_lot/service_local.py" in dockerignore_rules
