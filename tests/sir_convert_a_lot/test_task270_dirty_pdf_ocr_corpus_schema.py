"""Tests for the Task 270 dirty PDF OCR corpus schema.

Purpose:
    Validate metadata-only dirty PDF OCR corpus manifests, sanitized Task 74
    report extensions, and fail-closed benchmark profile handling without
    requiring private source PDFs in the repository.

Relationships:
    - Tests `scripts.sir_convert_a_lot.benchmarking.dirty_pdf_corpus`.
    - Exercises the Task 74 harness extension in
      `scripts.sir_convert_a_lot.benchmark_story20_throughput_report`.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.benchmark_story20_throughput_report import (
    ProfileSpec,
    RuntimeParityInputs,
    run_benchmark,
)
from scripts.sir_convert_a_lot.benchmarking import dirty_pdf_corpus
from scripts.sir_convert_a_lot.benchmarking.dirty_pdf_corpus import load_dirty_corpus_manifest
from scripts.sir_convert_a_lot.benchmarking.story20_throughput_types import (
    CorpusFileRecord,
    ProfilePayload,
)
from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult


def _stub_execute_v2_job_conversion(*, config, **_kwargs):
    if not config.enable_parallel_pdf_chunks:
        time.sleep(0.08)
    elif config.max_chunk_workers <= 2:
        time.sleep(0.03)
    else:
        time.sleep(0.01)
    return V2ExecutionResult(
        artifact_bytes=b"# benchmark\n",
        pipeline_used="pdf_to_md_v2",
        backend_used="docling",
        acceleration_used="cpu",
        warnings=[],
        phase_timings_ms={"conversion_total_ms": 10},
        options_fingerprint="sha256:task270-stub",
        ocr_enabled=True,
        ocr_engine_used="easyocr",
        ocr_languages_used=["sv", "en"],
    )


def _dirty_manifest_json(
    *,
    privacy_state: str = "private",
    include_path_field: bool = False,
    source_sha256: str = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ),
    page_count: int = 42,
) -> str:
    path_field = ', "source_pdf_path": "/private/corpus/dirty.pdf"' if include_path_field else ""
    return (
        "{"
        '"schema_version":"dirty_pdf_ocr_corpus_manifest_v1",'
        '"corpus_id":"task270-dirty-corpus-test",'
        '"entries":['
        "{"
        '"source_id":"dirty-sv-001",'
        f'"source_sha256":"{source_sha256}",'
        f'"page_count":{page_count},'
        '"dirty_data_classes":['
        '"scanned",'
        '"mixed_scanned_text",'
        '"low_contrast",'
        '"rotated_skewed",'
        '"table_form_heavy",'
        '"swedish_diacritic",'
        '"long_document"'
        "],"
        '"expected_ocr_languages":["sv","en"],'
        f'"privacy_state":"{privacy_state}",'
        '"safe_excerpts_may_be_reported":false'
        f"{path_field}"
        "}"
        "]"
        "}"
    )


def _write_private_pdf(path: Path, *, page_count: int = 1) -> str:
    import pymupdf

    path.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    try:
        for page_index in range(page_count):
            page = document.new_page(width=595, height=842)
            if page is None:
                raise RuntimeError("PyMuPDF returned no page for dirty fixture generation.")
            page.insert_textbox(
                pymupdf.Rect(48, 48, 547, 794),
                f"Private dirty OCR fixture page {page_index + 1} with å ä ö.",
                fontsize=14,
            )
        document.save(path.as_posix())
    finally:
        document.close()
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _service_profile_payload(
    *,
    profile: ProfileSpec,
    corpus_records: list[CorpusFileRecord],
) -> ProfilePayload:
    total_pages = sum(record["page_count"] for record in corpus_records)
    total_latency_seconds = 120.0
    return {
        "profile_name": profile.profile_name,
        "config": {
            "parallel_enabled": profile.parallel_enabled,
            "max_chunk_workers": profile.max_chunk_workers,
            "chunk_size_pages": profile.chunk_size_pages,
            "gpu_stage_max_concurrency": profile.gpu_stage_max_concurrency,
            "acceleration_policy": "gpu_required",
        },
        "summary": {
            "total_jobs": len(corpus_records),
            "succeeded_jobs": len(corpus_records),
            "failed_jobs": 0,
            "success_rate": 1.0,
            "error_rate": 0.0,
            "total_latency_seconds": total_latency_seconds,
            "latency_seconds": {
                "min": total_latency_seconds,
                "mean": total_latency_seconds,
                "p50": total_latency_seconds,
                "p90": total_latency_seconds,
                "max": total_latency_seconds,
            },
            "pages_per_minute_p50": round((float(total_pages) / total_latency_seconds) * 60.0, 6),
        },
        "resource_evidence": {
            "peak_jobs_queued": 0.0,
            "peak_jobs_active": 1.0,
            "peak_worker_saturation_ratio": 0.0,
            "peak_chunk_worker_saturation_ratio": 0.0,
            "peak_gpu_busy_percent": 50.0,
            "peak_gpu_memory_used_percent": 20.0,
            "contains_job_id_label": False,
        },
        "jobs": [
            {
                "source_file": record["filename"],
                "page_count": record["page_count"],
                "job_id": f"job_{index:03d}",
                "status": "succeeded",
                "latency_seconds": total_latency_seconds,
                "pages_per_minute": round(
                    (float(record["page_count"]) / total_latency_seconds) * 60.0,
                    6,
                ),
                "backend_used": "docling",
                "acceleration_used": "cuda",
                "ocr_enabled": True,
                "ocr_engine_used": "easyocr",
                "ocr_languages_used": ["sv", "en"],
                "gpu_busy_percent": 50,
                "gpu_memory_used_percent": 20,
                "warnings": [],
            }
            for index, record in enumerate(corpus_records, start=1)
        ],
    }


def test_dirty_corpus_manifest_validates_metadata_without_private_pdfs(tmp_path: Path) -> None:
    manifest_path = tmp_path / "dirty-corpus-manifest.json"
    manifest_path.write_text(_dirty_manifest_json(), encoding="utf-8")

    manifest = load_dirty_corpus_manifest(manifest_path)

    assert manifest["entry_count"] == 1
    assert manifest["total_pages"] == 42
    assert manifest["contains_real_dirty_inputs"] is True
    assert manifest["source_hashes_verified"] is False
    assert manifest["real_data_gate_satisfied"] is False
    assert manifest["missing_required_dirty_data_classes"] == []
    assert manifest["expected_ocr_languages"] == ["en", "sv"]


def test_dirty_corpus_manifest_rejects_commit_ready_source_paths(tmp_path: Path) -> None:
    manifest_path = tmp_path / "dirty-corpus-manifest.json"
    manifest_path.write_text(
        _dirty_manifest_json(include_path_field=True),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source_pdf_path is not allowed"):
        load_dirty_corpus_manifest(manifest_path)


def test_dirty_corpus_manifest_marks_synthetic_only_as_non_acceptance(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "dirty-corpus-manifest.json"
    manifest_path.write_text(
        _dirty_manifest_json(privacy_state="synthetic"),
        encoding="utf-8",
    )

    manifest = load_dirty_corpus_manifest(manifest_path)

    assert manifest["synthetic_fixture_entry_count"] == 1
    assert manifest["contains_real_dirty_inputs"] is False
    assert manifest["real_data_gate_satisfied"] is False


def test_dirty_corpus_manifest_command_prints_sanitized_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "dirty-corpus-manifest.json"
    manifest_path.write_text(_dirty_manifest_json(), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "dirty_pdf_corpus",
            "--manifest",
            manifest_path.as_posix(),
        ],
    )

    dirty_pdf_corpus.main()

    output = capsys.readouterr().out
    assert "dirty-corpus-manifest-valid" in output
    assert "task270-dirty-corpus-test" in output
    assert manifest_path.as_posix() not in output
    assert "/private/corpus" not in output


def test_run_benchmark_rejects_dirty_manifest_without_hash_verified_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2,
        "execute_v2_job_conversion",
        _stub_execute_v2_job_conversion,
    )
    manifest_path = tmp_path / "dirty-corpus-manifest.json"
    manifest_path.write_text(_dirty_manifest_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="private source root"):
        run_benchmark(
            output_json=tmp_path / "task74.json",
            output_report=tmp_path / "task74.md",
            corpus_root=tmp_path / "corpus",
            data_root=tmp_path / "runtime",
            page_counts=(2,),
            api_key="benchmark-key",
            acceleration_policy="cpu_only",
            ocr_mode="off",
            ocr_engine="auto",
            ocr_languages=[],
            gpu_available=False,
            dirty_corpus_manifest=manifest_path,
        )


def test_run_benchmark_embeds_verified_dirty_corpus_report_extension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2,
        "execute_v2_job_conversion",
        _stub_execute_v2_job_conversion,
    )
    private_source_root = tmp_path / "private" / "Class 9A Student Names"
    private_pdf = private_source_root / "olof-private-dirty-source.pdf"
    source_sha256 = _write_private_pdf(private_pdf, page_count=1)
    manifest_path = tmp_path / "dirty-corpus-manifest.json"
    manifest_path.write_text(
        _dirty_manifest_json(source_sha256=source_sha256, page_count=1),
        encoding="utf-8",
    )

    payload = run_benchmark(
        output_json=tmp_path / "task74.json",
        output_report=tmp_path / "task74.md",
        corpus_root=tmp_path / "corpus",
        data_root=tmp_path / "runtime",
        page_counts=(2,),
        api_key="benchmark-key",
        acceleration_policy="cpu_only",
        ocr_mode="off",
        ocr_engine="auto",
        ocr_languages=[],
        gpu_available=False,
        runtime_parity_inputs=RuntimeParityInputs(
            report_json_path=None,
            status="passed",
            lane="host",
            expected_revision="abc",
            remote_revision="abc",
            service_revision="abc",
            expected_revision_matches_remote=True,
            service_revision_matches_remote=True,
            live_smoke_passed=True,
            metrics_scan_passed=True,
        ),
        dirty_corpus_manifest=manifest_path,
        dirty_corpus_source_root=private_source_root,
    )

    dirty_corpus = payload["dirty_corpus"]
    assert dirty_corpus is not None
    assert dirty_corpus["schema_version"] == "dirty_pdf_ocr_benchmark_report_extension_v1"
    assert dirty_corpus["manifest"]["source_hashes_verified"] is True
    assert dirty_corpus["manifest"]["executed_entry_count"] == 1
    assert dirty_corpus["manifest"]["real_data_gate_satisfied"] is True
    assert payload["corpus"]["files"] == [
        {
            "filename": "dirty-sv-001.pdf",
            "page_count": 1,
            "size_bytes": (tmp_path / "corpus" / "dirty-sv-001.pdf").stat().st_size,
            "sha256": source_sha256,
        }
    ]
    assert dirty_corpus["task76_parity_required"] is True
    assert dirty_corpus["task76_parity_proven"] is True
    assert dirty_corpus["all_profiles_safe"] is True
    assert dirty_corpus["ocr_metadata_summary"]["ocr_engine_used_values"] == ["easyocr"]
    assert dirty_corpus["task271_proof"]["target_executed_pages"] == 150
    assert dirty_corpus["task271_proof"]["tuned_total_pages"] == 1
    assert dirty_corpus["task271_proof"]["meets_150_page_target"] is False
    output_json_text = (tmp_path / "task74.json").read_text(encoding="utf-8")
    report_text = (tmp_path / "task74.md").read_text(encoding="utf-8")
    assert "## Dirty Corpus Manifest" in report_text
    assert "## Dirty Corpus Safety" in report_text
    assert "## Dirty Corpus OCR Metadata" in report_text
    assert "## Task 271 Final Proof Target" in report_text
    assert manifest_path.as_posix() not in output_json_text
    assert private_source_root.as_posix() not in output_json_text
    assert private_pdf.name not in output_json_text
    assert manifest_path.as_posix() not in report_text
    assert private_source_root.as_posix() not in report_text
    assert private_pdf.name not in report_text


@pytest.mark.parametrize("page_count", [1, 149])
def test_task271_proof_rejects_under_150_pages_even_on_production_service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    page_count: int,
) -> None:
    private_source_root = tmp_path / "private"
    private_pdf = private_source_root / "dirty-source.pdf"
    source_sha256 = _write_private_pdf(private_pdf, page_count=page_count)
    manifest_path = tmp_path / "dirty-corpus-manifest.json"
    manifest_path.write_text(
        _dirty_manifest_json(source_sha256=source_sha256, page_count=page_count),
        encoding="utf-8",
    )

    def service_profile_stub(
        *,
        profile: ProfileSpec,
        service_url: str,
        corpus_root: Path,
        corpus_records: list[CorpusFileRecord],
        api_key: str,
        acceleration_policy: str,
        ocr_mode: str,
        ocr_engine: str,
        ocr_languages: list[str],
        max_poll_seconds: float,
    ) -> ProfilePayload:
        del service_url, corpus_root, api_key, acceleration_policy
        del ocr_mode, ocr_engine, ocr_languages, max_poll_seconds
        return _service_profile_payload(profile=profile, corpus_records=corpus_records)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.benchmarking.story20_profile_runner.run_service_profile",
        service_profile_stub,
    )

    payload = run_benchmark(
        output_json=tmp_path / f"task74-{page_count}.json",
        output_report=tmp_path / f"task74-{page_count}.md",
        corpus_root=tmp_path / f"corpus-{page_count}",
        data_root=tmp_path / f"runtime-{page_count}",
        api_key="benchmark-key",
        acceleration_policy="gpu_required",
        ocr_mode="force",
        ocr_engine="easyocr",
        ocr_languages=["sv", "en"],
        runtime_mode="production_service",
        runtime_host="hemma",
        runtime_service_url="http://127.0.0.1:28085",
        runtime_parity_inputs=RuntimeParityInputs(
            report_json_path=None,
            status="passed",
            lane="host",
            expected_revision="abc",
            remote_revision="abc",
            service_revision="abc",
            expected_revision_matches_remote=True,
            service_revision_matches_remote=True,
            live_smoke_passed=True,
            metrics_scan_passed=True,
        ),
        profiles=[
            ProfileSpec(
                profile_name="production_service_current",
                parallel_enabled=True,
                max_chunk_workers=2,
                chunk_size_pages=4,
                gpu_stage_max_concurrency=2,
            )
        ],
        dirty_corpus_manifest=manifest_path,
        dirty_corpus_source_root=private_source_root,
    )

    dirty_corpus = payload["dirty_corpus"]
    assert dirty_corpus is not None
    task271_proof = dirty_corpus["task271_proof"]
    assert task271_proof["production_service_runtime"] is True
    assert task271_proof["source_hashes_verified"] is True
    assert task271_proof["tuned_total_pages"] == page_count
    assert task271_proof["target_executed_pages"] == 150
    assert task271_proof["target_wall_clock_seconds"] == 3600
    assert task271_proof["meets_150_page_target"] is False


def test_dirty_corpus_report_fails_closed_on_removed_four_worker_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2,
        "execute_v2_job_conversion",
        _stub_execute_v2_job_conversion,
    )
    manifest_path = tmp_path / "dirty-corpus-manifest.json"
    manifest_path.write_text(_dirty_manifest_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="must fail closed"):
        run_benchmark(
            output_json=tmp_path / "task74.json",
            output_report=tmp_path / "task74.md",
            corpus_root=tmp_path / "corpus",
            data_root=tmp_path / "runtime",
            page_counts=(2,),
            api_key="benchmark-key",
            acceleration_policy="cpu_only",
            ocr_mode="off",
            ocr_engine="auto",
            ocr_languages=[],
            gpu_available=False,
            profiles=[
                ProfileSpec(
                    profile_name="serial_baseline",
                    parallel_enabled=False,
                    max_chunk_workers=1,
                    chunk_size_pages=8,
                    gpu_stage_max_concurrency=1,
                ),
                ProfileSpec(
                    profile_name="parallel_4w_removed_oom",
                    parallel_enabled=True,
                    max_chunk_workers=4,
                    chunk_size_pages=4,
                    gpu_stage_max_concurrency=2,
                ),
            ],
            dirty_corpus_manifest=manifest_path,
        )
