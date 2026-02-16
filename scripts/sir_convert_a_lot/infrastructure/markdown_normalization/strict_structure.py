"""Structural post-processing for strict markdown normalization.

Purpose:
    Apply deterministic structural corrections after strict prose reflow,
    including pagination cleanup, exam MCQ ordering repairs, and references
    numbering normalization.

Relationships:
    - Called by `markdown_normalization.strict_reflow.strict_reflow`.
    - Implements target-specific hardening from Task 25 while remaining
      section-scoped and fail-safe.
"""

from __future__ import annotations

import re

_STANDALONE_PAGE_NUMBER_RE = re.compile(r"^\s*\d{1,6}\s*$")
_PAGINATION_NUMERIC_LINES_THRESHOLD = 20

_MCQ_OPTION_LINE_RE = re.compile(r"^\s*-\s+\[\s\]\s+")
_MCQ_TRAILING_NUMBER_LINE_RE = re.compile(r"^\s*-\s*(?P<body>.+?)\s+(?P<number>\d{1,3})\.\s*$")
_MCQ_STANDALONE_NUMBER_LINE_RE = re.compile(r"^\s*-\s*(?P<number>\d{1,3})\.\s*$")
_MCQ_PLAIN_STANDALONE_NUMBER_LINE_RE = re.compile(r"^\s*(?P<number>\d{1,3})\.\s*$")
_MCQ_BULLET_LEADING_NUMBER_LINE_RE = re.compile(r"^\s*-\s*(?P<content>\d{1,3}\.\s+.+)$")
_MCQ_LEADING_NUMBER_LINE_RE = re.compile(r"^\s*(?:-\s*)?(?P<number>\d{1,3})\.\s+.+$")

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_REFERENCES_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+references\b", re.IGNORECASE)
_NUMBERED_REFERENCE_LINE_RE = re.compile(r"^\s*(?P<number>\d{1,4})\.\s+.+$")


def normalize_structural_blocks(lines: list[str]) -> list[str]:
    """Return strict-mode structural normalization over already reflowed lines."""
    processed = _strip_pagination_noise(lines)

    collapsed: list[str] = []
    for line in processed:
        if line == "" and collapsed and collapsed[-1] == "":
            continue
        collapsed.append(line)

    collapsed = _normalize_exam_mcq_blocks(collapsed)
    collapsed = _normalize_references_section_numbering(collapsed)
    return collapsed


def _strip_pagination_noise(lines: list[str]) -> list[str]:
    """Drop long standalone page-number blocks from strict-normalized output."""
    if not lines:
        return lines
    cleaned: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not _STANDALONE_PAGE_NUMBER_RE.match(line):
            cleaned.append(line)
            index += 1
            continue

        block_start = index
        numeric_line_count = 0
        while index < len(lines):
            block_line = lines[index]
            if _STANDALONE_PAGE_NUMBER_RE.match(block_line):
                numeric_line_count += 1
                index += 1
                continue
            if block_line.strip() == "":
                index += 1
                continue
            break

        if numeric_line_count >= _PAGINATION_NUMERIC_LINES_THRESHOLD:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue

        cleaned.extend(lines[block_start:index])
    return cleaned


def _normalize_exam_mcq_blocks(lines: list[str]) -> list[str]:
    """Reorder OCR/extraction-drifted MCQ blocks for exam-style forms."""
    if not any(_MCQ_OPTION_LINE_RE.match(line) is not None for line in lines):
        return lines

    normalized: list[str] = []
    index = 0
    total = len(lines)
    while index < total:
        line = lines[index]
        if _MCQ_OPTION_LINE_RE.match(line) is None:
            normalized.append(line)
            index += 1
            continue

        option_block: list[str] = []
        while index < total:
            option_line = lines[index]
            if _MCQ_OPTION_LINE_RE.match(option_line) is not None or option_line.strip() == "":
                option_block.append(option_line)
                index += 1
                continue
            break

        prompt_block: list[str] = []
        while index < total and _MCQ_OPTION_LINE_RE.match(lines[index]) is None:
            prompt_block.append(lines[index])
            index += 1
            if index < total and _MCQ_OPTION_LINE_RE.match(lines[index]) is not None:
                break

        option_line_count = sum(
            1 for item in option_block if _MCQ_OPTION_LINE_RE.match(item) is not None
        )
        raw_prompt_block = list(prompt_block)
        prompt_block = [_normalize_mcq_prompt_line(line=item) for item in prompt_block]
        prompt_block = _coalesce_mcq_standalone_number_lines(prompt_block)
        if (
            option_line_count >= 3
            and _first_nonblank_line_has_mcq_question_number(prompt_block)
            and _has_misordered_mcq_prompt_signal(raw_prompt_block)
        ):
            normalized.extend(_trim_outer_blank_lines(prompt_block))
            if normalized and normalized[-1].strip() != "":
                normalized.append("")
            normalized.extend(_trim_outer_blank_lines(option_block))
            continue

        normalized.extend(option_block)
        normalized.extend(prompt_block)

    collapsed: list[str] = []
    for line in normalized:
        if line == "" and collapsed and collapsed[-1] == "":
            continue
        collapsed.append(line)
    return collapsed


def _normalize_mcq_prompt_line(*, line: str) -> str:
    if _MCQ_OPTION_LINE_RE.match(line) is not None:
        return line
    trailing_match = _MCQ_TRAILING_NUMBER_LINE_RE.match(line)
    if trailing_match is not None:
        number = trailing_match.group("number")
        body = trailing_match.group("body").strip()
        if body != "":
            return f"{number}. {body}"
    standalone_match = _MCQ_STANDALONE_NUMBER_LINE_RE.match(line)
    if standalone_match is not None:
        return f"{standalone_match.group('number')}."
    leading_bullet_match = _MCQ_BULLET_LEADING_NUMBER_LINE_RE.match(line)
    if leading_bullet_match is not None:
        return leading_bullet_match.group("content")
    return line


def _first_nonblank_line(lines: list[str]) -> str | None:
    for line in lines:
        if line.strip() != "":
            return line
    return None


def _first_nonblank_line_has_mcq_question_number(lines: list[str]) -> bool:
    first = _first_nonblank_line(lines)
    if first is None:
        return False
    return _extract_mcq_question_number(first) is not None


def _has_misordered_mcq_prompt_signal(raw_prompt_block: list[str]) -> bool:
    """Return true when prompt lines match a high-signal misordered MCQ pattern."""
    first_nonblank_index: int | None = None
    for index, line in enumerate(raw_prompt_block):
        if line.strip() != "":
            first_nonblank_index = index
            break

    if first_nonblank_index is None:
        return False

    first_line = raw_prompt_block[first_nonblank_index]
    if _MCQ_TRAILING_NUMBER_LINE_RE.match(first_line) is not None:
        return True
    if _MCQ_BULLET_LEADING_NUMBER_LINE_RE.match(first_line) is not None:
        return True
    if _MCQ_STANDALONE_NUMBER_LINE_RE.match(first_line) is not None:
        return True

    if first_line.lstrip().startswith("- "):
        second_nonblank_index: int | None = None
        for index in range(first_nonblank_index + 1, len(raw_prompt_block)):
            if raw_prompt_block[index].strip() != "":
                second_nonblank_index = index
                break
        if (
            second_nonblank_index is not None
            and second_nonblank_index == first_nonblank_index + 1
            and _MCQ_STANDALONE_NUMBER_LINE_RE.match(raw_prompt_block[second_nonblank_index])
            is not None
        ):
            return True
    return False


def _extract_mcq_question_number(line: str) -> int | None:
    trailing_match = _MCQ_TRAILING_NUMBER_LINE_RE.match(line)
    if trailing_match is not None:
        return int(trailing_match.group("number"))
    standalone_match = _MCQ_STANDALONE_NUMBER_LINE_RE.match(line)
    if standalone_match is not None:
        return int(standalone_match.group("number"))
    plain_standalone_match = _MCQ_PLAIN_STANDALONE_NUMBER_LINE_RE.match(line)
    if plain_standalone_match is not None:
        return int(plain_standalone_match.group("number"))
    leading_match = _MCQ_LEADING_NUMBER_LINE_RE.match(line)
    if leading_match is not None:
        return int(leading_match.group("number"))
    return None


def _trim_outer_blank_lines(lines: list[str]) -> list[str]:
    if not lines:
        return lines
    start = 0
    end = len(lines)
    while start < end and lines[start].strip() == "":
        start += 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    return lines[start:end]


def _coalesce_mcq_standalone_number_lines(lines: list[str]) -> list[str]:
    if not lines:
        return lines
    merged: list[str] = []
    for line in lines:
        standalone_match = _MCQ_STANDALONE_NUMBER_LINE_RE.match(line)
        if standalone_match is None:
            standalone_match = _MCQ_PLAIN_STANDALONE_NUMBER_LINE_RE.match(line)
        if standalone_match is None:
            merged.append(line)
            continue
        if not merged:
            merged.append(line)
            continue
        previous_line = merged[-1]
        if previous_line.strip() == "":
            merged.append(line)
            continue
        if _extract_mcq_question_number(previous_line) is not None:
            merged.append(line)
            continue
        question_text = previous_line.lstrip()
        if question_text.startswith("- "):
            question_text = question_text[2:].strip()
        merged[-1] = f"{standalone_match.group('number')}. {question_text}"
    return merged


def _normalize_references_section_numbering(lines: list[str]) -> list[str]:
    """Sort scrambled numeric reference entries inside a References section only."""
    if not lines:
        return lines

    normalized = list(lines)
    index = 0
    while index < len(normalized):
        if _REFERENCES_HEADING_RE.match(normalized[index]) is None:
            index += 1
            continue

        section_start = index + 1
        section_end = section_start
        while section_end < len(normalized):
            line = normalized[section_end]
            if line.strip() != "" and _HEADING_RE.match(line) is not None:
                break
            section_end += 1

        numbered_indexes: list[int] = []
        numbered_lines: list[tuple[int, str]] = []
        for current in range(section_start, section_end):
            line = normalized[current]
            match = _NUMBERED_REFERENCE_LINE_RE.match(line)
            if match is None:
                if line.strip() == "":
                    continue
                break
            numbered_indexes.append(current)
            numbered_lines.append((int(match.group("number")), line))
        else:
            if len(numbered_lines) >= 4:
                numbers = [number for number, _ in numbered_lines]
                expected = list(range(min(numbers), max(numbers) + 1))
                if sorted(numbers) == expected and numbers != expected:
                    sorted_lines = [
                        line for _, line in sorted(numbered_lines, key=lambda item: item[0])
                    ]
                    for target, replacement in zip(numbered_indexes, sorted_lines, strict=True):
                        normalized[target] = replacement

        index = section_end

    return normalized
