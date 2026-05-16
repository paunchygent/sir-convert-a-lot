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

from scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation import (
    main as task309_runner_main,
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


def test_task309_llama_provider_launch_surface_dry_runs_hemma_local_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pretend_current_process_is_hemma(monkeypatch)
    exit_code = task309_runner_main(
        [
            "launch-llama-provider",
            "--provider-profile",
            "qwen36-llama-cpp",
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
    assert plan["provider_profile"] == "qwen36-llama-cpp"
    assert plan["provider_url"] == "http://127.0.0.1:8082"
    assert plan["model"] == "qwen3.6-27b-q6k"
    assert plan["host"] == "127.0.0.1"
    assert plan["port"] == 8082
    assert plan["hf_repo"] == "unsloth/Qwen3.6-27B-GGUF"
    assert plan["hf_file"] == "Qwen3.6-27B-Q6_K.gguf"
    assert "--n-gpu-layers" in command
    assert "all" in command
    assert "--offline" in command
    assert "--media-path" in command
    assert "--reasoning" in command
    assert "off" in command
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
