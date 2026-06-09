"""Formula crop metrics for Docling diagnostic replay.

Purpose:
    Build content-safe identifiers and dimensions for formula/code crop images
    so slow VLM batches can be correlated without storing document pixels.

Relationships:
    Used by `infrastructure.docling_formula_diagnostics` only when the Task 344
    JSONL sidecar is enabled.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable


def formula_crop_metrics(element_batch: Iterable[object]) -> list[dict[str, object]]:
    """Return sanitized per-crop metrics for a formula/code element batch."""
    metrics: list[dict[str, object]] = []
    for index, element in enumerate(element_batch):
        image = getattr(element, "image", None)
        width, height = image_dimensions(image)
        payload: dict[str, object] = {
            "index": index,
            "label": element_label(element),
        }
        item_identity = element_item_identity(element)
        payload.update(item_identity)
        if width is not None and height is not None:
            payload["image_width"] = width
            payload["image_height"] = height
            payload["pixel_area"] = width * height
        image_hash = image_sha256(image)
        if image_hash is not None:
            payload["image_sha256"] = image_hash
        image_mode = getattr(image, "mode", None)
        if isinstance(image_mode, str):
            payload["image_mode"] = image_mode
        image_shape = safe_shape(getattr(image, "shape", None))
        if image_shape:
            payload["image_shape"] = image_shape
        metrics.append(payload)
    return metrics


def element_item_identity(element: object) -> dict[str, object]:
    """Return content-free Docling item identity and provenance fields."""
    item = getattr(element, "item", None)
    payload: dict[str, object] = {}
    self_ref = getattr(item, "self_ref", None)
    if isinstance(self_ref, str):
        payload["item_self_ref"] = self_ref
    prov = getattr(item, "prov", None)
    if isinstance(prov, list) and prov:
        first_prov = prov[0]
        page_no = positive_int(getattr(first_prov, "page_no", None))
        if page_no is not None:
            payload["prov_page_no"] = page_no
        bbox_payload = bbox_coordinates(getattr(first_prov, "bbox", None))
        if bbox_payload:
            payload["prov_bbox"] = bbox_payload
    return payload


def element_label(element: object) -> str:
    """Return the Docling label for one enrichment element."""
    item = getattr(element, "item", None)
    return enum_or_string(getattr(item, "label", None)) or "unknown"


def image_dimensions(image: object) -> tuple[int | None, int | None]:
    """Return image width and height for PIL-like or ndarray-like images."""
    size = getattr(image, "size", None)
    if isinstance(size, tuple) and len(size) == 2:
        width = positive_int(size[0])
        height = positive_int(size[1])
        if width is not None and height is not None:
            return width, height
    shape = getattr(image, "shape", None)
    if isinstance(shape, tuple) and len(shape) >= 2:
        height = positive_int(shape[0])
        width = positive_int(shape[1])
        if width is not None and height is not None:
            return width, height
    return None, None


def image_sha256(image: object) -> str | None:
    """Return a deterministic image-byte hash when the object exposes bytes."""
    tobytes = getattr(image, "tobytes", None)
    if not callable(tobytes):
        return None
    try:
        raw_bytes = tobytes()
    except Exception:
        return None
    if not isinstance(raw_bytes, bytes):
        return None
    digest = hashlib.sha256()
    digest.update(type(image).__name__.encode("utf-8"))
    digest.update(str(getattr(image, "mode", "")).encode("utf-8"))
    digest.update(str(getattr(image, "size", "")).encode("utf-8"))
    digest.update(str(getattr(image, "shape", "")).encode("utf-8"))
    digest.update(raw_bytes)
    return digest.hexdigest()


def safe_shape(value: object) -> list[int | str]:
    """Return a JSON-safe shape list without importing ndarray types."""
    if not isinstance(value, tuple):
        return []
    shape: list[int | str] = []
    for item in value:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            shape.append(max(0, item))
        else:
            shape.append(str(item))
    return shape


def bbox_coordinates(value: object) -> dict[str, float]:
    """Return a JSON-safe bounding-box coordinate payload."""
    coordinates: dict[str, float] = {}
    for field_name in ("l", "t", "r", "b"):
        coordinate = getattr(value, field_name, None)
        if isinstance(coordinate, bool):
            continue
        if isinstance(coordinate, int | float):
            coordinates[field_name] = round(float(coordinate), 3)
    return coordinates


def positive_int(value: object) -> int | None:
    """Return a non-negative int for metrics, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(0, value)


def enum_or_string(value: object) -> str | None:
    """Return enum `.value` when string-like, otherwise `str(value)`."""
    if value is None:
        return None
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
