"""Pandoc-backed DOCX to Markdown conversion.

Purpose:
    Provide a local DOCX -> Markdown converter used by the v2 `docx -> md`
    route as a deterministic conversion stage before markdown normalization.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for DOCX-source routes.
    - Uses the local `pandoc` binary and maps failures to stable error codes.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import PANDOC_NOT_INSTALLED
from scripts.sir_convert_a_lot.infrastructure.pandoc_subprocess import run_pandoc_command

DOCX_TO_MARKDOWN_FAILED = "docx_to_markdown_failed"
DOCX_TO_MARKDOWN_EMPTY = "docx_to_markdown_empty"
DOCX_TO_MARKDOWN_UNREADABLE = "docx_to_markdown_unreadable"
DOCX_TO_MARKDOWN_TIMEOUT = "docx_to_markdown_timeout"
PANDOC_DEFAULT_TIMEOUT_SECONDS = 300

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_LIST_RE = re.compile(r"^\s{0,3}([-*+]\s+|\d+[.)]\s+)")
_BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>")
_HR_RE = re.compile(r"^\s{0,3}((\*\s*){3,}|(-\s*){3,}|(_\s*){3,})$")
_REFERENCE_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*\S+")
_FOOTNOTE_DEF_RE = re.compile(r"^\s{0,3}\[\^[^\]]+\]:\s*")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


@dataclass(frozen=True)
class DocxToMarkdownConversionError(Exception):
    """Typed, deterministic error for local DOCX->Markdown conversion failures."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial and stable
        return f"{self.code}: {self.message}"


def _looks_like_unreadable_docx(stderr: str) -> bool:
    lowered = stderr.lower()
    unreadable_markers = (
        "couldn't unpack docx container",
        "not a valid zip",
        "not a zip archive",
        "zip end of central directory",
        "docx container",
        "corrupt",
        "damaged",
    )
    return any(marker in lowered for marker in unreadable_markers)


def _is_protected_markdown_line(line: str) -> bool:
    """Return True for lines whose Markdown structure must remain untouched."""

    stripped = line.strip()
    if stripped == "":
        return True
    if _HEADING_RE.match(line) is not None:
        return True
    if _LIST_RE.match(line) is not None:
        return True
    if _BLOCKQUOTE_RE.match(line) is not None:
        return True
    if _HR_RE.match(stripped) is not None:
        return True
    if _REFERENCE_DEF_RE.match(line) is not None:
        return True
    if _FOOTNOTE_DEF_RE.match(line) is not None:
        return True
    if stripped.startswith(("```", "~~~")):
        return True
    if _TABLE_SEPARATOR_RE.match(stripped) is not None:
        return True
    if stripped.startswith("|"):
        return True
    return False


def _looks_like_exam_net_hard_break_block(lines: list[str]) -> bool:
    """Return True when a prose block matches Exam.net's DOCX hard-break pattern."""

    standalone_breaks = sum(1 for line in lines if line.strip() == "\\")
    content_lines_with_breaks = sum(
        1 for line in lines if line.strip() not in {"", "\\"} and line.rstrip().endswith("\\")
    )
    return standalone_breaks >= 1 and content_lines_with_breaks >= 2


def _repair_exam_net_hard_break_block(lines: list[str]) -> list[str]:
    """Restore paragraph blocks from Exam.net-style runs of hard-break lines."""

    if not _looks_like_exam_net_hard_break_block(lines):
        return lines

    repaired: list[str] = []
    paragraph_parts: list[str] = []
    break_count = 0

    def flush_paragraph(*, add_blank_line: bool) -> None:
        if not paragraph_parts:
            return
        repaired.append(" ".join(part for part in paragraph_parts if part).strip())
        paragraph_parts.clear()
        if add_blank_line:
            repaired.append("")

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped == "\\":
            break_count += 1
            continue

        has_trailing_break = raw_line.rstrip().endswith("\\")
        cleaned = raw_line.rstrip()
        if has_trailing_break:
            cleaned = cleaned[:-1].rstrip()

        if not paragraph_parts:
            paragraph_parts.append(cleaned)
        elif break_count >= 2:
            flush_paragraph(add_blank_line=True)
            paragraph_parts.append(cleaned)
        else:
            paragraph_parts.append(cleaned)

        break_count = 1 if has_trailing_break else 0

    flush_paragraph(add_blank_line=False)

    while repaired and repaired[-1] == "":
        repaired.pop()
    return repaired


def repair_exam_net_docx_markdown(markdown_content: str) -> str:
    """Repair Exam.net DOCX exports that encode paragraphs as repeated hard breaks."""

    lines = markdown_content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    repaired_lines: list[str] = []
    prose_block: list[str] = []

    def flush_block() -> None:
        if not prose_block:
            return
        repaired_lines.extend(_repair_exam_net_hard_break_block(prose_block))
        prose_block.clear()

    for line in lines:
        if _is_protected_markdown_line(line):
            flush_block()
            repaired_lines.append(line)
            continue
        prose_block.append(line)

    flush_block()
    return "\n".join(repaired_lines).rstrip("\n") + "\n"


def convert_docx_to_markdown(
    *,
    docx_path: Path,
    output_markdown_path: Path,
    timeout_seconds: int = PANDOC_DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Convert DOCX to Markdown using the local `pandoc` binary."""

    pandoc_bin = shutil.which("pandoc")
    if pandoc_bin is None:
        raise DocxToMarkdownConversionError(
            code=PANDOC_NOT_INSTALLED,
            message="Pandoc is not installed. Install the `pandoc` binary.",
        )

    output_markdown_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        pandoc_bin,
        "--sandbox",
        docx_path.as_posix(),
        "--from=docx",
        "--to=gfm",
        "--wrap=none",
        "-o",
        output_markdown_path.as_posix(),
    ]

    try:
        return_code, stderr = run_pandoc_command(
            command=command,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise DocxToMarkdownConversionError(
            code=DOCX_TO_MARKDOWN_TIMEOUT,
            message=f"Pandoc timed out after {timeout_seconds} seconds.",
        ) from exc
    except OSError as exc:
        raise DocxToMarkdownConversionError(
            code=DOCX_TO_MARKDOWN_FAILED,
            message=f"Failed to run pandoc: {exc}",
        ) from exc

    if return_code != 0:
        detail = f": {stderr}" if stderr else ""
        code = (
            DOCX_TO_MARKDOWN_UNREADABLE
            if _looks_like_unreadable_docx(stderr)
            else DOCX_TO_MARKDOWN_FAILED
        )
        raise DocxToMarkdownConversionError(
            code=code,
            message=f"Pandoc failed with exit code {return_code}{detail}",
        )

    if not output_markdown_path.exists() or output_markdown_path.stat().st_size == 0:
        raise DocxToMarkdownConversionError(
            code=DOCX_TO_MARKDOWN_EMPTY,
            message=f"Pandoc produced an empty Markdown file: {output_markdown_path}",
        )

    repaired_markdown = repair_exam_net_docx_markdown(
        output_markdown_path.read_text(encoding="utf-8")
    )
    output_markdown_path.write_text(repaired_markdown, encoding="utf-8")
