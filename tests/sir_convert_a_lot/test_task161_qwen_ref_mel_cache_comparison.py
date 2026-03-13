"""Tests for the Task 161 Hemma ref-mel cache comparison runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task161_hemma_ref_mel_cache_comparison import (
    _build_parser,
    main,
)
from scripts.sir_convert_a_lot.devops.task161_qwen_ref_mel_cache_runtime import (
    completed_task101_predicate,
)


def test_task161_parser_defaults_are_bounded() -> None:
    """The Task 161 runner should expose bounded defaults."""
    parser = _build_parser()
    args = parser.parse_args([])

    assert args.max_steps == 240
    assert args.checkpoint_interval_steps == 100
    assert args.batch_size == 1
    assert args.num_epochs == 1
    assert args.poll_interval_seconds == 20
    assert args.poll_timeout_seconds == 5400
    assert args.ref_mel_cache_max_items == 2048
    assert args.resource_monitor_interval_seconds == 1.0
    assert args.resource_monitor_duration_seconds is None
    assert args.skip_build is False


def test_task161_runner_writes_comparison_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Task 161 runner should emit deterministic cache-off/cache-on artifacts."""
    comparison_id = "task161-proof-test"
    remote_output_root = Path(
        "/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot"
    )
    captured_variants: list[str] = []

    def _fake_default_comparison_id() -> str:
        return comparison_id

    def _fake_launch_variant(
        *,
        settings: object,
        comparison_id: str,
        variant_id: str,
        ref_mel_cache_enabled: bool,
    ) -> dict[str, object]:
        del settings, ref_mel_cache_enabled
        captured_variants.append(variant_id)
        return {
            "launch_id": f"{comparison_id}-{variant_id}",
            "run_root": (
                "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/"
                f"{comparison_id}-{variant_id}"
            ),
        }

    def _fake_poll_remote_task101_status(
        *,
        remote_task101_output_root: Path,
        launch_root: Path,
        poll_interval_seconds: int,
        poll_timeout_seconds: int,
        predicate: object,
    ) -> dict[str, object]:
        del poll_interval_seconds, poll_timeout_seconds, predicate
        assert remote_task101_output_root == remote_output_root
        if launch_root.name.endswith("cache-off"):
            return {
                "status": "exited",
                "exit_code": 0,
                "pilot_report_found": True,
                "pilot_report": {
                    "training_summary": {
                        "optimizer_steps_completed": 120,
                        "train_iterations_completed": 120,
                        "ref_mel_cache": {
                            "enabled": False,
                            "cache_hits": 0,
                            "cache_misses": 0,
                            "cache_hit_rate": None,
                        },
                    }
                },
                "resource_monitor": {
                    "summary_train": {"gpu_busy_percent_median": 82.0},
                    "steady_state_train_gpu_busy_median_percent": 80.0,
                    "steady_state_train_sample_count": 600,
                    "steady_state_gpu_busy_gate_met": False,
                },
            }
        return {
            "status": "exited",
            "exit_code": 0,
            "pilot_report_found": True,
            "pilot_report": {
                "training_summary": {
                    "optimizer_steps_completed": 120,
                    "train_iterations_completed": 120,
                    "ref_mel_cache": {
                        "enabled": True,
                        "cache_hits": 450,
                        "cache_misses": 150,
                        "cache_hit_rate": 0.75,
                    },
                }
            },
            "resource_monitor": {
                "summary_train": {"gpu_busy_percent_median": 88.0},
                "steady_state_train_gpu_busy_median_percent": 86.0,
                "steady_state_train_sample_count": 600,
                "steady_state_gpu_busy_gate_met": False,
            },
        }

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task161_hemma_ref_mel_cache_comparison.default_comparison_id",
        _fake_default_comparison_id,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task161_hemma_ref_mel_cache_comparison._launch_variant",
        _fake_launch_variant,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task161_hemma_ref_mel_cache_comparison.poll_remote_task101_status",
        _fake_poll_remote_task101_status,
    )

    result = main(
        [
            "--output-root",
            tmp_path.as_posix(),
            "--remote-task101-output-root",
            remote_output_root.as_posix(),
        ]
    )

    assert result == 0
    assert captured_variants == ["cache-off", "cache-on"]
    comparison_root = tmp_path / comparison_id
    report_payload = json.loads((comparison_root / "report.json").read_text(encoding="utf-8"))
    assert report_payload["cache_off"]["variant_id"] == "cache-off"
    assert report_payload["cache_on"]["variant_id"] == "cache-on"
    assert report_payload["cache_on"]["ref_mel_cache_hit_rate"] == 0.75
    assert report_payload["delta_train_gpu_busy_percent_median"] == 6.0
    assert report_payload["delta_steady_state_gpu_busy_percent_median"] == 6.0
    assert (comparison_root / "report.md").exists() is True


def test_task161_completion_predicate_handles_success_and_failure() -> None:
    """Completion predicate should accept success and reject non-zero exits."""
    assert (
        completed_task101_predicate(
            {
                "pilot_report_found": True,
                "exit_code": 0,
                "status": "exited",
            }
        )
        is True
    )
    with pytest.raises(SystemExit):
        completed_task101_predicate(
            {
                "pilot_report_found": False,
                "exit_code": 1,
                "status": "exited",
            }
        )
