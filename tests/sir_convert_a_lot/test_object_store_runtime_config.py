"""Object-store runtime configuration tests.

Purpose:
    Prove Sir Convert fails closed when R2 artifact storage is selected without
    the full approved configuration surface.

Relationships:
    - Exercises `infrastructure.runtime_config.service_config_from_env`.
    - Protects Task 381's R2 backend selector and required env-name contract.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.infrastructure.runtime_config import service_config_from_env

_R2_ENV_NAMES: tuple[str, ...] = (
    "SIR_CONVERT_A_LOT_R2_ENDPOINT_URL",
    "SIR_CONVERT_A_LOT_R2_REGION",
    "SIR_CONVERT_A_LOT_R2_BUCKET",
    "SIR_CONVERT_A_LOT_R2_ACCESS_KEY_ID",
    "SIR_CONVERT_A_LOT_R2_SECRET_ACCESS_KEY",
    "SIR_CONVERT_A_LOT_R2_KEY_PREFIX",
)


@pytest.mark.parametrize("missing_name", _R2_ENV_NAMES)
def test_r2_backend_rejects_missing_required_config(
    monkeypatch: pytest.MonkeyPatch,
    missing_name: str,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND", "r2")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_GPU_AVAILABLE", "0")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_ENABLE_SUPERVISOR", "0")
    for name in _R2_ENV_NAMES:
        monkeypatch.setenv(name, f"configured-{name.lower()}")
    monkeypatch.delenv(missing_name, raising=False)

    with pytest.raises(ValueError, match=missing_name):
        service_config_from_env()
