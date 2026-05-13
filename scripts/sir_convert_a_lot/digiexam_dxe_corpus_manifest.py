"""Command runner for DigiExam `.dxe` validation corpus manifests.

Purpose:
    Provide a repo-local command surface for generating metadata-only
    DigiExam `.dxe` validation corpus manifests from local raw exports.

Relationships:
    - Delegates parser and manifest rules to
      `domain.digiexam_dxe_corpus_manifest`.
    - Used by Task 281 to keep raw validation corpora local while committing
      only safe aggregate parser evidence.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_dxe_corpus_manifest import (
    DEFAULT_DIGIEXAM_DXE_CORPUS_ID,
    build_digiexam_dxe_corpus_manifest,
    write_digiexam_dxe_corpus_manifest,
)


def main() -> None:
    """Generate a metadata-only DigiExam `.dxe` corpus manifest."""

    parser = argparse.ArgumentParser(
        description="Generate metadata-only DigiExam .dxe corpus manifest."
    )
    parser.add_argument("--corpus-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--corpus-id", default=DEFAULT_DIGIEXAM_DXE_CORPUS_ID)
    parser.add_argument("--source-root-hint", required=True)
    args = parser.parse_args()

    manifest = build_digiexam_dxe_corpus_manifest(
        args.corpus_root,
        corpus_id=args.corpus_id,
        source_root_hint=args.source_root_hint,
    )
    write_digiexam_dxe_corpus_manifest(manifest, args.output)
    print(args.output.as_posix())


if __name__ == "__main__":
    main()
