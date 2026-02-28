"""HTML local-resource reference validation helpers.

Purpose:
    Parse uploaded HTML content and deterministically validate local resource
    references against the extracted job workdir used by v2 conversion routes.

Relationships:
    - Used by `infrastructure.v2_conversion_executor` for the `html -> md`
      branch to emit stable 422 validation failures for missing/invalid local
      resources before converter execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

_RESOURCE_ATTRS = frozenset({"src", "href", "poster", "data"})
_SRCSET_ATTRS = frozenset({"srcset"})
_IGNORED_SCHEMES = frozenset({"http", "https", "mailto", "tel", "javascript", "data", "ftp"})


class _HtmlReferenceCollector(HTMLParser):
    """Collect raw resource references from HTML attributes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag
        self._collect(attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag
        self._collect(attrs)

    def _collect(self, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value is None:
                continue
            lower_name = name.lower()
            if lower_name in _RESOURCE_ATTRS:
                self.references.add(value)
            elif lower_name in _SRCSET_ATTRS:
                self.references.update(_split_srcset_candidates(value))


@dataclass(frozen=True)
class HtmlResourceValidationResult:
    """Result of local-resource validation for one HTML input file."""

    missing_references: list[str]
    invalid_references: list[str]


def _split_srcset_candidates(value: str) -> set[str]:
    candidates: set[str] = set()
    for segment in value.split(","):
        token = segment.strip()
        if token == "":
            continue
        candidate = token.split(maxsplit=1)[0].strip()
        if candidate != "":
            candidates.add(candidate)
    return candidates


def _is_external_reference(reference: str) -> bool:
    trimmed = reference.strip()
    if trimmed == "" or trimmed.startswith("#"):
        return True
    if trimmed.startswith("//"):
        return True
    parsed = urlparse(trimmed)
    scheme = parsed.scheme.lower()
    if scheme in _IGNORED_SCHEMES:
        return True
    return parsed.scheme != "" and parsed.scheme.lower() != "file"


def _resolve_local_reference(
    *,
    reference: str,
    html_path: Path,
    resource_root: Path,
) -> Path | None:
    parsed = urlparse(reference.strip())
    reference_path = unquote(parsed.path).strip()
    if reference_path == "":
        return None

    if parsed.scheme.lower() == "file":
        candidate = Path(reference_path)
        if not candidate.is_absolute():
            candidate = html_path.parent / candidate
    elif reference_path.startswith("/"):
        candidate = resource_root / reference_path.lstrip("/")
    else:
        candidate = html_path.parent / reference_path

    resolved_candidate = candidate.resolve()
    resolved_root = resource_root.resolve()
    if not resolved_candidate.is_relative_to(resolved_root):
        return None
    return resolved_candidate


def validate_html_local_resources(
    *,
    html_path: Path,
    resource_root: Path,
) -> HtmlResourceValidationResult:
    """Validate local HTML references and return missing/invalid lists."""

    collector = _HtmlReferenceCollector()
    collector.feed(html_path.read_text(encoding="utf-8", errors="replace"))

    missing_references: list[str] = []
    invalid_references: list[str] = []

    for reference in sorted(collector.references):
        if _is_external_reference(reference):
            continue

        resolved = _resolve_local_reference(
            reference=reference,
            html_path=html_path,
            resource_root=resource_root,
        )
        if resolved is None:
            invalid_references.append(reference)
            continue
        if not resolved.exists():
            missing_references.append(reference)

    return HtmlResourceValidationResult(
        missing_references=missing_references,
        invalid_references=invalid_references,
    )
