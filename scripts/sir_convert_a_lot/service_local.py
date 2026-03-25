"""Sir Convert-a-Lot local CPU Docker service entrypoint.

Purpose:
    Provide the canonical module-level `app` used by the CPU-only local Docker
    debug profile on laptops.

Relationships:
    - Used by `compose.local.yaml` and `Dockerfile.local`.
    - Keeps local health metadata distinct from the Hemma production profile.
"""

from scripts.sir_convert_a_lot.interfaces.http_api import create_app

app = create_app(service_profile="local_cpu_dev", expected_service_profile="local_cpu_dev")
