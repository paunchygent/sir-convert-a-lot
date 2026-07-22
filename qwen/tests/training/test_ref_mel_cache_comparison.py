"""Tests for the canonical Qwen ref-mel cache comparison runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.training.ref_mel_cache_comparison import (
    ComparisonSettings,
    build_parser,
    completed_training_predicate,
    launch_variant,
    main,
)


def test_ref_mel_parser_defaults_are_bounded() -> None:
    """The comparison runner should expose bounded defaults."""
    parser = build_parser()
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
    assert args.training_bundle_root is None
    assert args.skip_build is False


def test_launch_variant_passes_training_bundle_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Variant launch should forward explicit training-bundle roots."""
    captured_args: list[str] = []

    def fake_run_remote_training_json(args: list[str], *, label: str) -> dict[str, object]:
        del label
        captured_args.extend(args)
        return {"launch_id": "qwen-ref-mel-test-cache-on", "run_root": "/srv/scratch/run-root"}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.ref_mel_cache_comparison.run_remote_training_json",
        fake_run_remote_training_json,
    )
    settings = ComparisonSettings(
        local_output_root=tmp_path,
        remote_training_output_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training"
        ),
        training_bundle_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-training-bundle-20260312h"
        ),
        max_steps=240,
        checkpoint_interval_steps=100,
        batch_size=1,
        num_epochs=1,
        poll_interval_seconds=20,
        poll_timeout_seconds=5400,
        ref_mel_cache_max_items=2048,
        resource_monitor_interval_seconds=1.0,
        resource_monitor_duration_seconds=None,
        skip_build=False,
    )

    launch_payload = launch_variant(
        settings=settings,
        comparison_id="qwen-ref-mel-test",
        variant_id="cache-on",
        ref_mel_cache_enabled=True,
    )

    assert launch_payload["launch_id"] == "qwen-ref-mel-test-cache-on"
    assert "--pilot-bundle-root" in captured_args
    assert "--ref-mel-cache-enabled" in captured_args
    assert "true" not in captured_args
    assert "false" not in captured_args
    assert (
        "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-training-bundle-20260312h"
        in captured_args
    )


def test_ref_mel_runner_writes_comparison_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The comparison runner should emit deterministic cache-off/cache-on artifacts."""
    comparison_id = "qwen-ref-mel-test"
    remote_output_root = Path(
        "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training"
    )
    captured_variants: list[str] = []

    def fake_default_comparison_id() -> str:
        return comparison_id

    def fake_launch_variant(
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

    def fake_poll_remote_training_status(
        *,
        remote_training_output_root: Path,
        launch_root: Path,
        poll_interval_seconds: int,
        poll_timeout_seconds: int,
        predicate: object,
    ) -> dict[str, object]:
        del poll_interval_seconds, poll_timeout_seconds, predicate
        assert remote_training_output_root == remote_output_root
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
        "scripts.sir_convert_a_lot.ml.qwen.training.ref_mel_cache_comparison.default_comparison_id",
        fake_default_comparison_id,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.ref_mel_cache_comparison.launch_variant",
        fake_launch_variant,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.ref_mel_cache_comparison.poll_remote_training_status",
        fake_poll_remote_training_status,
    )

    result = main(
        [
            "--output-root",
            tmp_path.as_posix(),
            "--remote-training-output-root",
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


def test_completed_training_predicate_handles_success_and_failure() -> None:
    """Completion predicate should accept success and reject non-zero exits."""
    assert (
        completed_training_predicate(
            {
                "pilot_report_found": True,
                "exit_code": 0,
                "status": "exited",
            }
        )
        is True
    )
    with pytest.raises(SystemExit):
        completed_training_predicate(
            {
                "pilot_report_found": False,
                "exit_code": 1,
                "status": "exited",
            }
        )
