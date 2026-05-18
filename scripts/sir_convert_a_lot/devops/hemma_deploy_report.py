"""Report rendering helpers for Hemma deploy verification.

Purpose:
    Render the human-readable deploy-and-verify report while keeping the
    orchestrator module focused on workflow execution.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.hemma_deploy_and_verify`.
    - Documents Task 76 and Task 254 evidence file surfaces.
"""

from __future__ import annotations


def build_report_markdown(report: dict[str, object]) -> str:
    """Render human-readable markdown summary from report payload."""
    checks = report.get("checks")
    checks_obj = checks if isinstance(checks, dict) else {}
    metrics_forbidden = checks_obj.get("metrics_forbidden_substrings")
    forbidden = metrics_forbidden if isinstance(metrics_forbidden, list) else []
    expected_remote = checks_obj.get("expected_revision_matches_remote")
    service_remote = checks_obj.get("service_revision_matches_remote")
    public_host = checks_obj.get("nginx_proxy_public_host_registered")
    default_host = checks_obj.get("default_host_reserved_placeholder_passed")
    llm_models = checks_obj.get("structured_llm_models_reachable")
    llm_probe = checks_obj.get("structured_llm_microprobe_passed")

    lines: list[str] = [
        "# Task 76 Hemma Deploy and Verify Report",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- status: `{report.get('status')}`",
        f"- expected_revision: `{report.get('expected_revision')}`",
        f"- remote_revision: `{report.get('remote_revision')}`",
        f"- service_revision: `{report.get('service_revision')}`",
        f"- lane: `{report.get('lane')}`",
        f"- service_url: `{report.get('service_url')}`",
        f"- api_key_source: `{report.get('api_key_source')}`",
        "",
        "## Checks",
        "",
        f"- expected_revision_matches_remote: `{expected_remote}`",
        f"- service_revision_matches_remote: `{service_remote}`",
        f"- structured_llm_models_reachable: `{llm_models}`",
        f"- structured_llm_microprobe_passed: `{llm_probe}`",
        f"- live_smoke_passed: `{checks_obj.get('live_smoke_passed')}`",
        f"- live_smoke_required: `{checks_obj.get('live_smoke_required')}`",
        f"- metrics_scan_passed: `{checks_obj.get('metrics_scan_passed')}`",
        f"- public_https_reserved_passed: `{checks_obj.get('public_https_reserved_passed')}`",
        f"- public_tls_certificate_passed: `{checks_obj.get('public_tls_certificate_passed')}`",
        f"- nginx_proxy_public_host_registered: `{public_host}`",
        f"- default_host_reserved_placeholder_passed: `{default_host}`",
        f"- metrics_forbidden_substrings: `{forbidden}`",
        "",
    ]
    live_smoke_failure = report.get("live_smoke_failure")
    if isinstance(live_smoke_failure, str) and live_smoke_failure.strip() != "":
        lines.extend(["## Non-Blocking Evidence", "", live_smoke_failure, ""])
    failure_obj = report.get("failure")
    if isinstance(failure_obj, str) and failure_obj.strip() != "":
        lines.extend(["## Failure", "", failure_obj, ""])
    lines.extend(
        [
            "## Evidence Files",
            "",
            "- `report.json`",
            "- `report.md`",
            "- `readyz.json`",
            "- `metrics.prom`",
            "- `remote_head.txt`",
            "- `public_edge.json`",
            "- `public_host_response.txt`",
            "- `public_tls.json`",
            "- `nginx_proxy_default.conf`",
            "- `nginx_proxy_env.txt`",
            "- `unknown_host_response.txt`",
            "",
        ]
    )
    return "\n".join(lines)
