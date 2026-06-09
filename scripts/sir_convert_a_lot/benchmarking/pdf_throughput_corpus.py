"""PDF corpus preparation for PDF throughput benchmarks.

Purpose:
    Generate deterministic scanned-PDF smoke fixtures and prepare sanitized
    execution copies of private dirty-corpus PDFs after manifest hash
    verification.

Relationships:
    - Used by `pdf_throughput_profile_runner` to create local smoke corpus files.
    - Copies dirty PDF OCR corpus private dirty-corpus inputs into sanitized filenames
      before benchmark execution.
    - Produces `CorpusFileRecord` entries embedded in PDF throughput benchmark evidence payloads.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .pdf_throughput_types import CorpusFileRecord, DirtyCorpusManifestSummary


def _sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _pdf_page_count(path: Path) -> int:
    import pymupdf

    document = pymupdf.open(path.as_posix())
    try:
        return int(document.page_count)
    finally:
        document.close()


def _build_scan_template_image(text: str) -> bytes:
    import pymupdf

    template_doc = pymupdf.open()
    try:
        page = template_doc.new_page(width=595, height=842)
        if page is None:
            raise RuntimeError("PyMuPDF returned no page for template generation.")
        page.insert_textbox(
            pymupdf.Rect(48, 48, 547, 794),
            text,
            fontsize=14,
            fontname="helv",
            align=0,
        )
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2.0, 2.0), alpha=False)
        return bytes(pixmap.tobytes("png"))
    finally:
        template_doc.close()


def generate_corpus(*, corpus_root: Path, page_counts: tuple[int, ...]) -> list[CorpusFileRecord]:
    """Generate representative scanned PDFs for throughput benchmarking."""
    import pymupdf

    corpus_root.mkdir(parents=True, exist_ok=True)
    records: list[CorpusFileRecord] = []
    for document_index, page_count in enumerate(page_counts, start=1):
        templates = [
            _build_scan_template_image(
                "\n".join(
                    [
                        f"PDF throughput lane benchmark document {document_index}",
                        f"Template {template_index + 1}",
                        "OCR target text with Swedish characters: å ä ö.",
                        "Synthetic scanned textbook content for throughput profiling.",
                    ]
                )
            )
            for template_index in range(4)
        ]
        output_path = (
            corpus_root / f"pdf-throughput-benchmark-{document_index:02d}-{page_count}p.pdf"
        )
        document = pymupdf.open()
        try:
            for page_index in range(page_count):
                page = document.new_page(width=595, height=842)
                if page is None:
                    raise RuntimeError("PyMuPDF returned no page for corpus generation.")
                page.insert_image(page.rect, stream=templates[page_index % len(templates)])
            document.save(output_path.as_posix())
        finally:
            document.close()
        file_bytes = output_path.read_bytes()
        records.append(
            {
                "filename": output_path.name,
                "page_count": page_count,
                "size_bytes": len(file_bytes),
                "sha256": _sha256_bytes(file_bytes),
            }
        )
    return records


def build_verified_dirty_corpus(
    *,
    source_root: Path,
    execution_corpus_root: Path,
    manifest: DirtyCorpusManifestSummary,
) -> list[CorpusFileRecord]:
    """Copy manifest-hash-matched private PDFs into a sanitized execution corpus."""
    if not source_root.is_dir():
        raise ValueError("dirty corpus source root must be an existing private PDF directory.")

    expected_hashes = {entry["source_sha256"] for entry in manifest["entries"]}
    matched_paths: dict[str, Path] = {}
    for candidate in sorted(source_root.rglob("*")):
        if not candidate.is_file() or candidate.suffix.lower() != ".pdf":
            continue
        source_hash = _sha256_file(candidate)
        if source_hash not in expected_hashes:
            continue
        if source_hash in matched_paths:
            source_id = next(
                entry["source_id"]
                for entry in manifest["entries"]
                if entry["source_sha256"] == source_hash
            )
            raise ValueError(
                "dirty corpus source root contains multiple PDFs matching "
                f"manifest source_id `{source_id}`."
            )
        matched_paths[source_hash] = candidate

    missing_source_ids = [
        entry["source_id"]
        for entry in manifest["entries"]
        if entry["source_sha256"] not in matched_paths
    ]
    if missing_source_ids:
        joined = ", ".join(sorted(missing_source_ids))
        raise ValueError(
            f"dirty corpus source root is missing PDFs matching manifest source_ids: {joined}."
        )

    execution_corpus_root.mkdir(parents=True, exist_ok=True)
    records: list[CorpusFileRecord] = []
    for entry in manifest["entries"]:
        target_path = execution_corpus_root / f"{entry['source_id']}.pdf"
        shutil.copyfile(matched_paths[entry["source_sha256"]], target_path)
        copied_hash = _sha256_file(target_path)
        if copied_hash != entry["source_sha256"]:
            raise ValueError(f"dirty corpus hash verification failed for `{entry['source_id']}`.")
        copied_page_count = _pdf_page_count(target_path)
        if copied_page_count != entry["page_count"]:
            raise ValueError(
                f"dirty corpus page count mismatch for `{entry['source_id']}`: "
                f"manifest={entry['page_count']} observed={copied_page_count}."
            )
        records.append(
            {
                "filename": target_path.name,
                "page_count": copied_page_count,
                "size_bytes": target_path.stat().st_size,
                "sha256": copied_hash,
            }
        )
    return records
