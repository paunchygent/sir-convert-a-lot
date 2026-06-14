"""Remote-proof audio transcript evidence runner.

Purpose:
    Submit one `audio -> transcript_bundle` job to a Sir Convert-a-Lot Service
    API lane, poll asynchronously, and persist bounded evidence for Task 365
    local-proof diagnostics.

Relationships:
    - Uses the Service API v2 async job contract owned by
      `interfaces.http_routes_jobs_v2`.
    - Complements Skriptoteket browser proof by isolating the remote-proof
      Sir Convert/STT sidecar boundary without changing runtime settings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.interfaces.http_client_v2_upload_helpers import (
    content_type_for_source_path,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-365-remote-proof-audio-transcript")
DEFAULT_API_KEY_ENV = "SIR_CONVERT_A_LOT_V2_API_KEY"
TERMINAL_STATUSES = frozenset(("succeeded", "failed", "canceled"))


@dataclass(frozen=True)
class AudioTranscriptEvidenceSettings:
    """Settings for one remote-proof audio transcript evidence run."""

    service_url: str
    api_key: str
    audio_file: Path
    output_root: Path
    speaker_count: int
    timeout_seconds: float
    poll_interval_seconds: float
    expected_service_profile: str | None


def run_audio_transcript_evidence(
    settings: AudioTranscriptEvidenceSettings,
    *,
    client: httpx.Client | None = None,
) -> Path:
    """Run one async audio transcript job and return the summary path."""

    if not settings.audio_file.is_file():
        raise SystemExit(f"audio file not found: {settings.audio_file}")
    if settings.speaker_count <= 0:
        raise SystemExit("--speaker-count must be positive")
    if settings.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be positive")
    if settings.poll_interval_seconds < 0:
        raise SystemExit("--poll-interval-seconds must not be negative")

    run_dir = _run_dir(settings.output_root)
    if client is not None:
        return _run_with_client(settings=settings, client=client, run_dir=run_dir)
    with httpx.Client(base_url=settings.service_url.rstrip("/"), timeout=30.0) as owned_client:
        return _run_with_client(settings=settings, client=owned_client, run_dir=run_dir)


def _run_with_client(
    *,
    settings: AudioTranscriptEvidenceSettings,
    client: httpx.Client,
    run_dir: Path,
) -> Path:
    readyz = _get_json(
        client,
        "/readyz",
        headers={},
        label="readyz",
    )
    _validate_readyz(readyz, expected_service_profile=settings.expected_service_profile)
    _write_json(run_dir / "readyz.json", readyz)

    job_spec = _audio_job_spec(
        source_filename=settings.audio_file.name,
        speaker_count=settings.speaker_count,
    )
    _write_json(run_dir / "job-spec.json", job_spec)

    audio_bytes = settings.audio_file.read_bytes()
    correlation_id = f"corr_task365_remote_proof_audio_{int(time.time())}"
    idempotency_key = _idempotency_key(audio_bytes)
    create_payload = _create_job(
        client=client,
        settings=settings,
        audio_bytes=audio_bytes,
        job_spec=job_spec,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    _write_json(run_dir / "create-response.json", create_payload)
    job_id = _job_id_from_payload(create_payload)

    status_history = _poll_status_history(
        client=client,
        api_key=settings.api_key,
        job_id=job_id,
        correlation_id=correlation_id,
        timeout_seconds=settings.timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )
    _write_json(run_dir / "status-history.json", status_history)
    final_status = _final_status(status_history)

    result_payload: dict[str, object] | None = None
    manifest_payload: dict[str, object] | None = None
    transcript_payload: dict[str, object] | None = None
    if final_status == "succeeded":
        result_payload = _get_json(
            client,
            f"/v2/convert/jobs/{job_id}/result",
            headers=_headers(settings.api_key, correlation_id),
            label="result",
        )
        manifest_payload = _get_json(
            client,
            f"/v2/convert/jobs/{job_id}/artifacts",
            headers=_headers(settings.api_key, correlation_id),
            label="artifact manifest",
        )
        transcript_payload = _get_json(
            client,
            f"/v2/convert/jobs/{job_id}/artifacts/transcript_json",
            headers=_headers(settings.api_key, correlation_id),
            label="transcript_json",
        )
        _write_json(run_dir / "result.json", result_payload)
        _write_json(run_dir / "artifact-manifest.json", manifest_payload)
        _write_json(run_dir / "transcript_json.json", transcript_payload)

    summary = _summary_payload(
        settings=settings,
        run_dir=run_dir,
        readyz=readyz,
        job_id=job_id,
        final_status=final_status,
        status_history=status_history,
        result_payload=result_payload,
        manifest_payload=manifest_payload,
        transcript_payload=transcript_payload,
    )
    summary_path = run_dir / "summary.json"
    _write_json(summary_path, summary)
    return summary_path


def _run_dir(output_root: Path) -> Path:
    run_dir = output_root / datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _audio_job_spec(*, source_filename: str, speaker_count: int) -> dict[str, object]:
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": source_filename, "format": "audio"},
        "conversion": {"output_format": "transcript_bundle"},
        "audio_transcription_options": {
            "language": "auto",
            "diarization": {
                "mode": "known_speaker_count",
                "num_speakers": speaker_count,
                "min_speakers": None,
                "max_speakers": None,
            },
            "max_duration_seconds": 7200,
            "output_artifacts": ["json"],
        },
        "execution": {
            "acceleration_policy": "gpu_required",
            "priority": "normal",
            "document_timeout_seconds": 7200,
        },
        "retention": {"pin": False},
    }


def _create_job(
    *,
    client: httpx.Client,
    settings: AudioTranscriptEvidenceSettings,
    audio_bytes: bytes,
    job_spec: dict[str, object],
    idempotency_key: str,
    correlation_id: str,
) -> dict[str, object]:
    response = client.post(
        "/v2/convert/jobs?wait_seconds=0",
        files={
            "file": (
                settings.audio_file.name,
                audio_bytes,
                content_type_for_source_path(settings.audio_file),
            ),
            "job_spec": (None, json.dumps(job_spec, separators=(",", ":"))),
        },
        headers={
            **_headers(settings.api_key, correlation_id),
            "Idempotency-Key": idempotency_key,
        },
    )
    return _json_response(response, label="create job")


def _poll_status_history(
    *,
    client: httpx.Client,
    api_key: str,
    job_id: str,
    correlation_id: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[dict[str, object]]:
    deadline = time.monotonic() + timeout_seconds
    history: list[dict[str, object]] = []
    while time.monotonic() < deadline:
        payload = _get_json(
            client,
            f"/v2/convert/jobs/{job_id}",
            headers=_headers(api_key, correlation_id),
            label="job status",
        )
        job = _job_object(payload)
        status = _string_field(job, "status")
        progress = job.get("progress")
        history.append(
            {
                "observed_at": datetime.now(tz=UTC).replace(microsecond=0).isoformat(),
                "status": status,
                "progress": progress if isinstance(progress, dict) else {},
            }
        )
        if status in TERMINAL_STATUSES:
            return history
        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)
    raise SystemExit(f"job did not reach terminal status within {timeout_seconds} seconds")


def _summary_payload(
    *,
    settings: AudioTranscriptEvidenceSettings,
    run_dir: Path,
    readyz: dict[str, object],
    job_id: str,
    final_status: str,
    status_history: list[dict[str, object]],
    result_payload: dict[str, object] | None,
    manifest_payload: dict[str, object] | None,
    transcript_payload: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "schema_version": "task365_remote_proof_audio_transcript_evidence_v1",
        "status": final_status,
        "job_id": job_id,
        "service_url": settings.service_url.rstrip("/"),
        "audio_file": settings.audio_file.as_posix(),
        "output_dir": run_dir.as_posix(),
        "readyz": _readyz_summary(readyz),
        "status_observation_count": len(status_history),
        "final_progress": status_history[-1].get("progress") if status_history else {},
        "result": _result_summary(result_payload),
        "artifact_manifest": _manifest_summary(manifest_payload),
        "transcript_json": _transcript_summary(transcript_payload),
    }


def _final_status(status_history: list[dict[str, object]]) -> str:
    if not status_history:
        raise SystemExit("status history is empty")
    status = status_history[-1].get("status")
    if not isinstance(status, str) or status.strip() == "":
        raise SystemExit("final status history entry has no status")
    return status


def _readyz_summary(readyz: dict[str, object]) -> dict[str, object]:
    return {
        "ready": readyz.get("ready"),
        "service_revision": readyz.get("service_revision"),
        "service_profile": readyz.get("service_profile"),
        "expected_service_profile": readyz.get("expected_service_profile"),
    }


def _result_summary(payload: dict[str, object] | None) -> dict[str, object]:
    if payload is None:
        return {}
    result = payload.get("result")
    metadata = result.get("conversion_metadata") if isinstance(result, dict) else None
    return metadata if isinstance(metadata, dict) else {}


def _manifest_summary(payload: dict[str, object] | None) -> dict[str, object]:
    if payload is None:
        return {}
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        return {}
    availability: dict[str, str] = {}
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        key = item.get("artifact_key")
        value = item.get("availability")
        if isinstance(key, str) and isinstance(value, str):
            availability[key] = value
    return {"availability": availability}


def _transcript_summary(payload: dict[str, object] | None) -> dict[str, object]:
    if payload is None:
        return {}
    segments = payload.get("segments")
    if not isinstance(segments, list):
        transcript = payload.get("transcript")
        if isinstance(transcript, dict):
            nested_segments = transcript.get("segments")
            segments = nested_segments if isinstance(nested_segments, list) else []
        else:
            segments = []
    labels = sorted(
        {
            label
            for segment in segments
            if isinstance(segment, dict)
            for label in (segment.get("speaker_label"),)
            if isinstance(label, str)
        }
    )
    return {"segment_count": len(segments), "speaker_labels": labels}


def _get_json(
    client: httpx.Client,
    path: str,
    *,
    headers: dict[str, str],
    label: str,
) -> dict[str, object]:
    return _json_response(client.get(path, headers=headers), label=label)


def _json_response(response: httpx.Response, *, label: str) -> dict[str, object]:
    if response.status_code >= 400:
        raise SystemExit(f"{label} failed with HTTP {response.status_code}: {response.text}")
    try:
        payload: object = response.json()
    except ValueError as exc:
        raise SystemExit(f"{label} response was not JSON") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} response was not a JSON object")
    return payload


def _validate_readyz(
    readyz: dict[str, object],
    *,
    expected_service_profile: str | None,
) -> None:
    if readyz.get("ready") is not True:
        raise SystemExit(f"service is not ready: {readyz.get('reasons')!r}")
    if expected_service_profile is not None:
        profile = readyz.get("service_profile")
        if profile != expected_service_profile:
            raise SystemExit(
                f"service_profile mismatch: {profile!r} != {expected_service_profile!r}"
            )


def _job_id_from_payload(payload: dict[str, object]) -> str:
    job = _job_object(payload)
    return _string_field(job, "job_id")


def _job_object(payload: dict[str, object]) -> dict[str, object]:
    job = payload.get("job")
    if not isinstance(job, dict):
        raise SystemExit("response missing job object")
    return job


def _string_field(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise SystemExit(f"response missing non-empty {key}")
    return value


def _headers(api_key: str, correlation_id: str) -> dict[str, str]:
    return {"X-API-Key": api_key, "X-Correlation-ID": correlation_id}


def _idempotency_key(audio_bytes: bytes) -> str:
    digest = hashlib.sha256(audio_bytes).hexdigest()[:24]
    return f"task365_remote_proof_audio_{digest}_{int(time.time())}"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Task 365 remote-proof STT evidence.")
    parser.add_argument("--service-url", default="http://127.0.0.1:28085")
    parser.add_argument("--audio-file", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--speaker-count", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=1200.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--expected-service-profile", default="remote-proof")
    return parser.parse_args(argv)


def _api_key_from_args(args: argparse.Namespace) -> str:
    api_key_arg = args.api_key
    if isinstance(api_key_arg, str) and api_key_arg.strip() != "":
        return api_key_arg.strip()
    api_key_env = str(args.api_key_env)
    value = os.environ.get(api_key_env, "").strip()
    if value == "":
        raise SystemExit(f"Missing API key. Provide --api-key or set {api_key_env}.")
    return value


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for Task 365 remote-proof STT evidence."""

    args = _parse_args(sys.argv[1:] if argv is None else argv)
    summary_path = run_audio_transcript_evidence(
        AudioTranscriptEvidenceSettings(
            service_url=str(args.service_url),
            api_key=_api_key_from_args(args),
            audio_file=Path(args.audio_file),
            output_root=Path(args.output_root),
            speaker_count=int(args.speaker_count),
            timeout_seconds=float(args.timeout_seconds),
            poll_interval_seconds=float(args.poll_interval_seconds),
            expected_service_profile=str(args.expected_service_profile)
            if args.expected_service_profile is not None
            else None,
        )
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    print(summary_path.as_posix())
    return 0 if summary.get("status") == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
