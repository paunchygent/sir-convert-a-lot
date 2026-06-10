"""Audio transcription sidecar diarization access diagnostics.

Purpose:
    Build content-safe Hugging Face access evidence for the selected
    pyannote-backed diarization profile used by the STT sidecar proof lane.

Relationships:
    - Used by the STT sidecar diarization access command before rerunning full
      live profile proof.
    - Complements the live observation runner by identifying whether the
      operator token can fetch the gated pyannote artifact.
    - Keeps token values, private cache paths, and raw model identifiers out of
      retained diagnostic JSON.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from huggingface_hub import hf_hub_download, whoami

from scripts.sir_convert_a_lot.benchmarking.output_policy import (
    enforce_generated_output_path,
)

SCHEMA_VERSION = "audio_transcription_sidecar_diarization_access_v1"
DEFAULT_OUTPUT_ROOT = Path("build/verification/stt-sidecar-diarization-access")
DEFAULT_PYANNOTE_DIARIZATION_REPO_ID = "pyannote/speaker-diarization-community-1"
DEFAULT_PYANNOTE_ARTIFACT_FILENAME = "config.yaml"
DEFAULT_TOKEN_ENV_VAR_NAME = "HF_TOKEN"
READY_OPERATOR_ACTION = ""
TOKEN_MISSING_OPERATOR_ACTION = "configure_hf_token_for_stt_sidecar_operator"
GATED_ACCESS_OPERATOR_ACTION = "accept_or_request_pyannote_gated_model_access_for_hf_token_account"
GENERIC_ACCESS_OPERATOR_ACTION = "verify_pyannote_hugging_face_access_for_hf_token_account"


class HubModelAccessClient(Protocol):
    """Hugging Face access surface needed by the diarization diagnostic."""

    def whoami(self, *, token: str) -> Mapping[str, object]:
        """Return bounded authenticated-account metadata."""

    def download_file(self, *, repo_id: str, filename: str, token: str) -> Path:
        """Download or resolve a single gated artifact."""


@dataclass(frozen=True, slots=True)
class DiarizationModelAccessSettings:
    """Settings for one pyannote diarization access check."""

    output_root: Path
    repo_id: str = DEFAULT_PYANNOTE_DIARIZATION_REPO_ID
    artifact_filename: str = DEFAULT_PYANNOTE_ARTIFACT_FILENAME
    token_env_var_name: str = DEFAULT_TOKEN_ENV_VAR_NAME


class HuggingFaceHubModelAccessClient:
    """Hugging Face Hub client used by the diarization access diagnostic."""

    def whoami(self, *, token: str) -> Mapping[str, object]:
        """Return authenticated account metadata without exposing the token."""

        payload = whoami(token=token)
        if isinstance(payload, Mapping):
            return payload
        return {}

    def download_file(self, *, repo_id: str, filename: str, token: str) -> Path:
        """Resolve a gated model artifact through the Hugging Face cache."""

        resolved_path = hf_hub_download(repo_id=repo_id, filename=filename, token=token)
        return Path(resolved_path)


def build_diarization_model_access_report(
    *,
    settings: DiarizationModelAccessSettings,
    client: HubModelAccessClient,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Return content-safe access evidence for the pyannote diarization profile."""

    token = environment.get(settings.token_env_var_name, "").strip()
    if not token:
        return _blocked_report(
            settings=settings,
            token_present=False,
            authenticated_account_observed=False,
            failure_code="hf_token_missing",
            exception_class="MissingToken",
            operator_action=TOKEN_MISSING_OPERATOR_ACTION,
        )

    authenticated_account_observed = _authenticated_account_observed(
        client=client,
        token=token,
    )
    try:
        client.download_file(
            repo_id=settings.repo_id,
            filename=settings.artifact_filename,
            token=token,
        )
    except Exception as exc:
        failure_code = _failure_code(exc)
        return _blocked_report(
            settings=settings,
            token_present=True,
            authenticated_account_observed=authenticated_account_observed,
            failure_code=failure_code,
            exception_class=_bounded_exception_class(exc.__class__.__name__),
            operator_action=_operator_action(failure_code),
        )

    return _ready_report(
        settings=settings,
        authenticated_account_observed=authenticated_account_observed,
    )


def write_diarization_model_access_report(
    report: Mapping[str, object],
    *,
    output_root: Path,
) -> Path:
    """Write the content-safe diarization access report JSON."""

    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "diarization-access.json"
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _ready_report(
    *,
    settings: DiarizationModelAccessSettings,
    authenticated_account_observed: bool,
) -> dict[str, object]:
    return _base_report(
        settings=settings,
        status="ready",
        access_status="ready",
        token_present=True,
        authenticated_account_observed=authenticated_account_observed,
        failure_code="",
        exception_class="",
        operator_action=READY_OPERATOR_ACTION,
    )


def _blocked_report(
    *,
    settings: DiarizationModelAccessSettings,
    token_present: bool,
    authenticated_account_observed: bool,
    failure_code: str,
    exception_class: str,
    operator_action: str,
) -> dict[str, object]:
    return _base_report(
        settings=settings,
        status="blocked",
        access_status="blocked",
        token_present=token_present,
        authenticated_account_observed=authenticated_account_observed,
        failure_code=failure_code,
        exception_class=exception_class,
        operator_action=operator_action,
    )


def _base_report(
    *,
    settings: DiarizationModelAccessSettings,
    status: str,
    access_status: str,
    token_present: bool,
    authenticated_account_observed: bool,
    failure_code: str,
    exception_class: str,
    operator_action: str,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "access_status": access_status,
        "backend_family": "pyannote_audio",
        "profile_label": "diarization_sv_en_primary",
        "model_family": "pyannote_community_diarization",
        "artifact_label": _artifact_label(settings.artifact_filename),
        "token_env_var_names": (settings.token_env_var_name,),
        "token_env_vars_present": token_present,
        "authenticated_account_observed": authenticated_account_observed,
        "failure_code": failure_code,
        "exception_class": exception_class,
        "operator_action": operator_action,
        "secret_values_exposed": False,
        "private_cache_paths_exposed": False,
        "raw_model_identifiers_exposed": False,
    }


def _authenticated_account_observed(
    *,
    client: HubModelAccessClient,
    token: str,
) -> bool:
    try:
        payload = client.whoami(token=token)
    except Exception:
        return False
    name = payload.get("name")
    return isinstance(name, str) and name.strip() != ""


def _failure_code(exc: Exception) -> str:
    exception_class = exc.__class__.__name__
    message = str(exc).lower()
    if exception_class == "GatedRepoError" or "gated" in message:
        return "gated_model_access_denied"
    if "401" in message or "unauthorized" in message:
        return "hf_token_unauthorized"
    if "404" in message or "not found" in message:
        return "model_artifact_not_found_or_private"
    return "hugging_face_access_error"


def _operator_action(failure_code: str) -> str:
    if failure_code == "gated_model_access_denied":
        return GATED_ACCESS_OPERATOR_ACTION
    if failure_code == "hf_token_unauthorized":
        return TOKEN_MISSING_OPERATOR_ACTION
    return GENERIC_ACCESS_OPERATOR_ACTION


def _bounded_exception_class(value: str) -> str:
    if _ascii_identifier(value) and value.endswith(("Error", "Exception")):
        return value
    return "Exception"


def _ascii_identifier(value: str) -> bool:
    if not value:
        return False
    first_character = value[0]
    if not (first_character.isascii() and (first_character.isalpha() or first_character == "_")):
        return False
    return all(
        character.isascii() and (character.isalnum() or character == "_") for character in value
    )


def _artifact_label(filename: str) -> str:
    if filename == DEFAULT_PYANNOTE_ARTIFACT_FILENAME:
        return "pipeline_config"
    return "selected_pipeline_artifact"
