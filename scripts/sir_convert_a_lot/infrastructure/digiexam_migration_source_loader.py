"""DigiExam migration source loading for target rendering.

Purpose:
    Load the original DigiExam source and optional graded-result evidence for
    both first-pass migration bundles and correction replay artifact rendering.

Relationships:
    - Used by `infrastructure.digiexam_migration_bundle_builder` before writing
      terminal migration bundles.
    - Used by correction replay artifact rendering to rebuild source IR with
      the same parser and result-PDF evidence semantics as the original job.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamParseResult
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
    DigiExamResultPdfAnswerExtractor,
    normalize_result_text,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_job_companion_paths_v2 import (
    graded_result_pdf_path_for_upload,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    json_bytes,
    json_ready,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_pdf_text import DigiExamPdfTextExtractor
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


@dataclass(frozen=True)
class DigiExamMigrationSourceExam:
    """Loaded DigiExam source state and deterministic source digests."""

    exam: DigiExamIntermediateExam
    parse_result: DigiExamParseResult
    source_file_sha256: str
    source_ir_sha256: str


def load_digiexam_migration_source_exam(job: StoredJobV2) -> DigiExamMigrationSourceExam:
    """Parse one DigiExam job source with the governed result-PDF evidence path."""

    source_bytes = job.upload_path.read_bytes()
    answer_evidence = _answer_evidence_for_job(job)
    parse_result = DigiExamDxeParser().parse_file(job.upload_path, answer_evidence=answer_evidence)
    exam = build_digiexam_intermediate_exam(parse_result)
    return DigiExamMigrationSourceExam(
        exam=exam,
        parse_result=parse_result,
        source_file_sha256=f"sha256:{hashlib.sha256(source_bytes).hexdigest()}",
        source_ir_sha256=_source_ir_sha256(exam),
    )


def _source_ir_sha256(exam: DigiExamIntermediateExam) -> str:
    payload = json_bytes(json_ready(asdict(exam)))
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _answer_evidence_for_job(job: StoredJobV2) -> DigiExamResultPdfAnswerEvidence | None:
    result_pdf_path = graded_result_pdf_path_for_upload(job.upload_path)
    if not result_pdf_path.exists():
        return None
    _, lines = DigiExamPdfTextExtractor().extract(result_pdf_path)
    delimiter = _infer_student_block_delimiter(tuple(line.text for line in lines))
    if delimiter is None:
        raise ServiceError(
            status_code=422,
            code="digiexam_result_pdf_unsafe_evidence",
            message="Sanitized graded-result PDF evidence could not be classified safely.",
            retryable=False,
        )
    return DigiExamResultPdfAnswerExtractor(student_block_delimiter=delimiter).extract(lines)


def _infer_student_block_delimiter(lines: tuple[str, ...]) -> str | None:
    counts: dict[str, int] = {}
    for line in lines:
        normalized = normalize_result_text(line)
        if normalized == "" or _looks_like_result_content(normalized):
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
    repeated = tuple((value, count) for value, count in counts.items() if count >= 2)
    if not repeated:
        return None
    return sorted(repeated, key=lambda entry: (-entry[1], entry[0]))[0][0]


def _looks_like_result_content(value: str) -> bool:
    markers = ("Svar", "Erhållen poäng", "Korrekt", "Fel svar", "Max poäng")
    return any(marker in value for marker in markers)
