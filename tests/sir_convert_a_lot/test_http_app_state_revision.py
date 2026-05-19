"""Revision metadata resolution tests for the Sir Convert HTTP app.

Purpose:
    Verify local Docker builds can report deterministic revision metadata even
    when raw Compose supplies only placeholder environment values.

Relationships:
    - Covers `interfaces.http_app_state` revision resolution.
    - Protects the local `Dockerfile.local` baked-revision fallback used by
      `/readyz` health checks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.interfaces import http_app_state


def _set_baked_revision_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    expected_revision: str = "baked-expected",
    service_revision: str = "baked-service",
) -> None:
    service_path = tmp_path / "service_revision"
    expected_path = tmp_path / "expected_revision"
    service_path.write_text(service_revision, encoding="utf-8")
    expected_path.write_text(expected_revision, encoding="utf-8")
    monkeypatch.setenv(http_app_state.BAKED_SERVICE_REVISION_PATH_ENV, str(service_path))
    monkeypatch.setenv(http_app_state.BAKED_EXPECTED_REVISION_PATH_ENV, str(expected_path))


def test_service_revision_prefers_explicit_non_placeholder_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_baked_revision_path(monkeypatch, tmp_path)
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "explicit-service")

    assert http_app_state.resolve_service_revision() == "explicit-service"


def test_service_revision_uses_baked_file_when_compose_supplies_unknown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_baked_revision_path(monkeypatch, tmp_path)
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "unknown")

    assert http_app_state.resolve_service_revision() == "baked-service"


def test_service_revision_falls_back_to_repo_head_without_env_or_baked_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", raising=False)
    monkeypatch.setenv(
        http_app_state.BAKED_SERVICE_REVISION_PATH_ENV,
        str(tmp_path / "missing-service-revision"),
    )
    monkeypatch.setattr(http_app_state, "resolve_repo_head_revision", lambda: "repo-head")

    assert http_app_state.resolve_service_revision() == "repo-head"


def test_expected_revision_prefers_explicit_non_placeholder_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_baked_revision_path(monkeypatch, tmp_path)
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "explicit-expected")

    assert (
        http_app_state.resolve_expected_revision(default_revision="service-revision")
        == "explicit-expected"
    )


def test_expected_revision_uses_baked_file_before_default_revision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_baked_revision_path(monkeypatch, tmp_path)
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "unknown")

    assert (
        http_app_state.resolve_expected_revision(default_revision="service-revision")
        == "baked-expected"
    )


def test_expected_revision_uses_service_revision_when_baked_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        http_app_state.BAKED_EXPECTED_REVISION_PATH_ENV,
        str(tmp_path / "missing-expected-revision"),
    )
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "unknown")

    assert (
        http_app_state.resolve_expected_revision(default_revision="service-revision")
        == "service-revision"
    )
