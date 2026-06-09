"""Host-side batch-plan analysis launcher for Qwen batch-plan experiments.

Purpose:
    Run the committed Qwen batch-plan analysis batch-plan occupancy analysis inside the
    governed Qwen training image so candidate batching profiles can be compared
    faithfully before bounded Hemma proofs are promoted.

Relationships:
    - Launches `ml.qwen.training.batch_plan_analysis` inside the governed
      training image.
    - Reuses the same Hemma image, scratch, and Hugging Face cache helpers as
      the detached Qwen training launcher.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HOME,
    docker_checked,
    prepare_qwen_image,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
)
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_IMAGE,
    DEFAULT_MODEL_ID,
    DEFAULT_PILOT_BUNDLE_ROOT,
    DEFAULT_SCRATCH_BUILD_HOME_MOUNT,
    DEFAULT_SCRATCH_BUILD_ROOT,
    default_hf_cache_dir,
    default_hf_cache_home_mount,
)

CONTAINER_BUILD_ROOT = Path("/app/build")
DEFAULT_OUTPUT_ROOT = DEFAULT_SCRATCH_BUILD_ROOT / "verification/qwen-batch-plan-analysis"
DEFAULT_PROFILE_LABELS = (
    "hemma-throughput-balanced-v1",
    "hemma-throughput-balanced-quarantine-v1",
    "hemma-throughput-balanced-quarantine-tail-v1",
)
DEFAULT_FIT_AUDIT_CODEC_FRAME_BAND_MIN = 320
DEFAULT_FIT_AUDIT_CODEC_FRAME_BAND_MAX = 375


def build_parser() -> argparse.ArgumentParser:
    """Build the committed parser for Qwen batch-plan analysis batch-plan analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze Qwen batch-plan batch plans inside the governed training image."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--pilot-bundle-root", type=Path, default=DEFAULT_PILOT_BUNDLE_ROOT)
    parser.add_argument("--train-manifest-family", default="swedish_pilot_train")
    parser.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--hf-cache-dir", type=Path, default=default_hf_cache_dir())
    parser.add_argument(
        "--hf-cache-home-mount",
        type=Path,
        default=default_hf_cache_home_mount(),
    )
    parser.add_argument("--scratch-build-root", type=Path, default=DEFAULT_SCRATCH_BUILD_ROOT)
    parser.add_argument(
        "--scratch-build-home-mount",
        type=Path,
        default=DEFAULT_SCRATCH_BUILD_HOME_MOUNT,
    )
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--fit-audit-codec-frame-band-min",
        type=int,
        default=DEFAULT_FIT_AUDIT_CODEC_FRAME_BAND_MIN,
    )
    parser.add_argument(
        "--fit-audit-codec-frame-band-max",
        type=int,
        default=DEFAULT_FIT_AUDIT_CODEC_FRAME_BAND_MAX,
    )
    parser.add_argument(
        "--profile-label",
        action="append",
        dest="profile_labels",
        default=None,
        help="Repeat for each profile. Defaults to the Qwen batch-plan matrix.",
    )
    parser.add_argument("--skip-build", action="store_true")
    return parser


def _launch_id() -> str:
    """Return a deterministic launch id for one batch-plan analysis run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _containerize_scratch_path(host_path: Path, *, scratch_root: Path) -> str:
    """Translate one host scratch path into the container build-root path."""
    relative_path = host_path.resolve().relative_to(scratch_root.resolve())
    return (CONTAINER_BUILD_ROOT / relative_path).as_posix()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write one deterministic JSON artifact for the host-side launcher."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Launch one governed Qwen batch-plan analysis batch-plan analysis run."""
    parser = build_parser()
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    launch_id = _launch_id()
    run_root = output_root / launch_id
    run_root.mkdir(parents=True, exist_ok=True)

    prepare_qwen_image(
        argparse.Namespace(
            dockerfile_path=Path(args.dockerfile_path),
            image=str(args.image),
            build_image=not bool(args.skip_build),
        )
    )
    hf_mount = resolve_effective_hf_cache_dir(
        argparse.Namespace(
            image=str(args.image),
            hf_cache_dir=Path(args.hf_cache_dir),
            hf_cache_home_mount=Path(args.hf_cache_home_mount),
        )
    )
    scratch_mount = resolve_effective_bind_root(
        Path(args.scratch_build_root),
        Path(args.scratch_build_home_mount),
        image=str(args.image),
        sync_home_into_canonical=False,
    )
    train_jsonl = (
        Path(args.pilot_bundle_root)
        / "manifests"
        / f"{str(args.train_manifest_family)}.prepared.jsonl"
    )
    if not train_jsonl.exists():
        raise SystemExit(f"Prepared training manifest does not exist: `{train_jsonl.as_posix()}`.")

    report_json = run_root / "report.json"
    report_md = run_root / "report.md"
    profile_labels = list(args.profile_labels or DEFAULT_PROFILE_LABELS)
    container_command = [
        "run",
        "--rm",
        "-e",
        "HF_HUB_DISABLE_XET=1",
        "-e",
        f"HF_HOME={CONTAINER_HF_HOME}",
        "-v",
        f"{Path.cwd().resolve().as_posix()}:/app",
        "-v",
        f"{scratch_mount.effective_root.as_posix()}:{CONTAINER_BUILD_ROOT.as_posix()}",
        "-v",
        f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}",
        "--workdir",
        "/app",
        "--entrypoint",
        "python",
        str(args.image),
        "-m",
        "scripts.sir_convert_a_lot.ml.qwen.training.batch_plan_analysis",
        "--model-id",
        str(args.model_id),
        "--train-jsonl",
        _containerize_scratch_path(train_jsonl, scratch_root=Path(args.scratch_build_root)),
        "--batch-size",
        str(int(args.batch_size)),
        "--fit-audit-codec-frame-band-min",
        str(int(args.fit_audit_codec_frame_band_min)),
        "--fit-audit-codec-frame-band-max",
        str(int(args.fit_audit_codec_frame_band_max)),
        "--output-json",
        _containerize_scratch_path(report_json, scratch_root=Path(args.scratch_build_root)),
        "--output-md",
        _containerize_scratch_path(report_md, scratch_root=Path(args.scratch_build_root)),
    ]
    for profile_label in profile_labels:
        container_command.extend(["--profile-label", profile_label])
    docker_checked(container_command, label="docker run qwen batch plan analysis")
    _write_json(
        run_root / "launch.json",
        {
            "launch_id": launch_id,
            "pilot_bundle_root": Path(args.pilot_bundle_root).as_posix(),
            "train_manifest_family": str(args.train_manifest_family),
            "train_jsonl": train_jsonl.as_posix(),
            "profile_labels": profile_labels,
            "batch_size": int(args.batch_size),
            "fit_audit_codec_frame_band_min": int(args.fit_audit_codec_frame_band_min),
            "fit_audit_codec_frame_band_max": int(args.fit_audit_codec_frame_band_max),
            "report_json": report_json.as_posix(),
            "report_md": report_md.as_posix(),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
