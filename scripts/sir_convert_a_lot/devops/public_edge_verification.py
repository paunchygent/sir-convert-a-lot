"""Public-edge evidence capture for Hemma deploy verification.

Purpose:
    Produce deterministic public HTTPS and nginx-proxy default-host evidence
    for the Sir Convert-a-Lot deploy-and-verify workflow.

Relationships:
    - Called by `scripts.sir_convert_a_lot.devops.hemma_deploy_and_verify`.
    - Implements the durable public-edge artifact contract governed by Task 254.
"""

from __future__ import annotations

import json
import socket
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

PUBLIC_HOST = "convert.hule.education"
UNKNOWN_HOST_PROBE = "sir-convert-unowned-edge-proof.hule.education"
RESERVED_DEFAULT_HOST = "hemma-reserved-default-host"
UNKNOWN_HOST_ALLOWED_STATUS_LINES = (
    "HTTP/1.1 404",
    "HTTP/2 404",
    "HTTP/1.1 421",
    "HTTP/2 421",
)

CommandRunner = Callable[[list[str], str], str]


class PublicEdgeVerificationError(ValueError):
    """Raised when public-edge evidence fails Task 254 contracts."""


@dataclass(frozen=True)
class PublicEdgeArtifactPaths:
    """Paths for durable Task 254 public-edge evidence artifacts."""

    public_edge_json: Path
    public_readyz_json: Path
    public_tls_json: Path
    nginx_proxy_config_txt: Path
    nginx_proxy_env_txt: Path
    unknown_host_response_txt: Path


def initialize_public_edge_artifacts(output_root: Path) -> PublicEdgeArtifactPaths:
    """Create deterministic public-edge artifact placeholders."""
    paths = PublicEdgeArtifactPaths(
        public_edge_json=output_root / "public_edge.json",
        public_readyz_json=output_root / "public_readyz.json",
        public_tls_json=output_root / "public_tls.json",
        nginx_proxy_config_txt=output_root / "nginx_proxy_default.conf",
        nginx_proxy_env_txt=output_root / "nginx_proxy_env.txt",
        unknown_host_response_txt=output_root / "unknown_host_response.txt",
    )
    _write_json(paths.public_edge_json, {"status": "not captured"})
    _write_json(paths.public_readyz_json, {})
    _write_json(paths.public_tls_json, {})
    paths.nginx_proxy_config_txt.write_text("# nginx-proxy config not captured\n", encoding="utf-8")
    paths.nginx_proxy_env_txt.write_text("# nginx-proxy env not captured\n", encoding="utf-8")
    paths.unknown_host_response_txt.write_text(
        "# unknown-host response not captured\n", encoding="utf-8"
    )
    return paths


def verify_public_edge(
    *,
    paths: PublicEdgeArtifactPaths,
    remote_revision: str,
    run_local: CommandRunner,
    run_remote: CommandRunner,
) -> dict[str, object]:
    """Capture public-edge evidence and fail closed on Task 254 drift."""
    public_readyz = _fetch_public_readyz(run_local=run_local)
    _write_json(paths.public_readyz_json, public_readyz)
    _assert_public_readyz(public_readyz=public_readyz, remote_revision=remote_revision)

    tls_summary = _fetch_tls_certificate_summary(host=PUBLIC_HOST)
    _write_json(paths.public_tls_json, tls_summary)

    nginx_config = run_remote(
        [
            "sudo",
            "docker",
            "exec",
            "nginx-proxy",
            "sed",
            "-n",
            "1,260p",
            "/etc/nginx/conf.d/default.conf",
        ],
        "remote nginx-proxy rendered config",
    )
    paths.nginx_proxy_config_txt.write_text(nginx_config, encoding="utf-8")

    nginx_env = run_remote(
        [
            "sudo",
            "docker",
            "inspect",
            "--format",
            "{{range .Config.Env}}{{println .}}{{end}}",
            "nginx-proxy",
        ],
        "remote nginx-proxy environment",
    )
    paths.nginx_proxy_env_txt.write_text(nginx_env, encoding="utf-8")

    convert_server_registered = f"server_name {PUBLIC_HOST}" in nginx_config
    if not convert_server_registered:
        raise PublicEdgeVerificationError(
            f"nginx-proxy config does not register server_name {PUBLIC_HOST}."
        )

    reserved_default_host_configured = f"DEFAULT_HOST={RESERVED_DEFAULT_HOST}" in nginx_env
    if not reserved_default_host_configured:
        raise PublicEdgeVerificationError(
            f"nginx-proxy DEFAULT_HOST is not {RESERVED_DEFAULT_HOST}."
        )

    public_ip = _resolve_public_ip(PUBLIC_HOST)
    unknown_response = _fetch_unknown_host_response(run_local=run_local, public_ip=public_ip)
    paths.unknown_host_response_txt.write_text(unknown_response, encoding="utf-8")
    unknown_status_allowed = _contains_any(unknown_response, UNKNOWN_HOST_ALLOWED_STATUS_LINES)
    unknown_reserved_observed = RESERVED_DEFAULT_HOST in unknown_response
    if not unknown_status_allowed:
        raise PublicEdgeVerificationError("Unknown-host probe did not return 404 or 421.")
    if not unknown_reserved_observed:
        raise PublicEdgeVerificationError(
            f"Unknown-host probe did not expose {RESERVED_DEFAULT_HOST} evidence."
        )

    report: dict[str, object] = {
        "status": "passed",
        "public_host": PUBLIC_HOST,
        "public_ip": public_ip,
        "public_readyz_ready": public_readyz.get("ready") is True,
        "public_readyz_service_revision": public_readyz.get("service_revision"),
        "tls": tls_summary,
        "nginx_proxy": {
            "convert_server_name_registered": convert_server_registered,
            "reserved_default_host_configured": reserved_default_host_configured,
            "config_artifact": paths.nginx_proxy_config_txt.name,
            "env_artifact": paths.nginx_proxy_env_txt.name,
        },
        "unknown_host_probe": {
            "host": UNKNOWN_HOST_PROBE,
            "allowed_status_observed": unknown_status_allowed,
            "reserved_placeholder_observed": unknown_reserved_observed,
            "response_artifact": paths.unknown_host_response_txt.name,
        },
    }
    _write_json(paths.public_edge_json, report)
    return report


def _fetch_public_readyz(*, run_local: CommandRunner) -> dict[str, object]:
    readyz_raw = run_local(["curl", "-fsS", f"https://{PUBLIC_HOST}/readyz"], "public readyz fetch")
    parsed: object = json.loads(readyz_raw)
    if not isinstance(parsed, dict):
        raise PublicEdgeVerificationError("public readyz payload is not an object")
    payload: dict[str, object] = {}
    for key_obj, value_obj in parsed.items():
        if isinstance(key_obj, str):
            payload[key_obj] = value_obj
    return payload


def _assert_public_readyz(*, public_readyz: dict[str, object], remote_revision: str) -> None:
    if public_readyz.get("ready") is not True:
        raise PublicEdgeVerificationError("public readyz did not report ready=true")
    service_revision = public_readyz.get("service_revision")
    if service_revision != remote_revision:
        raise PublicEdgeVerificationError(
            "public readyz service_revision does not match remote HEAD. "
            f"service_revision={service_revision!r} remote_revision={remote_revision!r}"
        )


def _fetch_tls_certificate_summary(*, host: str) -> dict[str, object]:
    context = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=10.0) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls_sock:
            raw_cert = tls_sock.getpeercert()
    if not isinstance(raw_cert, dict):
        raise PublicEdgeVerificationError("TLS peer certificate payload is not a mapping")

    cert: dict[str, object] = {}
    for key_obj, value_obj in raw_cert.items():
        if isinstance(key_obj, str):
            cert[key_obj] = value_obj

    dns_names = _extract_dns_subject_alt_names(cert.get("subjectAltName"))
    return {
        "host": host,
        "hostname_validated": True,
        "subject": _format_certificate_name(cert.get("subject")),
        "issuer": _format_certificate_name(cert.get("issuer")),
        "not_before": _string_value(cert.get("notBefore")),
        "not_after": _string_value(cert.get("notAfter")),
        "dns_subject_alt_names": dns_names,
        "host_listed_in_dns_subject_alt_names": host in dns_names,
    }


def _format_certificate_name(name_obj: object) -> list[str]:
    if not isinstance(name_obj, tuple):
        return []
    rendered: list[str] = []
    for rdn_obj in name_obj:
        if not isinstance(rdn_obj, tuple):
            continue
        parts: list[str] = []
        for attribute_obj in rdn_obj:
            if not isinstance(attribute_obj, tuple) or len(attribute_obj) != 2:
                continue
            key_obj, value_obj = attribute_obj
            if isinstance(key_obj, str) and isinstance(value_obj, str):
                parts.append(f"{key_obj}={value_obj}")
        if parts:
            rendered.append(",".join(parts))
    return rendered


def _extract_dns_subject_alt_names(san_obj: object) -> list[str]:
    if not isinstance(san_obj, tuple):
        return []
    names: list[str] = []
    for item_obj in san_obj:
        if not isinstance(item_obj, tuple) or len(item_obj) != 2:
            continue
        key_obj, value_obj = item_obj
        if key_obj == "DNS" and isinstance(value_obj, str):
            names.append(value_obj)
    return names


def _fetch_unknown_host_response(*, run_local: CommandRunner, public_ip: str) -> str:
    return run_local(
        [
            "curl",
            "--resolve",
            f"{UNKNOWN_HOST_PROBE}:443:{public_ip}",
            "--insecure",
            "-isS",
            f"https://{UNKNOWN_HOST_PROBE}/",
        ],
        "unknown-host reserved default proof",
    )


def _resolve_public_ip(host: str) -> str:
    return socket.gethostbyname(host)


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _string_value(value_obj: object) -> str:
    if isinstance(value_obj, str):
        return value_obj
    return ""


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
