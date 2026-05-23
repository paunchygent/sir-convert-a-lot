"""OCR preflight gates for service API v2 PDF conversions.

Purpose:
    Fail fast on OCR engine/language drift so operators do not spend hours
    running large OCR batches that are guaranteed to produce incorrect output.

Relationships:
    - Called by `infrastructure.runtime_engine_v2.ServiceRuntimeV2.create_job`
      before persisting a new job when OCR may be executed.
    - Uses `infrastructure.ocr_resolution_v2` as the single source of truth for
      effective engine/language selection.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OcrEngineV2
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import probe_torch_gpu_runtime
from scripts.sir_convert_a_lot.infrastructure.ocr_language_mapping_v2 import (
    map_bcp47_languages_to_tesseract,
)
from scripts.sir_convert_a_lot.infrastructure.ocr_resolution_v2 import (
    ResolvedPdfOcrRequestV2,
    resolve_pdf_ocr_request,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError

_tesseract_lock = threading.Lock()
_cached_tesseract_languages: set[str] | None = None

_easyocr_lock = threading.Lock()
_cached_easyocr_languages: set[str] | None = None


@dataclass(frozen=True)
class OcrPreflightOutcomeV2:
    """Resolved OCR configuration returned by a successful preflight."""

    resolved: ResolvedPdfOcrRequestV2
    tesseract_languages: tuple[str, ...] | None = None


def _tesseract_available_languages() -> set[str]:
    global _cached_tesseract_languages
    with _tesseract_lock:
        if _cached_tesseract_languages is not None:
            return set(_cached_tesseract_languages)

        tesseract_path = shutil.which("tesseract")
        if tesseract_path is None:
            raise ServiceError(
                status_code=503,
                code="ocr_engine_unavailable",
                message="Tesseract OCR engine is not installed in this runtime.",
                retryable=False,
                details={
                    "engine": "tesseract_cli",
                    "remediation": "install tesseract-ocr + language packs",
                },
            )

        result = subprocess.run(
            [tesseract_path, "--list-langs"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ServiceError(
                status_code=503,
                code="ocr_engine_unavailable",
                message="Failed to query tesseract language packs via `tesseract --list-langs`.",
                retryable=False,
                details={
                    "engine": "tesseract_cli",
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                },
            )

        langs: set[str] = set()
        for line in result.stdout.splitlines():
            candidate = line.strip()
            if candidate == "" or candidate.lower().startswith("list of available languages"):
                continue
            langs.add(candidate)

        _cached_tesseract_languages = set(langs)
        return set(langs)


def _easyocr_supported_languages() -> set[str]:
    global _cached_easyocr_languages
    with _easyocr_lock:
        if _cached_easyocr_languages is not None:
            return set(_cached_easyocr_languages)

        try:
            import importlib

            easyocr = importlib.import_module("easyocr")
            if not isinstance(easyocr, ModuleType):
                raise TypeError("easyocr import returned non-module")
        except Exception as exc:
            raise ServiceError(
                status_code=503,
                code="ocr_engine_unavailable",
                message="EasyOCR engine is not installed in this runtime.",
                retryable=False,
                details={
                    "engine": "easyocr",
                    "remediation": "install easyocr in the runtime image",
                },
            ) from exc

        supported: object = getattr(getattr(easyocr, "config", None), "all_lang_list", None)
        if not isinstance(supported, list) or not all(isinstance(item, str) for item in supported):
            raise ServiceError(
                status_code=503,
                code="ocr_engine_unavailable",
                message=(
                    "EasyOCR supported language list could not be read from "
                    "easyocr.config.all_lang_list."
                ),
                retryable=False,
                details={"engine": "easyocr"},
            )

        langs = set(item.strip().lower() for item in supported if item.strip() != "")
        _cached_easyocr_languages = set(langs)
        return set(langs)


def preflight_pdf_ocr_or_raise(
    *, spec: JobSpecV2, config: ServiceConfig, enforce_local_gpu_runtime: bool = True
) -> OcrPreflightOutcomeV2 | None:
    """Run OCR preflight for a v2 job, raising ServiceError on failures."""
    try:
        resolved = resolve_pdf_ocr_request(spec=spec, config=config)
    except ValueError as exc:
        raise ServiceError(
            status_code=422,
            code="validation_error",
            message=str(exc),
            retryable=False,
        ) from exc
    if resolved is None:
        return None

    if (
        spec.execution is not None
        and spec.execution.acceleration_policy
        in {
            AccelerationPolicy.GPU_REQUIRED,
            AccelerationPolicy.GPU_PREFER,
        }
        and enforce_local_gpu_runtime
    ):
        if not config.gpu_available:
            if not config.allow_cpu_fallback:
                raise ServiceError(
                    status_code=503,
                    code="gpu_not_available",
                    message="GPU execution is required and no fallback is currently allowed.",
                    retryable=True,
                )
        else:
            probe = probe_torch_gpu_runtime()
            if not (probe.is_available and probe.runtime_kind in {"rocm", "cuda"}):
                raise ServiceError(
                    status_code=503,
                    code="gpu_not_available",
                    message="GPU runtime is unavailable for OCR under GPU policy.",
                    retryable=True,
                    details={
                        "reason": "ocr_gpu_runtime_unavailable",
                        "runtime_kind": probe.runtime_kind,
                        "hip_version": probe.hip_version,
                        "cuda_version": probe.cuda_version,
                    },
                )

    if resolved.engine == OcrEngineV2.TESSERACT_CLI:
        try:
            tesseract_langs = map_bcp47_languages_to_tesseract(resolved.languages)
        except ValueError as exc:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message=str(exc),
                retryable=False,
                details={"field": "pdf_options.ocr_languages", "engine": "tesseract_cli"},
            ) from exc
        available = _tesseract_available_languages()
        missing = sorted(lang for lang in tesseract_langs if lang not in available)
        if missing:
            raise ServiceError(
                status_code=503,
                code="ocr_language_unavailable",
                message="Requested Tesseract language pack(s) are not installed in this runtime.",
                retryable=False,
                details={
                    "engine": "tesseract_cli",
                    "missing": missing,
                    "requested": list(tesseract_langs),
                    "remediation": (
                        "install tesseract language packs (e.g. tesseract-ocr-swe, "
                        "tesseract-ocr-eng)"
                    ),
                },
            )
        return OcrPreflightOutcomeV2(resolved=resolved, tesseract_languages=tesseract_langs)

    if resolved.engine == OcrEngineV2.EASYOCR:
        supported = _easyocr_supported_languages()
        missing = sorted(lang for lang in resolved.languages if lang not in supported)
        if missing:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="Requested EasyOCR language(s) are not supported.",
                retryable=False,
                details={
                    "field": "pdf_options.ocr_languages",
                    "engine": "easyocr",
                    "missing": missing,
                },
            )

        model_dir = config.easyocr_model_storage_directory
        if model_dir is not None:
            candidate = Path(model_dir).expanduser()
            if not candidate.exists():
                raise ServiceError(
                    status_code=503,
                    code="ocr_engine_unavailable",
                    message=(
                        "EasyOCR model storage directory is missing while downloads are disabled."
                    ),
                    retryable=False,
                    details={
                        "engine": "easyocr",
                        "model_storage_directory": str(candidate),
                        "remediation": (
                            "warm up EasyOCR models at image build time or set "
                            "SIR_CONVERT_A_LOT_EASYOCR_MODEL_STORAGE_DIR"
                        ),
                    },
                )

        return OcrPreflightOutcomeV2(resolved=resolved, tesseract_languages=None)

    return OcrPreflightOutcomeV2(resolved=resolved, tesseract_languages=None)
