"""Unit tests for v2 PDF layout preset CSS rendering."""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.specs_v2 import (
    PdfLayoutV2,
    PdfOrientationV2,
    PdfPaperSizeV2,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_layout_presets_v2 import (
    render_pdf_layout_preset_css,
)


def test_render_pdf_layout_preset_css_portrait_defaults() -> None:
    layout = PdfLayoutV2()
    css = render_pdf_layout_preset_css(layout)
    assert "size: A4;" in css
    assert "margin: 12mm;" in css


def test_render_pdf_layout_preset_css_landscape_a5_custom_margin() -> None:
    layout = PdfLayoutV2(
        paper_size=PdfPaperSizeV2.A5,
        orientation=PdfOrientationV2.LANDSCAPE,
        margins_mm=5,
    )
    css = render_pdf_layout_preset_css(layout)
    assert "size: A5 landscape;" in css
    assert "margin: 5mm;" in css
