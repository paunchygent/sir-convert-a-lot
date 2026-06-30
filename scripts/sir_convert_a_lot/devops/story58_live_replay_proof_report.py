"""Story 58 live replay proof report rendering.

Purpose:
    Render the retained Story 58 proof summary into a compact Markdown report
    for governed closeout review.

Relationships:
    - Consumes sanitized case evidence from `story58_live_replay_proof`.
    - Produces the human-readable sibling to `summary.json`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import (
    JsonObject,
    Story58CaseEvidence,
)


def render_report(*, summary: JsonObject, cases: tuple[Story58CaseEvidence, ...]) -> str:
    """Render a Markdown report for the proof run."""

    lines = [
        "# Story 58 Live Replay Proof",
        "",
        f"- Overall status: `{summary.get('overall_status')}`",
        f"- Service URL: `{summary.get('service_url')}`",
        f"- Service revision: `{summary.get('service_revision')}`",
        f"- Run directory: `{summary.get('run_dir')}`",
        "",
        "## Cases",
        "",
    ]
    for case in cases:
        lines.append(f"### {case.label}")
        lines.append("")
        lines.append(f"- Case id: `{case.case_id}`")
        lines.append(f"- Status: `{case.status}`")
        lines.append(f"- Reason: {case.reason}")
        if case.external_command is not None:
            lines.append(f"- External command: `{case.external_command}`")
        for request in case.requests:
            lines.append(
                "- Request evidence: "
                f"`{request.label}` HTTP `{request.status_code}` -> "
                f"`{request.response_path.name}`"
            )
            if request.artifact_metadata_path is not None:
                lines.append(f"- Artifact metadata: `{request.artifact_metadata_path.name}`")
        lines.append("")
    lines.append("## Retention Policy")
    lines.append("")
    lines.append(
        "Retained files contain operational metadata only: ids, route/replay state, "
        "schema versions, request/artifact digests, HTTP status/error codes, "
        "timestamps, service revision, and content-safe case labels."
    )
    return "\n".join(lines).rstrip() + "\n"
