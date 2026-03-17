"""Artifact helpers for the Story 30 backward-lineage proof surface.

Purpose:
    Own deterministic proof configuration, artifact paths, and config loading
    for the T212 backward-lineage Hemma proof lane.

Relationships:
    - Used by `story30_backward_lineage_proof.py` for local proof packages.
    - Used by `story30_backward_lineage_runtime.py` for remote command building.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_PILOT_BUNDLE_ROOT,
)

DEFAULT_LOCAL_PROOF_ROOT = Path("build/verification/qwen-story30-backward-lineage")
DEFAULT_REMOTE_PROOF_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/qwen-story30-backward-lineage-proof"
)
DEFAULT_SOURCE_BUNDLE_ROOT = DEFAULT_PILOT_BUNDLE_ROOT
DEFAULT_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_TEXT_EMBEDDING_MASK_POLICY = "text_span_only"
DEFAULT_REQUIRED_SCRATCH_FREE_BYTES = 16 * 1024**3
DEFAULT_TASK_LABEL = "Task 212"
DEFAULT_COMMAND_NAME = "qwen-story30-backward-lineage"
DEFAULT_PROOF_ID_PREFIX = "task212"
DEFAULT_SOURCE_LINES = (13, 4)


@dataclass(frozen=True)
class Story30BackwardLineageProofConfig:
    """Deterministic configuration for one backward-lineage proof package."""

    task_label: str
    command_name: str
    prepared_at: str
    proof_id: str
    local_proof_root: str
    remote_proof_output_root: str
    source_bundle_root: str
    manifest_family: str
    source_lines: tuple[int, int]
    text_embedding_mask_policy: str
    required_scratch_free_bytes: int
    skip_build: bool
    launch_id: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_proof_id() -> str:
    """Return one deterministic backward-lineage proof identifier."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ").lower()
    return f"{DEFAULT_PROOF_ID_PREFIX}-{timestamp}"


def proof_root(base_output_root: Path, proof_id: str) -> Path:
    """Return the immutable local proof root for one prepared proof id."""
    return base_output_root / proof_id


def remote_proof_root(config: Story30BackwardLineageProofConfig) -> Path:
    """Return the immutable remote proof root for one proof id."""
    return Path(config.remote_proof_output_root) / config.proof_id


def config_path(local_proof_root: Path) -> Path:
    return local_proof_root / "proof-config.json"


def plan_path(local_proof_root: Path) -> Path:
    return local_proof_root / "plan.md"


def checklist_path(local_proof_root: Path) -> Path:
    return local_proof_root / "checklist.md"


def launch_path(local_proof_root: Path) -> Path:
    return local_proof_root / "launch.json"


def status_path(local_proof_root: Path) -> Path:
    return local_proof_root / "status.json"


def status_markdown_path(local_proof_root: Path) -> Path:
    return local_proof_root / "status.md"


def latest_pointer_path(base_output_root: Path) -> Path:
    return base_output_root / "latest-proof.json"


def write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def build_prepare_config(args: argparse.Namespace) -> Story30BackwardLineageProofConfig:
    """Build one normalized backward-lineage proof config from parsed args."""
    proof_id = default_proof_id() if args.proof_id is None else str(args.proof_id)
    local_root = proof_root(Path(args.output_root), proof_id)
    return Story30BackwardLineageProofConfig(
        task_label=DEFAULT_TASK_LABEL,
        command_name=DEFAULT_COMMAND_NAME,
        prepared_at=utc_now_iso(),
        proof_id=proof_id,
        local_proof_root=local_root.as_posix(),
        remote_proof_output_root=Path(args.remote_proof_output_root).as_posix(),
        source_bundle_root=Path(args.source_bundle_root).as_posix(),
        manifest_family=str(args.manifest_family),
        source_lines=_parse_source_lines(str(args.source_lines)),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        required_scratch_free_bytes=int(args.required_scratch_free_bytes),
        skip_build=bool(args.skip_build),
        launch_id=f"{proof_id}-backward-lineage",
    )


def _parse_source_lines(raw_value: str) -> tuple[int, int]:
    pieces = [piece.strip() for piece in raw_value.split(",") if piece.strip() != ""]
    if len(pieces) != 2:
        raise SystemExit("Backward-lineage proof requires exactly two source lines.")
    return int(pieces[0]), int(pieces[1])


def load_config(local_proof_root: Path) -> Story30BackwardLineageProofConfig:
    """Load one prepared backward-lineage proof config from disk."""
    payload = json.loads(config_path(local_proof_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Backward-lineage proof config was not a JSON object.")
    source_lines_value = payload.get("source_lines")
    if not isinstance(source_lines_value, list) or len(source_lines_value) != 2:
        raise SystemExit("Backward-lineage proof payload missing `source_lines`.")
    return Story30BackwardLineageProofConfig(
        task_label=_required_str(payload, "task_label"),
        command_name=_required_str(payload, "command_name"),
        prepared_at=_required_str(payload, "prepared_at"),
        proof_id=_required_str(payload, "proof_id"),
        local_proof_root=_required_str(payload, "local_proof_root"),
        remote_proof_output_root=_required_str(payload, "remote_proof_output_root"),
        source_bundle_root=_required_str(payload, "source_bundle_root"),
        manifest_family=_required_str(payload, "manifest_family"),
        source_lines=(int(source_lines_value[0]), int(source_lines_value[1])),
        text_embedding_mask_policy=_required_str(payload, "text_embedding_mask_policy"),
        required_scratch_free_bytes=_required_int(payload, "required_scratch_free_bytes"),
        skip_build=_required_bool(payload, "skip_build"),
        launch_id=_required_str(payload, "launch_id"),
    )


def resolve_proof_root(
    *, base_output_root: Path, proof_root_arg: Path | None, proof_id_arg: str | None
) -> Path:
    """Resolve one prepared proof root from explicit args or the latest pointer."""
    if proof_root_arg is not None:
        return proof_root_arg
    if proof_id_arg is not None:
        return proof_root(base_output_root, str(proof_id_arg))
    pointer = latest_pointer_path(base_output_root)
    if not pointer.exists():
        raise SystemExit(
            "Backward-lineage proof root was not provided and no latest pointer exists."
        )
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Backward-lineage latest-proof pointer was malformed.")
    return Path(_required_str(payload, "proof_root"))


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Backward-lineage proof payload missing string `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Backward-lineage proof payload missing integer `{key}`.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Backward-lineage proof payload missing boolean `{key}`.")
    return value
