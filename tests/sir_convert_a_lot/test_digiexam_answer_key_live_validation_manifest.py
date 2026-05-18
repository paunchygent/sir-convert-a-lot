"""Tests for Task 309 DigiExam answer-key live-validation manifests.

Purpose:
    Prove that the versioned Task 309 DigiExam DXE fixture corpus produces
    item-addressable validation metadata and expected-answer worklists without
    leaking raw prompts, alternatives, images, or provider artifacts.

Relationships:
    - Exercises `domain.digiexam_answer_key_live_validation_manifest`.
    - Guards the Task 309 corpus/golden groundwork before Hemma live runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_answer_key_live_validation
from scripts.sir_convert_a_lot.devops import (
    run_digiexam_answer_key_live_validation as digiexam_runner,
)
from scripts.sir_convert_a_lot.devops.answer_key_provider_run_metadata import (
    build_answer_key_provider_run_metadata,
)
from scripts.sir_convert_a_lot.devops.digiexam_answer_key_corpus_coverage import (
    build_task309_corpus_coverage_proof,
)
from scripts.sir_convert_a_lot.devops.digiexam_answer_key_live_corpus_execution import (
    Task309AdvisoryCorpusRunReport,
)
from scripts.sir_convert_a_lot.devops.digiexam_answer_key_openai_eval_gate import (
    OpenAIDataURLVisionCandidatePlanner,
)
from scripts.sir_convert_a_lot.devops.run_digiexam_answer_key_live_validation import (
    main as task309_runner_main,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    answer_key_candidate_planner_for_profile,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_goldens import (
    TASK309_EXPECTED_ANSWER_MANIFEST_SCHEMA_VERSION,
    validate_task309_expected_answer_manifest,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_manifest import (
    TASK309_CORPUS_ID,
    TASK309_CORPUS_MANIFEST_SCHEMA_VERSION,
    TASK309_EXPECTED_ANSWER_WORKLIST_SCHEMA_VERSION,
    TASK309_FIXTURE_POLICY,
    Task309AssetEvalPolicy,
    build_task309_expected_answer_worklist,
    build_task309_live_validation_manifest,
    write_task309_json,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMImageURLContentPart,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_local_model_profiles import (
    AnswerKeyProviderProfileName,
    AnswerKeyStructuredProviderRuntime,
    answer_key_defaults_for_provider_profile,
    build_answer_key_provider_profile,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_openai_model_profiles import (
    answer_key_openai_defaults_for_provider_profile,
    build_answer_key_openai_provider_profile,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_answer_key_vision_assets import (
    export_digiexam_answer_key_vision_assets,
)

_CORPUS_ROOT = Path("inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe")
_EXPECTED_ANSWER_MANIFEST = _CORPUS_ROOT / "expected-answer-manifest.json"
_FORBIDDEN_MARKERS = (
    "bodyHTML",
    "prompt_html",
    "prompt_lines",
    "content_base64",
    "alternatives",
    "provider_response",
    "system_prompt",
    "user_payload",
)


def test_answer_key_live_validation_dispatches_to_digiexam_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[list[str]] = []

    def fake_digiexam_main(argv: list[str] | None = None) -> int:
        received.append(list(argv or []))
        return 0

    monkeypatch.setattr(run_answer_key_live_validation, "digiexam_main", fake_digiexam_main)

    assert run_answer_key_live_validation.main(["digiexam", "status"]) == 0
    assert received == [["status"]]


def test_task309_manifest_records_versioned_fixture_corpus() -> None:
    manifest = build_task309_live_validation_manifest(_CORPUS_ROOT)
    payload = manifest.to_payload()
    summary = _object(payload["summary"])

    assert payload["schema_version"] == TASK309_CORPUS_MANIFEST_SCHEMA_VERSION
    assert payload["corpus_id"] == TASK309_CORPUS_ID
    assert payload["fixture_policy"] == TASK309_FIXTURE_POLICY
    assert summary["file_count"] == 23
    assert summary["item_count"] == 317
    assert summary["eligible_item_count"] == 42
    assert _count_map(summary["item_type_counts"]) == {
        "gap_fill": 13,
        "multiple_response": 4,
        "open_ended": 273,
        "single_choice": 27,
    }
    assert _count_map(summary["output_mode_counts"]) == {
        "json_schema": 11,
        "not_applicable": 275,
        "vllm_choice": 31,
    }
    assert _count_map(summary["skip_reason_counts"]) == {
        "none": 42,
        "unsupported_assets": 2,
        "unsupported_item_type": 273,
    }


def test_task309_corpus_coverage_proof_reports_missing_eligible_items() -> None:
    proof = build_task309_corpus_coverage_proof(
        manifest_items={
            ("exam-a.dxe", "item-001"): {"eligible": True, "skip_reason": "none"},
            ("exam-a.dxe", "item-002"): {"eligible": False, "skip_reason": "unsupported"},
            ("exam-b.dxe", "item-001"): {"eligible": True, "skip_reason": "none"},
        },
        report_keys={("exam-a.dxe", "item-001"), ("extra.dxe", "item-999")},
    )
    payload = proof.to_payload()

    assert payload["manifest_item_count"] == 3
    assert payload["manifest_eligible_item_count"] == 2
    assert payload["report_unique_item_count"] == 2
    assert payload["reported_manifest_item_count"] == 1
    assert payload["all_manifest_items_reported"] is False
    assert payload["all_eligible_items_reported"] is False
    assert payload["missing_manifest_item_count"] == 2
    assert payload["missing_eligible_item_count"] == 1
    assert payload["unexpected_report_item_count"] == 1
    missing_eligible_items = payload["missing_eligible_items"]
    assert isinstance(missing_eligible_items, tuple)
    assert tuple(_object(item) for item in missing_eligible_items) == (
        {
            "source_filename": "exam-b.dxe",
            "item_id": "item-001",
            "eligible": True,
            "skip_reason": "none",
        },
    )


def test_task309_expected_answer_worklist_contains_only_eligible_items() -> None:
    manifest = build_task309_live_validation_manifest(_CORPUS_ROOT)
    worklist = build_task309_expected_answer_worklist(manifest)
    payload = worklist.to_payload()
    items = _objects(payload["items"])

    assert payload["schema_version"] == TASK309_EXPECTED_ANSWER_WORKLIST_SCHEMA_VERSION
    assert payload["corpus_id"] == TASK309_CORPUS_ID
    assert len(items) == 42
    assert {item["expected_answer_state"] for item in items} == {"pending_teacher_verified_golden"}
    assert {item["output_mode"] for item in items} == {"json_schema", "vllm_choice"}


def test_task309_vision_asset_eval_policy_marks_supported_asset_items_eligible() -> None:
    manifest = build_task309_live_validation_manifest(
        _CORPUS_ROOT,
        asset_eval_policy=Task309AssetEvalPolicy(allow_supported_embedded_assets=True),
    )
    payload = manifest.to_payload()
    summary = _object(payload["summary"])
    asset_items = {
        (item["source_filename"], item["item_id"]): item
        for file_entry in _objects(payload["files"])
        for item in _objects(file_entry["items"])
        if item["embedded_asset_count"] == 1
    }

    assert summary["eligible_item_count"] == 44
    assert _count_map(summary["skip_reason_counts"]) == {
        "none": 44,
        "unsupported_item_type": 273,
    }
    assert (
        asset_items[("1776888013-ak7-lag-och-ratt.dxe", "item-003")]["output_mode"] == "json_schema"
    )
    assert (
        asset_items[("1811577114-ekologiprov-v-49-25d-e.dxe", "item-013")]["skip_reason"] == "none"
    )


def test_task309_manifest_outputs_do_not_persist_raw_prompt_or_provider_content(
    tmp_path: Path,
) -> None:
    manifest = build_task309_live_validation_manifest(_CORPUS_ROOT)
    worklist = build_task309_expected_answer_worklist(manifest)
    manifest_path = tmp_path / "validation-corpus-manifest.json"
    worklist_path = tmp_path / "expected-answer-worklist.json"

    write_task309_json(manifest.to_payload(), manifest_path)
    write_task309_json(worklist.to_payload(), worklist_path)

    combined_text = manifest_path.read_text(encoding="utf-8")
    combined_text += worklist_path.read_text(encoding="utf-8")
    for marker in _FORBIDDEN_MARKERS:
        assert marker not in combined_text


def test_task309_expected_answer_manifest_validates_teacher_verified_goldens() -> None:
    report = validate_task309_expected_answer_manifest(
        corpus_root=_CORPUS_ROOT,
        expected_answer_manifest_path=_EXPECTED_ANSWER_MANIFEST,
    )
    payload = report.to_payload()
    summary = _object(payload["summary"])

    assert report.summary.valid is True
    assert report.issues == ()
    assert summary["eligible_item_count"] == 44
    assert summary["entry_count"] == 44
    assert summary["validated_item_count"] == 44
    assert summary["adjudication_required_count"] == 0


def test_task309_expected_answer_manifest_rejects_wrong_but_valid_shape(
    tmp_path: Path,
) -> None:
    payload = _object(json.loads(_EXPECTED_ANSWER_MANIFEST.read_text(encoding="utf-8")))
    entries = _objects(payload["entries"])
    entries[0]["expected_answer_payload"] = {
        "kind": "choice",
        "correct_alternative_ids": [9999],
    }
    bad_manifest_path = tmp_path / "expected-answer-manifest-bad.json"
    write_task309_json(payload, bad_manifest_path)

    report = validate_task309_expected_answer_manifest(
        corpus_root=_CORPUS_ROOT,
        expected_answer_manifest_path=bad_manifest_path,
    )

    assert report.summary.valid is False
    assert "invalid_expected_answer_payload" in {issue.code for issue in report.issues}


def test_task309_runner_validates_goldens_and_writes_retained_report(tmp_path: Path) -> None:
    exit_code = task309_runner_main(
        [
            "validate-goldens",
            "--corpus-root",
            _CORPUS_ROOT.as_posix(),
            "--expected-answer-manifest",
            _EXPECTED_ANSWER_MANIFEST.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
            "--fail-on-blocked",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "expected-answer-validation.json").read_text(encoding="utf-8"))
    )

    assert exit_code == 0
    assert report_payload["corpus_id"] == TASK309_CORPUS_ID
    assert _object(report_payload["summary"])["valid"] is True


def test_task309_runner_previews_consumer_friendly_request_shape(tmp_path: Path) -> None:
    exit_code = task309_runner_main(
        [
            "preview-request-shape",
            "--corpus-root",
            _CORPUS_ROOT.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
            "--fail-on-blocked",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "request-shape-preview.json").read_text(encoding="utf-8"))
    )
    items = _objects(report_payload["items"])

    assert exit_code == 0
    assert report_payload["ok"] is True
    assert report_payload["manifest_eligible_item_count"] == 42
    assert report_payload["attempted_item_count"] == 42
    assert report_payload["issue_count"] == 0
    assert {item["ok"] for item in items} == {True}
    assert (tmp_path / "request-shape-preview.md").exists()


def test_task309_runner_applies_qwen36_llama_cpp_profile_defaults(tmp_path: Path) -> None:
    exit_code = task309_runner_main(
        [
            "preview-request-shape",
            "--provider-profile",
            "qwen36-llama-cpp",
            "--corpus-root",
            _CORPUS_ROOT.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
            "--fail-on-blocked",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "request-shape-preview.json").read_text(encoding="utf-8"))
    )

    assert exit_code == 0
    assert report_payload["provider_url"] == "http://127.0.0.1:8082"
    assert report_payload["model"] == "qwen3.6-27b-q6k"
    assert report_payload["provider_runtime"] == "llama-cpp-json-schema"
    assert report_payload["manifest_eligible_item_count"] == 44
    assert report_payload["attempted_item_count"] == 44
    assert any(item["multimodal_request"] is True for item in _objects(report_payload["items"]))
    assert report_payload["ok"] is True


def test_evaluate_advisory_corpus_derives_reports_root_from_output_root(
    tmp_path: Path,
) -> None:
    parser = digiexam_runner._build_parser()
    args = parser.parse_args(
        [
            "evaluate-advisory-corpus",
            "--output-root",
            tmp_path.as_posix(),
        ]
    )

    digiexam_runner._apply_provider_defaults(args)

    assert args.output_root == tmp_path
    assert args.reports_root is None


def test_task326_openai_vision_planner_uses_data_url_image_parts(tmp_path: Path) -> None:
    source_path = _CORPUS_ROOT / "1776888013-ak7-lag-och-ratt.dxe"
    exam = build_digiexam_intermediate_exam(DigiExamDxeParser().parse_file(source_path))
    item = next(item for item in exam.items if item.item_id == "item-003")
    media_path = tmp_path / "vision-assets"
    item_assets = export_digiexam_answer_key_vision_assets(
        exam=exam,
        media_path=media_path,
        relative_path_prefix=source_path.stem,
    )
    defaults = answer_key_openai_defaults_for_provider_profile("openai-gpt-5.4-mini-2026-03-17")
    profile = build_answer_key_openai_provider_profile(defaults)
    planner = OpenAIDataURLVisionCandidatePlanner(
        base_planner=answer_key_candidate_planner_for_profile(profile),
        item_assets_by_id=item_assets,
        media_path=media_path,
    )

    plan = planner.plan_candidate(job_id="task326:test", item=item, profile=profile)

    assert plan is not None
    image_parts = tuple(
        part
        for part in plan.request.user_content_parts
        if isinstance(part, StructuredLLMImageURLContentPart)
    )
    assert len(image_parts) == 1
    assert image_parts[0].url.startswith("data:image/png;base64,")


def test_task326_openai_runner_blocks_without_sanctioned_credential(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("SIR_CONVERT_A_LOT_OPENAI_API_KEY", raising=False)

    exit_code = task309_runner_main(
        [
            "run-openai-advisory-corpus",
            "--openai-provider-profile",
            "openai-gpt-5.4-mini-2026-03-17",
            "--corpus-root",
            _CORPUS_ROOT.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
            "--fail-on-blocked",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "in-process-advisory-corpus-run.json").read_text(encoding="utf-8"))
    )

    assert exit_code == 2
    assert report_payload["blocked"] is True
    assert report_payload["credential_present"] is False
    assert report_payload["provider_profile_id"] == "openai-gpt-5.4-mini-2026-03-17"
    assert report_payload["report_paths"] == []


def test_task309_raw_llama_runtime_stays_text_only_without_named_vision_profile(
    tmp_path: Path,
) -> None:
    exit_code = task309_runner_main(
        [
            "preview-request-shape",
            "--provider-runtime",
            "llama-cpp-json-schema",
            "--corpus-root",
            _CORPUS_ROOT.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
            "--fail-on-blocked",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "request-shape-preview.json").read_text(encoding="utf-8"))
    )

    assert exit_code == 0
    assert report_payload["provider_runtime"] == "llama-cpp-json-schema"
    assert report_payload["manifest_eligible_item_count"] == 42
    assert report_payload["attempted_item_count"] == 42
    assert not any(item["multimodal_request"] is True for item in _objects(report_payload["items"]))
    assert report_payload["ok"] is True


def test_task309_advisory_corpus_keeps_vision_media_under_output_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "operator-output"
    reports_root = tmp_path / "custom-reports"
    captured: dict[str, object] = {}

    def fake_run_task309_advisory_corpus(
        **kwargs: object,
    ) -> Task309AdvisoryCorpusRunReport:
        captured.update(kwargs)
        provider_runtime = kwargs["provider_runtime"]
        assert isinstance(provider_runtime, AnswerKeyStructuredProviderRuntime)
        return Task309AdvisoryCorpusRunReport(
            schema_version="task309_granite_advisory_corpus_run_v1",
            provider_url=str(kwargs["provider_url"]),
            model=str(kwargs["model"]),
            provider_runtime=provider_runtime.value,
            corpus_root=str(kwargs["corpus_root"]),
            provider_ready=True,
            blocked=False,
            file_count=0,
            item_count=0,
            eligible_item_count=0,
            suggested_count=0,
            manual_follow_up_count=0,
            skipped_count=0,
            backend_failure_counts=(),
            asset_eligible_count=0,
            multimodal_request_count=0,
            provider_run_metadata=_provider_run_metadata_payload(
                profile_name=AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP,
                reports_root=reports_root,
                vision_media_path=output_root / "vision-assets",
            ),
            total_latency_ms=0.0,
            report_paths=(),
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_digiexam_answer_key_live_validation"
        ".run_task309_advisory_corpus",
        fake_run_task309_advisory_corpus,
    )

    exit_code = task309_runner_main(
        [
            "run-advisory-corpus",
            "--provider-profile",
            "qwen36-llama-cpp",
            "--output-root",
            output_root.as_posix(),
            "--reports-root",
            reports_root.as_posix(),
            "--corpus-root",
            _CORPUS_ROOT.as_posix(),
            "--skip-provider-ready-check",
            "--fail-on-blocked",
        ]
    )

    assert exit_code == 0
    assert captured["reports_root"] == reports_root
    assert captured["vision_media_path"] == output_root / "vision-assets"
    assert captured["supports_multimodal_vision"] is True


def test_task309_provider_status_surface_is_persistent_by_default(tmp_path: Path) -> None:
    exit_code = task309_runner_main(
        [
            "provider-status",
            "--output-root",
            tmp_path.as_posix(),
            "--container-name",
            "sir-convert-task309-test-missing",
            "--provider-url",
            "http://127.0.0.1:9",
            "--port",
            "9",
            "--timeout-seconds",
            "0.1",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "provider-status.json").read_text(encoding="utf-8"))
    )

    assert exit_code == 0
    assert report_payload["persistent_policy"] == "leave_running_until_operator_stop"
    assert report_payload["container_name"] == "sir-convert-task309-test-missing"
    assert report_payload["ready"] is False
    assert (tmp_path / "provider-status.md").exists()


def test_task309_provider_launch_surface_dry_runs_persistent_vllm_command(tmp_path: Path) -> None:
    exit_code = task309_runner_main(
        [
            "launch-provider",
            "--output-root",
            tmp_path.as_posix(),
            "--container-name",
            "sir-convert-task309-test",
            "--port",
            "8017",
            "--host-cache-path",
            "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            "--fail-on-blocked",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "provider-launch.json").read_text(encoding="utf-8"))
    )
    plan = _object(report_payload["plan"])
    command = plan["command"]
    assert isinstance(command, list)

    assert exit_code == 0
    assert report_payload["dry_run"] is True
    assert report_payload["ok"] is True
    assert plan["persistent_policy"] == "leave_running_until_operator_stop"
    assert "--rm" not in command
    assert "--disable-log-requests" in command
    assert "127.0.0.1:8017:8000" in command


def test_answer_key_llama_provider_launch_surface_dry_runs_hemma_local_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pretend_current_process_is_hemma(monkeypatch)
    exit_code = task309_runner_main(
        [
            "launch-llama-provider",
            "--provider-profile",
            "qwen36-llama-cpp-mtp",
            "--output-root",
            tmp_path.as_posix(),
            "--fail-on-blocked",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "llama-provider-launch.json").read_text(encoding="utf-8"))
    )
    plan = _object(report_payload["plan"])
    command = plan["command"]
    assert isinstance(command, list)

    assert exit_code == 0
    assert report_payload["dry_run"] is True
    assert report_payload["ok"] is True
    assert plan["provider_profile"] == "qwen36-llama-cpp-mtp"
    assert plan["provider_url"] == "http://127.0.0.1:8082"
    assert plan["model"] == "qwen3.6-27b-q6k-mtp"
    assert plan["host"] == "127.0.0.1"
    assert plan["port"] == 8082
    assert plan["hf_repo"] == "unsloth/Qwen3.6-27B-MTP-GGUF"
    assert plan["hf_file"] == "Qwen3.6-27B-Q6_K.gguf"
    assert "--n-gpu-layers" in command
    assert "all" in command
    assert "--offline" in command
    assert "--media-path" in command
    assert "--reasoning" in command
    assert "off" in command
    assert "--spec-type" in command
    assert "draft-mtp" in command
    assert "--spec-draft-n-max" in command
    assert "2" in command
    assert "--log-file" in command
    assert (tmp_path / "llama-provider-launch.md").exists()


def test_task309_microprobe_surface_blocks_without_ready_provider(tmp_path: Path) -> None:
    exit_code = task309_runner_main(
        [
            "microprobes",
            "--output-root",
            tmp_path.as_posix(),
            "--provider-url",
            "http://127.0.0.1:9",
            "--port",
            "9",
            "--timeout-seconds",
            "0.1",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "provider-microprobes.json").read_text(encoding="utf-8"))
    )

    assert exit_code == 0
    assert report_payload["blocked"] is True
    assert report_payload["provider_ready"] is False
    assert report_payload["results"] == []


def test_task309_in_process_corpus_surface_blocks_without_ready_provider(tmp_path: Path) -> None:
    exit_code = task309_runner_main(
        [
            "run-advisory-corpus",
            "--output-root",
            tmp_path.as_posix(),
            "--corpus-root",
            _CORPUS_ROOT.as_posix(),
            "--provider-url",
            "http://127.0.0.1:9",
            "--port",
            "9",
            "--timeout-seconds",
            "0.1",
        ]
    )
    report_payload = _object(
        json.loads((tmp_path / "in-process-advisory-corpus-run.json").read_text(encoding="utf-8"))
    )

    assert exit_code == 0
    assert report_payload["blocked"] is True
    assert report_payload["provider_ready"] is False
    assert report_payload["file_count"] == 23
    assert report_payload["report_paths"] == []
    metadata = _object(report_payload["provider_run_metadata"])
    assert metadata["available"] is True
    assert metadata["profile_name"] == "granite-vllm"
    assert metadata["model"] == "ibm-granite/granite-4.1-8b-fp8"


def test_task309_evaluation_uses_qwen_run_metadata_without_granite_fallback(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "qwen-eval"
    reports_root = output_root / "advisory-corpus-reports"
    reports_root.mkdir(parents=True)
    write_task309_json(
        {
            "schema_version": "digiexam_answer_key_completion_report_v1",
            "job_id": "task309:1776888013-ak7-lag-och-ratt",
            "completion_mode": "local_llm_suggest_missing_machine_marked",
            "items": [
                {
                    "item_id": "item-001",
                    "item_type": "gap_fill",
                    "sequence": 1,
                    "decision_state": "skipped",
                    "backend_failure_code": None,
                }
            ],
        },
        reports_root / "1776888013-ak7-lag-och-ratt.answer-key-completion-report.json",
    )
    write_task309_json(
        {
            "schema_version": "task309_granite_advisory_corpus_run_v1",
            "provider_run_metadata": _provider_run_metadata_payload(
                profile_name=AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP,
                reports_root=reports_root,
                vision_media_path=output_root / "vision-assets",
            ),
        },
        output_root / "in-process-advisory-corpus-run.json",
    )

    exit_code = task309_runner_main(
        [
            "evaluate-advisory-corpus",
            "--provider-profile",
            "qwen36-llama-cpp",
            "--expected-answer-manifest",
            _EXPECTED_ANSWER_MANIFEST.as_posix(),
            "--output-root",
            output_root.as_posix(),
            "--reports-root",
            reports_root.as_posix(),
        ]
    )
    evaluation = _object(
        json.loads((output_root / "advisory-golden-evaluation.json").read_text(encoding="utf-8"))
    )
    metadata = _object(json.loads(str(evaluation["provider_run_metadata_json"])))
    coverage = _object(evaluation["coverage_proof"])

    assert exit_code == 0
    assert coverage["manifest_item_count"] == 317
    assert coverage["manifest_eligible_item_count"] == 44
    assert coverage["report_unique_item_count"] == 1
    assert coverage["all_manifest_items_reported"] is False
    assert coverage["all_eligible_items_reported"] is False
    assert coverage["missing_eligible_item_count"] == 43
    assert metadata["available"] is True
    assert metadata["profile_name"] == "qwen36-llama-cpp"
    assert metadata["model"] == "qwen3.6-27b-q6k"
    assert metadata["provider_runtime"] == "llama-cpp-json-schema"
    assert metadata["default_output_mode"] == "json_schema"
    assert metadata["context_window_tokens"] == 16384
    assert metadata["max_output_tokens"] == 4096
    assert metadata["temperature"] == 0.15
    assert _object(metadata["capabilities"])["supports_multimodal_vision"] is True
    assert _object(metadata["request_settings"])["context_window_tokens"] == 16384
    assert _object(metadata["request_settings"])["temperature"] == 0.15
    assert (
        _object(metadata["artifact_paths"])["vision_media_path"]
        == (output_root / "vision-assets").as_posix()
    )
    assert "ibm-granite/granite-4.1-8b-fp8" not in str(evaluation["model_settings_json"])


def test_task309_evaluation_reports_unavailable_metadata_without_defaulting_to_granite(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "legacy-eval"
    reports_root = output_root / "advisory-corpus-reports"
    reports_root.mkdir(parents=True)
    write_task309_json(
        {
            "schema_version": "digiexam_answer_key_completion_report_v1",
            "job_id": "task309:1776888013-ak7-lag-och-ratt",
            "completion_mode": "local_llm_suggest_missing_machine_marked",
            "items": [],
        },
        reports_root / "1776888013-ak7-lag-och-ratt.answer-key-completion-report.json",
    )

    exit_code = task309_runner_main(
        [
            "evaluate-advisory-corpus",
            "--expected-answer-manifest",
            _EXPECTED_ANSWER_MANIFEST.as_posix(),
            "--output-root",
            output_root.as_posix(),
            "--reports-root",
            reports_root.as_posix(),
        ]
    )
    evaluation = _object(
        json.loads((output_root / "advisory-golden-evaluation.json").read_text(encoding="utf-8"))
    )
    metadata = _object(json.loads(str(evaluation["provider_run_metadata_json"])))

    assert exit_code == 0
    assert metadata["available"] is False
    assert str(metadata["metadata_source"]).startswith("run_report_missing:")
    assert "ibm-granite/granite-4.1-8b-fp8" not in str(evaluation["model_settings_json"])


def test_task309_evaluation_upgrades_legacy_qwen_run_report_metadata(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "legacy-qwen-eval"
    reports_root = output_root / "advisory-corpus-reports"
    reports_root.mkdir(parents=True)
    report_path = reports_root / "1776888013-ak7-lag-och-ratt.answer-key-completion-report.json"
    write_task309_json(
        {
            "schema_version": "digiexam_answer_key_completion_report_v1",
            "job_id": "task309:1776888013-ak7-lag-och-ratt",
            "completion_mode": "local_llm_suggest_missing_machine_marked",
            "items": [],
        },
        report_path,
    )
    write_task309_json(
        {
            "schema_version": "task309_granite_advisory_corpus_run_v1",
            "provider_url": "http://127.0.0.1:8082",
            "model": "qwen3.6-27b-q6k",
            "provider_runtime": "llama-cpp-json-schema",
            "report_paths": [report_path.as_posix()],
        },
        output_root / "in-process-advisory-corpus-run.json",
    )

    exit_code = task309_runner_main(
        [
            "evaluate-advisory-corpus",
            "--provider-profile",
            "qwen36-llama-cpp",
            "--expected-answer-manifest",
            _EXPECTED_ANSWER_MANIFEST.as_posix(),
            "--output-root",
            output_root.as_posix(),
            "--reports-root",
            reports_root.as_posix(),
        ]
    )
    evaluation = _object(
        json.loads((output_root / "advisory-golden-evaluation.json").read_text(encoding="utf-8"))
    )
    metadata = _object(json.loads(str(evaluation["provider_run_metadata_json"])))

    assert exit_code == 0
    assert metadata["metadata_source"] == "legacy_task309_run_report_profile_match"
    assert metadata["profile_name"] == "qwen36-llama-cpp"
    assert metadata["model"] == "qwen3.6-27b-q6k"
    assert metadata["context_window_tokens"] == 16384
    assert metadata["temperature"] == 0.15
    assert (
        _object(metadata["artifact_paths"])["vision_media_path"]
        == (output_root / "vision-assets").as_posix()
    )
    assert "ibm-granite/granite-4.1-8b-fp8" not in str(evaluation["model_settings_json"])


def test_task309_expected_answer_manifest_has_committed_schema() -> None:
    payload = _object(json.loads(_EXPECTED_ANSWER_MANIFEST.read_text(encoding="utf-8")))

    assert payload["schema_version"] == TASK309_EXPECTED_ANSWER_MANIFEST_SCHEMA_VERSION
    assert payload["corpus_id"] == TASK309_CORPUS_ID


def _object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _objects(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    result: list[dict[str, object]] = []
    for item in value:
        result.append(_object(item))
    return result


def _count_map(value: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for count in _objects(value):
        key = count.get("key")
        amount = count.get("count")
        assert isinstance(key, str)
        assert isinstance(amount, int)
        counts[key] = amount
    return counts


def _provider_run_metadata_payload(
    *,
    profile_name: AnswerKeyProviderProfileName,
    reports_root: Path,
    vision_media_path: Path | None,
) -> dict[str, object]:
    defaults = answer_key_defaults_for_provider_profile(profile_name.value)
    profile = build_answer_key_provider_profile(
        runtime=defaults.provider_runtime,
        model=defaults.model,
        context_window_tokens=defaults.context_window_tokens,
        max_output_tokens=defaults.max_output_tokens,
        temperature=defaults.temperature,
        supports_multimodal_vision=defaults.permits_vision_assets,
    )
    return build_answer_key_provider_run_metadata(
        profile_name=profile_name,
        defaults=defaults,
        provider_url=defaults.provider_url,
        provider_runtime=defaults.provider_runtime,
        profile=profile,
        reports_root=reports_root,
        vision_media_path=vision_media_path,
    ).to_payload()


def _pretend_current_process_is_hemma(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path.cwd().resolve()
    skill_repository = repo_root.parent / "skill-repository"
    monkeypatch.setenv("SIR_CONVERT_A_LOT_HEMMA_LOCAL_HOSTNAME", "fake-hemma-host")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_CURRENT_HOSTNAME", "fake-hemma-host")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_HEMMA_ROOT", repo_root.as_posix())
    monkeypatch.setenv("SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY", skill_repository.as_posix())
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY",
        skill_repository.as_posix(),
    )
