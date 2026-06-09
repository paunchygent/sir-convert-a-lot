"""PyMuPDF text extraction adapter for DigiExam parser v1.

Purpose:
    Convert a DigiExam PDF fixture into page-aware text lines consumed by the
    pure domain parser without coupling parser rules to PyMuPDF.

Relationships:
    - Uses the existing PyMuPDF dependency already owned by Sir Convert PDF
      infrastructure.
    - Feeds `domain.digiexam_parser.DigiExamParser` for DigiExam parser fixture tests.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamDocumentMetadata,
    DigiExamSourceLine,
)


class DigiExamPdfTextExtractor:
    """Extract page-aware plain text lines from a DigiExam PDF export."""

    def extract(
        self, path: Path
    ) -> tuple[DigiExamDocumentMetadata, tuple[DigiExamSourceLine, ...]]:
        lines: list[DigiExamSourceLine] = []
        with pymupdf.open(path) as document:
            metadata = DigiExamDocumentMetadata(
                filename=path.name,
                page_count=document.page_count,
                producer=document.metadata.get("producer"),
            )
            for page_index, page in enumerate(document, start=1):
                page_text = str(page.get_text("text", sort=True))
                for line_index, text in enumerate(page_text.splitlines(), start=1):
                    lines.append(
                        DigiExamSourceLine(
                            page_number=page_index,
                            line_number=line_index,
                            text=text,
                        )
                    )
        return metadata, tuple(lines)
