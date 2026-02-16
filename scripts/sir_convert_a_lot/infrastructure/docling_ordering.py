"""Docling ordering patch and quality evaluation utilities.

Purpose:
    Provide deterministic source-level ordering hardening for Docling form-like
    PDFs and a structural quality report used by layout-model fallback logic.

Relationships:
    - Used by `infrastructure.docling_backend` during converter setup and
      source-level markdown candidate selection.
    - Complements strict normalization by moving question-order correction closer
      to extraction-time behavior.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Callable

from docling.datamodel.base_models import Cluster
from docling.utils.layout_postprocessor import LayoutPostprocessor
from docling_core.types.doc.labels import DocItemLabel
from docling_core.types.doc.page import TextCell

_FORM_CLUSTER_LABELS: frozenset[DocItemLabel] = frozenset(
    {
        DocItemLabel.FORM,
        DocItemLabel.KEY_VALUE_REGION,
        DocItemLabel.LIST_ITEM,
        DocItemLabel.CHECKBOX_SELECTED,
        DocItemLabel.CHECKBOX_UNSELECTED,
    }
)
_STANDALONE_NUMBER_RE = re.compile(r"^\d{1,3}\.$")
_OPTION_LINE_RE = re.compile(r"^\s*-\s+\[\s\]\s+")
_QUESTION_NUMBER_LINE_RE = re.compile(r"^\s*(\d{1,3})\.\s+")
_TRAILING_NUMBER_SIGNAL_RE = re.compile(r"^\s*-\s*.+\s+\d{1,3}\.\s*$")
_STANDALONE_BULLET_SIGNAL_RE = re.compile(r"^\s*-\s*\d{1,3}\.\s*$")

_PATCH_LOCK = threading.Lock()
_PATCH_INSTALLED = False
_ORIGINAL_SORT_CLUSTERS: Callable[..., list[Cluster]] | None = None
_ORIGINAL_SORT_CELLS: Callable[..., list[TextCell]] | None = None


@dataclass(frozen=True)
class OrderingQualityReport:
    """Structural ordering quality report for extracted markdown."""

    is_exam_like: bool
    option_line_count: int
    question_count: int
    min_question_number: int | None
    max_question_number: int | None
    missing_question_numbers: tuple[int, ...]
    trailing_number_signals: int
    standalone_number_signals: int
    option_before_question_signals: int

    @property
    def passes(self) -> bool:
        """Return True when report indicates acceptable question ordering."""
        if not self.is_exam_like:
            return True
        if self.trailing_number_signals > 0:
            return False
        if self.standalone_number_signals > 0:
            return False
        if self.option_before_question_signals > 0:
            return False
        if self.question_count >= 6 and len(self.missing_question_numbers) > 0:
            return False
        return True

    @property
    def penalty(self) -> int:
        """Return deterministic severity score for candidate ranking."""
        return (
            len(self.missing_question_numbers) * 20
            + self.trailing_number_signals * 25
            + self.standalone_number_signals * 25
            + self.option_before_question_signals * 30
        )


def install_docling_form_ordering_patch() -> bool:
    """Install idempotent runtime patch for Docling form-ordering behavior."""
    global _PATCH_INSTALLED, _ORIGINAL_SORT_CLUSTERS, _ORIGINAL_SORT_CELLS
    with _PATCH_LOCK:
        if _PATCH_INSTALLED:
            return False

        _ORIGINAL_SORT_CLUSTERS = LayoutPostprocessor._sort_clusters
        _ORIGINAL_SORT_CELLS = LayoutPostprocessor._sort_cells

        def patched_sort_clusters(
            self: LayoutPostprocessor,
            clusters: list[Cluster],
            mode: str = "id",
        ) -> list[Cluster]:
            assert _ORIGINAL_SORT_CLUSTERS is not None
            if mode != "id":
                return _ORIGINAL_SORT_CLUSTERS(self, clusters, mode)
            if not _is_form_like_cluster_group(clusters):
                return _ORIGINAL_SORT_CLUSTERS(self, clusters, mode)
            return sorted(clusters, key=_cluster_geometric_key)

        def patched_sort_cells(
            self: LayoutPostprocessor,
            cells: list[TextCell],
        ) -> list[TextCell]:
            assert _ORIGINAL_SORT_CELLS is not None
            if not _should_apply_form_cell_geometric_sort(cells):
                return _ORIGINAL_SORT_CELLS(self, cells)
            return sorted(cells, key=_cell_geometric_key)

        setattr(LayoutPostprocessor, "_sort_clusters", patched_sort_clusters)
        setattr(LayoutPostprocessor, "_sort_cells", patched_sort_cells)
        _PATCH_INSTALLED = True
        return True


def evaluate_docling_ordering_quality(markdown_content: str) -> OrderingQualityReport:
    """Build deterministic quality report from extracted markdown structure."""
    lines = markdown_content.splitlines()
    option_line_count = sum(1 for line in lines if _OPTION_LINE_RE.match(line) is not None)
    trailing_number_signals = sum(
        1 for line in lines if _TRAILING_NUMBER_SIGNAL_RE.match(line) is not None
    )
    standalone_number_signals = sum(
        1 for line in lines if _STANDALONE_BULLET_SIGNAL_RE.match(line) is not None
    )

    question_numbers: list[int] = []
    first_option_index: int | None = None
    first_question_index: int | None = None
    for index, line in enumerate(lines):
        if first_option_index is None and _OPTION_LINE_RE.match(line) is not None:
            first_option_index = index
        question_match = _QUESTION_NUMBER_LINE_RE.match(line.strip())
        if question_match is not None:
            question_numbers.append(int(question_match.group(1)))
            if first_question_index is None:
                first_question_index = index

    min_question: int | None = None
    max_question: int | None = None
    missing_questions: tuple[int, ...] = ()
    if question_numbers:
        min_question = min(question_numbers)
        max_question = max(question_numbers)
        missing_questions = tuple(
            number
            for number in range(min_question, max_question + 1)
            if number not in set(question_numbers)
        )

    option_before_question_signals = 0
    if first_option_index is not None and first_question_index is not None:
        if first_option_index < first_question_index:
            option_before_question_signals = 1

    is_exam_like = option_line_count >= 8 and (
        len(question_numbers) >= 4 or trailing_number_signals > 0 or standalone_number_signals > 0
    )

    return OrderingQualityReport(
        is_exam_like=is_exam_like,
        option_line_count=option_line_count,
        question_count=len(question_numbers),
        min_question_number=min_question,
        max_question_number=max_question,
        missing_question_numbers=missing_questions,
        trailing_number_signals=trailing_number_signals,
        standalone_number_signals=standalone_number_signals,
        option_before_question_signals=option_before_question_signals,
    )


def _is_form_like_cluster_group(clusters: list[Cluster]) -> bool:
    for cluster in clusters:
        if cluster.label in _FORM_CLUSTER_LABELS:
            return True
    return False


def _cluster_geometric_key(cluster: Cluster) -> tuple[float, float, int]:
    min_cell_index = min((cell.index for cell in cluster.cells), default=10**9)
    return (cluster.bbox.t, cluster.bbox.l, min_cell_index)


def _should_apply_form_cell_geometric_sort(cells: list[TextCell]) -> bool:
    if len(cells) < 4:
        return False

    standalone_number_count = 0
    question_mark_count = 0
    tops: list[float] = []

    for cell in cells:
        text = cell.text.strip()
        if _STANDALONE_NUMBER_RE.match(text) is not None:
            standalone_number_count += 1
        if "?" in text:
            question_mark_count += 1
        tops.append(_cell_top(cell))

    if standalone_number_count == 0 or question_mark_count == 0:
        return False

    return _count_inversions(tops) > 0


def _cell_geometric_key(cell: TextCell) -> tuple[float, float, int]:
    return (_cell_top(cell), _cell_left(cell), cell.index)


def _cell_top(cell: TextCell) -> float:
    rect = cell.rect
    return min(rect.r_y0, rect.r_y1, rect.r_y2, rect.r_y3)


def _cell_left(cell: TextCell) -> float:
    rect = cell.rect
    return min(rect.r_x0, rect.r_x1, rect.r_x2, rect.r_x3)


def _count_inversions(values: list[float]) -> int:
    inversions = 0
    for i, first in enumerate(values):
        for second in values[i + 1 :]:
            if first > second:
                inversions += 1
    return inversions
