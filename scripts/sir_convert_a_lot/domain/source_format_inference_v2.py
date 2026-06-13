"""Service API v2 filename source-format inference.

Purpose:
    Map uploaded filenames to broad v2 source formats before route-specific
    create-job admission runs.

Relationships:
    - Used by the v2 HTTP create-job route registry.
    - Keeps extension taxonomy out of the already busy HTTP route module.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs_v2 import SourceFormatV2

_AUDIO_SOURCE_SUFFIXES_V2 = frozenset(
    {
        ".aac",
        ".aiff",
        ".flac",
        ".m4a",
        ".mkv",
        ".mov",
        ".mp3",
        ".mp4",
        ".ogg",
        ".opus",
        ".wav",
        ".webm",
    }
)


def infer_source_format_from_filename_v2(filename: str) -> SourceFormatV2 | None:
    """Infer the broad v2 source format from an uploaded filename."""

    suffix = Path(filename).suffix.lower()
    if suffix in _AUDIO_SOURCE_SUFFIXES_V2:
        return SourceFormatV2.AUDIO
    if suffix == ".json":
        return SourceFormatV2.TRANSCRIPT_JSON
    if suffix == ".pdf":
        return SourceFormatV2.PDF
    if suffix in {".md", ".markdown"}:
        return SourceFormatV2.MD
    if suffix in {".html", ".htm"}:
        return SourceFormatV2.HTML
    if suffix == ".docx":
        return SourceFormatV2.DOCX
    if suffix == ".dxe":
        return SourceFormatV2.DIGIEXAM_DXE
    return None
