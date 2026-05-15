"""DigiExam parser v1 domain contract and parsing rules.

Purpose:
    Parse layout-aware DigiExam PDF text lines into a typed item stream with
    source evidence, confidence status, and answer-key provenance.

Relationships:
    - Consumed by the Task 267 infrastructure PDF text adapter.
    - Intentionally independent of service routes, renderers, and bulk
      migration workflows so downstream Exam.net work can depend on a stable
      parser boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamDocumentMetadata,
    DigiExamItem,
    DigiExamItemType,
    DigiExamParseResult,
    DigiExamParseStatus,
    DigiExamPointMarker,
    DigiExamSourceLine,
    DigiExamSourceSpan,
    DigiExamWarning,
    DigiExamWarningCode,
)


@dataclass(frozen=True)
class _MultipleChoiceParts:
    prompt_lines: tuple[str, ...]
    options: tuple[str, ...]
    warnings: tuple[DigiExamWarning, ...]


_QUESTION_HEADER_RE = re.compile(r"^Fråga\s+\d+$")
_POINT_MARKER_RE = re.compile(r"^Max poäng\s*:\s*(?P<points>\d+)$")
_KNOWN_CHEMISTRY_HEADERS = frozenset(
    {
        "Materia",
        "Para ihop",
        "Grundämnen",
        "Atomen",
        "Ämnen",
        "Joner",
        "Emulsion",
        "Separera",
        "Reaktion",
        "Förklara",
        "Te",
        "Dela upp färg",
    }
)
_SWEDISH_SENTINELS = ("å", "ä", "ö", "Å", "Ä", "Ö")


class DigiExamParser:
    """Parse layout-aware DigiExam source lines into Task 267 domain results."""

    def parse(
        self,
        *,
        metadata: DigiExamDocumentMetadata,
        lines: tuple[DigiExamSourceLine, ...],
    ) -> DigiExamParseResult:
        non_empty_lines = tuple(line for line in lines if line.text.strip() != "")
        blocks, block_warnings = self._split_blocks(non_empty_lines)
        blocks = self._repair_page_boundary_option_spillover(blocks)
        items = tuple(self._parse_block(block) for block in blocks)
        warnings = block_warnings + self._document_warnings(non_empty_lines, items)
        for item in items:
            warnings = warnings + item.warnings

        blocking = any(warning.blocking for warning in warnings)
        status = DigiExamParseStatus.BLOCKED if blocking else DigiExamParseStatus.SUCCESS
        return DigiExamParseResult(
            metadata=metadata,
            status=status,
            renderer_ready=status == DigiExamParseStatus.SUCCESS,
            items=items,
            warnings=warnings,
        )

    def _split_blocks(
        self, lines: tuple[DigiExamSourceLine, ...]
    ) -> tuple[tuple[tuple[DigiExamSourceLine, ...], ...], tuple[DigiExamWarning, ...]]:
        blocks: list[tuple[DigiExamSourceLine, ...]] = []
        current: list[DigiExamSourceLine] = []
        warnings: list[DigiExamWarning] = []

        for line in lines:
            if self._is_header(line.text.strip()):
                if current:
                    blocks.append(tuple(current))
                current = [line]
                continue
            if not current:
                warnings.append(
                    DigiExamWarning(
                        code=DigiExamWarningCode.MISSING_REQUIRED_ANCHOR,
                        message="Text appeared before the first item header.",
                        blocking=True,
                        source_span=_line_span(line),
                    )
                )
                continue
            current.append(line)

        if current:
            blocks.append(tuple(current))
        if not blocks:
            warnings.append(
                DigiExamWarning(
                    code=DigiExamWarningCode.MISSING_REQUIRED_ANCHOR,
                    message="No DigiExam item headers were found.",
                    blocking=True,
                )
            )
        return tuple(blocks), tuple(warnings)

    def _repair_page_boundary_option_spillover(
        self, blocks: tuple[tuple[DigiExamSourceLine, ...], ...]
    ) -> tuple[tuple[DigiExamSourceLine, ...], ...]:
        adjusted: list[tuple[DigiExamSourceLine, ...]] = []
        for block in blocks:
            if not adjusted:
                adjusted.append(block)
                continue

            spillover = _pre_point_indented_lines(block)
            previous = adjusted[-1]
            if spillover and self._classify_block(previous[0].text.strip(), previous, None) == (
                DigiExamItemType.MULTIPLE_CHOICE
            ):
                adjusted[-1] = previous + spillover
                adjusted.append((block[0],) + block[1 + len(spillover) :])
                continue
            adjusted.append(block)
        return tuple(adjusted)

    def _parse_block(self, block: tuple[DigiExamSourceLine, ...]) -> DigiExamItem:
        header = block[0].text.strip()
        span = _block_span(block)
        point_marker = _point_marker_from_block(block)
        item_type = self._classify_block(header, block, point_marker)
        multiple_choice = (
            self._multiple_choice_parts(block, span)
            if item_type == DigiExamItemType.MULTIPLE_CHOICE
            else None
        )
        options = multiple_choice.options if multiple_choice is not None else ()
        warnings = self._item_warnings(header, item_type, span)
        if multiple_choice is not None:
            warnings = warnings + multiple_choice.warnings
        return DigiExamItem(
            header=header,
            item_type=item_type,
            source_span=span,
            prompt_lines=self._prompt_lines(block, point_marker, item_type, multiple_choice),
            point_marker=point_marker,
            options=options,
            answer_key_provenance=self._answer_key_provenance(item_type),
            warnings=warnings,
        )

    def _classify_block(
        self,
        header: str,
        block: tuple[DigiExamSourceLine, ...],
        point_marker: DigiExamPointMarker | None,
    ) -> DigiExamItemType:
        if point_marker is not None:
            return DigiExamItemType.OPEN_ENDED
        if self._has_multiple_choice_options(block):
            return DigiExamItemType.MULTIPLE_CHOICE
        return DigiExamItemType.UNKNOWN

    def _has_multiple_choice_options(self, block: tuple[DigiExamSourceLine, ...]) -> bool:
        option_like_lines = [
            line.text.strip()
            for line in block[1:]
            if line.text.strip() != ""
            and not _POINT_MARKER_RE.match(line.text.strip())
            and _is_indented(line.text)
        ]
        return len(option_like_lines) >= 3

    def _multiple_choice_parts(
        self, block: tuple[DigiExamSourceLine, ...], span: DigiExamSourceSpan
    ) -> _MultipleChoiceParts:
        prompt_lines: list[str] = []
        options: list[str] = []
        warnings: list[DigiExamWarning] = []
        seen_option = False

        for line in block[1:]:
            clean = _normalize_inline_space(line.text)
            if clean == "":
                continue
            if _is_indented(line.text):
                seen_option = True
                options.append(clean)
                continue
            if seen_option:
                warnings.append(
                    DigiExamWarning(
                        code=DigiExamWarningCode.UNSUPPORTED_STRUCTURE,
                        message=(
                            "Multiple-choice prompt text appears after option "
                            f"lines in '{block[0].text.strip()}'."
                        ),
                        blocking=True,
                        source_span=_line_span(line),
                    )
                )
                continue
            prompt_lines.append(clean)

        if not prompt_lines or len(options) < 2:
            warnings.append(
                DigiExamWarning(
                    code=DigiExamWarningCode.UNSUPPORTED_STRUCTURE,
                    message=f"Multiple-choice boundary is ambiguous for '{block[0].text.strip()}'.",
                    blocking=True,
                    source_span=span,
                )
            )

        return _MultipleChoiceParts(
            prompt_lines=tuple(prompt_lines),
            options=tuple(options),
            warnings=tuple(warnings),
        )

    def _options(self, block: tuple[DigiExamSourceLine, ...]) -> tuple[str, ...]:
        prompt_seen = False
        options: list[str] = []
        for line in block[1:]:
            clean = line.text.strip()
            if clean == "":
                continue
            if _POINT_MARKER_RE.match(clean):
                continue
            if not prompt_seen:
                prompt_seen = True
                continue
            options.append(_normalize_inline_space(clean))
        return tuple(options)

    def _prompt_lines(
        self,
        block: tuple[DigiExamSourceLine, ...],
        point_marker: DigiExamPointMarker | None,
        item_type: DigiExamItemType,
        multiple_choice: _MultipleChoiceParts | None,
    ) -> tuple[str, ...]:
        if multiple_choice is not None:
            return multiple_choice.prompt_lines

        lines: list[str] = []
        point_text = point_marker.raw_text if point_marker is not None else None
        for line in block[1:]:
            clean = _normalize_inline_space(line.text)
            if clean == "" or clean == point_text:
                continue
            lines.append(clean)
        return tuple(lines)

    def _item_warnings(
        self,
        header: str,
        item_type: DigiExamItemType,
        span: DigiExamSourceSpan,
    ) -> tuple[DigiExamWarning, ...]:
        warnings: list[DigiExamWarning] = []
        if item_type == DigiExamItemType.UNKNOWN:
            warnings.append(
                DigiExamWarning(
                    code=DigiExamWarningCode.UNKNOWN_SOURCE_SHAPE,
                    message=f"Item shape is unknown for header '{header}'.",
                    blocking=True,
                    source_span=span,
                )
            )
        if item_type == DigiExamItemType.MULTIPLE_CHOICE:
            warnings.append(
                DigiExamWarning(
                    code=DigiExamWarningCode.MISSING_ANSWER_KEY_PROVENANCE,
                    message=f"Answer key provenance is absent for '{header}'.",
                    blocking=False,
                    source_span=span,
                )
            )
        return tuple(warnings)

    def _document_warnings(
        self,
        lines: tuple[DigiExamSourceLine, ...],
        items: tuple[DigiExamItem, ...],
    ) -> tuple[DigiExamWarning, ...]:
        warnings: list[DigiExamWarning] = []
        combined_text = "\n".join(line.text for line in lines)
        if not any(sentinel in combined_text for sentinel in _SWEDISH_SENTINELS):
            warnings.append(
                DigiExamWarning(
                    code=DigiExamWarningCode.LOSSY_SWEDISH_TEXT_EXTRACTION,
                    message="No Swedish diacritics were found in extracted text.",
                    blocking=True,
                )
            )
        return tuple(warnings)

    def _answer_key_provenance(self, item_type: DigiExamItemType) -> DigiExamAnswerKeyProvenance:
        if item_type == DigiExamItemType.MULTIPLE_CHOICE:
            return DigiExamAnswerKeyProvenance.ABSENT
        return DigiExamAnswerKeyProvenance.NOT_APPLICABLE

    def _is_header(self, text: str) -> bool:
        return _QUESTION_HEADER_RE.match(text) is not None or text in _KNOWN_CHEMISTRY_HEADERS


def _point_marker_from_block(block: tuple[DigiExamSourceLine, ...]) -> DigiExamPointMarker | None:
    for line in block:
        clean = line.text.strip()
        match = _POINT_MARKER_RE.match(clean)
        if match is None:
            continue
        return DigiExamPointMarker(
            points=int(match.group("points")),
            raw_text=clean,
            source_span=_line_span(line),
        )
    return None


def _block_span(block: tuple[DigiExamSourceLine, ...]) -> DigiExamSourceSpan:
    return DigiExamSourceSpan(
        start_page=block[0].page_number,
        start_line=block[0].line_number,
        end_page=block[-1].page_number,
        end_line=block[-1].line_number,
    )


def _line_span(line: DigiExamSourceLine) -> DigiExamSourceSpan:
    return DigiExamSourceSpan(
        start_page=line.page_number,
        start_line=line.line_number,
        end_page=line.page_number,
        end_line=line.line_number,
    )


def _pre_point_indented_lines(
    block: tuple[DigiExamSourceLine, ...],
) -> tuple[DigiExamSourceLine, ...]:
    moved: list[DigiExamSourceLine] = []
    for line in block[1:]:
        clean = line.text.strip()
        if clean == "":
            continue
        if _POINT_MARKER_RE.match(clean):
            return tuple(moved)
        if not _is_indented(line.text):
            return ()
        moved.append(line)
    return ()


def _is_indented(value: str) -> bool:
    return value[:1].isspace()


def _normalize_inline_space(value: str) -> str:
    return " ".join(value.strip().split())
