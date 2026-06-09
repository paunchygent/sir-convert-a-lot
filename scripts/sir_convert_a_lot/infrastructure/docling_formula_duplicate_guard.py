"""Duplicate guard for Docling formula enrichment items.

Purpose:
    Prevent one Docling conversion from sending the same formula item reference
    through the formula VLM more than once.

Relationships:
    Used by `infrastructure.docling_formula_diagnostics`, which wraps Docling's
    `CodeFormulaVlmModel` call boundary.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from docling.datamodel.base_models import ItemAndImageEnrichmentElement
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc import NodeItem

_SEEN_LOCK = threading.Lock()
_SEEN_ITEM_REFS_BY_DOC_ID: dict[int, set[str]] = {}


@dataclass(frozen=True)
class FormulaBatchPartition:
    """Partition of one formula batch into fresh and duplicate elements."""

    fresh_elements: tuple[ItemAndImageEnrichmentElement, ...]
    fresh_positions: tuple[int, ...]
    outputs: tuple[NodeItem | None, ...]
    duplicate_elements: tuple[ItemAndImageEnrichmentElement, ...]

    @property
    def has_duplicates(self) -> bool:
        """Return true when at least one item was already processed."""
        return bool(self.duplicate_elements)


def partition_formula_batch_by_item_ref(
    elements: tuple[ItemAndImageEnrichmentElement, ...],
    seen_item_refs: set[str],
) -> FormulaBatchPartition:
    """Split a formula batch by conversion-local Docling item references."""
    fresh_elements: list[ItemAndImageEnrichmentElement] = []
    fresh_positions: list[int] = []
    outputs: list[NodeItem | None] = []
    duplicate_elements: list[ItemAndImageEnrichmentElement] = []

    for index, element in enumerate(elements):
        item_ref = formula_item_self_ref(element)
        if item_ref is not None and item_ref in seen_item_refs:
            outputs.append(element.item)
            duplicate_elements.append(element)
            continue

        if item_ref is not None:
            seen_item_refs.add(item_ref)
        fresh_positions.append(index)
        fresh_elements.append(element)
        outputs.append(None)

    return FormulaBatchPartition(
        fresh_elements=tuple(fresh_elements),
        fresh_positions=tuple(fresh_positions),
        outputs=tuple(outputs),
        duplicate_elements=tuple(duplicate_elements),
    )


def partition_formula_batch_by_doc(
    doc: DoclingDocument,
    elements: tuple[ItemAndImageEnrichmentElement, ...],
) -> FormulaBatchPartition:
    """Split a formula batch using process-local document-scoped state."""
    with _SEEN_LOCK:
        seen_item_refs = _SEEN_ITEM_REFS_BY_DOC_ID.setdefault(id(doc), set())
        return partition_formula_batch_by_item_ref(elements, seen_item_refs)


def clear_formula_batch_doc_state(doc: DoclingDocument) -> None:
    """Drop process-local duplicate state for a completed Docling document."""
    with _SEEN_LOCK:
        _SEEN_ITEM_REFS_BY_DOC_ID.pop(id(doc), None)


def formula_item_self_ref(element: ItemAndImageEnrichmentElement) -> str | None:
    """Return the stable Docling item reference for a formula element."""
    self_ref = getattr(element.item, "self_ref", None)
    return self_ref if isinstance(self_ref, str) else None
