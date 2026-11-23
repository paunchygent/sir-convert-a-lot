"""Secrets-overlay contract tests for the production compose lane.

Purpose:
    Verify `compose.yaml` carries no secret interpolation, the new
    `compose.secrets.yaml` overlay declares the guarded secret variables, and
    `scripts/devops/compose-actions.sh` passes the overlay only through
    `agent-secrets run` on the mutating actions.

Relationships:
    - Implements TASK-SIRCON-REP-0039 (EPIC-SKILL-18 leaf).
    - Complements the compose wrapper argv test modules.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "compose.yaml"
SECRETS_FILE = REPO_ROOT / "compose.secrets.yaml"
REMOTE_PROOF_FILE = REPO_ROOT / "compose.remote-proof.yaml"
REMOTE_PROOF_SECRETS_FILE = REPO_ROOT / "compose.remote-proof.secrets.yaml"
PROD_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "prod-compose.sh"
DEV_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "dev-compose.sh"
REMOTE_PROOF_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "remote-proof-compose.sh"
COMPOSE_ACTIONS_SCRIPT = REPO_ROOT / "scripts" / "devops" / "compose-actions.sh"

PROD_GUARD = "run through agent-secrets run --set sir-convert-a-lot-prod"
REMOTE_PROOF_GUARD = "run through agent-secrets run --set sir-convert-a-lot-remote-proof"
SECRET_KEYS = ("SIR_CONVERT_A_LOT_V2_API_KEY", "HF_TOKEN")


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"{path.name} did not parse into a mapping")
    return loaded


def _service_env_map(service: dict[str, object]) -> dict[str, str]:
    env_obj = service.get("environment")
    parsed: dict[str, str] = {}
    if isinstance(env_obj, dict):
        for key, value in env_obj.items():
            if isinstance(key, str) and isinstance(value, str):
                parsed[key] = value
        return parsed
    for item in env_obj if isinstance(env_obj, list) else []:
        if isinstance(item, str) and "=" in item:
            key, value = item.split("=", maxsplit=1)
            parsed[key] = value
    return parsed


def _services(compose: dict[str, object]) -> dict[str, object]:
    services = compose.get("services")
    if not isinstance(services, dict):
        raise AssertionError("compose services section missing")
    return services


def test_base_compose_carries_no_secret_interpolation() -> None:
    raw = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "dev-only-key" not in raw
    assert "SIR_CONVERT_A_LOT_V2_API_KEY" not in raw
    assert "HF_TOKEN" not in raw

    compose = _load_yaml_mapping(COMPOSE_FILE)
    for service_name, service in _services(compose).items():
        assert isinstance(service, dict)
        env_map = _service_env_map(service)
        for key in SECRET_KEYS:
            assert key not in env_map, f"{service_name} still interpolates {key}"


def test_secrets_overlay_declares_guarded_secret_variables_only() -> None:
    compose = _load_yaml_mapping(SECRETS_FILE)
    services = _services(compose)

    assert set(services) == {
        "sir_convert_a_lot_prod",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_stt_sidecar",
    }

    expected = {
        "sir_convert_a_lot_prod": {
            "SIR_CONVERT_A_LOT_V2_API_KEY": f"${{SIR_CONVERT_A_LOT_V2_API_KEY:?{PROD_GUARD}}}"
        },
        "sir_convert_a_lot_gpu_worker": {
            "SIR_CONVERT_A_LOT_V2_API_KEY": f"${{SIR_CONVERT_A_LOT_V2_API_KEY:?{PROD_GUARD}}}"
        },
        "sir_convert_a_lot_stt_sidecar": {"HF_TOKEN": f"${{HF_TOKEN:?{PROD_GUARD}}}"},
    }
    for service_name, expected_env in expected.items():
        service = services[service_name]
        assert isinstance(service, dict)
        assert _service_env_map(service) == expected_env
        assert set(service) == {"environment"}


def test_compose_actions_wraps_only_secret_actions_through_agent_secrets() -> None:
    script = COMPOSE_ACTIONS_SCRIPT.read_text(encoding="utf-8")

    assert 'COMPOSE_SECRETS_FILE="${SIR_CONVERT_A_LOT_COMPOSE_SECRETS_FILE:-}"' in script
    assert 'COMPOSE_SECRETS_SET="${SIR_CONVERT_A_LOT_AGENT_SECRETS_SET:-}"' in script
    assert (
        'COMPOSE_SECRET_ACTIONS="${SIR_CONVERT_A_LOT_COMPOSE_SECRET_ACTIONS:-'
        'start recreate build build-clean}"' in script
    )
    assert 'agent-secrets run --set "${COMPOSE_SECRETS_SET}" --' in script
    assert 'bash -c "exec sudo -n --preserve-env=' in script
    assert "AGENT_SECRETS_VARIABLES" in script
    assert 'wrapped_cmd+=(-f "${COMPOSE_SECRETS_FILE}")' in script

    assert "run_compose_for_action start up -d --build" in script
    assert "run_compose_for_action recreate up -d --force-recreate --build" in script
    assert "run_compose_for_action build build" in script
    assert "run_compose_for_action logs logs" in script
    assert "run_compose_for_action ps ps" in script
    assert "run_compose_for_action config config" in script


def test_compose_actions_passes_source_env_file_without_copy_or_exclude_list() -> None:
    script = COMPOSE_ACTIONS_SCRIPT.read_text(encoding="utf-8")

    assert "COMPOSE_ENV_EXCLUDE_KEYS" not in script
    assert "SIR_CONVERT_A_LOT_COMPOSE_ENV_EXCLUDE_KEYS" not in script
    assert 'cp "${COMPOSE_SOURCE_ENV_FILE}"' not in script
    assert "grep -vE" not in script
    assert 'if [[ "${has_dynamic_values}" == "0" ]]; then' in script

    source_env_arg = 'compose_env_args+=(--env-file "${COMPOSE_SOURCE_ENV_FILE}")'
    dynamic_env_arg = 'compose_env_args+=(--env-file "${COMPOSE_DYNAMIC_ENV_FILE}")'
    assert source_env_arg in script
    assert dynamic_env_arg in script
    assert script.index(source_env_arg) < script.index(dynamic_env_arg)


def test_prod_wrapper_declares_overlay_set_without_secret_exclusions() -> None:
    script = PROD_COMPOSE_SCRIPT.read_text(encoding="utf-8")

    assert 'SIR_CONVERT_A_LOT_COMPOSE_SECRETS_FILE="${REPO_ROOT}/compose.secrets.yaml"' in script
    assert 'SIR_CONVERT_A_LOT_AGENT_SECRETS_SET="sir-convert-a-lot-prod"' in script
    assert "COMPOSE_ENV_EXCLUDE_KEYS" not in script


def test_dev_wrapper_keeps_unwrapped_secret_free_lane() -> None:
    script = DEV_COMPOSE_SCRIPT.read_text(encoding="utf-8")

    assert "AGENT_SECRETS_SET" not in script
    assert "COMPOSE_SECRETS_FILE" not in script
    assert "COMPOSE_ENV_EXCLUDE_KEYS" not in script


def test_remote_proof_lane_wraps_mutating_actions_through_its_overlay() -> None:
    script = REMOTE_PROOF_COMPOSE_SCRIPT.read_text(encoding="utf-8")

    assert 'SIR_CONVERT_A_LOT_AGENT_SECRETS_SET="sir-convert-a-lot-remote-proof"' in script
    assert (
        'SIR_CONVERT_A_LOT_COMPOSE_SECRETS_FILE="${REPO_ROOT}/compose.remote-proof.secrets.yaml"'
        in script
    )
    assert "SIR_CONVERT_A_LOT_COMPOSE_SECRET_ACTIONS" not in script
    assert "COMPOSE_ENV_EXCLUDE_KEYS" not in script
    assert "SIR_CONVERT_A_LOT_REMOTE_PROOF_V2_API_KEY" not in script

    compose = _load_yaml_mapping(REMOTE_PROOF_FILE)
    for service_name, service in _services(compose).items():
        assert isinstance(service, dict)
        assert "SIR_CONVERT_A_LOT_V2_API_KEY" not in _service_env_map(service), service_name

    overlay = _load_yaml_mapping(REMOTE_PROOF_SECRETS_FILE)
    overlay_services = _services(overlay)
    expected_key = f"${{SIR_CONVERT_A_LOT_V2_API_KEY:?{REMOTE_PROOF_GUARD}}}"
    for service_name in (
        "sir_convert_a_lot_remote_proof",
        "sir_convert_a_lot_remote_proof_worker",
    ):
        service = overlay_services[service_name]
        assert isinstance(service, dict)
        assert _service_env_map(service) == {"SIR_CONVERT_A_LOT_V2_API_KEY": expected_key}
        assert set(service) == {"environment"}
