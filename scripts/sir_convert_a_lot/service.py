"""Sir Convert-a-Lot compatibility HTTP exports.

Purpose:
    Preserve stable service imports while delegating HTTP API implementation to
    the DDD interface layer.

Relationships:
    - Re-exports `app`/`create_app` from `interfaces.http_api`.
    - Re-exports `ServiceConfig` for test configuration convenience.
"""

from scripts.sir_convert_a_lot.infrastructure.runtime_engine import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import app, create_app

__all__ = ["ServiceConfig", "app", "create_app"]
