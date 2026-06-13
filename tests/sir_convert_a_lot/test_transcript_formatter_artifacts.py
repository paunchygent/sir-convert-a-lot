"""Transcript formatter artifacts over canonical JSON behavior.

Purpose:
    Prove Task 358 formatter artifacts are deterministic, product-neutral
    derivatives of canonical transcript JSON and are exposed through the v2
    named-artifact lifecycle.

Relationships:
    - Exercises domain formatter rendering over a checked-in canonical JSON
      fixture.
    - Exercises `infrastructure.audio_transcript_bundle_artifacts` and the v2
      HTTP artifact routes without invoking STT, diarization, alignment, or
      media-processing modules.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, TypeAlias

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_artifacts import (
    build_audio_transcript_artifact_manifest,
    resolve_audio_transcript_artifact,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.test_audio_transcript_bundle_runtime_v2 import (
    _API_KEY,
    _FakeAudioTranscriptionSidecar,
    _headers,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / ("transcript_formatter_canonical.json")
)
_MultipartFieldValue: TypeAlias = (
    IO[bytes]
    | bytes
    | str
    | tuple[str | None, IO[bytes] | bytes | str]
    | tuple[str | None, IO[bytes] | bytes | str, str | None]
    | tuple[str | None, IO[bytes] | bytes | str, str | None, Mapping[str, str]]
)
_MultipartFiles: TypeAlias = list[tuple[str, _MultipartFieldValue]]


def test_formatter_renders_golden_outputs_over_canonical_json() -> None:
    from scripts.sir_convert_a_lot.domain.transcript_formatter_artifacts import (
        render_transcript_formatter_outputs,
    )

    rendered = render_transcript_formatter_outputs(canonical_payload=_canonical_payload())

    assert rendered["transcript_txt"].decode("utf-8") == _expected_txt()
    assert rendered["transcript_md"].decode("utf-8") == _expected_md()
    assert rendered["transcript_vtt"].decode("utf-8") == _expected_vtt()
    assert rendered["transcript_srt"].decode("utf-8") == _expected_srt()


def test_formatter_module_does_not_import_stt_or_media_processing_boundaries() -> None:
    from scripts.sir_convert_a_lot.domain import transcript_formatter_artifacts

    source_path = inspect.getsourcefile(transcript_formatter_artifacts)
    if source_path is None:
        raise AssertionError("Formatter module must have an inspectable source file.")
    source = Path(source_path).read_text(encoding="utf-8")

    forbidden_fragments = (
        "audio_transcript_alignment",
        "audio_transcript_sidecar",
        "audio_transcription_sidecar",
        "audio_transcript_chunking",
        "audio_transcript_merge",
        "audio_transcript_sidecar_requests",
        "ffmpeg",
        "ffprobe",
        "diarize(",
        "transcribe_chunk(",
        "probe_media(",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source


def test_invalid_canonical_json_precondition_preserves_transcript_json(
    tmp_path: Path,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_artifacts import (
        write_requested_transcript_formatter_artifacts,
    )

    job = _stored_audio_job(tmp_path, output_artifacts=("json", "txt", "md", "vtt", "srt"))
    original_bytes = b"{not-valid-json"
    job.artifact_path.write_bytes(original_bytes)

    with pytest.raises(ServiceError) as exc_info:
        write_requested_transcript_formatter_artifacts(
            job=job,
            canonical_json_bytes=original_bytes,
        )

    assert exc_info.value.code == "audio_transcript_artifact_unavailable"
    assert job.artifact_path.read_bytes() == original_bytes
    assert not (job.artifact_path.parent / "transcript_txt.txt").exists()
    assert not (job.artifact_path.parent / "transcript_md.md").exists()
    assert not (job.artifact_path.parent / "transcript_vtt.vtt").exists()
    assert not (job.artifact_path.parent / "transcript_srt.srt").exists()


def test_json_only_manifest_keeps_formatters_explicitly_unrequested(
    tmp_path: Path,
) -> None:
    job = _successful_stored_audio_job(tmp_path, output_artifacts=("json",))

    manifest = build_audio_transcript_artifact_manifest(job=job)

    entries = _artifact_entries(manifest)
    assert entries["transcript_json"]["availability"] == "available"
    assert entries["transcript_txt"] == {
        "artifact_key": "transcript_txt",
        "availability": "unrequested",
        "content_type": "text/plain",
        "filename": "transcript_txt.txt",
        "unavailable_code": "audio_transcript_artifact_unavailable",
    }
    assert entries["transcript_md"]["availability"] == "unrequested"
    assert entries["transcript_vtt"]["availability"] == "unrequested"
    assert entries["transcript_srt"]["availability"] == "unrequested"


def test_requested_formatter_artifacts_resolve_with_stable_metadata(
    tmp_path: Path,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_artifacts import (
        write_requested_transcript_formatter_artifacts,
    )

    job = _successful_stored_audio_job(
        tmp_path,
        output_artifacts=("json", "txt", "md", "vtt", "srt"),
    )
    write_requested_transcript_formatter_artifacts(
        job=job,
        canonical_json_bytes=job.artifact_path.read_bytes(),
    )

    manifest = build_audio_transcript_artifact_manifest(job=job)
    entries = _artifact_entries(manifest)

    expected = {
        "transcript_txt": ("text/plain", "transcript_txt.txt"),
        "transcript_md": ("text/markdown", "transcript_md.md"),
        "transcript_vtt": ("text/vtt", "transcript_vtt.vtt"),
        "transcript_srt": ("application/x-subrip", "transcript_srt.srt"),
    }
    for artifact_key, (content_type, filename) in expected.items():
        entry = entries[artifact_key]
        path = job.artifact_path.parent / filename
        assert entry["availability"] == "available"
        assert entry["content_type"] == content_type
        assert entry["filename"] == filename
        assert entry["size_bytes"] == path.stat().st_size
        assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert entry["retrieval_path"] == f"/v2/convert/jobs/{job.job_id}/artifacts/{artifact_key}"

        resolved = resolve_audio_transcript_artifact(job=job, artifact_key=artifact_key)
        assert resolved.content_type == content_type
        assert resolved.filename == filename
        assert resolved.path == path


def test_api_accepts_all_formatter_artifacts_and_serves_named_outputs(
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(
            ServiceConfig(
                api_key=_API_KEY,
                data_root=tmp_path / "service_data",
                enable_supervisor=False,
                run_jobs_on_submit=True,
                processing_delay_seconds=0.0,
                enable_runtime_telemetry_calls=False,
            ),
            audio_transcription_sidecar=_FakeAudioTranscriptionSidecar(),
        )
    )

    response = _post_audio_job(
        client=client,
        idempotency_key="idem-audio-formatters-all",
        output_artifacts=("json", "txt", "md", "vtt", "srt"),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    manifest_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts",
        headers=_headers(),
    )
    assert manifest_response.status_code == 200
    entries = _artifact_entries(manifest_response.json())
    assert entries["transcript_txt"]["availability"] == "available"
    assert entries["transcript_md"]["availability"] == "available"
    assert entries["transcript_vtt"]["availability"] == "available"
    assert entries["transcript_srt"]["availability"] == "available"

    txt_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_txt",
        headers=_headers(),
    )
    md_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_md",
        headers=_headers(),
    )
    vtt_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_vtt",
        headers=_headers(),
    )
    srt_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_srt",
        headers=_headers(),
    )

    assert txt_response.status_code == 200
    assert txt_response.headers["content-type"].startswith("text/plain")
    assert "[00:00:00.000 - 00:00:04.200] SPEAKER_00" in txt_response.text
    assert md_response.status_code == 200
    assert md_response.headers["content-type"].startswith("text/markdown")
    assert "| Start | End | Speaker | Language | Confidence | Text |" in md_response.text
    assert vtt_response.status_code == 200
    assert vtt_response.headers["content-type"].startswith("text/vtt")
    assert vtt_response.text.startswith("WEBVTT\n\n")
    assert srt_response.status_code == 200
    assert srt_response.headers["content-type"].startswith("application/x-subrip")
    assert "1\n00:00:00,000 --> 00:00:04,200" in srt_response.text


def _canonical_payload() -> Mapping[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise AssertionError("Canonical transcript fixture must be a JSON object.")
    return {str(key): value for key, value in payload.items()}


def _stored_audio_job(tmp_path: Path, *, output_artifacts: tuple[str, ...]) -> StoredJobV2:
    raw_dir = tmp_path / "raw"
    artifact_dir = tmp_path / "artifacts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    upload_path = raw_dir / "teacher-meeting.m4a"
    upload_path.write_bytes(b"audio bytes")
    now = datetime.now(UTC)
    return StoredJobV2(
        job_id="job-v2-audio-formatters-test",
        spec=JobSpecV2.model_validate(_audio_job_spec(output_artifacts=output_artifacts)),
        source_filename="teacher-meeting.m4a",
        source_format=SourceFormatV2.AUDIO,
        output_format=OutputFormatV2.TRANSCRIPT_BUNDLE,
        upload_path=upload_path,
        resources_zip_path=None,
        reference_docx_path=None,
        artifact_path=artifact_dir / "transcript_json.json",
        status=JobStatus.RUNNING,
        created_at=now,
        updated_at=now,
        expires_at=None,
        progress_stage="running",
    )


def _successful_stored_audio_job(
    tmp_path: Path,
    *,
    output_artifacts: tuple[str, ...],
) -> StoredJobV2:
    job = _stored_audio_job(tmp_path, output_artifacts=output_artifacts)
    artifact_bytes = FIXTURE_PATH.read_bytes()
    job.artifact_path.write_bytes(artifact_bytes)
    job.status = JobStatus.SUCCEEDED
    job.artifact_size_bytes = len(artifact_bytes)
    job.artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    job.pipeline_used = "audio_to_transcript_bundle_v2"
    job.options_fingerprint = "0" * 64
    return job


def _artifact_entries(manifest: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise AssertionError("Manifest must include an artifacts list.")
    entries: dict[str, Mapping[str, object]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise AssertionError("Artifact manifest entries must be objects.")
        key = artifact.get("artifact_key")
        if not isinstance(key, str):
            raise AssertionError("Artifact manifest entry must include artifact_key.")
        entries[key] = artifact
    return entries


def _post_audio_job(
    *,
    client: TestClient,
    idempotency_key: str,
    output_artifacts: tuple[str, ...],
) -> Response:
    payload = _audio_job_spec(output_artifacts=output_artifacts)
    files: _MultipartFiles = [
        ("file", ("teacher-meeting.m4a", b"audio bytes", "application/octet-stream")),
        ("job_spec", (None, json.dumps(payload))),
    ]
    return client.post(
        "/v2/convert/jobs?wait_seconds=20",
        headers={**_headers(), "Idempotency-Key": idempotency_key},
        files=files,
    )


def _audio_job_spec(*, output_artifacts: tuple[str, ...]) -> dict[str, object]:
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "teacher-meeting.m4a", "format": "audio"},
        "conversion": {"output_format": "transcript_bundle"},
        "execution": {
            "acceleration_policy": "gpu_required",
            "priority": "normal",
            "document_timeout_seconds": 7200,
        },
        "audio_transcription_options": {
            "language": "auto",
            "diarization": {
                "mode": "auto",
                "num_speakers": None,
                "min_speakers": None,
                "max_speakers": None,
            },
            "max_duration_seconds": 7200,
            "output_artifacts": list(output_artifacts),
        },
        "retention": {"pin": False},
    }


def _expected_txt() -> str:
    return (
        "Language: en (confidence 0.98)\n"
        "Duration: 8.000 seconds\n"
        "Warnings:\n"
        "- low_confidence_segment\n"
        "\n"
        "[00:00:00.000 - 00:00:04.200] SPEAKER_00 (en, confidence 0.94): "
        "Hello <there> & welcome.\n"
        "[00:00:04.200 - 00:00:05.000] SPEAKER_01 (en, confidence 0.82): "
        "Adjacent cue uses --> safely.\n"
        "[00:00:04.900 - 00:00:08.000] SPEAKER_00 (sv): "
        "Overlapping segment stays in JSON order.\n"
    )


def _expected_md() -> str:
    return (
        "# Transcript\n"
        "\n"
        "Language: en (confidence 0.98)  \n"
        "Duration: 8.000 seconds\n"
        "\n"
        "## Warnings\n"
        "\n"
        "- low_confidence_segment\n"
        "\n"
        "| Start | End | Speaker | Language | Confidence | Text |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 00:00:00.000 | 00:00:04.200 | SPEAKER_00 | en | 0.94 | "
        "Hello &lt;there&gt; &amp; welcome. |\n"
        "| 00:00:04.200 | 00:00:05.000 | SPEAKER_01 | en | 0.82 | "
        "Adjacent cue uses --&gt; safely. |\n"
        "| 00:00:04.900 | 00:00:08.000 | SPEAKER_00 | sv |  | "
        "Overlapping segment stays in JSON order. |\n"
    )


def _expected_vtt() -> str:
    return (
        "WEBVTT\n"
        "\n"
        "seg-0001\n"
        "00:00:00.000 --> 00:00:04.200\n"
        "SPEAKER_00: Hello &lt;there&gt; &amp; welcome.\n"
        "\n"
        "seg->bad id\n"
        "00:00:04.200 --> 00:00:05.000\n"
        "SPEAKER_01: Adjacent cue uses -&gt; safely.\n"
        "\n"
        "seg-0003\n"
        "00:00:04.900 --> 00:00:08.000\n"
        "SPEAKER_00: Overlapping segment stays in JSON order.\n"
    )


def _expected_srt() -> str:
    return (
        "1\n"
        "00:00:00,000 --> 00:00:04,200\n"
        "SPEAKER_00: Hello &lt;there&gt; &amp; welcome.\n"
        "\n"
        "2\n"
        "00:00:04,200 --> 00:00:05,000\n"
        "SPEAKER_01: Adjacent cue uses -&gt; safely.\n"
        "\n"
        "3\n"
        "00:00:04,900 --> 00:00:08,000\n"
        "SPEAKER_00: Overlapping segment stays in JSON order.\n"
    )
