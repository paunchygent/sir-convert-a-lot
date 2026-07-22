"""Emit the active interpreter's PEP 508 marker environment as JSON."""

from __future__ import annotations

import json

from packaging.markers import default_environment


def main() -> None:
    """Write the current interpreter's marker environment to standard output."""
    print(json.dumps(default_environment(), sort_keys=True))


if __name__ == "__main__":
    main()
