"""Sir Convert-a-Lot compatibility client exports.

Purpose:
    Preserve stable client imports while delegating implementation to the
    DDD interface layer.

Relationships:
    - Re-exports from `interfaces.http_client`.
"""

from scripts.sir_convert_a_lot.interfaces.http_client import (
    ClientError,
    ConversionOutcome,
    SirConvertALotClient,
    SubmittedJob,
)

__all__ = ["ClientError", "ConversionOutcome", "SirConvertALotClient", "SubmittedJob"]
