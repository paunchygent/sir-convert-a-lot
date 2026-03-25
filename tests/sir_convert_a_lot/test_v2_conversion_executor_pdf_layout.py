"""V2 conversion executor tests for `conversion.pdf_layout` application."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

import scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_routes_html as v2_non_pdf_routes_html
import scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_routes_md as v2_non_pdf_routes_md
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    execute_v2_job_conversion,
)
from tests.sir_convert_a_lot.v2_conversion_executor_test_support import (
    _build_job,
    _service_config,
    _UnusedBackend,
)


def test_execute_v2_job_conversion_md_to_pdf_applies_pdf_layout_preset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_convert_markdown_to_html(
        *,
        markdown_path: Path,
        output_html_path: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del markdown_path, timeout_seconds
        output_html_path.write_text("<html><body>Converted</body></html>", encoding="utf-8")

    css_seen: tuple[Path, ...] | None = None

    def _fake_convert_html_to_pdf(
        *,
        html_path: Path,
        output_pdf_path: Path,
        css_paths: tuple[Path, ...] = (),
        base_url: str | None = None,
        allowed_resource_root: Path | None = None,
        input_trust_mode: object | None = None,
    ) -> None:
        nonlocal css_seen
        del html_path, base_url, allowed_resource_root, input_trust_mode
        css_seen = css_paths
        output_pdf_path.write_bytes(b"%PDF-1.7\nstub-pdf\n")

    monkeypatch.setattr(
        v2_non_pdf_routes_md, "convert_markdown_to_html", _fake_convert_markdown_to_html
    )
    monkeypatch.setattr(v2_non_pdf_routes_md, "convert_html_to_pdf", _fake_convert_html_to_pdf)

    job = _build_job(
        tmp_path,
        source_filename="note.md",
        source_bytes=b"# Note\n\nBody\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
        pdf_layout={"paper_size": "a4", "orientation": "landscape", "margins_mm": 10},
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.pipeline_used == "md_to_pdf_v2"
    assert css_seen is not None
    assert len(css_seen) == 1
    assert css_seen[0].name == "__pdf_layout_preset_v2.css"
    assert "A4 landscape" in css_seen[0].read_text(encoding="utf-8")


def test_execute_v2_job_conversion_html_to_pdf_applies_pdf_layout_preset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    css_seen: tuple[Path, ...] | None = None

    def _fake_convert_html_to_pdf(
        *,
        html_path: Path,
        output_pdf_path: Path,
        css_paths: tuple[Path, ...] = (),
        base_url: str | None = None,
        allowed_resource_root: Path | None = None,
        input_trust_mode: object | None = None,
    ) -> None:
        nonlocal css_seen
        del html_path, base_url, allowed_resource_root, input_trust_mode
        css_seen = css_paths
        output_pdf_path.write_bytes(b"%PDF-1.7\nstub-pdf\n")

    monkeypatch.setattr(v2_non_pdf_routes_html, "convert_html_to_pdf", _fake_convert_html_to_pdf)

    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.PDF,
        pdf_layout={"paper_size": "a5", "orientation": "portrait", "margins_mm": 0},
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.pipeline_used == "html_to_pdf_v2"
    assert css_seen is not None
    assert len(css_seen) == 1
    assert css_seen[0].name == "__pdf_layout_preset_v2.css"
    css = css_seen[0].read_text(encoding="utf-8")
    assert "size: A5;" in css
    assert "margin: 0mm;" in css


def test_execute_v2_job_conversion_html_to_pdf_skips_preset_for_author_owned_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    css_seen: tuple[Path, ...] | None = None
    resources_zip_path = tmp_path / "raw" / "resources.zip"
    resources_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(resources_zip_path, mode="w") as archive:
        archive.writestr("print.css", "@page { size: A3 landscape; margin: 0; }\n")

    def _fake_convert_html_to_pdf(
        *,
        html_path: Path,
        output_pdf_path: Path,
        css_paths: tuple[Path, ...] = (),
        base_url: str | None = None,
        allowed_resource_root: Path | None = None,
        input_trust_mode: object | None = None,
    ) -> None:
        nonlocal css_seen
        del html_path, base_url, allowed_resource_root, input_trust_mode
        css_seen = css_paths
        output_pdf_path.write_bytes(b"%PDF-1.7\nstub-pdf\n")

    monkeypatch.setattr(v2_non_pdf_routes_html, "convert_html_to_pdf", _fake_convert_html_to_pdf)

    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.PDF,
        css_filenames=["print.css"],
        page_css_mode="author_owned",
    )
    job.resources_zip_path = resources_zip_path

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.pipeline_used == "html_to_pdf_v2"
    assert css_seen is not None
    assert [path.name for path in css_seen] == ["print.css"]


def test_execute_v2_job_conversion_html_to_pdf_threads_trusted_bundle_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seen_trust_mode: object | None = None

    def _fake_convert_html_to_pdf(
        *,
        html_path: Path,
        output_pdf_path: Path,
        css_paths: tuple[Path, ...] = (),
        base_url: str | None = None,
        allowed_resource_root: Path | None = None,
        input_trust_mode: object | None = None,
    ) -> None:
        nonlocal seen_trust_mode
        del html_path, css_paths, base_url, allowed_resource_root
        seen_trust_mode = input_trust_mode
        output_pdf_path.write_bytes(b"%PDF-1.7\nstub-pdf\n")

    monkeypatch.setattr(v2_non_pdf_routes_html, "convert_html_to_pdf", _fake_convert_html_to_pdf)

    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.PDF,
        input_trust_mode="trusted_app_bundle",
    )

    execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert seen_trust_mode is not None
    assert getattr(seen_trust_mode, "value", None) == "trusted_app_bundle"
