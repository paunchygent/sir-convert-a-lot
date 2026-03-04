"""Sir Convert-a-Lot integration adapter package.

Purpose:
    Provide thin, contract-aligned integration helpers for consumer backends
    (HuleEdu and Skriptoteket) without introducing conversion business logic.

Relationships:
    - Delegates HTTP operations to `interfaces.http_client_v2`.
    - Enforces adapter requirements documented in converter integration docs.
"""
