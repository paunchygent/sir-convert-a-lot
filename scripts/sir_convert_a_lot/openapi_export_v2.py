"""Export the Sir Convert-a-Lot service API v2 OpenAPI contract.

Purpose:
    Produce a deterministic OpenAPI JSON snapshot from the canonical FastAPI app
    factory so downstream consumers can generate client types before live
    Docker/service tests.

Relationships:
    - Uses `interfaces.http_api.create_app` as the runtime source of truth.
    - Writes `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`.
    - Tested by `tests/sir_convert_a_lot/test_openapi_contract_v2.py`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.sir_convert_a_lot.interfaces.http_api import create_app

DEFAULT_OPENAPI_CONTRACT_PATH = Path("docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json")


def build_openapi_contract_v2() -> dict[str, object]:
    """Build the OpenAPI schema from the canonical local-dev app factory."""

    app = create_app(service_profile="local_cpu_dev", expected_service_profile="local_cpu_dev")
    schema = app.openapi()
    if not isinstance(schema, dict):
        raise TypeError("FastAPI OpenAPI generator returned a non-object schema")
    return {str(key): value for key, value in schema.items()}


def openapi_contract_bytes_v2() -> bytes:
    """Return deterministic OpenAPI JSON bytes."""

    text = json.dumps(build_openapi_contract_v2(), ensure_ascii=False, indent=2, sort_keys=True)
    return f"{text}\n".encode("utf-8")


def export_openapi_contract_v2(output_path: Path = DEFAULT_OPENAPI_CONTRACT_PATH) -> Path:
    """Write the deterministic OpenAPI contract snapshot."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(openapi_contract_bytes_v2())
    return output_path


def main() -> None:
    """CLI entrypoint for deterministic contract export."""

    parser = argparse.ArgumentParser(description="Export Sir Convert-a-Lot v2 OpenAPI JSON.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OPENAPI_CONTRACT_PATH,
        help="OpenAPI JSON output path.",
    )
    args = parser.parse_args()
    written = export_openapi_contract_v2(output_path=args.output)
    print(written.as_posix())


if __name__ == "__main__":
    main()
