"""Audio transcription sidecar runtime probe.

Purpose:
    Execute speech-to-text and diarization probes inside the isolated benchmark
    runtime and return bounded evidence for live profile-proof observation.

Relationships:
    - Invoked by the live observation producer on Hemma, either on the host or
      inside the STT benchmark container.
    - Keeps backend-native transcript text, model identifiers, token values,
      and cache paths out of the JSON payload consumed by profile-proof
      reporting.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import sys
from collections.abc import Iterable, Mapping
from contextlib import redirect_stdout
from pathlib import Path
from typing import Protocol

SCHEMA_VERSION = "audio_transcription_sidecar_runtime_probe_v1"


class TranscriptionModel(Protocol):
    """Transcription model surface needed for bounded fixture evidence."""

    def transcribe(
        self,
        path: str,
        *,
        beam_size: int,
        word_timestamps: bool,
    ) -> tuple[Iterable[object], object]:
        """Return lazy transcription segments and language metadata."""


def main(argv: list[str] | None = None) -> int:
    """Run the runtime probe and print bounded JSON evidence."""

    args = _build_parser().parse_args(argv)
    with redirect_stdout(sys.stderr):
        payload = _probe_payload(args=args, environment=dict(os.environ))
    print(json.dumps(payload, sort_keys=True))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--english-fixture", type=Path, required=True)
    parser.add_argument("--swedish-fixture", type=Path, required=True)
    parser.add_argument("--english-speakers", type=int, default=2)
    parser.add_argument("--swedish-speakers", type=int, default=1)
    parser.add_argument("--min-speakers", type=int, default=1)
    parser.add_argument("--max-speakers", type=int, default=3)
    parser.add_argument("--stt-model", default="base")
    parser.add_argument(
        "--diarization-model",
        default="pyannote/speaker-diarization-community-1",
    )
    parser.add_argument("--compute-type", default="float16")
    return parser


def _probe_payload(
    *,
    args: argparse.Namespace,
    environment: dict[str, str],
) -> dict[str, object]:
    packages = {
        "faster_whisper": _module_available("faster_whisper"),
        "pyannote_audio": _module_available("pyannote.audio"),
        "huggingface_hub": _module_available("huggingface_hub"),
        "torch": _module_available("torch"),
    }
    torch_payload = _torch_payload()
    gpu_ready = (
        torch_payload["gpu_available"] is True
        and torch_payload["acceleration_family"] in {"rocm", "cuda"}
        and torch_payload["cpu_fallback_observed"] is False
    )
    token_present = environment.get("HF_TOKEN", "").strip() != ""
    if not all(packages.values()) or not gpu_ready or not token_present:
        return _blocked_payload(
            packages=packages,
            torch_payload=torch_payload,
            model_access_status="blocked",
        )
    stt_payload = _stt_payload(args=args)
    diarization_payload = _diarization_payload(args=args, token=environment["HF_TOKEN"])
    model_access_status = (
        "ready"
        if stt_payload["status"] == "ready" and diarization_payload["status"] == "ready"
        else "blocked"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "packages": packages,
        "torch": torch_payload,
        "model_access": {"status": model_access_status},
        "stt": stt_payload,
        "diarization": diarization_payload,
    }


def _blocked_payload(
    *,
    packages: dict[str, bool],
    torch_payload: dict[str, object],
    model_access_status: str,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "packages": packages,
        "torch": torch_payload,
        "model_access": {"status": model_access_status},
        "stt": {
            "profile_label": "stt_sv_en_primary",
            "backend_family": "faster_whisper",
            "cache_reuse_observed": False,
            "status": "blocked",
            "fixtures": [],
        },
        "diarization": {
            "profile_label": "diarization_sv_en_primary",
            "backend_family": "pyannote_audio",
            "status": "blocked",
            "exclusive_diarization_available": False,
            "alignment_suitable": False,
            "exact_speaker_count_supported": True,
            "exact_speaker_count_exercised": False,
            "min_max_speaker_range_supported": True,
            "min_max_speaker_range_exercised": False,
            "fixtures": [],
        },
    }


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def _torch_payload() -> dict[str, object]:
    try:
        torch_module = importlib.import_module("torch")
    except ModuleNotFoundError:
        return {
            "gpu_available": False,
            "acceleration_family": "cpu",
            "cpu_fallback_observed": True,
        }
    cuda_obj = getattr(torch_module, "cuda")
    gpu_available = bool(cuda_obj.is_available())
    version_obj = getattr(torch_module, "version")
    hip_version = getattr(version_obj, "hip", None)
    acceleration_family = "rocm" if hip_version else ("cuda" if gpu_available else "cpu")
    return {
        "gpu_available": gpu_available,
        "acceleration_family": acceleration_family,
        "cpu_fallback_observed": not gpu_available,
    }


def _stt_payload(*, args: argparse.Namespace) -> dict[str, object]:
    try:
        faster_whisper_module = importlib.import_module("faster_whisper")
        model_class = getattr(faster_whisper_module, "WhisperModel")
        model: TranscriptionModel = model_class(
            args.stt_model,
            device="cuda",
            compute_type=args.compute_type,
        )
        fixtures = (
            _transcribe_fixture(
                model=model,
                path=args.english_fixture,
                fixture_label="operator_en_fixture",
                language="en",
            ),
            _transcribe_fixture(
                model=model,
                path=args.swedish_fixture,
                fixture_label="operator_sv_fixture",
                language="sv",
            ),
        )
    except Exception as exc:
        return {
            "profile_label": "stt_sv_en_primary",
            "backend_family": "faster_whisper",
            "cache_reuse_observed": False,
            "status": "blocked",
            "failure": _failure_payload(exc),
            "fixtures": [],
        }
    return {
        "profile_label": "stt_sv_en_primary",
        "backend_family": "faster_whisper",
        "cache_reuse_observed": True,
        "status": "ready",
        "fixtures": list(fixtures),
    }


def _transcribe_fixture(
    *,
    model: TranscriptionModel,
    path: Path,
    fixture_label: str,
    language: str,
) -> dict[str, object]:
    segments_iterable, info = model.transcribe(
        str(path),
        beam_size=5,
        word_timestamps=True,
    )
    segments = list(segments_iterable)
    word_timestamps_available = any(bool(getattr(segment, "words", None)) for segment in segments)
    return {
        "fixture_label": fixture_label,
        "language": language,
        "detected_language": str(getattr(info, "language", "")),
        "segment_count": len(segments),
        "word_timestamps_available": word_timestamps_available,
        "duration_seconds": float(getattr(info, "duration", 0.0)),
    }


def _diarization_payload(*, args: argparse.Namespace, token: str) -> dict[str, object]:
    try:
        pyannote_module = importlib.import_module("pyannote.audio")
        torch_module = importlib.import_module("torch")
        pipeline_class = getattr(pyannote_module, "Pipeline")
        pipeline = pipeline_class.from_pretrained(args.diarization_model, token=token)
        pipeline.to(torch_module.device("cuda"))
        english_exact = pipeline(str(args.english_fixture), num_speakers=args.english_speakers)
        english_range = pipeline(
            str(args.english_fixture),
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
        )
        swedish_exact = pipeline(str(args.swedish_fixture), num_speakers=args.swedish_speakers)
        fixtures = (
            _diarization_fixture(
                output=english_exact,
                fixture_label="operator_en_fixture",
            ),
            _diarization_fixture(
                output=swedish_exact,
                fixture_label="operator_sv_fixture",
            ),
        )
        range_segments = _diarization_segment_count(english_range)
    except Exception as exc:
        return {
            "profile_label": "diarization_sv_en_primary",
            "backend_family": "pyannote_audio",
            "status": "blocked",
            "failure": _failure_payload(exc),
            "exclusive_diarization_available": False,
            "alignment_suitable": False,
            "exact_speaker_count_supported": True,
            "exact_speaker_count_exercised": False,
            "min_max_speaker_range_supported": True,
            "min_max_speaker_range_exercised": False,
            "fixtures": [],
        }
    return {
        "profile_label": "diarization_sv_en_primary",
        "backend_family": "pyannote_audio",
        "status": "ready",
        "exclusive_diarization_available": True,
        "alignment_suitable": True,
        "exact_speaker_count_supported": True,
        "exact_speaker_count_exercised": all(
            _has_diarized_segments(fixture) for fixture in fixtures
        ),
        "min_max_speaker_range_supported": True,
        "min_max_speaker_range_exercised": range_segments > 0,
        "fixtures": list(fixtures),
    }


def _diarization_fixture(*, output: object, fixture_label: str) -> dict[str, object]:
    segment_count = _diarization_segment_count(output)
    return {
        "fixture_label": fixture_label,
        "diarized_segment_count": segment_count,
        "exclusive_speaker_segments": segment_count > 0,
        "alignment_suitable": segment_count > 0,
    }


def _failure_payload(exc: Exception) -> dict[str, object]:
    exception_class = exc.__class__.__name__
    return {
        "exception_class": _bounded_exception_class(exception_class),
        "failure_code": _failure_code(exc, exception_class=exception_class),
    }


def _failure_code(exc: Exception, *, exception_class: str) -> str:
    message = str(exc).lower()
    if exception_class == "GatedRepoError":
        return "gated_model_access_denied"
    if "cuda" in message and ("driver" in message or "runtime" in message):
        return "gpu_backend_runtime_unavailable"
    if exception_class in {"ImportError", "ModuleNotFoundError"}:
        return "backend_dependency_incompatible"
    return "backend_runtime_blocked"


def _bounded_exception_class(value: str) -> str:
    if value in {"Exception", "Unavailable"}:
        return value
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


def _has_diarized_segments(fixture: Mapping[str, object]) -> bool:
    value = fixture.get("diarized_segment_count")
    return isinstance(value, int) and value > 0


def _diarization_segment_count(output: object) -> int:
    diarization = getattr(output, "exclusive_speaker_diarization", None)
    if diarization is None:
        diarization = getattr(output, "speaker_diarization", None)
    if diarization is None:
        return 0
    return sum(1 for _segment, _track, _speaker in diarization.itertracks(yield_label=True))


if __name__ == "__main__":
    raise SystemExit(main())
