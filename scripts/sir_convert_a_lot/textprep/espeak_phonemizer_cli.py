"""Generate Swedish phoneme text with the benchmark-only eSpeak helper path.

Purpose:
    Convert one text file into one phonemized text artifact using the official
    `phonemizer` package with the eSpeak backend, so Chatterbox experiments can
    compare text-input and phoneme-like input without changing the sidecar
    contract.

Relationships:
    - Intended to run inside the dedicated Task 89 helper container.
    - Called by the Task 89 Hemma experiment runner.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class EspeakPhonemizerResult:
    """One deterministic record of the phonemizer helper output."""

    backend: str
    language: str
    preserve_punctuation: bool
    strip: bool
    input_text: str
    output_text: str


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for the eSpeak phonemizer helper."""
    parser = argparse.ArgumentParser(description="Generate phonemized text with eSpeak.")
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    parser.add_argument("--metadata-file", type=Path, required=True)
    parser.add_argument("--language", default="sv")
    parser.add_argument("--preserve-punctuation", action="store_true", default=True)
    parser.add_argument(
        "--no-preserve-punctuation", dest="preserve_punctuation", action="store_false"
    )
    parser.add_argument("--strip", action="store_true", default=True)
    parser.add_argument("--no-strip", dest="strip", action="store_false")
    return parser.parse_args(argv)


def _phonemize_text(*, text: str, language: str, preserve_punctuation: bool, strip: bool) -> str:
    """Return one phonemized text string using the official phonemizer backend."""
    from phonemizer import phonemize

    return str(
        phonemize(
            text=text,
            language=language,
            backend="espeak",
            preserve_punctuation=preserve_punctuation,
            strip=strip,
            njobs=1,
        )
    ).strip()


def main(argv: list[str] | None = None) -> int:
    """Run the helper and write text plus metadata artifacts."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    input_text = args.input_file.read_text(encoding="utf-8").strip()
    if input_text == "":
        raise SystemExit(f"Input file is empty: {args.input_file}")
    output_text = _phonemize_text(
        text=input_text,
        language=str(args.language),
        preserve_punctuation=bool(args.preserve_punctuation),
        strip=bool(args.strip),
    )
    if output_text == "":
        raise SystemExit("Phonemizer returned an empty output string.")
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(output_text + "\n", encoding="utf-8")
    metadata = EspeakPhonemizerResult(
        backend="espeak",
        language=str(args.language),
        preserve_punctuation=bool(args.preserve_punctuation),
        strip=bool(args.strip),
        input_text=input_text,
        output_text=output_text,
    )
    args.metadata_file.write_text(
        json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
