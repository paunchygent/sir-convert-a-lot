"""Contracts for Hemma deploy and live-verification workflows.

Purpose:
    Centralize canonical lane mapping, API-key resolution, metrics safety scans,
    and revision-parity guardrails used by Task 76 deploy verification surfaces.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.hemma_deploy_and_verify`.
    - Used by `scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime`.
    - Covered by targeted regression tests in `tests/sir_convert_a_lot/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

API_KEY_ENV_VAR = "SIR_CONVERT_A_LOT_V2_API_KEY"
DEFAULT_DEV_API_KEY = "dev-only-key"
LANE_PORTS: dict[str, int] = {
    "host": 28085,
    "docker": 8085,
}
FORBIDDEN_METRICS_SUBSTRINGS: tuple[str, ...] = (
    "job_id=",
    "jobv2_",
)


class VerificationContractError(ValueError):
    """Raised when Task 76 deploy/verification contracts are violated."""


@dataclass(frozen=True)
class ResolvedApiKey:
    """Resolved API-key payload with provenance for policy checks."""

    value: str
    source: str


def resolve_api_key(
    *,
    api_key_arg: str | None,
    environ: Mapping[str, str],
    allow_dev_key: bool,
) -> ResolvedApiKey:
    """Resolve API key from CLI/env with strict precedence and dev-key policy."""
    if api_key_arg is not None and api_key_arg.strip() != "":
        resolved = ResolvedApiKey(value=api_key_arg.strip(), source="cli")
    else:
        env_value = environ.get(API_KEY_ENV_VAR, "").strip()
        if env_value == "":
            raise VerificationContractError(
                "Missing API key. Provide --api-key or set SIR_CONVERT_A_LOT_V2_API_KEY."
            )
        resolved = ResolvedApiKey(value=env_value, source="env")

    if resolved.value == DEFAULT_DEV_API_KEY and resolved.source != "cli" and not allow_dev_key:
        raise VerificationContractError(
            "Refusing implicit dev-only-key from environment. "
            "Pass --api-key dev-only-key explicitly or add --allow-dev-key."
        )
    return resolved


def port_for_lane(lane: str) -> int:
    """Return canonical listener port for verification lane."""
    port = LANE_PORTS.get(lane)
    if port is None:
        raise VerificationContractError(
            f"Unsupported lane {lane!r}. Expected one of: {', '.join(sorted(LANE_PORTS))}."
        )
    return port


def service_url_for_lane(lane: str) -> str:
    """Return canonical local service URL for verification lane."""
    return f"http://127.0.0.1:{port_for_lane(lane)}"


def expected_revision_mismatch_message(*, expected_revision: str, remote_revision: str) -> str:
    """Build actionable remediation message for expected-vs-remote mismatch."""
    return (
        "Expected revision does not match remote repository HEAD. "
        f"expected_revision={expected_revision!r} remote_revision={remote_revision!r}. "
        "Remediation: 1) commit/stage local changes; 2) push the expected revision "
        "to origin; 3) rerun hemma-deploy-and-verify with --expected-revision set "
        "to the pushed commit SHA."
    )


def service_revision_mismatch_message(*, service_revision: str, remote_revision: str) -> str:
    """Build actionable remediation message for service-vs-remote mismatch."""
    return (
        "Service revision reported by /readyz does not match remote repository HEAD. "
        f"service_revision={service_revision!r} remote_revision={remote_revision!r}. "
        "Remediation: 1) run remote rebuild/recreate (pdm run dev-recreate); "
        "2) verify compose uses current revision env; 3) rerun verification once "
        "service is ready."
    )


def assert_expected_revision_matches_remote(
    *, expected_revision: str, remote_revision: str
) -> None:
    """Enforce expected_revision == remote_revision with remediation guidance."""
    if expected_revision != remote_revision:
        raise VerificationContractError(
            expected_revision_mismatch_message(
                expected_revision=expected_revision,
                remote_revision=remote_revision,
            )
        )


def assert_service_revision_matches_remote(*, service_revision: str, remote_revision: str) -> None:
    """Enforce service_revision == remote_revision with remediation guidance."""
    if service_revision != remote_revision:
        raise VerificationContractError(
            service_revision_mismatch_message(
                service_revision=service_revision,
                remote_revision=remote_revision,
            )
        )


def scan_metrics_forbidden_substrings(metrics_text: str) -> list[str]:
    """Return sorted forbidden metrics substrings found in metrics text."""
    found = {token for token in FORBIDDEN_METRICS_SUBSTRINGS if token in metrics_text}
    return sorted(found)
