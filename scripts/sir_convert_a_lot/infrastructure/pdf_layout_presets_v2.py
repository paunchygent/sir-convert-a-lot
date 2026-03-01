"""V2 PDF layout preset rendering for WeasyPrint-backed PDF outputs.

Purpose:
    Provide a typed, deterministic bridge from the v2 JobSpec `conversion.pdf_layout`
    surface to concrete CSS applied during WeasyPrint HTML->PDF rendering.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for all PDF-output routes.
    - Depends only on v2 domain models; does not import WeasyPrint directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs_v2 import PdfLayoutV2, PdfOrientationV2, PdfPaperSizeV2

_PRESET_STYLESHEET_FILENAME = "__pdf_layout_preset_v2.css"


@dataclass(frozen=True)
class PdfLayoutPresetWriteError(Exception):
    """Deterministic error when the preset stylesheet cannot be written."""

    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial and stable
        return self.message


def _paper_size_css_value(paper_size: PdfPaperSizeV2) -> str:
    if paper_size == PdfPaperSizeV2.A5:
        return "A5"
    if paper_size == PdfPaperSizeV2.A4:
        return "A4"
    if paper_size == PdfPaperSizeV2.A3:
        return "A3"
    raise ValueError(f"Unsupported paper size: {paper_size}")


def render_pdf_layout_preset_css(layout: PdfLayoutV2) -> str:
    """Render the v2 pdf_layout preset as a deterministic CSS stylesheet."""

    size = _paper_size_css_value(layout.paper_size)
    if layout.orientation == PdfOrientationV2.LANDSCAPE:
        size = f"{size} landscape"

    margin_mm = max(0, int(layout.margins_mm))

    return f"@page {{\n  size: {size};\n  margin: {margin_mm}mm;\n}}\n"


def write_pdf_layout_preset_stylesheet(*, workdir: Path, layout: PdfLayoutV2) -> Path:
    """Write the preset CSS stylesheet under workdir and return its path."""

    target = workdir / _PRESET_STYLESHEET_FILENAME
    css = render_pdf_layout_preset_css(layout)
    try:
        target.write_text(css, encoding="utf-8")
    except OSError as exc:
        raise PdfLayoutPresetWriteError(
            message=f"Failed to write preset stylesheet: {target}: {exc}"
        ) from exc
    return target
