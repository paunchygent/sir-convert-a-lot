"""Test deterministic docs-as-code index generation.

Purpose:
    Protect generated documentation indexes from date churn so docs-sync
    remains a stable navigation upkeep command.

Relationships:
    - Exercises `scripts.docs_as_code.index_docs`, which backs `pdm run
      docs-sync` and the generated-index freshness gate.
"""

from pathlib import Path

from scripts.docs_as_code.index_docs import existing_created_date


def test_existing_created_date_preserves_yaml_date(tmp_path: Path) -> None:
    """Generated indexes preserve their original YAML date value."""
    generated_index = tmp_path / "INDEX.md"
    generated_index.write_text(
        "\n".join(
            [
                "---",
                "type: reference",
                "id: REF-reference-index",
                "title: Reference Index",
                "status: active",
                "created: 2026-07-04",
                "owners:",
                "  - platform",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert existing_created_date(generated_index) == "2026-07-04"
