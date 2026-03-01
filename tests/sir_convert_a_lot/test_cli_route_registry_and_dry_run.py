"""CLI route registry behavior tests for Sir Convert-a-Lot.

Purpose:
    Validate deterministic route discovery and `--dry-run` diagnostics for the
    local `convert-a-lot` workflow on the unified v2 service contract.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.cli_routes` indirectly via
      the `scripts.sir_convert_a_lot.cli` Typer app surface.
    - Ensures future local/hybrid pipelines remain discoverable without
      requiring a running service or API key for diagnostics.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from scripts.sir_convert_a_lot import cli

runner = CliRunner()


def test_routes_command_lists_supported_routes_in_stable_order() -> None:
    result = runner.invoke(cli.app, ["routes"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "Supported routes:",
        "- pdf -> md [service] (implemented)",
        "- docx -> md [service] (implemented)",
        "- docx -> pdf [service] (implemented)",
        "- html -> md [service] (implemented)",
        "- pdf -> docx [service] (implemented)",
        "- md -> pdf [service] (implemented)",
        "- md -> docx [service] (implemented)",
        "- html -> pdf [service] (implemented)",
        "- html -> docx [service] (implemented)",
    ]


def test_dry_run_reports_selected_service_route_pipeline_without_api_key(tmp_path: Path) -> None:
    source_dir = tmp_path / "inputs"
    source_dir.mkdir(parents=True)
    (source_dir / "a.pdf").write_bytes(b"%PDF-1.4\n% a\n%%EOF\n")
    (source_dir / "b.pdf").write_bytes(b"%PDF-1.4\n% b\n%%EOF\n")

    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "convert",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--to",
            "md",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "Dry run: selected route pdf -> md [service] (implemented)",
        "Pipeline:",
        "  - service: pdf -> md (v2)",
        "Discovered 2 file(s).",
    ]


def test_dry_run_reports_selected_v2_route_pipeline(tmp_path: Path) -> None:
    source_file = tmp_path / "note.md"
    source_file.write_text("# hello\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "pdf",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "Dry run: selected route md -> pdf [service] (implemented)",
        "Pipeline:",
        "  - service: md -> pdf (v2)",
        "Discovered 1 file(s).",
    ]


def test_dry_run_reports_docx_to_md_route_pipeline(tmp_path: Path) -> None:
    source_file = tmp_path / "template.docx"
    source_file.write_bytes(b"PK\x03\x04fake-docx")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "md",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "Dry run: selected route docx -> md [service] (implemented)",
        "Pipeline:",
        "  - service: docx -> md (v2)",
        "Discovered 1 file(s).",
    ]


def test_dry_run_reports_html_to_md_route_pipeline(tmp_path: Path) -> None:
    source_file = tmp_path / "index.html"
    source_file.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "md",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "Dry run: selected route html -> md [service] (implemented)",
        "Pipeline:",
        "  - service: html -> md (v2)",
        "Discovered 1 file(s).",
    ]


def test_convert_command_requires_from_when_directory_is_ambiguous(tmp_path: Path) -> None:
    source_dir = tmp_path / "mixed_inputs"
    source_dir.mkdir(parents=True)
    (source_dir / "a.md").write_text("# a\n", encoding="utf-8")
    (source_dir / "b.html").write_text("<p>b</p>\n", encoding="utf-8")

    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "convert",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--to",
            "pdf",
        ],
    )

    assert result.exit_code == 2
    assert "Ambiguous input directory" in result.output


def test_convert_command_requires_from_for_ambiguous_markdown_target_directory(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "mixed_markdown_inputs"
    source_dir.mkdir(parents=True)
    (source_dir / "a.pdf").write_bytes(b"%PDF-1.4\n% a\n%%EOF\n")
    (source_dir / "b.docx").write_bytes(b"PK\x03\x04fake-docx")

    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "convert",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--to",
            "md",
        ],
    )

    assert result.exit_code == 2
    assert "Ambiguous input directory" in result.output


def test_convert_command_rejects_resources_for_non_html_markdown_route(tmp_path: Path) -> None:
    source_file = tmp_path / "paper.pdf"
    source_file.write_bytes(b"%PDF-1.4\n% fake\n%%EOF\n")
    resources_dir = tmp_path / "resources"
    resources_dir.mkdir(parents=True)
    (resources_dir / "asset.txt").write_text("x", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "md",
            "--resources",
            str(resources_dir),
            "--api-key",
            "dev-key",
        ],
    )

    assert result.exit_code == 2
    assert "only accept --resources for html ->" in result.output
    assert "md." in result.output
