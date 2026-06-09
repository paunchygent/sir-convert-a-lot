"""answer-key live validation provider-run metadata contract.

Purpose:
    Preserve the provider profile, runtime, request settings, launch settings,
    capabilities, and artifact paths that produced one answer-key live validation
    run.

Relationships:
    - Built from `infrastructure.answer_key_local_model_profiles` provider
      defaults and the selected `StructuredLLMProviderProfile`.
    - Written by `answer_key_live_corpus_execution` into retained run artifacts.
    - Read by `answer_key_live_evaluation` so adjudication evidence describes the
      evaluated provider without reconstructing a hardcoded model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMThinkingMode,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_local_model_profiles import (
    AnswerKeyProviderDefaults,
    AnswerKeyProviderProfileName,
    AnswerKeyProviderSetting,
    AnswerKeyStructuredProviderRuntime,
    answer_key_defaults_for_provider_profile,
    answer_key_provider_profile_values,
    build_answer_key_provider_profile,
)

ANSWER_KEY_PROVIDER_RUN_METADATA_SCHEMA_VERSION = (
    "answer-key-live-validation_provider_run_metadata_v1"
)


@dataclass(frozen=True)
class AnswerKeyProviderRunMetadata:
    """Serializable provider metadata for one answer-key live validation run."""

    schema_version: str
    available: bool
    metadata_source: str
    profile_name: str | None
    provider_url: str | None
    expected_model_id: str | None
    provider_id: str | None
    model: str | None
    endpoint_kind: str | None
    provider_runtime: str | None
    default_output_mode: str | None
    is_remote: bool | None
    context_window_tokens: int | None
    max_output_tokens: int | None
    temperature: float | None
    capabilities: dict[str, object]
    output_mode_policy: dict[str, object]
    request_settings: dict[str, object]
    launch_settings: dict[str, object]
    artifact_paths: dict[str, object]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON-safe metadata."""

        return {
            "schema_version": self.schema_version,
            "available": self.available,
            "metadata_source": self.metadata_source,
            "profile_name": self.profile_name,
            "provider_url": self.provider_url,
            "expected_model_id": self.expected_model_id,
            "provider_id": self.provider_id,
            "model": self.model,
            "endpoint_kind": self.endpoint_kind,
            "provider_runtime": self.provider_runtime,
            "default_output_mode": self.default_output_mode,
            "is_remote": self.is_remote,
            "context_window_tokens": self.context_window_tokens,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "capabilities": _json_object(self.capabilities),
            "output_mode_policy": _json_object(self.output_mode_policy),
            "request_settings": _json_object(self.request_settings),
            "launch_settings": _json_object(self.launch_settings),
            "artifact_paths": _json_object(self.artifact_paths),
        }

    def to_json(self) -> str:
        """Return canonical JSON for embedding in evaluation artifacts."""

        return _canonical_json(self.to_payload())


def build_answer_key_provider_run_metadata(
    *,
    profile_name: AnswerKeyProviderProfileName,
    defaults: AnswerKeyProviderDefaults,
    provider_url: str,
    provider_runtime: AnswerKeyStructuredProviderRuntime,
    profile: StructuredLLMProviderProfile,
    reports_root: Path,
    vision_media_path: Path | None,
    metadata_source: str = "answer_key_run_report",
) -> AnswerKeyProviderRunMetadata:
    """Build provider-run metadata from selected profile values."""

    artifact_paths: dict[str, object] = {"reports_root": reports_root.as_posix()}
    if vision_media_path is not None:
        artifact_paths["vision_media_path"] = vision_media_path.as_posix()
    launch_settings = _settings_payload(defaults.launch_settings)
    if vision_media_path is not None:
        launch_settings["vision_media_path"] = vision_media_path.as_posix()
    return AnswerKeyProviderRunMetadata(
        schema_version=ANSWER_KEY_PROVIDER_RUN_METADATA_SCHEMA_VERSION,
        available=True,
        metadata_source=metadata_source,
        profile_name=profile_name.value,
        provider_url=provider_url,
        expected_model_id=defaults.expected_model_id,
        provider_id=profile.provider_id,
        model=profile.model,
        endpoint_kind=profile.endpoint_kind.value,
        provider_runtime=provider_runtime.value,
        default_output_mode=profile.output_mode.value,
        is_remote=profile.is_remote,
        context_window_tokens=profile.context_window_tokens,
        max_output_tokens=profile.max_output_tokens,
        temperature=profile.temperature,
        capabilities=_capabilities_payload(profile.capabilities),
        output_mode_policy=_output_mode_policy_payload(profile),
        request_settings=_request_settings_payload(defaults=defaults, profile=profile),
        launch_settings=launch_settings,
        artifact_paths=artifact_paths,
    )


def unavailable_answer_key_provider_run_metadata(
    *,
    metadata_source: str,
) -> AnswerKeyProviderRunMetadata:
    """Return explicit unavailable metadata for report-only evaluation."""

    return AnswerKeyProviderRunMetadata(
        schema_version=ANSWER_KEY_PROVIDER_RUN_METADATA_SCHEMA_VERSION,
        available=False,
        metadata_source=metadata_source,
        profile_name=None,
        provider_url=None,
        expected_model_id=None,
        provider_id=None,
        model=None,
        endpoint_kind=None,
        provider_runtime=None,
        default_output_mode=None,
        is_remote=None,
        context_window_tokens=None,
        max_output_tokens=None,
        temperature=None,
        capabilities={},
        output_mode_policy={},
        request_settings={},
        launch_settings={},
        artifact_paths={},
    )


def load_answer_key_provider_run_metadata_from_report(
    *,
    run_report_path: Path | None,
) -> AnswerKeyProviderRunMetadata:
    """Load provider metadata from a retained run report path when available."""

    if run_report_path is None:
        return unavailable_answer_key_provider_run_metadata(
            metadata_source="run_report_not_provided"
        )
    if not run_report_path.exists():
        return unavailable_answer_key_provider_run_metadata(
            metadata_source=f"run_report_missing:{run_report_path.as_posix()}"
        )
    payload = json.loads(run_report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            f"answer-key live validation run report must be a JSON object: {run_report_path}"
        )
    metadata = payload.get("provider_run_metadata")
    if metadata is None:
        return _metadata_from_legacy_run_report(
            payload=payload,
            run_report_path=run_report_path,
        )
    if not isinstance(metadata, dict):
        raise ValueError("answer-key live validation provider_run_metadata must be an object.")
    return answer_key_provider_run_metadata_from_payload(metadata)


def _metadata_from_legacy_run_report(
    *,
    payload: dict[str, object],
    run_report_path: Path,
) -> AnswerKeyProviderRunMetadata:
    model = _optional_str(payload, "model")
    provider_url = _optional_str(payload, "provider_url")
    provider_runtime = _optional_str(payload, "provider_runtime")
    if model is None or provider_url is None or provider_runtime is None:
        return unavailable_answer_key_provider_run_metadata(
            metadata_source=f"provider_run_metadata_missing:{run_report_path.as_posix()}"
        )
    defaults = _profile_defaults_matching_legacy_run(
        model=model,
        provider_url=provider_url,
        provider_runtime=provider_runtime,
    )
    if defaults is None:
        return unavailable_answer_key_provider_run_metadata(
            metadata_source=f"provider_run_metadata_unmatched:{run_report_path.as_posix()}"
        )
    profile = build_answer_key_provider_profile(
        runtime=defaults.provider_runtime,
        model=model,
        context_window_tokens=defaults.context_window_tokens,
        max_output_tokens=defaults.max_output_tokens,
        temperature=defaults.temperature,
        supports_multimodal_vision=defaults.permits_vision_assets,
    )
    output_root = run_report_path.parent
    vision_media_path = output_root / "vision-assets" if defaults.permits_vision_assets else None
    reports_root = _legacy_reports_root(payload=payload, output_root=output_root)
    return build_answer_key_provider_run_metadata(
        profile_name=defaults.profile_name,
        defaults=defaults,
        provider_url=provider_url,
        provider_runtime=defaults.provider_runtime,
        profile=profile,
        reports_root=reports_root,
        vision_media_path=vision_media_path,
        metadata_source="legacy_answer_key_run_report_profile_match",
    )


def _profile_defaults_matching_legacy_run(
    *,
    model: str,
    provider_url: str,
    provider_runtime: str,
) -> AnswerKeyProviderDefaults | None:
    for profile_value in answer_key_provider_profile_values():
        defaults = answer_key_defaults_for_provider_profile(profile_value)
        if (
            defaults.model == model
            and defaults.provider_url == provider_url
            and defaults.provider_runtime.value == provider_runtime
        ):
            return defaults
    return None


def _legacy_reports_root(
    *,
    payload: dict[str, object],
    output_root: Path,
) -> Path:
    report_paths_value = payload.get("report_paths")
    if isinstance(report_paths_value, list):
        for report_path_value in report_paths_value:
            if isinstance(report_path_value, str):
                return Path(report_path_value).parent
    return output_root / "advisory-corpus-reports"


def answer_key_provider_run_metadata_from_payload(
    payload: dict[str, object],
) -> AnswerKeyProviderRunMetadata:
    """Parse provider metadata from a JSON object."""

    return AnswerKeyProviderRunMetadata(
        schema_version=_required_str(payload, "schema_version"),
        available=_required_bool(payload, "available"),
        metadata_source=_required_str(payload, "metadata_source"),
        profile_name=_optional_str(payload, "profile_name"),
        provider_url=_optional_str(payload, "provider_url"),
        expected_model_id=_optional_str(payload, "expected_model_id"),
        provider_id=_optional_str(payload, "provider_id"),
        model=_optional_str(payload, "model"),
        endpoint_kind=_optional_str(payload, "endpoint_kind"),
        provider_runtime=_optional_str(payload, "provider_runtime"),
        default_output_mode=_optional_str(payload, "default_output_mode"),
        is_remote=_optional_bool(payload, "is_remote"),
        context_window_tokens=_optional_int(payload, "context_window_tokens"),
        max_output_tokens=_optional_int(payload, "max_output_tokens"),
        temperature=_optional_float(payload, "temperature"),
        capabilities=_optional_object(payload, "capabilities"),
        output_mode_policy=_optional_object(payload, "output_mode_policy"),
        request_settings=_optional_object(payload, "request_settings"),
        launch_settings=_optional_object(payload, "launch_settings"),
        artifact_paths=_optional_object(payload, "artifact_paths"),
    )


def structured_profile_from_answer_key_provider_run_metadata(
    metadata: AnswerKeyProviderRunMetadata,
) -> StructuredLLMProviderProfile | None:
    """Rehydrate a generic provider profile from metadata for diagnostics."""

    if not metadata.available:
        return None
    provider_id = _required_metadata_str(metadata.provider_id, "provider_id")
    model = _required_metadata_str(metadata.model, "model")
    endpoint_kind = StructuredLLMEndpointKind(
        _required_metadata_str(metadata.endpoint_kind, "endpoint_kind")
    )
    output_mode = StructuredLLMOutputMode(
        _required_metadata_str(metadata.default_output_mode, "default_output_mode")
    )
    return StructuredLLMProviderProfile(
        provider_id=provider_id,
        model=model,
        endpoint_kind=endpoint_kind,
        output_mode=output_mode,
        is_remote=_required_metadata_bool(metadata.is_remote, "is_remote"),
        context_window_tokens=_required_metadata_int(
            metadata.context_window_tokens, "context_window_tokens"
        ),
        max_output_tokens=_required_metadata_int(metadata.max_output_tokens, "max_output_tokens"),
        temperature=_required_metadata_float(metadata.temperature, "temperature"),
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=_bool_capability(metadata, "supports_json_schema"),
            supports_json_object=_optional_bool_capability(metadata, "supports_json_object"),
            supports_gbnf=_bool_capability(metadata, "supports_gbnf"),
            supports_vllm_structured_choice=_bool_capability(
                metadata, "supports_vllm_structured_choice"
            ),
            supports_multimodal_vision=_bool_capability(metadata, "supports_multimodal_vision"),
        ),
        thinking_mode=_optional_thinking_mode(metadata),
    )


def _capabilities_payload(capabilities: StructuredLLMProviderCapabilities) -> dict[str, object]:
    return {
        "supports_json_schema": capabilities.supports_json_schema,
        "supports_json_object": capabilities.supports_json_object,
        "supports_gbnf": capabilities.supports_gbnf,
        "supports_vllm_structured_choice": capabilities.supports_vllm_structured_choice,
        "supports_multimodal_vision": capabilities.supports_multimodal_vision,
    }


def _output_mode_policy_payload(profile: StructuredLLMProviderProfile) -> dict[str, object]:
    if profile.capabilities.supports_vllm_structured_choice:
        return {
            "single_choice": StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE.value,
            "multiple_choice": StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE.value,
            "multiple_response": StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE.value,
            "gap_fill": StructuredLLMOutputMode.VLLM_JSON_SCHEMA.value,
        }
    return {
        "single_choice": profile.output_mode.value,
        "multiple_choice": profile.output_mode.value,
        "multiple_response": profile.output_mode.value,
        "gap_fill": profile.output_mode.value,
    }


def _request_settings_payload(
    *,
    defaults: AnswerKeyProviderDefaults,
    profile: StructuredLLMProviderProfile,
) -> dict[str, object]:
    payload = _settings_payload(defaults.request_settings)
    payload["temperature"] = profile.temperature
    payload["max_output_tokens"] = profile.max_output_tokens
    payload["context_window_tokens"] = profile.context_window_tokens
    if profile.thinking_mode is not None:
        payload["thinking_mode"] = profile.thinking_mode.value
    return payload


def _settings_payload(settings: tuple[AnswerKeyProviderSetting, ...]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for setting in settings:
        payload[setting.key] = _json_value(setting.value)
    return payload


def _canonical_json(payload: object) -> str:
    return json.dumps(
        _json_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_object(value: dict[str, object]) -> dict[str, object]:
    return {str(key): _json_value(child) for key, child in value.items()}


def _json_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(
        f"Unsupported answer-key live validation provider metadata value: {type(value).__name__}"
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"answer-key live validation provider metadata {key} must be a string.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"answer-key live validation provider metadata {key} must be a boolean.")
    return value


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(
            f"answer-key live validation provider metadata {key} must be a string or null."
        )
    return value


def _optional_bool(payload: dict[str, object], key: str) -> bool | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(
            f"answer-key live validation provider metadata {key} must be a boolean or null."
        )
    return value


def _optional_int(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"answer-key live validation provider metadata {key} must be an integer or null."
        )
    return value


def _optional_float(payload: dict[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(
            f"answer-key live validation provider metadata {key} must be a number or null."
        )
    return float(value)


def _optional_object(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"answer-key live validation provider metadata {key} must be an object.")
    return {str(child_key): _json_value(child) for child_key, child in value.items()}


def _required_metadata_str(value: str | None, key: str) -> str:
    if value is None:
        raise ValueError(f"answer-key live validation provider metadata missing {key}.")
    return value


def _required_metadata_bool(value: bool | None, key: str) -> bool:
    if value is None:
        raise ValueError(f"answer-key live validation provider metadata missing {key}.")
    return value


def _required_metadata_int(value: int | None, key: str) -> int:
    if value is None:
        raise ValueError(f"answer-key live validation provider metadata missing {key}.")
    return value


def _required_metadata_float(value: float | None, key: str) -> float:
    if value is None:
        raise ValueError(f"answer-key live validation provider metadata missing {key}.")
    return value


def _optional_thinking_mode(
    metadata: AnswerKeyProviderRunMetadata,
) -> StructuredLLMThinkingMode | None:
    value = metadata.request_settings.get("thinking_mode")
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(
            "answer-key live validation provider metadata thinking_mode must be a string."
        )
    return StructuredLLMThinkingMode(value)


def _bool_capability(metadata: AnswerKeyProviderRunMetadata, key: str) -> bool:
    value = metadata.capabilities.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"answer-key live validation provider capability {key} must be a boolean.")
    return value


def _optional_bool_capability(metadata: AnswerKeyProviderRunMetadata, key: str) -> bool:
    value = metadata.capabilities.get(key)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError(f"answer-key live validation provider capability {key} must be a boolean.")
    return value
