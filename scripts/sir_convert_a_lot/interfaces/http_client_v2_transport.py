"""Structural HTTP transport types for the Sir Convert-a-Lot v2 client.

Purpose:
    Declare the minimal HTTP client and response surface that
    `SirConvertALotClientV2` calls, so any client with this surface can be
    injected (`httpx.Client`, Starlette's `TestClient`, or a test double)
    without depending on one `httpx` distribution's concrete classes.

Relationships:
    - Used by `scripts.sir_convert_a_lot.interfaces.http_client_v2` to type the
      injected `http_client` argument and the responses it reads.
    - `RequestFileValue` is the multipart file tuple owned by
      `scripts.sir_convert_a_lot.interfaces.http_client_v2_models`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import RequestFileValue


class HttpResponse(Protocol):
    """Response members the v2 client reads."""

    @property
    def status_code(self) -> int: ...

    @property
    def content(self) -> bytes: ...

    @property
    def headers(self) -> Mapping[str, str]: ...

    def json(self) -> object: ...


class HttpClient(Protocol):
    """Client members the v2 client calls."""

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...

    def post(
        self,
        url: str,
        *,
        params: Mapping[str, int] | None = None,
        headers: Mapping[str, str] | None = None,
        data: Mapping[str, str] | None = None,
        files: Mapping[str, RequestFileValue] | None = None,
    ) -> HttpResponse: ...

    def close(self) -> None: ...
