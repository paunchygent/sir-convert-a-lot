"""Sir Convert-a-Lot DevOps helpers.

Purpose:
    Provide operational utilities that validate or maintain Hemma deployments
    of Sir Convert-a-Lot.

Relationships:
    - Invoked by shell wrappers under `scripts/devops/` that run through the
      canonical Hemma command context wrapper (`pdm run run-hemma`).
    - These utilities are not part of the service request path and should stay
      lightweight and deterministic.
"""
