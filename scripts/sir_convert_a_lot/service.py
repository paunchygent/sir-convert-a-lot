"""Sir Convert-a-Lot HTTP service entrypoint.

Purpose:
    Provide the canonical module-level `app` used by Uvicorn for the production
    service profile.

Relationships:
    - Uses `interfaces.http_api.create_app` as canonical app factory.
"""

from scripts.sir_convert_a_lot.interfaces.http_api import create_app

app = create_app(service_profile="prod", expected_service_profile="prod")
