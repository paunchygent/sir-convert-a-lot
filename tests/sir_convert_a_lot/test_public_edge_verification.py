"""Tests for durable Task 254 public-edge evidence capture.

Purpose:
    Lock public HTTPS, nginx-proxy, and unknown-host proof artifacts emitted by
    the Hemma deploy-and-verify workflow.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.public_edge_verification`.
    - Complements Task 254 production public-edge recovery contracts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import public_edge_verification


def test_verify_public_edge_writes_durable_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = public_edge_verification.initialize_public_edge_artifacts(tmp_path)
    remote_calls: list[list[str]] = []
    local_calls: list[list[str]] = []

    def fake_run_local(command: list[str], label: str) -> str:
        del label
        local_calls.append(command)
        if command == ["curl", "-isS", "https://convert.hule.education/readyz"]:
            return (
                "HTTP/2 421\r\n"
                "x-sir-convert-public-edge: reserved\r\n"
                "\r\n"
                "sir-convert-a-lot-public-edge-reserved\n"
            )
        if command[:3] == [
            "curl",
            "--resolve",
            "sir-convert-unowned-edge-proof.hule.education:443:203.0.113.10",
        ]:
            return "HTTP/2 421\r\ncontent-type: text/plain\r\n\r\nhemma-reserved-default-host\n"
        raise AssertionError(f"unexpected local command: {command!r}")

    def fake_run_remote(command: list[str], label: str) -> str:
        del label
        remote_calls.append(command)
        if command[-1] == "/etc/nginx/conf.d/default.conf":
            return "server_name convert.hule.education;\n"
        if command[-1] == "nginx-proxy":
            return "DEFAULT_HOST=hemma-reserved-default-host\n"
        raise AssertionError(f"unexpected remote command: {command!r}")

    monkeypatch.setattr(
        public_edge_verification,
        "_fetch_tls_certificate_summary",
        lambda host: {
            "host": host,
            "hostname_validated": True,
            "dns_subject_alt_names": [host],
            "host_listed_in_dns_subject_alt_names": True,
        },
    )
    monkeypatch.setattr(
        public_edge_verification,
        "_resolve_public_ip",
        lambda host: "203.0.113.10",
    )

    report = public_edge_verification.verify_public_edge(
        paths=paths,
        remote_revision="abc",
        run_local=fake_run_local,
        run_remote=fake_run_remote,
    )

    assert report["status"] == "passed"
    public_host_reserved = report["public_host_reserved"]
    assert isinstance(public_host_reserved, dict)
    assert public_host_reserved["allowed_status_observed"] is True
    assert public_host_reserved["reserved_marker_observed"] is True
    nginx_proxy = report["nginx_proxy"]
    assert isinstance(nginx_proxy, dict)
    assert nginx_proxy["convert_server_name_registered"] is True
    assert nginx_proxy["reserved_default_host_configured"] is True

    edge_payload = json.loads(paths.public_edge_json.read_text(encoding="utf-8"))
    assert edge_payload["status"] == "passed"
    assert "sir-convert-a-lot-public-edge-reserved" in paths.public_host_response_txt.read_text(
        encoding="utf-8"
    )
    assert "server_name convert.hule.education" in paths.nginx_proxy_config_txt.read_text(
        encoding="utf-8"
    )
    assert "DEFAULT_HOST=hemma-reserved-default-host" in paths.nginx_proxy_env_txt.read_text(
        encoding="utf-8"
    )
    assert "hemma-reserved-default-host" in paths.unknown_host_response_txt.read_text(
        encoding="utf-8"
    )
    assert remote_calls[0][:4] == ["sudo", "docker", "exec", "nginx-proxy"]
    assert local_calls[-1][0:2] == ["curl", "--resolve"]


def test_verify_public_edge_rejects_product_default_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = public_edge_verification.initialize_public_edge_artifacts(tmp_path)

    def fake_run_local(command: list[str], label: str) -> str:
        del command, label
        return "HTTP/2 421\r\n\r\nsir-convert-a-lot-public-edge-reserved\n"

    def fake_run_remote(command: list[str], label: str) -> str:
        del label
        if command[-1] == "/etc/nginx/conf.d/default.conf":
            return "server_name convert.hule.education;\n"
        if command[-1] == "nginx-proxy":
            return "DEFAULT_HOST=skriptoteket.hule.education\n"
        raise AssertionError(f"unexpected remote command: {command!r}")

    monkeypatch.setattr(
        public_edge_verification,
        "_fetch_tls_certificate_summary",
        lambda host: {"host": host, "hostname_validated": True},
    )

    with pytest.raises(
        public_edge_verification.PublicEdgeVerificationError,
        match="DEFAULT_HOST",
    ):
        public_edge_verification.verify_public_edge(
            paths=paths,
            remote_revision="abc",
            run_local=fake_run_local,
            run_remote=fake_run_remote,
        )
