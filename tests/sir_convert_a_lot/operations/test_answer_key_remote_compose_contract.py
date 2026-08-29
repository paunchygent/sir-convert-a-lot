"""Compose contract for answer-key remote provider credentials and budget."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "compose.yaml"
_SERVICE_NAMES = ("sir_convert_a_lot_prod", "sir_convert_a_lot_gpu_worker")
_DATA_ROOT = "/var/lib/sir-convert-a-lot/prod"
_DATA_VOLUME_MOUNT = f"sir-convert-a-lot-prod-data:{_DATA_ROOT}"


def test_remote_answer_key_services_share_key_budget_and_data_root() -> None:
    loaded = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    services = loaded["services"]
    assert isinstance(services, dict)

    for service_name in _SERVICE_NAMES:
        service = services[service_name]
        assert isinstance(service, dict)
        environment = _environment(service)
        volumes = service["volumes"]
        assert isinstance(volumes, list)

        assert environment["SIR_CONVERT_A_LOT_OPENROUTER_API_KEY"] == (
            "${SIR_CONVERT_A_LOT_OPENROUTER_API_KEY:-}"
        )
        assert environment["SIR_CONVERT_A_LOT_ANSWER_KEY_DAILY_TOKEN_LIMIT"] == (
            "${SIR_CONVERT_A_LOT_ANSWER_KEY_DAILY_TOKEN_LIMIT:-5000000}"
        )
        assert environment["SIR_CONVERT_A_LOT_DATA_DIR"] == _DATA_ROOT
        assert _DATA_VOLUME_MOUNT in volumes


def _environment(service: dict[str, str | list[str]]) -> dict[str, str]:
    raw_environment = service["environment"]
    assert isinstance(raw_environment, list)
    environment: dict[str, str] = {}
    for item in raw_environment:
        assert isinstance(item, str)
        key, value = item.split("=", maxsplit=1)
        environment[key] = value
    return environment
