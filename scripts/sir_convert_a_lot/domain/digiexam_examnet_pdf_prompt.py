"""Exam.net PDF renderer prompt HTML sanitation.

Purpose:
    Convert DigiExam prompt HTML into a small, safe HTML subset for the
    Exam.net-oriented PDF renderer while resolving embedded image references.

Relationships:
    - Consumes asset reference paths prepared by
      `domain.digiexam_examnet_pdf_assets`.
    - Used by `domain.digiexam_examnet_pdf_items` before item sections are
      assembled.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from html import escape
from html.parser import HTMLParser

from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    AssetReferenceKey,
    DigiExamExamNetPdfPromptRender,
    DigiExamExamNetPdfWarning,
    DigiExamExamNetPdfWarningCode,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem


def render_examnet_prompt_html(
    *,
    item: DigiExamIrItem,
    asset_paths_by_reference: Mapping[AssetReferenceKey, str],
) -> DigiExamExamNetPdfPromptRender:
    """Render one item prompt into the PDF target HTML subset."""

    if item.prompt_html:
        return _PromptHtmlRenderer(
            item_id=item.item_id,
            asset_paths_by_reference=asset_paths_by_reference,
        ).render(item.prompt_html)

    html = "".join(f"<p>{escape(line)}</p>" for line in item.prompt_lines)
    return DigiExamExamNetPdfPromptRender(html=html, warnings=())


def prompt_has_renderable_content(prompt_html: str) -> bool:
    """Return whether prompt HTML contains text or an image."""

    return bool(re.search(r"<img\b|[A-Za-z0-9ÅÄÖåäö]", prompt_html))


class _PromptHtmlRenderer(HTMLParser):
    """Render a safe subset of DigiExam prompt HTML for the PDF target."""

    def __init__(
        self,
        *,
        item_id: str,
        asset_paths_by_reference: Mapping[AssetReferenceKey, str],
    ) -> None:
        super().__init__(convert_charrefs=True)
        self._item_id = item_id
        self._asset_paths_by_reference = asset_paths_by_reference
        self._parts: list[str] = []
        self._warnings: list[DigiExamExamNetPdfWarning] = []
        self._gap_span_depth = 0

    def render(self, prompt_html: str) -> DigiExamExamNetPdfPromptRender:
        """Return sanitized prompt HTML and warnings."""

        self.feed(prompt_html)
        self.close()
        return DigiExamExamNetPdfPromptRender(
            html="".join(self._parts),
            warnings=tuple(self._warnings),
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle allowed prompt start tags."""

        if self._gap_span_depth:
            self._gap_span_depth += 1
            return
        normalized_tag = tag.lower()
        if normalized_tag == "img":
            self._handle_image(attrs)
            return
        if normalized_tag == "span" and _has_gap_id(attrs):
            self._parts.append('<span class="gap-placeholder">[____]</span>')
            self._gap_span_depth = 1
            return
        if normalized_tag in {"p", "strong", "em", "sup", "sub"}:
            self._parts.append(f"<{normalized_tag}>")
            return
        if normalized_tag in {"b", "i"}:
            replacement = "strong" if normalized_tag == "b" else "em"
            self._parts.append(f"<{replacement}>")
            return
        if normalized_tag == "br":
            self._parts.append("<br>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle self-closing allowed prompt tags."""

        normalized_tag = tag.lower()
        if normalized_tag == "img":
            self._handle_image(attrs)
            return
        if normalized_tag == "span" and _has_gap_id(attrs):
            self._parts.append('<span class="gap-placeholder">[____]</span>')
            return
        if normalized_tag == "br":
            self._parts.append("<br>")

    def handle_endtag(self, tag: str) -> None:
        """Handle allowed prompt end tags."""

        if self._gap_span_depth:
            self._gap_span_depth -= 1
            return
        normalized_tag = tag.lower()
        if normalized_tag in {"p", "strong", "em", "sup", "sub"}:
            self._parts.append(f"</{normalized_tag}>")
            return
        if normalized_tag in {"b", "i"}:
            replacement = "strong" if normalized_tag == "b" else "em"
            self._parts.append(f"</{replacement}>")

    def handle_data(self, data: str) -> None:
        """Handle prompt text."""

        if self._gap_span_depth:
            return
        self._parts.append(escape(data))

    def _handle_image(self, attrs: list[tuple[str, str | None]]) -> None:
        image_id = _image_id(attrs)
        if image_id is None:
            self._warnings.append(_missing_image_warning(self._item_id, "unresolved"))
            return

        relative_path = self._asset_paths_by_reference.get((self._item_id, image_id))
        if relative_path is None:
            self._warnings.append(_missing_image_warning(self._item_id, str(image_id)))
            return

        self._parts.append(
            '<img class="prompt-image" '
            f'src="{escape(relative_path, quote=True)}" '
            f'alt="embedded image {image_id + 1}">'
        )


def _image_id(attrs: list[tuple[str, str | None]]) -> int | None:
    attr_map = {key.lower(): value for key, value in attrs if value is not None}
    value = attr_map.get("data-image-id")
    if value is None or not value.isdecimal():
        return None
    return int(value)


def _has_gap_id(attrs: list[tuple[str, str | None]]) -> bool:
    attr_map = {key.lower(): value for key, value in attrs if value is not None}
    gap_id = attr_map.get("dx-wg-id")
    return gap_id is not None and gap_id.strip() != ""


def _missing_image_warning(item_id: str, image_id: str) -> DigiExamExamNetPdfWarning:
    return DigiExamExamNetPdfWarning(
        code=DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_REFERENCE_MISSING,
        message=f"Embedded image reference {image_id} cannot be resolved.",
        item_id=item_id,
    )
