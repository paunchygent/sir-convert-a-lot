"""Sir Convert-a-Lot compatibility CLI exports.

Purpose:
    Preserve stable CLI imports and command execution while delegating
    implementation to the DDD interface layer.

Relationships:
    - Re-exports CLI symbols from `interfaces.cli_app`.
"""

from scripts.sir_convert_a_lot.interfaces.cli_app import (
    SirConvertALotClient,
    app,
    cli_root,
    convert_command,
    main,
)

__all__ = ["SirConvertALotClient", "app", "cli_root", "convert_command", "main"]

if __name__ == "__main__":
    main()
