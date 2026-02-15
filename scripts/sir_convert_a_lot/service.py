"""Sir Convert-a-Lot compatibility HTTP exports.

Purpose:
    Preserve stable service imports while delegating HTTP API implementation to
    the DDD interface layer.

Relationships:
    - Uses `interfaces.http_api.create_app` as canonical app factory.
    - Re-exports `ServiceConfig` for test configuration convenience.
"""

from scripts.sir_convert_a_lot.infrastructure.runtime_engine import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

app = create_app(service_profile="prod")

__all__ = ["ServiceConfig", "app", "create_app"]
