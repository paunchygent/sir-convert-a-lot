"""Unit tests for live Docling GPU validation helpers.

Purpose:
    Validate deterministic helper behavior used by the canonical Hemma
    live-run command.

Relationships:
    - Tests `scripts.sir_convert_a_lot.live_docling_gpu_quality`.
    - Covers GPU utilization parsing and git revision helper behavior.
"""

from __future__ import annotations

import subprocess
from typing import Callable

from scripts.sir_convert_a_lot import live_docling_gpu_quality


def test_parse_gpu_busy_peak_reads_max_percent() -> None:
    smi_output = """
GPU[0]          : GPU use (%): 3
GPU[1]          : GPU use (%): 82
GPU[2]          : GPU use (%): 47
"""
    assert live_docling_gpu_quality.parse_gpu_busy_peak(smi_output) == 82


def test_parse_gpu_busy_peak_returns_zero_without_matches() -> None:
    smi_output = "GPU utilization unavailable"
    assert live_docling_gpu_quality.parse_gpu_busy_peak(smi_output) == 0


def test_try_read_git_head_returns_none_when_git_fails(monkeypatch) -> None:
    def _raise_git_error(*_: object, **__: object) -> str:
        raise subprocess.CalledProcessError(returncode=1, cmd=["git", "rev-parse", "HEAD"])

    monkeypatch.setattr(live_docling_gpu_quality.subprocess, "check_output", _raise_git_error)
    assert live_docling_gpu_quality.try_read_git_head() is None


def test_try_read_git_head_returns_trimmed_revision(monkeypatch) -> None:
    def _return_sha(*_: object, **__: object) -> str:
        return "abc123\n"

    monkeypatch.setattr(live_docling_gpu_quality.subprocess, "check_output", _return_sha)
    assert live_docling_gpu_quality.try_read_git_head() == "abc123"


def test_manifest_is_consistent_returns_true_for_matching_hash_and_size() -> None:
    markdown = "hello world\n"
    markdown_bytes = markdown.encode("utf-8")
    result_payload: dict[str, object] = {
        "artifact": {
            "sha256": live_docling_gpu_quality.hashlib.sha256(markdown_bytes).hexdigest(),
            "size_bytes": len(markdown_bytes),
        },
        "markdown_content": markdown,
    }
    assert live_docling_gpu_quality.manifest_is_consistent(result_payload) is True


def test_manifest_is_consistent_returns_false_for_mismatch() -> None:
    result_payload: dict[str, object] = {
        "artifact": {"sha256": "bad", "size_bytes": 1},
        "markdown_content": "content\n",
    }
    assert live_docling_gpu_quality.manifest_is_consistent(result_payload) is False


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeClient:
    def __init__(self, responder: Callable[[], dict[str, object]]) -> None:
        self._responder = responder

    def get(self, _url: str, headers: dict[str, str]) -> _FakeResponse:
        assert headers["X-API-Key"] == "k"
        return _FakeResponse(self._responder())


def test_fetch_result_with_manifest_check_retries_until_consistent(monkeypatch) -> None:
    markdown = "ok\n"
    markdown_bytes = markdown.encode("utf-8")
    good_payload: dict[str, object] = {
        "result": {
            "artifact": {
                "sha256": live_docling_gpu_quality.hashlib.sha256(markdown_bytes).hexdigest(),
                "size_bytes": len(markdown_bytes),
            },
            "markdown_content": markdown,
            "conversion_metadata": {},
        }
    }
    bad_payload: dict[str, object] = {
        "result": {
            "artifact": {"sha256": "bad", "size_bytes": 1},
            "markdown_content": markdown,
            "conversion_metadata": {},
        }
    }
    calls = {"count": 0}

    def _responder() -> dict[str, object]:
        calls["count"] += 1
        if calls["count"] == 1:
            return bad_payload
        return good_payload

    monkeypatch.setattr(live_docling_gpu_quality.time, "sleep", lambda _seconds: None)
    result, consistent = live_docling_gpu_quality.fetch_result_with_manifest_check(
        fetch_result=lambda url, headers: _FakeClient(_responder).get(url, headers),
        job_id="job_1",
        api_key="k",
        max_attempts=3,
        retry_delay_seconds=0.0,
    )

    assert consistent is True
    assert result["markdown_content"] == markdown
    assert calls["count"] == 2


def test_fetch_result_with_manifest_check_returns_false_after_retries(monkeypatch) -> None:
    markdown = "still bad\n"
    payload: dict[str, object] = {
        "result": {
            "artifact": {"sha256": "bad", "size_bytes": 1},
            "markdown_content": markdown,
            "conversion_metadata": {},
        }
    }
    calls = {"count": 0}

    def _responder() -> dict[str, object]:
        calls["count"] += 1
        return payload

    monkeypatch.setattr(live_docling_gpu_quality.time, "sleep", lambda _seconds: None)
    result, consistent = live_docling_gpu_quality.fetch_result_with_manifest_check(
        fetch_result=lambda url, headers: _FakeClient(_responder).get(url, headers),
        job_id="job_2",
        api_key="k",
        max_attempts=3,
        retry_delay_seconds=0.0,
    )

    assert consistent is False
    assert result["markdown_content"] == markdown
    assert calls["count"] == 3
