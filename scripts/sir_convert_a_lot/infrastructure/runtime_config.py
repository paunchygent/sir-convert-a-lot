"""Runtime configuration and fingerprint helpers.

Purpose:
    Keep environment-based runtime configuration resolution and request
    fingerprint logic separate from runtime orchestration concerns.

Relationships:
    - Imported by `infrastructure.runtime_engine`.
    - Produces `ServiceConfig` and idempotency fingerprint inputs used by HTTP API.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from scripts.sir_convert_a_lot.application.public_exam_converter_access_policy_v2 import (
    PublicExamConverterAccessProfileV2,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import OcrEngineV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import (
    PublicExamConverterRuntimeAccessConfig,
    ServiceConfig,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    structured_llm_runtime_config_from_env,
)

CPU_UNLOCK_ENV_VARS: tuple[str, str] = (
    "SIR_CONVERT_A_LOT_ALLOW_CPU_ONLY",
    "SIR_CONVERT_A_LOT_ALLOW_CPU_FALLBACK",
)

_BOOL_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_BOOL_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _parse_bool_env(*, name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _BOOL_TRUE_VALUES:
        return True
    if normalized in _BOOL_FALSE_VALUES:
        return False
    raise ValueError(
        f"Invalid boolean value for {name}: {raw!r}. Use one of: 1/0, true/false, yes/no, on/off."
    )


def _parse_bounded_int_env(
    *,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {name}: {raw!r}.") from exc
    if value < minimum or value > maximum:
        raise ValueError(
            f"Invalid value for {name}: {value}. Expected range [{minimum}, {maximum}]."
        )
    return value


def _normalize_pem_text(value: str, *, field_name: str) -> str:
    """Normalize PEM text supplied inline or through JSON environment values."""

    normalized = value.strip().replace("\\n", "\n")
    if normalized == "":
        raise ValueError(f"{field_name} must not be empty when configured")
    return normalized


def _read_public_key_path(value: str, *, field_name: str) -> str:
    path = Path(value.strip())
    if not path.exists():
        raise ValueError(f"{field_name} points to a missing file: {path}")
    return _normalize_pem_text(path.read_text(encoding="utf-8"), field_name=field_name)


def _internal_identity_public_keys_from_env() -> dict[str, str]:
    """Return configured HuleEdu internal-identity public keys by key id."""

    public_keys: dict[str, str] = {}
    trusted_json = os.getenv("HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON")
    if trusted_json is not None and trusted_json.strip() != "":
        try:
            decoded = json.loads(trusted_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON must be valid JSON"
            ) from exc
        if not isinstance(decoded, dict):
            raise ValueError(
                "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON must decode to an object"
            )
        for raw_key_id, raw_public_key in decoded.items():
            if not isinstance(raw_key_id, str) or not isinstance(raw_public_key, str):
                raise ValueError(
                    "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON entries must map "
                    "string key ids to PEM strings"
                )
            key_id = raw_key_id.strip()
            if key_id == "":
                raise ValueError(
                    "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON contains a blank key id"
                )
            public_keys[key_id] = _normalize_pem_text(
                raw_public_key,
                field_name=f"HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON[{key_id}]",
            )

    signing_key_id = os.getenv(
        "HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID", "gateway-identity-rs256-v1"
    ).strip()
    inline_public_key = os.getenv("HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY")
    public_key_path = os.getenv("HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH")
    if inline_public_key is not None and inline_public_key.strip() != "":
        public_keys.setdefault(
            signing_key_id,
            _normalize_pem_text(
                inline_public_key,
                field_name="HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY",
            ),
        )
    elif public_key_path is not None and public_key_path.strip() != "":
        public_keys.setdefault(
            signing_key_id,
            _read_public_key_path(
                public_key_path,
                field_name="HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH",
            ),
        )
    return public_keys


def _public_exam_converter_grant_public_keys_from_env() -> dict[str, str]:
    """Return HuleEdu public Exam Converter grant verification keys by key id."""

    public_keys: dict[str, str] = {}
    trusted_json = os.getenv("SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEYS_JSON")
    if trusted_json is not None and trusted_json.strip() != "":
        try:
            decoded = json.loads(trusted_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEYS_JSON must be valid JSON"
            ) from exc
        if not isinstance(decoded, dict):
            raise ValueError(
                "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEYS_JSON must decode to an object"
            )
        for raw_key_id, raw_public_key in decoded.items():
            if not isinstance(raw_key_id, str) or not isinstance(raw_public_key, str):
                raise ValueError(
                    "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEYS_JSON entries "
                    "must map string key ids to PEM strings"
                )
            key_id = raw_key_id.strip()
            if key_id == "":
                raise ValueError(
                    "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEYS_JSON "
                    "contains a blank key id"
                )
            public_keys[key_id] = _normalize_pem_text(
                raw_public_key,
                field_name=(f"SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEYS_JSON[{key_id}]"),
            )

    signing_key_id = os.getenv(
        "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_SIGNING_KEY_ID",
        "gateway-identity-rs256-v1",
    ).strip()
    inline_public_key = os.getenv("SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEY")
    public_key_path = os.getenv("SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEY_PATH")
    if inline_public_key is not None and inline_public_key.strip() != "":
        public_keys.setdefault(
            signing_key_id,
            _normalize_pem_text(
                inline_public_key,
                field_name="SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEY",
            ),
        )
    elif public_key_path is not None and public_key_path.strip() != "":
        public_keys.setdefault(
            signing_key_id,
            _read_public_key_path(
                public_key_path,
                field_name="SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_PUBLIC_KEY_PATH",
            ),
        )
    return public_keys


def _public_exam_converter_access_from_env(
    *,
    allowed_clock_skew_seconds: int,
) -> PublicExamConverterRuntimeAccessConfig | None:
    """Return public Exam Converter access config when explicitly configured."""

    public_keys = _public_exam_converter_grant_public_keys_from_env()
    lease_secret = os.getenv("SIR_CONVERT_PUBLIC_EXAM_CONVERTER_ARTIFACT_READ_LEASE_SECRET")
    public_env_present = bool(public_keys) or (lease_secret is not None and lease_secret.strip())
    if not public_env_present:
        return None
    if not public_keys:
        raise ValueError("Public Exam Converter grant verification keys must be configured")
    if lease_secret is None or lease_secret.strip() == "":
        raise ValueError("Public Exam Converter artifact-read lease secret must be configured")

    grant_max_ttl_seconds = _parse_bounded_int_env(
        name="SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_MAX_TTL_SECONDS",
        default=300,
        minimum=1,
        maximum=3600,
    )
    lease_max_seconds = _parse_bounded_int_env(
        name="SIR_CONVERT_PUBLIC_EXAM_CONVERTER_ARTIFACT_READ_LEASE_MAX_SECONDS",
        default=1800,
        minimum=1,
        maximum=86_400,
    )
    profile = PublicExamConverterAccessProfileV2(
        grant_expected_issuer=os.getenv(
            "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_ISSUER",
            "api_gateway_service",
        ).strip()
        or "api_gateway_service",
        grant_expected_audience=os.getenv(
            "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_GRANT_AUDIENCE",
            "sir-convert-a-lot",
        ).strip()
        or "sir-convert-a-lot",
        grant_expected_policy_version=os.getenv(
            "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_POLICY_VERSION",
            "public-exam-converter-2026-05-13",
        ).strip()
        or "public-exam-converter-2026-05-13",
        grant_max_ttl_seconds=grant_max_ttl_seconds,
        allowed_clock_skew_seconds=allowed_clock_skew_seconds,
        artifact_read_lease_issuer=os.getenv(
            "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_ARTIFACT_READ_LEASE_ISSUER",
            "sir-convert-a-lot",
        ).strip()
        or "sir-convert-a-lot",
        artifact_read_lease_audience=os.getenv(
            "SIR_CONVERT_PUBLIC_EXAM_CONVERTER_ARTIFACT_READ_LEASE_AUDIENCE",
            "sir-convert-public-artifact-read",
        ).strip()
        or "sir-convert-public-artifact-read",
        artifact_read_lease_max_seconds=lease_max_seconds,
    )
    return PublicExamConverterRuntimeAccessConfig(
        profile=profile,
        grant_public_keys=public_keys,
        artifact_read_lease_secret=lease_secret.strip(),
    )


def fingerprint_for_request(spec_payload: dict[str, object], file_sha256: str) -> str:
    """Create deterministic idempotency fingerprint for a create-job request."""
    normalized = json.dumps(spec_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{normalized}:{file_sha256}".encode("utf-8")).hexdigest()


def service_config_from_env() -> ServiceConfig:
    """Load runtime configuration from environment variables."""
    api_key = os.getenv("SIR_CONVERT_A_LOT_V2_API_KEY", "dev-only-key")
    data_root = Path(
        os.getenv("CONVERTER_STORAGE_ROOT")
        or os.getenv("SIR_CONVERT_A_LOT_DATA_DIR")
        or "build/sir_convert_a_lot"
    )
    gpu_available = os.getenv("SIR_CONVERT_A_LOT_GPU_AVAILABLE", "1") == "1"
    max_workers = _parse_bounded_int_env(
        name="SIR_CONVERT_A_LOT_MAX_WORKERS",
        default=1,
        minimum=1,
        maximum=64,
    )
    enable_parallel_pdf_chunks = _parse_bool_env(
        name="SIR_CONVERT_A_LOT_ENABLE_PARALLEL_PDF_CHUNKS",
        default=False,
    )
    max_chunk_workers = _parse_bounded_int_env(
        name="SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS",
        default=1,
        minimum=1,
        maximum=32,
    )
    pdf_chunk_size_pages = _parse_bounded_int_env(
        name="SIR_CONVERT_A_LOT_PDF_CHUNK_SIZE_PAGES",
        default=10,
        minimum=1,
        maximum=500,
    )
    gpu_stage_max_concurrency = _parse_bounded_int_env(
        name="SIR_CONVERT_A_LOT_GPU_STAGE_MAX_CONCURRENCY",
        default=max_workers,
        minimum=1,
        maximum=64,
    )
    enable_sse_stream = os.getenv("SIR_CONVERT_A_LOT_ENABLE_SSE_STREAM", "0") == "1"
    sse_replay_horizon_seconds = int(
        os.getenv("SIR_CONVERT_A_LOT_SSE_REPLAY_HORIZON_SECONDS", str(24 * 3600))
    )
    sse_poll_interval_seconds = float(
        os.getenv("SIR_CONVERT_A_LOT_SSE_POLL_INTERVAL_SECONDS", "0.05")
    )
    sse_stream_max_seconds = float(os.getenv("SIR_CONVERT_A_LOT_SSE_STREAM_MAX_SECONDS", "15.0"))
    enable_webhook_onboarding = os.getenv("SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_ONBOARDING", "0") == "1"
    webhook_secret_overlap_seconds = int(
        os.getenv("SIR_CONVERT_A_LOT_WEBHOOK_SECRET_OVERLAP_SECONDS", str(24 * 3600))
    )
    enable_webhook_delivery = os.getenv("SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_DELIVERY", "0") == "1"
    internal_identity_ttl_seconds = _parse_bounded_int_env(
        name="HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS",
        default=60,
        minimum=1,
        maximum=3600,
    )
    internal_identity_allowed_clock_skew_seconds = _parse_bounded_int_env(
        name="HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS",
        default=5,
        minimum=0,
        maximum=300,
    )

    default_ocr_engine_raw = os.getenv("SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE", "auto").strip()
    default_pdf_ocr_engine = OcrEngineV2.AUTO
    if default_ocr_engine_raw:
        try:
            default_pdf_ocr_engine = OcrEngineV2(default_ocr_engine_raw.lower())
        except ValueError as exc:
            supported = ", ".join(engine.value for engine in OcrEngineV2)
            raise ValueError(
                f"Invalid SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE. Use one of: {supported}."
            ) from exc

    default_lang_raw = os.getenv("SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES", "en")
    default_pdf_ocr_languages: list[str] = []
    for raw in default_lang_raw.split(","):
        candidate = raw.strip().lower()
        if candidate == "":
            continue
        parts = candidate.split("-")
        primary = parts[0]
        if len(primary) != 2 or not primary.isalpha():
            raise ValueError(
                "Invalid SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES entry. "
                "Expected BCP47/ISO639-1 tags like 'sv' or 'en'."
            )
        if candidate not in default_pdf_ocr_languages:
            default_pdf_ocr_languages.append(candidate)

    easyocr_model_storage_directory_raw = os.getenv("SIR_CONVERT_A_LOT_EASYOCR_MODEL_STORAGE_DIR")
    if easyocr_model_storage_directory_raw is None:
        easyocr_model_storage_directory = "/opt/easyocr-models"
    else:
        easyocr_model_storage_directory = easyocr_model_storage_directory_raw.strip()
        if easyocr_model_storage_directory == "":
            easyocr_model_storage_directory = None

    enabled_unlock_envs = [name for name in CPU_UNLOCK_ENV_VARS if os.getenv(name) == "1"]
    if enabled_unlock_envs:
        joined_names = ", ".join(enabled_unlock_envs)
        raise ValueError(
            "CPU unlock env vars are disabled during GPU-first rollout lock: "
            f"{joined_names}. Use explicit ServiceConfig test overrides instead."
        )

    return ServiceConfig(
        api_key=api_key,
        data_root=data_root,
        max_workers=max_workers,
        enable_parallel_pdf_chunks=enable_parallel_pdf_chunks,
        max_chunk_workers=max_chunk_workers,
        pdf_chunk_size_pages=pdf_chunk_size_pages,
        gpu_stage_max_concurrency=gpu_stage_max_concurrency,
        gpu_available=gpu_available,
        enable_sse_stream=enable_sse_stream,
        sse_replay_horizon_seconds=sse_replay_horizon_seconds,
        sse_poll_interval_seconds=sse_poll_interval_seconds,
        sse_stream_max_seconds=sse_stream_max_seconds,
        enable_webhook_onboarding=enable_webhook_onboarding,
        webhook_secret_overlap_seconds=webhook_secret_overlap_seconds,
        enable_webhook_delivery=enable_webhook_delivery,
        default_pdf_ocr_engine=default_pdf_ocr_engine,
        default_pdf_ocr_languages=tuple(default_pdf_ocr_languages),
        easyocr_model_storage_directory=easyocr_model_storage_directory,
        internal_identity_public_keys=_internal_identity_public_keys_from_env(),
        internal_identity_expected_audience=os.getenv(
            "HULEEDU_INTERNAL_IDENTITY_AUDIENCE", "sir-convert-a-lot"
        ).strip()
        or "sir-convert-a-lot",
        internal_identity_expected_issuer=os.getenv(
            "HULEEDU_INTERNAL_IDENTITY_ISSUER", "api_gateway_service"
        ).strip()
        or "api_gateway_service",
        internal_identity_ttl_seconds=internal_identity_ttl_seconds,
        internal_identity_allowed_clock_skew_seconds=internal_identity_allowed_clock_skew_seconds,
        public_exam_converter_access=_public_exam_converter_access_from_env(
            allowed_clock_skew_seconds=internal_identity_allowed_clock_skew_seconds,
        ),
        structured_llm=structured_llm_runtime_config_from_env(),
    )
