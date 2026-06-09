"""Prepare formula candidate evaluation source page and formula-crop evaluation inputs.

Purpose:
    Extract established Docling page-window replay page/crop evidence and render local visual
    inputs for formula/OCR candidate evaluation.

Relationships:
    - Consumes Docling page-window replay replay report metadata.
    - Reuses `render_pdf_bbox_crop` for crop images.
    - Feeds formula candidate evaluation candidate and reporting helpers.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from scripts.sir_convert_a_lot.devops.render_pdf_bbox_crop import render_bbox_crop


@dataclass(frozen=True)
class SourceInput:
    """One rendered page or formula crop used by candidate evaluation."""

    input_id: str
    kind: str
    page: int
    image_path: Path
    source_text_path: Path | None
    bbox: Mapping[str, float] | None = None
    item_self_ref: str | None = None


class _PageRect(Protocol):
    height: float


class _PdfPage(Protocol):
    rect: _PageRect

    def get_text(self, option: str = "text", *, clip: object | None = None) -> object:
        """Return PyMuPDF text extraction output."""


class _PdfDocument(Protocol):
    def load_page(self, page_id: int) -> _PdfPage:
        """Load one 0-based page."""


def harvest_formula_regions(
    report: Mapping[str, object],
    *,
    fallback_first_page: int,
) -> list[dict[str, object]]:
    """Extract formula crop metadata from a Docling page-window replay replay report."""
    records = report.get("records")
    if not isinstance(records, list):
        return []
    regions: list[dict[str, object]] = []
    seen: set[str] = set()
    for record_obj in records:
        if not isinstance(record_obj, dict):
            continue
        child_payload = object_mapping(record_obj.get("child_payload"))
        first_page = int_field(child_payload, "start_page", fallback_first_page)
        events = record_obj.get("formula_diagnostics_events")
        if not isinstance(events, list):
            continue
        harvest_regions_from_events(
            events=events,
            first_page=first_page,
            regions=regions,
            seen=seen,
        )
    return regions


def harvest_regions_from_events(
    *,
    events: Sequence[object],
    first_page: int,
    regions: list[dict[str, object]],
    seen: set[str],
) -> None:
    """Append formula crop records from replay diagnostic events."""
    for event_obj in events:
        event = object_mapping(event_obj)
        if event.get("event") != "code_formula_batch_started":
            continue
        crops = event.get("crops")
        if not isinstance(crops, list):
            continue
        for crop_obj in crops:
            crop = object_mapping(crop_obj)
            bbox = bbox_mapping(crop.get("prov_bbox"))
            if bbox is None:
                continue
            relative_page = int_field(crop, "prov_page_no", 1)
            absolute_page = first_page + relative_page - 1
            item_self_ref = str(crop.get("item_self_ref", "formula"))
            region_id = f"p{absolute_page}-{safe_identifier(item_self_ref)}"
            if region_id in seen:
                continue
            seen.add(region_id)
            regions.append(
                {
                    "id": region_id,
                    "item_self_ref": item_self_ref,
                    "absolute_page": absolute_page,
                    "relative_page": relative_page,
                    "label": str(crop.get("label", "formula")),
                    "image_width": int_field(crop, "image_width", 0),
                    "image_height": int_field(crop, "image_height", 0),
                    "image_sha256": str(crop.get("image_sha256", "")),
                    "bbox": bbox,
                }
            )


def build_source_inputs(
    *,
    source_pdf: Path,
    rendered_root: Path,
    regions: Sequence[Mapping[str, object]],
    pages: Sequence[int],
    output_root: Path,
) -> tuple[SourceInput, ...]:
    """Create local page/crop images used by the evaluation candidates."""
    inputs: list[SourceInput] = []
    page_texts = extract_page_texts(
        source_pdf=source_pdf,
        pages=pages,
        output_root=output_root / "source-text-pages",
    )
    for page_number in pages:
        inputs.append(
            build_page_input(
                source_pdf=source_pdf,
                rendered_root=rendered_root,
                page_number=page_number,
                output_root=output_root / "pages",
                page_text_path=page_texts.get(page_number),
            )
        )
    for region in regions:
        crop_input = build_crop_input(
            source_pdf=source_pdf,
            region=region,
            fallback_page=pages[0],
            output_root=output_root / "formula-crops",
        )
        if crop_input is not None:
            inputs.append(crop_input)
    return tuple(inputs)


def build_page_input(
    *,
    source_pdf: Path,
    rendered_root: Path,
    page_number: int,
    output_root: Path,
    page_text_path: Path | None,
) -> SourceInput:
    """Return one full-page source input, rendering it when necessary."""
    image_path = output_root / f"page-{page_number}.png"
    existing = rendered_root / f"page-{page_number}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if existing.exists():
        shutil.copyfile(existing, image_path)
    else:
        render_page(source_pdf=source_pdf, page_number=page_number, output_path=image_path)
    return SourceInput(
        input_id=f"page-{page_number}",
        kind="page",
        page=page_number,
        image_path=image_path,
        source_text_path=page_text_path,
    )


def build_crop_input(
    *,
    source_pdf: Path,
    region: Mapping[str, object],
    fallback_page: int,
    output_root: Path,
) -> SourceInput | None:
    """Render and return one formula-crop source input."""
    bbox = bbox_mapping(region.get("bbox"))
    if bbox is None:
        return None
    page_number = int_field(region, "absolute_page", fallback_page)
    region_id = str(region.get("id", f"p{page_number}-formula"))
    image_path = output_root / f"{region_id}.png"
    render_bbox_crop(
        pdf_path=source_pdf,
        output_path=image_path,
        page_number=page_number,
        bbox_left=bbox["l"],
        bbox_top=bbox["t"],
        bbox_right=bbox["r"],
        bbox_bottom=bbox["b"],
        scale=2.0,
        expansion_factor=0.18,
    )
    return SourceInput(
        input_id=region_id,
        kind="formula_crop",
        page=page_number,
        image_path=image_path,
        source_text_path=None,
        bbox=bbox,
        item_self_ref=str(region.get("item_self_ref", "")),
    )


def source_text_for_input(*, document: _PdfDocument, source_input: SourceInput) -> str:
    """Extract page or clipped source text with PyMuPDF."""
    page = document.load_page(source_input.page - 1)
    if source_input.kind == "formula_crop" and source_input.bbox is not None:
        import pymupdf

        page_height = float(page.rect.height)
        bbox = source_input.bbox
        rect = pymupdf.Rect(
            bbox["l"],
            page_height - bbox["t"],
            bbox["r"],
            page_height - bbox["b"],
        ).intersect(page.rect)
        return str(page.get_text("text", clip=rect))
    return str(page.get_text("text"))


def extract_page_texts(
    *,
    source_pdf: Path,
    pages: Sequence[int],
    output_root: Path,
) -> dict[int, Path]:
    """Write PyMuPDF page text sidecars for source review."""
    output_root.mkdir(parents=True, exist_ok=True)
    paths: dict[int, Path] = {}
    import pymupdf

    with pymupdf.open(source_pdf.as_posix()) as document:
        for page_number in pages:
            page = document.load_page(page_number - 1)
            output_path = output_root / f"page-{page_number}.txt"
            output_path.write_text(str(page.get_text("text")), encoding="utf-8")
            paths[page_number] = output_path
    return paths


def render_page(*, source_pdf: Path, page_number: int, output_path: Path) -> None:
    """Render one full source page to PNG."""
    import pymupdf

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(source_pdf.as_posix()) as document:
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2.0, 2.0), alpha=False)
        pixmap.save(output_path.as_posix())


def parse_page_range(raw_value: str) -> tuple[int, ...]:
    """Parse `13-16` or comma-separated pages into 1-based page numbers."""
    value = raw_value.strip()
    if "," in value:
        return tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if "-" in value:
        start_raw, end_raw = value.split("-", maxsplit=1)
        start_page = int(start_raw)
        end_page = int(end_raw)
        return tuple(range(start_page, end_page + 1))
    return (int(value),)


def limit_regions(
    regions: Sequence[Mapping[str, object]],
    max_formula_crops: int,
) -> tuple[Mapping[str, object], ...]:
    """Limit formula crops when requested; zero means all regions."""
    if max_formula_crops <= 0:
        return tuple(regions)
    return tuple(regions[:max_formula_crops])


def source_input_payload(source_input: SourceInput) -> dict[str, object]:
    """Return a JSON-serializable source input record."""
    return {
        "input_id": source_input.input_id,
        "kind": source_input.kind,
        "page": source_input.page,
        "image_path": source_input.image_path.as_posix(),
        "source_text_path": source_input.source_text_path.as_posix()
        if source_input.source_text_path is not None
        else None,
        "item_self_ref": source_input.item_self_ref,
        "bbox": dict(source_input.bbox) if source_input.bbox is not None else None,
    }


def load_source_inputs_from_report(payload: Mapping[str, object]) -> list[SourceInput]:
    """Rehydrate source inputs from a JSON payload for review rendering."""
    inputs_obj = payload.get("source_inputs")
    if not isinstance(inputs_obj, list):
        return []
    source_inputs: list[SourceInput] = []
    for item_obj in inputs_obj:
        item = object_mapping(item_obj)
        source_text_path = item.get("source_text_path")
        source_inputs.append(
            SourceInput(
                input_id=str(item.get("input_id", "")),
                kind=str(item.get("kind", "")),
                page=int_field(item, "page", 0),
                image_path=Path(str(item.get("image_path", ""))),
                source_text_path=Path(source_text_path)
                if isinstance(source_text_path, str)
                else None,
            )
        )
    return source_inputs


def read_json_object(path: Path) -> dict[str, object]:
    """Read a JSON object from disk."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return {str(key): value for key, value in loaded.items()}
    return {}


def object_mapping(value: object) -> dict[str, object]:
    """Return a string-key mapping for JSON-like dictionaries."""
    if isinstance(value, dict):
        return {str(key): child for key, child in value.items()}
    return {}


def bbox_mapping(value: object) -> dict[str, float] | None:
    """Return a normalized bbox mapping when all fields are present."""
    mapping = object_mapping(value)
    required = ("l", "t", "r", "b")
    if not all(key in mapping for key in required):
        return None
    try:
        return {key: float_value(mapping[key]) for key in required}
    except ValueError:
        return None


def int_field(mapping: Mapping[str, object], key: str, fallback: int) -> int:
    """Return an integer JSON field when present."""
    value = mapping.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return int(value)
    return fallback


def float_value(value: object) -> float:
    """Convert a JSON scalar to float or raise ValueError."""
    if isinstance(value, bool):
        raise ValueError("boolean is not a coordinate")
    if isinstance(value, int | float | str):
        return float(value)
    raise ValueError("coordinate is not numeric")


def safe_identifier(value: str) -> str:
    """Return a stable path-safe identifier."""
    cleaned = value.replace("#/", "").replace("/", "-").replace("_", "-")
    allowed = [
        character if character.isalnum() or character == "-" else "-" for character in cleaned
    ]
    return "-".join(part for part in "".join(allowed).split("-") if part)


def sha256_file(path: Path) -> str:
    """Return SHA256 for a local file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
