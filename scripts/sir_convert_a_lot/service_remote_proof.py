"""Sir Convert-a-Lot remote-proof HTTP service entrypoint.

Purpose:
    Provide the module-level `app` used by Uvicorn for the fenced Hemma
    remote-proof service profile.

Relationships:
    - Uses `interfaces.http_api.create_app` as canonical app factory.
    - Keeps remote-proof readiness distinct from the production `service.py`
      entrypoint so downstream proof preflight can fail closed on profile drift.
"""

from scripts.sir_convert_a_lot.interfaces.http_api import create_app

app = create_app(service_profile="remote-proof", expected_service_profile="remote-proof")
