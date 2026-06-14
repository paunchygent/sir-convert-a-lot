"""Remote-proof compose contract tests.

Purpose:
    Prove the Hemma remote-proof lane is a fenced non-production runtime for
    local-auth STT proof and cannot bleed its trust, data, or ingress settings
    into production Sir Convert.

Relationships:
    - Validates `compose.remote-proof.yaml` and the `remote-proof-*` PDM wrapper
      surface introduced by Task 365.
    - Complements production `compose.yaml` contract tests.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_PROOF_COMPOSE_FILE = REPO_ROOT / "compose.remote-proof.yaml"
PROD_COMPOSE_FILE = REPO_ROOT / "compose.yaml"
REMOTE_PROOF_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "remote-proof-compose.sh"
DOCKER_COMMAND_SCRIPT = REPO_ROOT / "scripts" / "devops" / "docker-command.sh"
PYPROJECT_FILE = REPO_ROOT / "pyproject.toml"


def test_remote_proof_compose_declares_fenced_api_and_worker_services() -> None:
    compose = _load_yaml_mapping(REMOTE_PROOF_COMPOSE_FILE)
    services = _services(compose)

    assert set(services) == {
        "sir_convert_a_lot_remote_proof",
        "sir_convert_a_lot_remote_proof_worker",
    }

    api_service = _require_service(compose, "sir_convert_a_lot_remote_proof")
    worker_service = _require_service(compose, "sir_convert_a_lot_remote_proof_worker")

    assert api_service.get("container_name") == "sir_convert_a_lot_remote_proof"
    assert worker_service.get("container_name") == "sir_convert_a_lot_remote_proof_worker"
    assert api_service.get("ports") == ["${SIR_CONVERT_A_LOT_REMOTE_PROOF_PORT:-38085}:8085"]
    assert worker_service.get("ports") is None
    assert worker_service.get("expose") == ["8085"]
    assert worker_service.get("devices") == ["/dev/kfd:/dev/kfd", "/dev/dri:/dev/dri"]

    api_env = _service_env_map(api_service)
    worker_env = _service_env_map(worker_service)
    for env_map in (api_env, worker_env):
        assert env_map["SIR_CONVERT_A_LOT_DATA_DIR"] == "/var/lib/sir-convert-a-lot/remote-proof"
        assert env_map["SIR_CONVERT_A_LOT_V2_API_KEY"] == (
            "${SIR_CONVERT_A_LOT_REMOTE_PROOF_V2_API_KEY:?Set remote-proof Sir Convert API key}"
        )
        assert env_map["HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH"] == (
            "/run/secrets/huleedu-local-auth-integration-public-key.pem"
        )
        assert env_map["HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON"] == (
            "${HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_TRUST_PROFILE_JSON:?"
            "Set sanitized HuleEdu local-auth-integration internal identity trust profile JSON}"
        )
        assert (
            env_map["SIR_CONVERT_A_LOT_STT_SIDECAR_BASE_URL"]
            == "http://sir_convert_a_lot_stt_sidecar:8095"
        )
        assert "VIRTUAL_HOST" not in env_map
        assert "LETSENCRYPT_HOST" not in env_map

    assert api_env["SIR_CONVERT_A_LOT_GPU_AVAILABLE"] == "0"
    assert api_env["SIR_CONVERT_A_LOT_ENABLE_SUPERVISOR"] == "0"
    assert worker_env["SIR_CONVERT_A_LOT_GPU_AVAILABLE"] == (
        "${SIR_CONVERT_A_LOT_REMOTE_PROOF_GPU_AVAILABLE:-1}"
    )
    assert worker_env["SIR_CONVERT_A_LOT_ENABLE_SUPERVISOR"] == "1"


def test_remote_proof_compose_uses_distinct_volume_entrypoint_and_key_mount() -> None:
    compose = _load_yaml_mapping(REMOTE_PROOF_COMPOSE_FILE)
    volumes = compose.get("volumes")
    assert volumes == {"sir-convert-a-lot-remote-proof-data": None}

    api_service = _require_service(compose, "sir_convert_a_lot_remote_proof")
    worker_service = _require_service(compose, "sir_convert_a_lot_remote_proof_worker")
    for service in (api_service, worker_service):
        assert service.get("command") == [
            "uvicorn",
            "scripts.sir_convert_a_lot.service_remote_proof:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8085",
        ]
        assert service.get("volumes") == [
            "sir-convert-a-lot-remote-proof-data:/var/lib/sir-convert-a-lot/remote-proof",
            (
                "${SIR_CONVERT_A_LOT_MIOPEN_CACHE_HOST_DIR:-"
                "/home/paunchygent/.data/sir-convert-a-lot/cache/miopen}:"
                "/srv/scratch/sir-convert-a-lot/cache/miopen"
            ),
            (
                "${HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH:?"
                "Set HuleEdu local-auth-integration public key PEM host path}:"
                "/run/secrets/huleedu-local-auth-integration-public-key.pem:ro"
            ),
        ]


def test_production_compose_does_not_reference_remote_proof_settings() -> None:
    raw = PROD_COMPOSE_FILE.read_text(encoding="utf-8")

    assert "REMOTE_PROOF" not in raw
    assert "remote-proof" not in raw
    assert "local-auth-integration" not in raw
    assert "sir-convert-a-lot-remote-proof-data" not in raw


def test_remote_proof_wrapper_and_pdm_scripts_are_first_class() -> None:
    script_text = REMOTE_PROOF_COMPOSE_SCRIPT.read_text(encoding="utf-8")
    assert "compose.remote-proof.yaml" in script_text
    assert "remote-proof-compose" in script_text
    assert "sir_convert_require_hemma_server" in script_text
    assert "SIR_CONVERT_A_LOT_REMOTE_PROOF_ENV_FILE" in script_text
    assert "/home/paunchygent/.data/sir-convert-a-lot/remote-proof/remote-proof.env" in (
        script_text
    )
    assert "SIR_CONVERT_A_LOT_REMOTE_PROOF_TRUST_DIR" in script_text
    assert "gateway-internal-identity-public-key.pem" in script_text
    assert "HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH" in script_text
    assert 'SIR_CONVERT_A_LOT_DOCKER_USE_SUDO="1"' in script_text

    compose_actions = (REPO_ROOT / "scripts" / "devops" / "compose-actions.sh").read_text(
        encoding="utf-8"
    )
    assert "docker-command.sh" in compose_actions
    assert "SIR_CONVERT_A_LOT_COMPOSE_USE_SUDO" not in compose_actions
    service_deps = (REPO_ROOT / "scripts" / "devops" / "service-deps-image.sh").read_text(
        encoding="utf-8"
    )
    assert "docker-command.sh" in service_deps
    assert "SIR_CONVERT_A_LOT_COMPOSE_USE_SUDO" not in service_deps
    docker_command = DOCKER_COMMAND_SCRIPT.read_text(encoding="utf-8")
    assert "SIR_CONVERT_A_LOT_DOCKER_USE_SUDO" in docker_command
    assert "sudo -n docker" in docker_command

    pyproject = tomllib.loads(PYPROJECT_FILE.read_text(encoding="utf-8"))
    scripts = pyproject["tool"]["pdm"]["scripts"]
    expected = {
        "remote-proof-start": "bash scripts/devops/remote-proof-compose.sh start",
        "remote-proof-stop": "bash scripts/devops/remote-proof-compose.sh stop",
        "remote-proof-build": "bash scripts/devops/remote-proof-compose.sh build",
        "remote-proof-build-clean": "bash scripts/devops/remote-proof-compose.sh build-clean",
        "remote-proof-recreate": "bash scripts/devops/remote-proof-compose.sh recreate",
        "remote-proof-logs": "bash scripts/devops/remote-proof-compose.sh logs",
        "remote-proof-ps": "bash scripts/devops/remote-proof-compose.sh ps",
        "remote-proof-config": "bash scripts/devops/remote-proof-compose.sh config",
        "remote-proof-check": "bash scripts/devops/remote-proof-compose.sh check",
    }
    for script_name, command in expected.items():
        assert scripts[script_name] == command


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)
    if not isinstance(loaded, dict):
        raise AssertionError(f"{path.name} did not parse into a mapping")
    return loaded


def _services(compose: dict[str, object]) -> dict[str, object]:
    services_obj = compose.get("services")
    if not isinstance(services_obj, dict):
        raise AssertionError("compose services section missing")
    return services_obj


def _require_service(compose: dict[str, object], service_name: str) -> dict[str, object]:
    service_obj = _services(compose).get(service_name)
    if not isinstance(service_obj, dict):
        raise AssertionError(f"compose service missing: {service_name}")
    return service_obj


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
