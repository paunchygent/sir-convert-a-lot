"""V2 conversion executor workdir preparation tests."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_conversion_executor
from scripts.sir_convert_a_lot.infrastructure.resources_zip import ResourcesZipError
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from tests.sir_convert_a_lot.conversion.v2_conversion_executor_test_support import _build_job


def test_prepare_workdir_extracts_resources_zip_and_copies_source(tmp_path: Path) -> None:
    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Source</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.DOCX,
    )
    resources_zip_path = tmp_path / "raw" / "resources.zip"
    with zipfile.ZipFile(resources_zip_path, mode="w") as archive:
        archive.writestr("styles/site.css", "body { color: #111; }\n")
        archive.writestr("assets/data.txt", "ok\n")
    job.resources_zip_path = resources_zip_path

    workdir, input_path = v2_conversion_executor._prepare_workdir(job)

    assert workdir == job.upload_path.parent / "workdir"
    assert input_path == workdir / "page.html"
    assert input_path.read_bytes() == b"<html><body>Source</body></html>"
    assert (workdir / "styles/site.css").read_text(encoding="utf-8") == "body { color: #111; }\n"
    assert (workdir / "assets/data.txt").read_text(encoding="utf-8") == "ok\n"


def test_prepare_workdir_maps_resources_zip_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    job = _build_job(
        tmp_path,
        source_filename="note.md",
        source_bytes=b"# Note\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
    )
    resources_zip_path = tmp_path / "raw" / "broken.zip"
    resources_zip_path.write_bytes(b"not-a-real-zip")
    job.resources_zip_path = resources_zip_path

    def _raise_resources_zip_error(*, zip_path: Path, output_dir: Path) -> None:
        del zip_path, output_dir
        raise ResourcesZipError(
            code="resources_zip_invalid",
            message="Uploaded resources bundle is not a valid zip file.",
        )

    monkeypatch.setattr(v2_conversion_executor, "extract_resources_zip", _raise_resources_zip_error)

    with pytest.raises(ServiceError) as exc_info:
        v2_conversion_executor._prepare_workdir(job)

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "resources_zip_invalid"
    assert error.message == "Uploaded resources bundle is not a valid zip file."
    assert error.retryable is False
