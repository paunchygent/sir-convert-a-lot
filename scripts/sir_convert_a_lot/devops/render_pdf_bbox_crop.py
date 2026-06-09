"""Render a source PDF bbox crop for conversion diagnostics.

Purpose:
    Produce a visual artifact for one Docling provenance bbox so formula VLM
    failures can be checked against the actual source crop.

Relationships:
    Complements Docling page-window replay formula-generation JSONL sidecars without changing
    conversion runtime behavior.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf


def main() -> None:
    """Render a Docling bottom-left-origin bbox from one PDF page to PNG."""
    args = _parse_args()
    render_bbox_crop(
        pdf_path=args.pdf,
        output_path=args.output,
        page_number=args.page,
        bbox_left=args.left,
        bbox_top=args.top,
        bbox_right=args.right,
        bbox_bottom=args.bottom,
        scale=args.scale,
        expansion_factor=args.expansion_factor,
    )


def render_bbox_crop(
    *,
    pdf_path: Path,
    output_path: Path,
    page_number: int,
    bbox_left: float,
    bbox_top: float,
    bbox_right: float,
    bbox_bottom: float,
    scale: float,
    expansion_factor: float,
) -> None:
    """Render a Docling bbox using PyMuPDF page coordinates."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(pdf_path.as_posix()) as document:
        page = document.load_page(page_number - 1)
        page_height = float(page.rect.height)
        rect = pymupdf.Rect(
            bbox_left,
            page_height - bbox_top,
            bbox_right,
            page_height - bbox_bottom,
        )
        rect = _expanded_rect(rect, expansion_factor).intersect(page.rect)
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(scale, scale),
            clip=rect,
            alpha=False,
        )
        pixmap.save(output_path.as_posix())


def _expanded_rect(rect: pymupdf.Rect, expansion_factor: float) -> pymupdf.Rect:
    width = float(rect.width)
    height = float(rect.height)
    x_margin = width * expansion_factor
    y_margin = height * expansion_factor
    rect.x0 -= x_margin
    rect.x1 += x_margin
    rect.y0 -= y_margin
    rect.y1 += y_margin
    return rect


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--left", type=float, required=True)
    parser.add_argument("--top", type=float, required=True)
    parser.add_argument("--right", type=float, required=True)
    parser.add_argument("--bottom", type=float, required=True)
    parser.add_argument("--scale", type=float, default=1.67)
    parser.add_argument("--expansion-factor", type=float, default=0.18)
    return parser.parse_args()


if __name__ == "__main__":
    main()
