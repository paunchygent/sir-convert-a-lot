"""WeasyPrint-backed HTML(+CSS) to PDF conversion.

Purpose:
    Provide a local, deterministic HTML(+CSS) -> PDF converter for the canonical
    Sir Convert-a-Lot CLI routes.

Relationships:
    - Called by `scripts.sir_convert_a_lot.interfaces.cli_app` for the
      `html -> pdf` local route (Task 32).
    - Must not affect the locked PDF->MD service v1 contract; this is a purely
      local execution utility.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlparse

WEASYPRINT_NOT_INSTALLED = "weasyprint_not_installed"
WEASYPRINT_NATIVE_DEPS_MISSING = "weasyprint_native_deps_missing"
HTML_TO_PDF_FAILED = "html_to_pdf_failed"
HTML_TO_PDF_RESOURCE_BLOCKED = "html_to_pdf_resource_blocked"


@dataclass(frozen=True)
class HtmlToPdfConversionError(Exception):
    """Typed, deterministic error for local HTML->PDF conversion failures."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial and stable
        return f"{self.code}: {self.message}"


class _HtmlDocument(Protocol):
    def write_pdf(
        self, target: str, *, stylesheets: list[object] | None = None
    ) -> bytes | None: ...


class _UrlFetcher(Protocol):
    def __call__(
        self,
        url: str,
        timeout: int = 10,
        ssl_context: object | None = None,
        http_headers: object | None = None,
    ) -> dict[str, object]: ...


class _HtmlFactory(Protocol):
    def __call__(
        self,
        *,
        filename: str,
        base_url: str,
        url_fetcher: _UrlFetcher,
    ) -> _HtmlDocument: ...


class _CssFactory(Protocol):
    def __call__(self, *, filename: str) -> object: ...


def _load_weasyprint() -> tuple[_HtmlFactory, _CssFactory, _UrlFetcher]:
    try:
        from weasyprint import CSS, HTML, default_url_fetcher
    except ModuleNotFoundError as exc:
        raise HtmlToPdfConversionError(
            code=WEASYPRINT_NOT_INSTALLED,
            message="WeasyPrint is not installed. Add the 'weasyprint' dependency.",
        ) from exc
    except OSError as exc:
        raise HtmlToPdfConversionError(
            code=WEASYPRINT_NATIVE_DEPS_MISSING,
            message=f"WeasyPrint native dependencies are missing: {exc}",
        ) from exc

    return HTML, CSS, default_url_fetcher


def _build_restricted_url_fetcher(
    *,
    allowed_resource_root: Path,
    default_url_fetcher: _UrlFetcher,
) -> _UrlFetcher:
    resolved_root = allowed_resource_root.resolve()

    def _restricted_url_fetcher(
        url: str,
        timeout: int = 10,
        ssl_context: object | None = None,
        http_headers: object | None = None,
    ) -> dict[str, object]:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        if scheme in {"http", "https", "ftp", "data", "mailto", "tel", "javascript"}:
            raise HtmlToPdfConversionError(
                code=HTML_TO_PDF_RESOURCE_BLOCKED,
                message=f"Blocked external resource URL: {url}",
            )

        if scheme not in {"", "file"}:
            raise HtmlToPdfConversionError(
                code=HTML_TO_PDF_RESOURCE_BLOCKED,
                message=f"Blocked unsupported resource URL scheme: {url}",
            )

        if scheme == "file" and parsed.netloc not in {"", "localhost"}:
            raise HtmlToPdfConversionError(
                code=HTML_TO_PDF_RESOURCE_BLOCKED,
                message=f"Blocked file URL with unsupported host component: {url}",
            )

        candidate_str = unquote(parsed.path).strip()
        if candidate_str == "":
            raise HtmlToPdfConversionError(
                code=HTML_TO_PDF_RESOURCE_BLOCKED,
                message=f"Blocked empty resource URL: {url}",
            )

        candidate_path = Path(candidate_str)
        if not candidate_path.is_absolute():
            candidate_path = resolved_root / candidate_path

        resolved_candidate = candidate_path.resolve()
        if not resolved_candidate.is_relative_to(resolved_root):
            raise HtmlToPdfConversionError(
                code=HTML_TO_PDF_RESOURCE_BLOCKED,
                message=f"Blocked resource path outside allowed workdir: {url}",
            )

        return default_url_fetcher(
            resolved_candidate.as_uri(),
            timeout=timeout,
            ssl_context=ssl_context,
            http_headers=http_headers,
        )

    return _restricted_url_fetcher


def convert_html_to_pdf(
    *,
    html_path: Path,
    output_pdf_path: Path,
    css_paths: tuple[Path, ...] = (),
    base_url: str | None = None,
    allowed_resource_root: Path | None = None,
) -> None:
    """Convert a local HTML file (+ optional CSS files) into a PDF."""

    HTML, CSS, default_url_fetcher = _load_weasyprint()

    resolved_base_url = base_url or html_path.parent.resolve().as_uri()
    stylesheets = [CSS(filename=css_path.as_posix()) for css_path in css_paths]
    resolved_allowed_resource_root = (
        html_path.parent.resolve()
        if allowed_resource_root is None
        else allowed_resource_root.resolve()
    )
    restricted_url_fetcher = _build_restricted_url_fetcher(
        allowed_resource_root=resolved_allowed_resource_root,
        default_url_fetcher=default_url_fetcher,
    )

    try:
        HTML(
            filename=html_path.as_posix(),
            base_url=resolved_base_url,
            url_fetcher=restricted_url_fetcher,
        ).write_pdf(
            output_pdf_path.as_posix(),
            stylesheets=stylesheets,
        )
    except HtmlToPdfConversionError:
        raise
    except OSError as exc:
        raise HtmlToPdfConversionError(
            code=WEASYPRINT_NATIVE_DEPS_MISSING,
            message=f"WeasyPrint native dependencies are missing: {exc}",
        ) from exc
    except Exception as exc:
        raise HtmlToPdfConversionError(
            code=HTML_TO_PDF_FAILED,
            message=f"Failed to convert HTML to PDF: {type(exc).__name__}: {exc}",
        ) from exc
