"""Source-routed answer-key live-validation runner.

Purpose:
    Provide a source-neutral command entrypoint for answer-key live validation
    while routing source-specific corpus handling to dedicated runners.

Relationships:
    - Dispatches the DigiExam `.dxe` lane to
      `devops.run_digiexam_answer_key_live_validation`.
    - Keeps provider-only command registration independent from any one source
      format so future conversion lanes can add their own adapters.
"""

from __future__ import annotations

import sys

from scripts.sir_convert_a_lot.devops.run_digiexam_answer_key_live_validation import (
    main as digiexam_main,
)

_SUPPORTED_SOURCES = frozenset({"digiexam"})


def main(argv: list[str] | None = None) -> int:
    """Dispatch answer-key live validation to a source-specific runner."""

    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit("Expected source lane: digiexam")
    source = args[0]
    if source not in _SUPPORTED_SOURCES:
        supported = ", ".join(sorted(_SUPPORTED_SOURCES))
        raise SystemExit(
            f"Unsupported answer-key live-validation source {source!r}; expected {supported}."
        )
    if source == "digiexam":
        return digiexam_main(args[1:])
    raise AssertionError("unreachable source dispatch")


if __name__ == "__main__":
    raise SystemExit(main())
