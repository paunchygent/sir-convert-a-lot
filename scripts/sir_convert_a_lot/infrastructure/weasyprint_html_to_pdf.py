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

WEASYPRINT_NOT_INSTALLED = "weasyprint_not_installed"
WEASYPRINT_NATIVE_DEPS_MISSING = "weasyprint_native_deps_missing"
HTML_TO_PDF_FAILED = "html_to_pdf_failed"


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


class _HtmlFactory(Protocol):
    def __call__(self, *, filename: str, base_url: str) -> _HtmlDocument: ...


class _CssFactory(Protocol):
    def __call__(self, *, filename: str) -> object: ...


def _load_weasyprint() -> tuple[_HtmlFactory, _CssFactory]:
    try:
        from weasyprint import CSS, HTML
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

    return HTML, CSS


def convert_html_to_pdf(
    *,
    html_path: Path,
    output_pdf_path: Path,
    css_paths: tuple[Path, ...] = (),
    base_url: str | None = None,
) -> None:
    """Convert a local HTML file (+ optional CSS files) into a PDF."""

    HTML, CSS = _load_weasyprint()

    resolved_base_url = base_url or html_path.parent.resolve().as_uri()
    stylesheets = [CSS(filename=css_path.as_posix()) for css_path in css_paths]

    try:
        HTML(filename=html_path.as_posix(), base_url=resolved_base_url).write_pdf(
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
