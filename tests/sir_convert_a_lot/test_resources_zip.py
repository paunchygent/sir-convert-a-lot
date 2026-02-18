"""Unit tests for v2 resources zip extraction.

Purpose:
    Ensure `resources.zip` extraction is safe against zip-slip and zip-bomb
    abuse while remaining deterministic for normal CSS/image bundles.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.resources_zip`.
    - Supports v2 conversion pipelines that rely on uploaded resource bundles.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.resources_zip import (
    RESOURCES_ZIP_MEMBER_TOO_LARGE,
    RESOURCES_ZIP_PATH_TRAVERSAL,
    RESOURCES_ZIP_TOO_MANY_MEMBERS,
    RESOURCES_ZIP_TOTAL_TOO_LARGE,
    ResourcesZipError,
    extract_resources_zip,
)


def _write_zip(path: Path, *, members: dict[str, bytes]) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for name, payload in members.items():
            zip_handle.writestr(name, payload)
    path.write_bytes(buffer.getvalue())


def test_rejects_path_traversal_member(tmp_path: Path) -> None:
    zip_path = tmp_path / "resources.zip"
    _write_zip(zip_path, members={"../evil.txt": b"nope"})

    with pytest.raises(ResourcesZipError) as exc_info:
        extract_resources_zip(
            zip_path=zip_path,
            output_dir=tmp_path / "out",
            max_members=10,
            max_total_uncompressed_bytes=1024,
            max_member_uncompressed_bytes=1024,
        )

    assert exc_info.value.code == RESOURCES_ZIP_PATH_TRAVERSAL


def test_rejects_absolute_path_member(tmp_path: Path) -> None:
    zip_path = tmp_path / "resources.zip"
    _write_zip(zip_path, members={"/abs.txt": b"nope"})

    with pytest.raises(ResourcesZipError) as exc_info:
        extract_resources_zip(
            zip_path=zip_path,
            output_dir=tmp_path / "out",
            max_members=10,
            max_total_uncompressed_bytes=1024,
            max_member_uncompressed_bytes=1024,
        )

    assert exc_info.value.code == RESOURCES_ZIP_PATH_TRAVERSAL


def test_rejects_excessive_member_count(tmp_path: Path) -> None:
    zip_path = tmp_path / "resources.zip"
    _write_zip(zip_path, members={"a.txt": b"a", "b.txt": b"b", "c.txt": b"c"})

    with pytest.raises(ResourcesZipError) as exc_info:
        extract_resources_zip(
            zip_path=zip_path,
            output_dir=tmp_path / "out",
            max_members=2,
            max_total_uncompressed_bytes=1024,
            max_member_uncompressed_bytes=1024,
        )

    assert exc_info.value.code == RESOURCES_ZIP_TOO_MANY_MEMBERS


def test_rejects_excessive_total_uncompressed_bytes(tmp_path: Path) -> None:
    zip_path = tmp_path / "resources.zip"
    _write_zip(zip_path, members={"a.txt": b"123456", "b.txt": b"123456"})

    with pytest.raises(ResourcesZipError) as exc_info:
        extract_resources_zip(
            zip_path=zip_path,
            output_dir=tmp_path / "out",
            max_members=10,
            max_total_uncompressed_bytes=10,
            max_member_uncompressed_bytes=10,
        )

    assert exc_info.value.code == RESOURCES_ZIP_TOTAL_TOO_LARGE


def test_rejects_excessive_single_member_uncompressed_bytes(tmp_path: Path) -> None:
    zip_path = tmp_path / "resources.zip"
    _write_zip(zip_path, members={"big.bin": b"01234567890"})

    with pytest.raises(ResourcesZipError) as exc_info:
        extract_resources_zip(
            zip_path=zip_path,
            output_dir=tmp_path / "out",
            max_members=10,
            max_total_uncompressed_bytes=1024,
            max_member_uncompressed_bytes=10,
        )

    assert exc_info.value.code == RESOURCES_ZIP_MEMBER_TOO_LARGE


def test_extracts_small_zip_successfully(tmp_path: Path) -> None:
    zip_path = tmp_path / "resources.zip"
    _write_zip(
        zip_path,
        members={
            "assets/style.css": b"body { font-family: serif; }\n",
            "img/logo.png": b"\x89PNG\r\n\x1a\nfake",
        },
    )

    output_dir = tmp_path / "out"
    extract_resources_zip(
        zip_path=zip_path,
        output_dir=output_dir,
        max_members=10,
        max_total_uncompressed_bytes=1024,
        max_member_uncompressed_bytes=1024,
    )

    css_path = output_dir / "assets" / "style.css"
    image_path = output_dir / "img" / "logo.png"
    assert css_path.exists()
    assert image_path.exists()
    assert css_path.read_bytes() == b"body { font-family: serif; }\n"
    assert image_path.read_bytes().startswith(b"\x89PNG")
