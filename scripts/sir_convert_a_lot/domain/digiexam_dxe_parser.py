"""DigiExam `.dxe` source parser and result-answer enrichment rules.

Purpose:
    Parse DigiExam `.dxe` JSON exports into the shared DigiExam parser contract
    and optionally enrich machine-marked answer keys from sanitized graded
    result-PDF text evidence.

Relationships:
    - Uses `domain.digiexam_contracts` for renderer-neutral parser output.
    - Complements the legacy PDF fallback parser in `domain.digiexam_parser`.
    - Consumes page-aware result-PDF lines from `infrastructure.digiexam_pdf_text`
      without depending on PyMuPDF or renderer/import concerns.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAlternative,
    DigiExamAnswerKeyProvenance,
    DigiExamDocumentMetadata,
    DigiExamGap,
    DigiExamGradingPolicy,
    DigiExamItem,
    DigiExamItemType,
    DigiExamParseResult,
    DigiExamParseStatus,
    DigiExamPointMarker,
    DigiExamSourceSpan,
    DigiExamWarning,
    DigiExamWarningCode,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_answer_enrichment import (
    dxe_gap_answers,
    match_result_pdf_answers,
)
from scripts.sir_convert_a_lot.domain.digiexam_embedded_assets import (
    extract_digiexam_embedded_assets,
)
from scripts.sir_convert_a_lot.domain.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
)


@dataclass(frozen=True)
class _QuestionParse:
    item: DigiExamItem
    warnings: tuple[DigiExamWarning, ...]


_DXE_ITEM_TYPES: dict[int, DigiExamItemType] = {
    0: DigiExamItemType.OPEN_ENDED,
    1: DigiExamItemType.SINGLE_CHOICE,
    2: DigiExamItemType.MULTIPLE_RESPONSE,
    3: DigiExamItemType.GAP_FILL,
}


class DigiExamDxeParser:
    """Parse DigiExam `.dxe` JSON exports into renderer-neutral domain items."""

    def parse_file(
        self,
        path: Path,
        *,
        answer_evidence: DigiExamResultPdfAnswerEvidence | None = None,
    ) -> DigiExamParseResult:
        """Parse a `.dxe` file from disk."""

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return _blocked_parse(path.name, f"Could not read `.dxe` file: {exc}")
        return self.parse_text(text, filename=path.name, answer_evidence=answer_evidence)

    def parse_text(
        self,
        text: str,
        *,
        filename: str,
        answer_evidence: DigiExamResultPdfAnswerEvidence | None = None,
    ) -> DigiExamParseResult:
        """Parse `.dxe` JSON text without raising untyped JSON or shape errors."""

        try:
            payload: object = json.loads(text)
        except JSONDecodeError as exc:
            return _blocked_parse(filename, f"Invalid `.dxe` JSON: {exc.msg}")
        return self.parse_payload(payload, filename=filename, answer_evidence=answer_evidence)

    def parse_payload(
        self,
        payload: object,
        *,
        filename: str,
        answer_evidence: DigiExamResultPdfAnswerEvidence | None = None,
    ) -> DigiExamParseResult:
        """Parse a decoded `.dxe` JSON payload into the shared parser result."""

        warnings: list[DigiExamWarning] = []
        root = _mapping(payload)
        if root is None:
            return _blocked_parse(filename, "Top-level `.dxe` payload must be a JSON object.")

        exams = _sequence(root.get("exams"))
        if exams is None or not exams:
            return _blocked_parse(filename, "Top-level `.dxe` payload must contain exams.")

        exam = _mapping(exams[0])
        if exam is None:
            return _blocked_parse(filename, "First `.dxe` exam entry must be a JSON object.")

        questions = _sequence(exam.get("questions"))
        if questions is None:
            return _blocked_parse(filename, "DigiExam exam must contain a questions array.")

        items: list[DigiExamItem] = []
        for index, question_value in enumerate(questions, start=1):
            question = _mapping(question_value)
            if question is None:
                warnings.append(
                    _warning(
                        f"Question {index} must be a JSON object.",
                        blocking=True,
                        source_span=_json_span(index),
                    )
                )
                continue
            parsed = self._parse_question(index, question, answer_evidence)
            items.append(parsed.item)
            warnings.extend(parsed.warnings)

        blocking = any(warning.blocking for warning in warnings)
        status = DigiExamParseStatus.BLOCKED if blocking else DigiExamParseStatus.SUCCESS
        return DigiExamParseResult(
            metadata=DigiExamDocumentMetadata(
                filename=filename,
                page_count=0,
                producer="DigiExam .dxe",
            ),
            status=status,
            renderer_ready=status == DigiExamParseStatus.SUCCESS,
            items=tuple(items),
            warnings=tuple(warnings),
        )

    def _parse_question(
        self,
        index: int,
        question: Mapping[str, object],
        answer_evidence: DigiExamResultPdfAnswerEvidence | None,
    ) -> _QuestionParse:
        warnings: list[DigiExamWarning] = []
        span = _json_span(index)
        question_id = _int_value(question.get("id"))
        title = _str_value(question.get("title"))
        about = _str_value(question.get("about"))
        prompt_html = _str_value(question.get("bodyHTML"))
        max_score = _int_value(question.get("maxScore"))
        type_code = _int_value(question.get("type"))

        if title is None or prompt_html is None or max_score is None or type_code is None:
            warnings.append(
                _warning(
                    f"Question {index} is missing required `.dxe` fields.",
                    blocking=True,
                    source_span=span,
                )
            )

        item_type = (
            _DXE_ITEM_TYPES.get(type_code, DigiExamItemType.UNKNOWN)
            if type_code is not None
            else DigiExamItemType.UNKNOWN
        )
        if item_type == DigiExamItemType.UNKNOWN:
            warnings.append(
                DigiExamWarning(
                    code=DigiExamWarningCode.UNKNOWN_SOURCE_SHAPE,
                    message=f"Unsupported DigiExam question type code {type_code}.",
                    blocking=True,
                    source_span=span,
                )
            )

        alternatives, alternative_warnings = _alternatives(question.get("alternatives"), span)
        gaps, gap_warnings = _gaps(question.get("blanks"), span)
        warnings.extend(alternative_warnings)
        warnings.extend(gap_warnings)
        embedded_assets = extract_digiexam_embedded_assets(
            image_values=question.get("images"),
            prompt_html=prompt_html,
            item_sequence=index,
            source_span=span,
        )
        warnings.extend(embedded_assets.warnings)

        evidence_item = answer_evidence.item_for_title(title) if answer_evidence and title else None
        dxe_correct_alternative_ids = tuple(
            alternative.id for alternative in alternatives if alternative.right
        )
        dxe_gap_values = tuple(
            validation for gap in gaps for validation in gap.validations if validation
        )
        result_answer_match = match_result_pdf_answers(
            alternatives=alternatives,
            gaps=gaps,
            evidence_item=evidence_item,
            source_span=span,
        )
        warnings.extend(result_answer_match.warnings)
        result_gap_values = tuple(
            answer.value for answer in result_answer_match.correct_gap_answers
        )

        correct_alternative_ids = (
            dxe_correct_alternative_ids
            if dxe_correct_alternative_ids
            else result_answer_match.correct_alternative_ids
        )
        correct_gap_values = dxe_gap_values if dxe_gap_values else result_gap_values
        correct_gap_answers = (
            dxe_gap_answers(gaps) if dxe_gap_values else result_answer_match.correct_gap_answers
        )
        provenance = _answer_key_provenance(
            item_type=item_type,
            dxe_correct_alternative_ids=dxe_correct_alternative_ids,
            dxe_gap_values=dxe_gap_values,
            result_correct_alternative_ids=result_answer_match.correct_alternative_ids,
            result_gap_values=result_gap_values,
        )
        if provenance == DigiExamAnswerKeyProvenance.ABSENT:
            warning_title = title or f"question {index}"
            warnings.append(
                DigiExamWarning(
                    code=DigiExamWarningCode.MISSING_ANSWER_KEY_PROVENANCE,
                    message=f"Answer key provenance is absent for '{warning_title}'.",
                    blocking=False,
                    source_span=span,
                )
            )

        item = DigiExamItem(
            header=title or f"Question {index}",
            item_type=item_type,
            source_span=span,
            prompt_lines=(about,) if about else (),
            point_marker=(
                DigiExamPointMarker(
                    points=max_score, raw_text=f"maxScore: {max_score}", source_span=span
                )
                if max_score is not None
                else None
            ),
            options=tuple(alternative.title for alternative in alternatives),
            answer_key_provenance=provenance,
            warnings=tuple(warnings),
            question_id=question_id,
            digiexam_type_code=type_code,
            prompt_html=prompt_html,
            max_score=max_score,
            alternatives=alternatives,
            gaps=gaps,
            grading_policy=_grading_policy(question),
            correct_alternative_ids=correct_alternative_ids,
            correct_gap_values=correct_gap_values,
            correct_gap_answers=correct_gap_answers,
            embedded_assets=embedded_assets.assets,
            embedded_asset_references=embedded_assets.references,
        )
        return _QuestionParse(item=item, warnings=tuple(warnings))


def _blocked_parse(filename: str, message: str) -> DigiExamParseResult:
    return DigiExamParseResult(
        metadata=DigiExamDocumentMetadata(filename=filename, page_count=0, producer=None),
        status=DigiExamParseStatus.BLOCKED,
        renderer_ready=False,
        items=(),
        warnings=(
            DigiExamWarning(
                code=DigiExamWarningCode.MALFORMED_SOURCE,
                message=message,
                blocking=True,
            ),
        ),
    )


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    normalized: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        normalized[key] = item
    return normalized


def _sequence(value: object) -> tuple[object, ...] | None:
    if isinstance(value, str) or not isinstance(value, Sequence):
        return None
    return tuple(value)


def _str_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _bool_value(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _alternatives(
    value: object, source_span: DigiExamSourceSpan
) -> tuple[tuple[DigiExamAlternative, ...], tuple[DigiExamWarning, ...]]:
    if value is None:
        return (), ()
    alternative_values = _sequence(value)
    if alternative_values is None:
        return (), (_warning("DigiExam alternatives must be an array.", True, source_span),)

    alternatives: list[DigiExamAlternative] = []
    warnings: list[DigiExamWarning] = []
    for index, raw_alternative in enumerate(alternative_values, start=1):
        alternative = _mapping(raw_alternative)
        if alternative is None:
            warnings.append(
                _warning(f"Alternative {index} must be a JSON object.", True, source_span)
            )
            continue
        alternative_id = _int_value(alternative.get("id"))
        title = _str_value(alternative.get("title"))
        about = _str_value(alternative.get("about")) or ""
        right = _bool_value(alternative.get("right"))
        if alternative_id is None or title is None or right is None:
            warnings.append(
                _warning(f"Alternative {index} is missing required fields.", True, source_span)
            )
            continue
        alternatives.append(
            DigiExamAlternative(id=alternative_id, title=title, about=about, right=right)
        )
    return tuple(alternatives), tuple(warnings)


def _gaps(
    value: object, source_span: DigiExamSourceSpan
) -> tuple[tuple[DigiExamGap, ...], tuple[DigiExamWarning, ...]]:
    if value is None:
        return (), ()
    gap_values = _sequence(value)
    if gap_values is None:
        return (), (_warning("DigiExam blanks must be an array.", True, source_span),)

    gaps: list[DigiExamGap] = []
    warnings: list[DigiExamWarning] = []
    for index, raw_gap in enumerate(gap_values, start=1):
        gap = _mapping(raw_gap)
        if gap is None:
            warnings.append(_warning(f"Blank {index} must be a JSON object.", True, source_span))
            continue
        guid = _str_value(gap.get("guid"))
        validations = _validations(gap.get("validations"))
        if guid is None or validations is None:
            warnings.append(
                _warning(f"Blank {index} is missing required fields.", True, source_span)
            )
            continue
        gaps.append(DigiExamGap(guid=guid, validations=validations))
    return tuple(gaps), tuple(warnings)


def _validations(value: object) -> tuple[str, ...] | None:
    validation_values = _sequence(value)
    if validation_values is None:
        return None
    validations: list[str] = []
    for validation in validation_values:
        if not isinstance(validation, str):
            return None
        validations.append(validation)
    return tuple(validations)


def _grading_policy(question: Mapping[str, object]) -> DigiExamGradingPolicy | None:
    grading_type = _int_value(question.get("gradingType"))
    choice_limit_enabled = _bool_value(question.get("isAlternativeChoiceLimitEnabled"))
    choice_limit = _int_value(question.get("alternativeChoiceLimit"))
    if grading_type is None and choice_limit_enabled is None and choice_limit is None:
        return None
    return DigiExamGradingPolicy(
        grading_type=grading_type,
        is_alternative_choice_limit_enabled=choice_limit_enabled,
        alternative_choice_limit=choice_limit,
    )


def _answer_key_provenance(
    *,
    item_type: DigiExamItemType,
    dxe_correct_alternative_ids: tuple[int, ...],
    dxe_gap_values: tuple[str, ...],
    result_correct_alternative_ids: tuple[int, ...],
    result_gap_values: tuple[str, ...],
) -> DigiExamAnswerKeyProvenance:
    if item_type == DigiExamItemType.OPEN_ENDED:
        return DigiExamAnswerKeyProvenance.NOT_APPLICABLE
    if dxe_correct_alternative_ids or dxe_gap_values:
        return DigiExamAnswerKeyProvenance.DXE_POPULATED_KEY
    if result_correct_alternative_ids or result_gap_values:
        return DigiExamAnswerKeyProvenance.GRADED_RESULT_PDF_CORRECT_LABELS
    if item_type in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
    }:
        return DigiExamAnswerKeyProvenance.ABSENT
    return DigiExamAnswerKeyProvenance.NOT_APPLICABLE


def _warning(
    message: str,
    blocking: bool,
    source_span: DigiExamSourceSpan | None = None,
) -> DigiExamWarning:
    return DigiExamWarning(
        code=DigiExamWarningCode.MALFORMED_SOURCE,
        message=message,
        blocking=blocking,
        source_span=source_span,
    )


def _json_span(index: int) -> DigiExamSourceSpan:
    return DigiExamSourceSpan(start_page=0, start_line=index, end_page=0, end_line=index)
