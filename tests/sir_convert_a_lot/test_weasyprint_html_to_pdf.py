"""Security-focused tests for WeasyPrint HTML->PDF wrapper.

Purpose:
    Verify restricted URL fetching behavior so SSRF and local file inclusion
    are blocked for conversion jobs.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.weasyprint_html_to_pdf`.
    - Supports Task 60 hardening coverage for resource sandboxing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pytest

from scripts.sir_convert_a_lot.infrastructure import weasyprint_html_to_pdf
from scripts.sir_convert_a_lot.infrastructure.weasyprint_html_to_pdf import (
    HTML_TO_PDF_RESOURCE_BLOCKED,
    HtmlToPdfConversionError,
    convert_html_to_pdf,
)


class _Fetcher(Protocol):
    def __call__(
        self,
        url: str,
        timeout: int = 10,
        ssl_context: object | None = None,
        http_headers: object | None = None,
    ) -> dict[str, object]: ...


def _install_fake_loader(
    monkeypatch: pytest.MonkeyPatch,
    *,
    resource_url_to_fetch: str,
    fetched_urls: list[str],
    html_factory_calls: list[dict[str, object]] | None = None,
) -> None:
    class _FakeHtmlDocument:
        def __init__(self, *, url_fetcher: _Fetcher) -> None:
            self._url_fetcher = url_fetcher

        def write_pdf(
            self,
            target: str,
            *,
            stylesheets: list[object] | None = None,
        ) -> bytes | None:
            del stylesheets
            self._url_fetcher(resource_url_to_fetch)
            Path(target).write_bytes(b"%PDF-1.7\nstub\n")
            return None

    def _fake_html_factory(
        **kwargs: object,
    ) -> _FakeHtmlDocument:
        if html_factory_calls is not None:
            html_factory_calls.append(dict(kwargs))
        url_fetcher = kwargs["url_fetcher"]
        assert callable(url_fetcher)
        return _FakeHtmlDocument(url_fetcher=url_fetcher)

    def _fake_css_factory(*, filename: str) -> object:
        del filename
        return object()

    def _fake_default_url_fetcher(
        url: str,
        timeout: int = 10,
        ssl_context: object | None = None,
        http_headers: object | None = None,
    ) -> dict[str, object]:
        del timeout, ssl_context, http_headers
        fetched_urls.append(url)
        return {"string": b""}

    monkeypatch.setattr(
        weasyprint_html_to_pdf,
        "_load_weasyprint",
        lambda: (_fake_html_factory, _fake_css_factory, _fake_default_url_fetcher),
    )


def test_convert_html_to_pdf_allows_local_resource_within_workdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    local_image = tmp_path / "assets" / "logo.png"
    local_image.parent.mkdir(parents=True)
    local_image.write_bytes(b"\x89PNG")
    output_pdf = tmp_path / "out.pdf"
    fetched_urls: list[str] = []

    _install_fake_loader(
        monkeypatch,
        resource_url_to_fetch=local_image.resolve().as_uri(),
        fetched_urls=fetched_urls,
    )

    convert_html_to_pdf(
        html_path=html_path,
        output_pdf_path=output_pdf,
        allowed_resource_root=tmp_path,
    )

    assert output_pdf.exists()
    assert fetched_urls == [local_image.resolve().as_uri()]


def test_convert_html_to_pdf_uses_filename_loading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    local_image = tmp_path / "assets" / "logo.png"
    local_image.parent.mkdir(parents=True)
    local_image.write_bytes(b"\x89PNG")
    output_pdf = tmp_path / "out.pdf"
    fetched_urls: list[str] = []
    html_factory_calls: list[dict[str, object]] = []

    _install_fake_loader(
        monkeypatch,
        resource_url_to_fetch=local_image.resolve().as_uri(),
        fetched_urls=fetched_urls,
        html_factory_calls=html_factory_calls,
    )

    convert_html_to_pdf(
        html_path=html_path,
        output_pdf_path=output_pdf,
        allowed_resource_root=tmp_path,
    )

    assert output_pdf.exists()
    assert fetched_urls == [local_image.resolve().as_uri()]
    assert len(html_factory_calls) == 1
    assert html_factory_calls[0]["filename"] == html_path.as_posix()
    assert "string" not in html_factory_calls[0]


def test_convert_html_to_pdf_blocks_external_http_resource(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_pdf = tmp_path / "out.pdf"
    fetched_urls: list[str] = []

    _install_fake_loader(
        monkeypatch,
        resource_url_to_fetch="http://169.254.169.254/latest/meta-data/",
        fetched_urls=fetched_urls,
    )

    with pytest.raises(HtmlToPdfConversionError) as exc_info:
        convert_html_to_pdf(
            html_path=html_path,
            output_pdf_path=output_pdf,
            allowed_resource_root=tmp_path,
        )

    error = exc_info.value
    assert error.code == HTML_TO_PDF_RESOURCE_BLOCKED
    assert fetched_urls == []


def test_convert_html_to_pdf_blocks_file_resource_outside_workdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    output_pdf = tmp_path / "out.pdf"
    fetched_urls: list[str] = []

    _install_fake_loader(
        monkeypatch,
        resource_url_to_fetch=outside.resolve().as_uri(),
        fetched_urls=fetched_urls,
    )

    with pytest.raises(HtmlToPdfConversionError) as exc_info:
        convert_html_to_pdf(
            html_path=html_path,
            output_pdf_path=output_pdf,
            allowed_resource_root=tmp_path,
        )

    error = exc_info.value
    assert error.code == HTML_TO_PDF_RESOURCE_BLOCKED
    assert fetched_urls == []
