"""Unit tests for v2 OCR preflight gates.

Purpose:
    Validate fail-fast behavior for OCR engine/language selection so operators
    do not spend hours running large OCR batches that are guaranteed to produce
    incorrect output.

Relationships:
    - Tests `scripts.sir_convert_a_lot.infrastructure.ocr_preflight_v2`.
    - Complements v2 API contract tests by exercising the preflight logic
      without requiring a live OCR engine runtime.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure import ocr_preflight_v2
from scripts.sir_convert_a_lot.infrastructure.ocr_preflight_v2 import preflight_pdf_ocr_or_raise
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError


class _EasyOcrConfigStub:
    def __init__(self, all_lang_list: list[str]) -> None:
        self.all_lang_list = all_lang_list


class _EasyOcrStub(ModuleType):
    config: _EasyOcrConfigStub

    def __init__(self, all_lang_list: list[str]) -> None:
        super().__init__("easyocr")
        self.config = _EasyOcrConfigStub(all_lang_list)


def _pdf_job_spec(
    *,
    ocr_engine: str,
    ocr_languages: list[str],
    acceleration_policy: str = "cpu_only",
) -> JobSpecV2:
    payload: dict[str, object] = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "paper.pdf", "format": "pdf"},
        "conversion": {"output_format": "md", "css_filenames": []},
        "pdf_options": {
            "backend_strategy": "auto",
            "ocr_mode": "force",
            "ocr_engine": ocr_engine,
            "ocr_languages": ocr_languages,
            "table_mode": "fast",
            "normalize": "standard",
        },
        "execution": {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }
    return JobSpecV2.model_validate(payload)


def test_preflight_tesseract_missing_language_pack_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ocr_preflight_v2, "_cached_tesseract_languages", None)
    monkeypatch.setattr(ocr_preflight_v2.shutil, "which", lambda _name: "/usr/bin/tesseract")
    monkeypatch.setattr(
        ocr_preflight_v2.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout="List of available languages (1):\neng\n",
            stderr="",
        ),
    )

    spec = _pdf_job_spec(ocr_engine="tesseract_cli", ocr_languages=["sv", "en"])
    config = ServiceConfig(api_key="secret-key", data_root=tmp_path / "service_data")

    with pytest.raises(ServiceError) as exc_info:
        preflight_pdf_ocr_or_raise(spec=spec, config=config)

    error = exc_info.value
    assert error.status_code == 503
    assert error.code == "ocr_language_unavailable"
    assert error.retryable is False
    details = error.details
    assert isinstance(details, dict)
    assert details.get("engine") == "tesseract_cli"
    assert details.get("missing") == ["swe"]


def test_preflight_tesseract_rejects_unsupported_language_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ocr_preflight_v2, "_cached_tesseract_languages", None)

    spec = _pdf_job_spec(ocr_engine="tesseract_cli", ocr_languages=["fr", "en"])
    config = ServiceConfig(api_key="secret-key", data_root=tmp_path / "service_data")

    with pytest.raises(ServiceError) as exc_info:
        preflight_pdf_ocr_or_raise(spec=spec, config=config)

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "validation_error"
    assert error.retryable is False


def test_preflight_easyocr_missing_dependency_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ocr_preflight_v2, "_cached_easyocr_languages", None)

    original_import = importlib.import_module

    def _import_module(name: str) -> ModuleType:
        if name == "easyocr":
            raise ImportError("easyocr not installed")
        return original_import(name)

    monkeypatch.setattr(importlib, "import_module", _import_module)

    spec = _pdf_job_spec(ocr_engine="easyocr", ocr_languages=["sv", "en"])
    config = ServiceConfig(api_key="secret-key", data_root=tmp_path / "service_data")

    with pytest.raises(ServiceError) as exc_info:
        preflight_pdf_ocr_or_raise(spec=spec, config=config)

    error = exc_info.value
    assert error.status_code == 503
    assert error.code == "ocr_engine_unavailable"
    details = error.details
    assert isinstance(details, dict)
    assert details.get("engine") == "easyocr"


def test_preflight_easyocr_rejects_unsupported_languages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ocr_preflight_v2, "_cached_easyocr_languages", None)

    easyocr_stub = _EasyOcrStub(["en"])

    original_import = importlib.import_module

    def _import_module(name: str) -> ModuleType:
        if name == "easyocr":
            return easyocr_stub
        return original_import(name)

    monkeypatch.setattr(importlib, "import_module", _import_module)

    spec = _pdf_job_spec(ocr_engine="easyocr", ocr_languages=["sv", "en"])
    config = ServiceConfig(api_key="secret-key", data_root=tmp_path / "service_data")

    with pytest.raises(ServiceError) as exc_info:
        preflight_pdf_ocr_or_raise(spec=spec, config=config)

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "validation_error"
    details = error.details
    assert isinstance(details, dict)
    assert details.get("engine") == "easyocr"
    assert details.get("missing") == ["sv"]


def test_preflight_easyocr_requires_model_storage_directory_when_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ocr_preflight_v2, "_cached_easyocr_languages", None)

    easyocr_stub = _EasyOcrStub(["en", "sv"])

    original_import = importlib.import_module

    def _import_module(name: str) -> ModuleType:
        if name == "easyocr":
            return easyocr_stub
        return original_import(name)

    monkeypatch.setattr(importlib, "import_module", _import_module)

    spec = _pdf_job_spec(ocr_engine="easyocr", ocr_languages=["sv", "en"])
    config = ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / "service_data",
        easyocr_model_storage_directory=str(tmp_path / "missing_models"),
    )

    with pytest.raises(ServiceError) as exc_info:
        preflight_pdf_ocr_or_raise(spec=spec, config=config)

    error = exc_info.value
    assert error.status_code == 503
    assert error.code == "ocr_engine_unavailable"


def test_preflight_gpu_required_skips_probe_when_gpu_disabled_and_fallback_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _unexpected_probe() -> object:
        raise AssertionError("probe_torch_gpu_runtime must be skipped for gpu_available=0")

    monkeypatch.setattr(ocr_preflight_v2, "probe_torch_gpu_runtime", _unexpected_probe)

    spec = _pdf_job_spec(ocr_engine="auto", ocr_languages=[], acceleration_policy="gpu_required")
    config = ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / "service_data",
        gpu_available=False,
        allow_cpu_fallback=True,
    )

    outcome = preflight_pdf_ocr_or_raise(spec=spec, config=config)
    assert outcome is not None
    assert outcome.resolved.use_gpu is False


def test_preflight_gpu_required_can_defer_runtime_probe_for_enqueue_only_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _unexpected_probe() -> object:
        raise AssertionError("enqueue-only admission must defer local GPU runtime probing")

    monkeypatch.setattr(ocr_preflight_v2, "probe_torch_gpu_runtime", _unexpected_probe)

    spec = _pdf_job_spec(ocr_engine="auto", ocr_languages=[], acceleration_policy="gpu_required")
    config = ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / "service_data",
        gpu_available=False,
        allow_cpu_fallback=False,
    )

    outcome = preflight_pdf_ocr_or_raise(
        spec=spec,
        config=config,
        enforce_local_gpu_runtime=False,
    )

    assert outcome is not None
    assert outcome.resolved.use_gpu is False


def test_preflight_gpu_required_fails_when_local_runtime_will_execute_without_gpu(
    tmp_path: Path,
) -> None:
    spec = _pdf_job_spec(ocr_engine="auto", ocr_languages=[], acceleration_policy="gpu_required")
    config = ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / "service_data",
        gpu_available=False,
        allow_cpu_fallback=False,
    )

    with pytest.raises(ServiceError) as exc_info:
        preflight_pdf_ocr_or_raise(
            spec=spec,
            config=config,
            enforce_local_gpu_runtime=True,
        )

    error = exc_info.value
    assert error.status_code == 503
    assert error.code == "gpu_not_available"
