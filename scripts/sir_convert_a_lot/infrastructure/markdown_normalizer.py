"""Deterministic markdown normalization for Sir Convert-a-Lot conversions.

Purpose:
    Provide stable markdown normalization modes (`none`, `standard`, `strict`)
    aligned with the v1 conversion contract.

Relationships:
    - Used by `infrastructure.runtime_engine` after backend conversion.
    - Normalization semantics are documented in `docs/converters/pdf_to_md_service_api_v1.md`.
"""

from __future__ import annotations

import re
import textwrap

from scripts.sir_convert_a_lot.domain.specs import NormalizeMode

_BLANKS_RE = re.compile(r"\n{3,}")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_LIST_RE = re.compile(r"^\s{0,3}([-*+]\s+|\d+[.)]\s+)")
_BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>")
_HR_RE = re.compile(r"^\s{0,3}((\*\s*){3,}|(-\s*){3,}|(_\s*){3,})$")
_TABLE_RULE_RE = re.compile(r"^\s*\|?[\s:-]+\|[\s|:-]*$")


def normalize_markdown(markdown_content: str, mode: NormalizeMode) -> str:
    """Normalize markdown content based on v1 `conversion.normalize` semantics."""
    if mode == NormalizeMode.NONE:
        return markdown_content
    normalized = _normalize_common(markdown_content)
    if mode == NormalizeMode.STANDARD:
        return normalized
    if mode == NormalizeMode.STRICT:
        return _strict_reflow(normalized)
    return normalized


def _normalize_common(markdown_content: str) -> str:
    text = markdown_content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _BLANKS_RE.sub("\n\n", text)
    stripped = text.strip("\n")
    if stripped == "":
        return ""
    return stripped + "\n"


def _strict_reflow(markdown_content: str) -> str:
    lines = markdown_content.split("\n")
    output_lines: list[str] = []
    paragraph_lines: list[str] = []
    in_fence = False

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        joined = " ".join(part.strip() for part in paragraph_lines if part.strip() != "")
        paragraph_lines.clear()
        if joined == "":
            return
        wrapped = textwrap.fill(
            joined,
            width=100,
            break_long_words=False,
            break_on_hyphens=False,
        )
        output_lines.extend(wrapped.split("\n"))

    for line in lines:
        stripped = line.strip()
        if _is_fence(line):
            flush_paragraph()
            output_lines.append(line)
            in_fence = not in_fence
            continue

        if in_fence:
            output_lines.append(line)
            continue

        if stripped == "":
            flush_paragraph()
            if output_lines and output_lines[-1] != "":
                output_lines.append("")
            continue

        if _is_protected_line(line):
            flush_paragraph()
            output_lines.append(line)
            continue

        paragraph_lines.append(line)

    flush_paragraph()

    collapsed: list[str] = []
    for line in output_lines:
        if line == "" and collapsed and collapsed[-1] == "":
            continue
        collapsed.append(line)

    final_text = "\n".join(collapsed).strip("\n")
    if final_text == "":
        return ""
    return final_text + "\n"


def _is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("|"):
        return True
    if "|" in stripped and (_TABLE_RULE_RE.match(stripped) is not None):
        return True
    return False


def _is_protected_line(line: str) -> bool:
    stripped = line.strip()
    if _is_table_line(line):
        return True
    if _HEADING_RE.match(line) is not None:
        return True
    if _LIST_RE.match(line) is not None:
        return True
    if _BLOCKQUOTE_RE.match(line) is not None:
        return True
    if _HR_RE.match(stripped) is not None:
        return True
    return False
