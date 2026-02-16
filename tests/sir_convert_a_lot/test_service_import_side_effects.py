"""Import side-effect regression tests for service entry modules.

Purpose:
    Ensure service modules do not instantiate unintended extra runtimes due to
    import-time side effects.

Relationships:
    - Tests `scripts.sir_convert_a_lot.interfaces.http_api`.
    - Tests `scripts.sir_convert_a_lot.service_eval`.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure.runtime_engine import ServiceConfig


def _clear_modules() -> None:
    sys.modules.pop("scripts.sir_convert_a_lot.interfaces.http_api", None)
    sys.modules.pop("scripts.sir_convert_a_lot.interfaces.http_app_state", None)
    sys.modules.pop("scripts.sir_convert_a_lot.interfaces.http_routes_health", None)
    sys.modules.pop("scripts.sir_convert_a_lot.interfaces.http_routes_jobs", None)
    sys.modules.pop("scripts.sir_convert_a_lot.service_eval", None)


def test_http_api_import_does_not_instantiate_runtime(monkeypatch, tmp_path: Path) -> None:
    runtime_engine_module = importlib.import_module(
        "scripts.sir_convert_a_lot.infrastructure.runtime_engine"
    )
    call_count = {"value": 0}

    class _CountingRuntime:
        def __init__(self, config: ServiceConfig) -> None:
            call_count["value"] += 1
            self.config = config

        def shutdown(self) -> None:
            return None

    monkeypatch.setattr(runtime_engine_module, "ServiceRuntime", _CountingRuntime)
    _clear_modules()
    http_api_module = importlib.import_module("scripts.sir_convert_a_lot.interfaces.http_api")

    assert call_count["value"] == 0

    app = http_api_module.create_app(
        ServiceConfig(
            api_key="k",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            gpu_available=False,
            allow_cpu_only=True,
            processing_delay_seconds=0.0,
        )
    )
    assert call_count["value"] == 0

    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
    assert call_count["value"] == 1


def test_service_eval_import_creates_only_one_runtime(monkeypatch, tmp_path: Path) -> None:
    runtime_engine_module = importlib.import_module(
        "scripts.sir_convert_a_lot.infrastructure.runtime_engine"
    )
    call_count = {"value": 0}

    class _CountingRuntime:
        def __init__(self, config: ServiceConfig) -> None:
            call_count["value"] += 1
            self.config = config

        def shutdown(self) -> None:
            return None

    monkeypatch.setattr(runtime_engine_module, "ServiceRuntime", _CountingRuntime)
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", str(tmp_path / "prod_data"))
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EVAL_DATA_DIR", str(tmp_path / "eval_data"))

    _clear_modules()
    service_eval_module = importlib.import_module("scripts.sir_convert_a_lot.service_eval")

    assert call_count["value"] == 0
    with TestClient(service_eval_module.app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
    assert call_count["value"] == 1


def test_http_api_lifespan_shutdown_calls_runtime_shutdown(monkeypatch, tmp_path: Path) -> None:
    runtime_engine_module = importlib.import_module(
        "scripts.sir_convert_a_lot.infrastructure.runtime_engine"
    )
    call_count = {"start": 0, "shutdown": 0}

    class _CountingRuntime:
        def __init__(self, config: ServiceConfig) -> None:
            call_count["start"] += 1
            self.config = config

        def shutdown(self) -> None:
            call_count["shutdown"] += 1

    monkeypatch.setattr(runtime_engine_module, "ServiceRuntime", _CountingRuntime)
    _clear_modules()
    http_api_module = importlib.import_module("scripts.sir_convert_a_lot.interfaces.http_api")

    app = http_api_module.create_app(
        ServiceConfig(
            api_key="k",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            gpu_available=False,
            allow_cpu_only=True,
            processing_delay_seconds=0.0,
        )
    )

    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
    assert call_count["start"] == 1
    assert call_count["shutdown"] == 1
