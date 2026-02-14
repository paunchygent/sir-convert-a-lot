"""Helpers for stable PDF fixtures used by Sir Convert-a-Lot tests.

Purpose:
    Provide deterministic access to checked-in valid PDF fixtures for tests that
    execute real conversion backends.

Relationships:
    - Used by API/runtime/integration tests that assert successful conversion.
    - Fixtures live in `tests/fixtures/benchmark_pdfs`.
"""

from __future__ import annotations

from pathlib import Path

FIXTURE_ROOT = Path("tests/fixtures/benchmark_pdfs")


def fixture_pdf_path(filename: str = "paper_alpha.pdf") -> Path:
    return FIXTURE_ROOT / filename


def fixture_pdf_bytes(filename: str = "paper_alpha.pdf") -> bytes:
    return fixture_pdf_path(filename).read_bytes()


def copy_fixture_pdf(target_path: Path, filename: str = "paper_alpha.pdf") -> None:
    target_path.write_bytes(fixture_pdf_bytes(filename))


def docling_cuda_available() -> bool:
    """Return whether CUDA is available in the current execution environment."""
    try:
        import torch
    except Exception:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def expected_acceleration_for_gpu_requested() -> str:
    """Return expected backend acceleration label when GPU is requested."""
    return "cuda" if docling_cuda_available() else "cpu"
