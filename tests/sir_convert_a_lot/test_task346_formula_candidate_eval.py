"""Tests for Task 346 formula candidate evaluation.

Purpose:
    Prove the Task 346 evaluation harness extracts established replay formula
    regions, records candidate blockers, and produces reviewable local reports.

Relationships:
    Exercises `scripts.sir_convert_a_lot.devops.task346_formula_candidate_eval`
    without invoking heavyweight OCR/model runtimes.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.task346_formula_candidate_eval import (
    BAD_MARKERS,
    CandidateSpec,
    SourceInput,
    collect_marker_counts,
    harvest_formula_regions,
    render_visual_review_index,
    run_external_candidate,
)
from scripts.sir_convert_a_lot.devops.task346_formula_candidate_eval_candidates import (
    candidate_output_text,
    default_external_candidates,
)


def test_harvest_formula_regions_maps_relative_docling_pages() -> None:
    report = {
        "records": [
            {
                "child_payload": {"start_page": 13},
                "formula_diagnostics_events": [
                    {
                        "event": "code_formula_batch_started",
                        "crops": [
                            {
                                "item_self_ref": "#/texts/5",
                                "label": "formula",
                                "prov_page_no": 2,
                                "image_width": 320,
                                "image_height": 64,
                                "image_sha256": "abc",
                                "prov_bbox": {"l": 10.0, "t": 200.0, "r": 300.0, "b": 150.0},
                            }
                        ],
                    }
                ],
            }
        ]
    }

    regions = harvest_formula_regions(report, fallback_first_page=13)

    assert regions == [
        {
            "id": "p14-texts-5",
            "item_self_ref": "#/texts/5",
            "absolute_page": 14,
            "relative_page": 2,
            "label": "formula",
            "image_width": 320,
            "image_height": 64,
            "image_sha256": "abc",
            "bbox": {"l": 10.0, "t": 200.0, "r": 300.0, "b": 150.0},
        }
    ]


def test_marker_counts_include_task344_failure_markers() -> None:
    text = "$$bad </formula$$ \\mathbmath l o o l y " + "\\mathbf " * 3

    counts = collect_marker_counts(text)

    assert set(counts) == set(BAD_MARKERS)
    assert counts["</formula"] == 1
    assert counts["\\mathbmath"] == 1
    assert counts["l o o l y"] == 1
    assert counts["\\mathbf"] == 3


def test_external_candidate_records_missing_executable_blocker(tmp_path: Path) -> None:
    image_path = tmp_path / "crop.png"
    image_path.write_bytes(b"fake")
    source_input = SourceInput(
        input_id="crop-1",
        kind="formula_crop",
        page=14,
        image_path=image_path,
        source_text_path=None,
    )
    candidate = CandidateSpec(
        candidate_id="missing_paddle",
        label="Missing Paddle",
        kind="paddle_pipeline",
        model_name="UniMERNet",
        input_kind="formula_crop",
    )

    result = run_external_candidate(
        candidate=candidate,
        source_inputs=(source_input,),
        output_root=tmp_path / "out",
        executable="definitely-missing-paddleocr",
        device="gpu:0",
        paddle_template=None,
        timeout_seconds=1.0,
        deepseek_template=None,
        deepseek_batch_template=None,
    )

    assert result["status"] == "blocked"
    assert result["block_reason"] == "candidate_executable_not_found"
    assert result["input_count"] == 1


def test_visual_review_index_links_images_and_outputs(tmp_path: Path) -> None:
    image_path = tmp_path / "source.png"
    image_path.write_bytes(b"fake")
    output_path = tmp_path / "candidate.txt"
    output_path.write_text("\\alpha + \\beta", encoding="utf-8")
    index_path = tmp_path / "review.html"

    render_visual_review_index(
        path=index_path,
        source_inputs=(
            SourceInput(
                input_id="formula-p14-texts-5",
                kind="formula_crop",
                page=14,
                image_path=image_path,
                source_text_path=None,
            ),
        ),
        candidate_results=(
            {
                "candidate_id": "source_layer_pymupdf",
                "input_results": [
                    {
                        "input_id": "formula-p14-texts-5",
                        "output_text_path": output_path.as_posix(),
                    }
                ],
            },
        ),
    )

    rendered = index_path.read_text(encoding="utf-8")
    assert "formula-p14-texts-5" in rendered
    assert "\\alpha + \\beta" in rendered
    assert "source.png" in rendered


def test_candidate_output_text_reads_configured_text_artifact(tmp_path: Path) -> None:
    candidate_dir = tmp_path / "deepseek"
    candidate_dir.mkdir()
    (candidate_dir / "stdout.txt").write_text("progress only", encoding="utf-8")
    (candidate_dir / "deepseek-output.txt").write_text("$$x^2 + y^2$$", encoding="utf-8")

    text = candidate_output_text(output_root=candidate_dir, stdout="fallback")

    assert "$$x^2 + y^2$$" in text
    assert "progress only" not in text


def test_candidate_output_text_reads_deepseek_native_mmd_artifact(tmp_path: Path) -> None:
    candidate_dir = tmp_path / "deepseek"
    candidate_dir.mkdir()
    (candidate_dir / "result.mmd").write_text("$$E = mc^2$$", encoding="utf-8")

    text = candidate_output_text(output_root=candidate_dir, stdout="fallback")

    assert "$$E = mc^2$$" in text
    assert "fallback" not in text


def test_default_deepseek_candidate_uses_hf_eager_single_image_lane() -> None:
    candidates = {candidate.candidate_id: candidate for candidate in default_external_candidates()}

    deepseek = candidates["deepseek_ocr2_hf_eager"]

    assert deepseek.kind == "deepseek_template"
    assert deepseek.input_kind == "page"
    assert "HF eager" in deepseek.label
    assert "deepseek_ocr2_command" not in candidates
