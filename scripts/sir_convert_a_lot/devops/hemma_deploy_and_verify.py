"""One-command Hemma deploy and live verification orchestrator.

Purpose:
    Execute Hemma revision parity and live verification in one deterministic
    command: push -> remote pull -> production rebuild/recreate -> readiness
    parity -> live smoke -> metrics safety scan.

Relationships:
    - Exposed as `pdm run hemma-deploy-and-verify`.
    - Uses `scripts/devops/run-hemma.sh` via `run-local-pdm` for canonical
      remote execution context.
    - Delegates live GPU smoke to
      `scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.hemma_deploy_report import build_report_markdown
from scripts.sir_convert_a_lot.devops.hemma_deploy_verification_contracts import (
    VerificationContractError,
    assert_expected_revision_matches_remote,
    assert_service_revision_matches_remote,
    port_for_lane,
    resolve_api_key,
    scan_metrics_forbidden_substrings,
    service_url_for_lane,
)
from scripts.sir_convert_a_lot.devops.public_edge_verification import (
    PublicEdgeVerificationError,
    initialize_public_edge_artifacts,
    verify_public_edge,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/hemma-deploy-verify")
REMOTE_PDM = "/home/paunchygent/.local/bin/pdm"
REMOTE_DEPLOY_PATH = (
    "/home/paunchygent/.local/bin:"
    "/snap/bin:"
    "/usr/local/sbin:"
    "/usr/local/bin:"
    "/usr/sbin:"
    "/usr/bin:"
    "/sbin:"
    "/bin"
)
REMOTE_HEMMA_SKILL_REPOSITORY = "/home/paunchygent/apps/skill-repository"
DOCKER_SOCKET_PERMISSION_DENIED_MESSAGES = (
    "permission denied while trying to connect to the Docker daemon socket",
    "permission denied while trying to connect to the docker API",
)


class CommandExecutionError(RuntimeError):
    """Raised when subprocess execution fails."""


@dataclass(frozen=True)
class WorkflowSettings:
    """Normalized settings for the deploy-and-verify workflow."""

    expected_revision: str
    lane: str
    service_url: str
    output_root: Path
    api_key: str
    api_key_source: str
    allow_dev_key: bool


def _utc_now_iso() -> str:
    """Return RFC3339 UTC timestamp for reports."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for Hemma deploy verification command surface."""
    parser = argparse.ArgumentParser(
        description="Hemma deploy + verify orchestrator (Hemma deploy verification)."
    )
    parser.add_argument(
        "--expected-revision",
        required=True,
        help="Local Git revision intended for deployment (SHA or rev-parse expression).",
    )
    parser.add_argument(
        "--lane",
        choices=["host", "docker"],
        default="host",
        help="Verification lane: host (28085 canonical) or docker (8085 internal-only).",
    )
    parser.add_argument(
        "--service-url",
        default="",
        help="Override service URL (default derived from --lane).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="X-API-Key value. Precedence: --api-key > SIR_CONVERT_A_LOT_V2_API_KEY.",
    )
    parser.add_argument(
        "--allow-dev-key",
        action="store_true",
        help="Allow implicit env-based dev-only-key for local/dev scenarios.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Deterministic artifact output path.",
    )
    return parser.parse_args(argv)


def _run_command(
    command: list[str],
    *,
    label: str,
    env: dict[str, str] | None = None,
    redactions: tuple[str, ...] = (),
) -> str:
    """Run command and return stdout, raising sanitized diagnostics on failure."""
    result = subprocess.run(command, check=False, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        stdout = result.stdout
        stderr = result.stderr
        for token in redactions:
            if token != "":
                stdout = stdout.replace(token, "<redacted>")
                stderr = stderr.replace(token, "<redacted>")
        raise CommandExecutionError(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{stdout.strip()}\n"
            f"stderr:\n{stderr.strip()}"
        )
    return result.stdout


def _run_remote(
    remote_args: list[str],
    *,
    label: str,
    redactions: tuple[str, ...] = (),
) -> str:
    """Execute argv-safe command on Hemma via canonical wrappers."""
    command = ["pdm", "run", "run-local-pdm", "run-hemma", "--", *remote_args]
    return _run_command(command, label=label, redactions=redactions)


def _write_json(path: Path, payload: object) -> None:
    """Write deterministic JSON output."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_expected_revision(raw_revision: str) -> str:
    """Resolve revision expression to full commit SHA."""
    output = _run_command(
        ["git", "rev-parse", f"{raw_revision}^{{commit}}"],
        label="resolve expected revision",
    )
    resolved = output.strip()
    if resolved == "":
        raise CommandExecutionError("resolve expected revision produced empty SHA")
    return resolved


def _load_workflow_settings(args: argparse.Namespace) -> WorkflowSettings:
    """Resolve settings and enforce API-key contracts before workflow execution."""
    resolved_expected_revision = _resolve_expected_revision(str(args.expected_revision))
    try:
        resolved_api_key = resolve_api_key(
            api_key_arg=args.api_key,
            environ=os.environ,
            allow_dev_key=bool(args.allow_dev_key),
        )
    except VerificationContractError as exc:
        raise CommandExecutionError(str(exc)) from exc

    lane = str(args.lane)
    # Validate lane mapping early for deterministic failure messaging.
    port_for_lane(lane)

    service_url = str(args.service_url).strip().rstrip("/")
    if service_url == "":
        service_url = service_url_for_lane(lane)

    output_root = Path(str(args.output_root))
    return WorkflowSettings(
        expected_revision=resolved_expected_revision,
        lane=lane,
        service_url=service_url,
        output_root=output_root,
        api_key=resolved_api_key.value,
        api_key_source=resolved_api_key.source,
        allow_dev_key=bool(args.allow_dev_key),
    )


def _parse_json_object(payload_text: str, *, label: str) -> dict[str, object]:
    """Parse JSON text and require top-level object payload."""
    parsed: object = json.loads(payload_text)
    if not isinstance(parsed, dict):
        raise VerificationContractError(f"{label} payload is not an object")
    return parsed


def _fetch_readyz_with_retry(
    *,
    service_url: str,
    timeout_seconds: float = 120.0,
    poll_interval_seconds: float = 2.0,
) -> dict[str, object]:
    """Fetch readyz payload with bounded retries for recreate/startup transitions."""
    deadline = time.monotonic() + timeout_seconds
    last_error = "readyz not yet checked"
    while time.monotonic() < deadline:
        try:
            readyz_raw = _run_remote(
                ["curl", "-sS", f"{service_url}/readyz"],
                label="remote readyz fetch",
            )
            payload = _parse_json_object(readyz_raw, label="readyz")
            if payload.get("ready") is True:
                return payload
            last_error = f"readyz reports not ready: reasons={payload.get('reasons')!r}"
        except (CommandExecutionError, VerificationContractError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(poll_interval_seconds)

    raise VerificationContractError(
        f"readyz did not become ready within retry window. Last observed issue: {last_error}"
    )


def _initialize_artifacts(output_root: Path) -> tuple[Path, Path, Path, Path, Path]:
    """Create output path and deterministic evidence file placeholders."""
    output_root.mkdir(parents=True, exist_ok=True)
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    readyz_path = output_root / "readyz.json"
    metrics_path = output_root / "metrics.prom"
    remote_head_path = output_root / "remote_head.txt"

    readyz_path.write_text("{}\n", encoding="utf-8")
    metrics_path.write_text("# metrics not captured\n", encoding="utf-8")
    remote_head_path.write_text("unavailable\n", encoding="utf-8")

    return report_json_path, report_md_path, readyz_path, metrics_path, remote_head_path


def _remote_recreate_service(remote_revision: str) -> None:
    """Recreate remote service, retrying with sudo when Docker socket is restricted."""
    recreate_args = [
        "env",
        f"SIR_CONVERT_A_LOT_SERVICE_REVISION={remote_revision}",
        f"SIR_CONVERT_A_LOT_EXPECTED_REVISION={remote_revision}",
        "pdm",
        "run",
        "prod-recreate",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_prod",
        "sir_convert_a_lot_public_reserved",
    ]
    try:
        _run_remote(
            recreate_args,
            label="remote pdm run prod-recreate public edge services",
        )
        return
    except CommandExecutionError as exc:
        error_text = str(exc)
        if not any(message in error_text for message in DOCKER_SOCKET_PERMISSION_DENIED_MESSAGES):
            raise

    _run_remote(
        [
            "sudo",
            "-n",
            "env",
            f"PATH={REMOTE_DEPLOY_PATH}",
            f"SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY={REMOTE_HEMMA_SKILL_REPOSITORY}",
            f"SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY={REMOTE_HEMMA_SKILL_REPOSITORY}",
            f"SIR_CONVERT_A_LOT_SERVICE_REVISION={remote_revision}",
            f"SIR_CONVERT_A_LOT_EXPECTED_REVISION={remote_revision}",
            REMOTE_PDM,
            "run",
            "prod-recreate",
            "sir_convert_a_lot_gpu_worker",
            "sir_convert_a_lot_prod",
            "sir_convert_a_lot_public_reserved",
        ],
        label="remote sudo -n pdm run prod-recreate public edge services",
    )


def execute_workflow(settings: WorkflowSettings) -> dict[str, object]:
    """Run deploy + verify sequence and return report payload."""
    report: dict[str, object] = {
        "generated_at": _utc_now_iso(),
        "status": "failed",
        "expected_revision": settings.expected_revision,
        "remote_revision": None,
        "service_revision": None,
        "lane": settings.lane,
        "service_url": settings.service_url,
        "api_key_source": settings.api_key_source,
        "checks": {
            "expected_revision_matches_remote": False,
            "service_revision_matches_remote": False,
            "live_smoke_passed": False,
            "live_smoke_required": False,
            "metrics_scan_passed": False,
            "public_https_reserved_passed": False,
            "public_tls_certificate_passed": False,
            "nginx_proxy_public_host_registered": False,
            "default_host_reserved_placeholder_passed": False,
            "metrics_forbidden_substrings": [],
        },
        "public_edge": None,
        "live_smoke_failure": None,
        "failure": None,
    }

    report_json_path, report_md_path, readyz_path, metrics_path, remote_head_path = (
        _initialize_artifacts(settings.output_root)
    )
    public_edge_paths = initialize_public_edge_artifacts(settings.output_root)

    try:
        _run_command(["git", "push", "origin", "HEAD"], label="git push origin HEAD")
        _run_remote(["git", "pull", "--ff-only"], label="remote git pull --ff-only")

        remote_revision = _run_remote(
            ["git", "rev-parse", "HEAD"],
            label="remote git rev-parse HEAD",
        ).strip()
        remote_head_path.write_text(remote_revision + "\n", encoding="utf-8")
        report["remote_revision"] = remote_revision

        assert_expected_revision_matches_remote(
            expected_revision=settings.expected_revision,
            remote_revision=remote_revision,
        )
        checks_obj = report["checks"]
        if isinstance(checks_obj, dict):
            checks_obj["expected_revision_matches_remote"] = True

        _remote_recreate_service(remote_revision)

        readyz_payload = _fetch_readyz_with_retry(service_url=settings.service_url)
        _write_json(readyz_path, readyz_payload)

        service_revision_obj = readyz_payload.get("service_revision")
        if not isinstance(service_revision_obj, str) or service_revision_obj.strip() == "":
            raise VerificationContractError("readyz payload missing service_revision")
        report["service_revision"] = service_revision_obj

        assert_service_revision_matches_remote(
            service_revision=service_revision_obj,
            remote_revision=remote_revision,
        )
        checks_obj = report["checks"]
        if isinstance(checks_obj, dict):
            checks_obj["service_revision_matches_remote"] = True

        remote_smoke_output_root = "build/verification/hemma-deploy-verify/v2-smoke"
        remote_verify_args: list[str] = [
            "pdm",
            "run",
            "python",
            "-m",
            "scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions",
            "--lane",
            settings.lane,
            "--api-key",
            settings.api_key,
            "--output-root",
            remote_smoke_output_root,
        ]
        try:
            _run_remote(
                remote_verify_args,
                label="remote verify_hemma_v2_conversions",
                redactions=(settings.api_key,),
            )
            checks_obj = report["checks"]
            if isinstance(checks_obj, dict):
                checks_obj["live_smoke_passed"] = True
        except CommandExecutionError as exc:
            report["live_smoke_failure"] = str(exc)

        metrics_text = _run_remote(
            ["curl", "-fsS", f"{settings.service_url}/metrics"],
            label="remote metrics fetch",
        )
        metrics_path.write_text(metrics_text, encoding="utf-8")

        forbidden = scan_metrics_forbidden_substrings(metrics_text)
        checks_obj = report["checks"]
        if isinstance(checks_obj, dict):
            checks_obj["metrics_forbidden_substrings"] = forbidden
        if forbidden:
            raise VerificationContractError(
                "Metrics safety scan failed. Forbidden substrings found: "
                f"{', '.join(forbidden)}. Remediation: remove high-cardinality labels "
                "(for example job identifiers) and rerun verification."
            )
        if isinstance(checks_obj, dict):
            checks_obj["metrics_scan_passed"] = True

        public_edge_report = verify_public_edge(
            paths=public_edge_paths,
            remote_revision=remote_revision,
            run_local=lambda command, label: _run_command(command, label=label),
            run_remote=lambda command, label: _run_remote(command, label=label),
        )
        report["public_edge"] = public_edge_report
        checks_obj = report["checks"]
        if isinstance(checks_obj, dict):
            checks_obj["public_https_reserved_passed"] = True
            checks_obj["public_tls_certificate_passed"] = True
            checks_obj["nginx_proxy_public_host_registered"] = True
            checks_obj["default_host_reserved_placeholder_passed"] = True

        report["status"] = "passed"
        report["failure"] = None
    except (
        CommandExecutionError,
        VerificationContractError,
        PublicEdgeVerificationError,
        json.JSONDecodeError,
    ) as exc:
        report["status"] = "failed"
        report["failure"] = str(exc)

    _write_json(report_json_path, report)
    report_md_path.write_text(build_report_markdown(report) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the Hemma deploy and live-verification workflow."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        settings = _load_workflow_settings(args)
    except CommandExecutionError as exc:
        # Keep deterministic artifact location if settings resolution fails.
        output_root = Path(str(args.output_root))
        report_json_path, report_md_path, readyz_path, metrics_path, remote_head_path = (
            _initialize_artifacts(output_root)
        )
        report: dict[str, object] = {
            "generated_at": _utc_now_iso(),
            "status": "failed",
            "expected_revision": str(args.expected_revision),
            "remote_revision": None,
            "service_revision": None,
            "lane": str(args.lane),
            "service_url": str(args.service_url).strip() or service_url_for_lane(str(args.lane)),
            "api_key_source": None,
            "checks": {
                "expected_revision_matches_remote": False,
                "service_revision_matches_remote": False,
                "live_smoke_passed": False,
                "live_smoke_required": False,
                "metrics_scan_passed": False,
                "public_https_reserved_passed": False,
                "public_tls_certificate_passed": False,
                "nginx_proxy_public_host_registered": False,
                "default_host_reserved_placeholder_passed": False,
                "metrics_forbidden_substrings": [],
            },
            "public_edge": None,
            "live_smoke_failure": None,
            "failure": str(exc),
        }
        initialize_public_edge_artifacts(output_root)
        _write_json(report_json_path, report)
        report_md_path.write_text(build_report_markdown(report) + "\n", encoding="utf-8")
        readyz_path.write_text("{}\n", encoding="utf-8")
        metrics_path.write_text("# metrics not captured\n", encoding="utf-8")
        remote_head_path.write_text("unavailable\n", encoding="utf-8")
        print(report_md_path.as_posix())
        return 1

    report = execute_workflow(settings)
    report_md = settings.output_root / "report.md"
    print(report_md.as_posix())
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
