"""Offline token-span audit for Story 29 Qwen RCA.

Purpose:
    Inspect one saved Story 29 failure artifact, reconstruct the current
    trainable text-embedding span versus the intended semantic text span, and
    persist deterministic JSON/Markdown artifacts that prove whether the
    current runtime still leaks non-semantic positions into the trainable
    text-embedding surface.

Relationships:
    - Reuses `text_embedding_mask_policy.py` for the current resolved
      text-embedding span contract.
    - Consumes saved bounded-proof status artifacts produced by the detached
      Story 29 proof surfaces.
    - Exposed through the public `qwen-token-span-audit` CLI entrypoint.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso, write_json
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY,
    TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
    resolve_active_text_embedding_span,
)

DEFAULT_STATUS_JSON_PATH = Path(
    "build/verification/qwen-t198-proof/"
    "task198-20260317t062816z-fallback1470-a1/fallback1470-status.json"
)
DEFAULT_OUTPUT_ROOT = Path("build/verification/qwen-token-span-audit/task206-canonical-line101")
DEFAULT_MANIFEST_LINE_NUMBER = 101
DEFAULT_TRAIN_ITERATION = 851
SEMANTIC_TEXT_START_INDEX = 8
PREFIX_SPECIAL_COUNT = 3
PREFIX_PAD_START_INDEX = 3
PREFIX_PAD_END_INDEX_EXCLUSIVE = 7
BOS_INDEX = 7


@dataclass(frozen=True)
class TokenSpanAuditSettings:
    """Normalized settings for one offline token-span audit run."""

    status_json_path: Path
    output_root: Path
    manifest_line_number: int
    train_iteration: int


@dataclass(frozen=True)
class TokenSpanSample:
    """One tokenized sample extracted from a saved optimizer-boundary artifact."""

    row_id: str
    manifest_path: str
    manifest_line_number: int
    train_iteration: int
    text_preview: str
    full_text: str | None
    token_ids: tuple[int, ...]
    unique_token_ids: tuple[int, ...]
    non_finite_token_positions: tuple[int, ...]
    non_finite_token_ids: tuple[int, ...]


@dataclass(frozen=True)
class TokenSpanWindow:
    """One positional token span over the collated text channel."""

    start_index: int
    end_index_exclusive: int
    positions: tuple[int, ...]
    token_ids: tuple[int, ...]
    unique_token_ids: tuple[int, ...]


@dataclass(frozen=True)
class TokenSpanLayout:
    """Reconstructed collated-row boundary facts for one sample."""

    token_count: int
    inferred_text_ids_len: int
    inferred_codec_ids_len: int
    prefix_special_positions: tuple[int, ...]
    prefix_pad_positions: tuple[int, ...]
    bos_position: int
    eos_position: int
    first_trailing_pad_position: int
    tts_pad_token_id: int
    tts_bos_token_id: int
    tts_eos_token_id: int


@dataclass(frozen=True)
class TokenSpanLeakage:
    """Current non-semantic positions still included in the trainable span."""

    leaked_positions: tuple[int, ...]
    leaked_token_ids: tuple[int, ...]
    leaked_unique_token_ids: tuple[int, ...]
    leaked_non_finite_positions: tuple[int, ...]
    leaked_non_finite_count: int
    current_trainable_non_finite_count: int
    intended_semantic_non_finite_count: int


@dataclass(frozen=True)
class TokenSpanAuditResult:
    """Deterministic audit payload for one canonical and one synthetic sample."""

    generated_at: str
    source_status_json_path: str
    sample: TokenSpanSample
    layout: TokenSpanLayout
    current_text_span_only: TokenSpanWindow
    current_legacy_codec_span: TokenSpanWindow
    intended_semantic_text_span: TokenSpanWindow
    leakage: TokenSpanLeakage
    requires_explicit_position_mask: bool
    recommended_correction_family: str
    synthetic_regression_case: dict[str, object]


def parse_args(argv: list[str] | None) -> TokenSpanAuditSettings:
    """Parse CLI arguments into normalized audit settings."""
    parser = argparse.ArgumentParser(description="Run the offline Story 29 token-span audit.")
    parser.add_argument("--status-json", type=Path, default=DEFAULT_STATUS_JSON_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest-line-number", type=int, default=DEFAULT_MANIFEST_LINE_NUMBER)
    parser.add_argument("--train-iteration", type=int, default=DEFAULT_TRAIN_ITERATION)
    args = parser.parse_args(argv)
    return TokenSpanAuditSettings(
        status_json_path=Path(args.status_json),
        output_root=Path(args.output_root),
        manifest_line_number=int(args.manifest_line_number),
        train_iteration=int(args.train_iteration),
    )


def prepare_output_paths(output_root: Path) -> tuple[Path, Path]:
    """Return deterministic artifact paths for one audit run."""
    output_root.mkdir(parents=True, exist_ok=True)
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    enforce_generated_output_path(report_json_path, label="token_span_audit_report_json")
    enforce_generated_output_path(report_md_path, label="token_span_audit_report_md")
    return report_json_path, report_md_path


def load_sample_from_status(
    *,
    status_json_path: Path,
    manifest_line_number: int,
    train_iteration: int,
) -> TokenSpanSample:
    """Extract the canonical failing sample from one saved detached-status artifact."""
    if not status_json_path.is_file():
        raise SystemExit(f"Status JSON does not exist: {status_json_path}")
    payload = json.loads(status_json_path.read_text(encoding="utf-8"))
    microbatches = (
        payload.get("pilot_status", {})
        .get("optimizer_boundary_guard", {})
        .get("step_forensics", {})
        .get("microbatches", [])
    )
    if not isinstance(microbatches, list):
        raise SystemExit("Status JSON did not contain one microbatch forensic list.")
    for microbatch in microbatches:
        if not isinstance(microbatch, dict):
            continue
        if int(microbatch.get("train_iteration", -1)) != train_iteration:
            continue
        gradient_forensics = microbatch.get("gradient_forensics")
        if not isinstance(gradient_forensics, dict):
            continue
        sample_payloads = gradient_forensics.get("input_text_embedding_gradient", {}).get("samples")
        if not isinstance(sample_payloads, list):
            continue
        for sample_payload in sample_payloads:
            if not isinstance(sample_payload, dict):
                continue
            if int(sample_payload.get("manifest_line_number", -1)) != manifest_line_number:
                continue
            return _build_sample(sample_payload=sample_payload, train_iteration=train_iteration)
    raise SystemExit(
        "Could not find the canonical failing sample in the provided status artifact. "
        "Expected "
        f"train_iteration={train_iteration} and "
        f"manifest_line_number={manifest_line_number}."
    )


def _build_sample(*, sample_payload: dict[str, object], train_iteration: int) -> TokenSpanSample:
    """Convert one JSON payload into the typed audit sample contract."""
    token_ids = _required_int_tuple(sample_payload, "token_ids")
    unique_token_ids = _required_int_tuple(sample_payload, "unique_token_ids")
    non_finite_token_positions = _required_int_tuple(sample_payload, "non_finite_token_positions")
    non_finite_token_ids = _required_int_tuple(sample_payload, "non_finite_token_ids")
    return TokenSpanSample(
        row_id=_required_str(sample_payload, "row_id"),
        manifest_path=_required_str(sample_payload, "manifest_path"),
        manifest_line_number=_required_int(sample_payload, "manifest_line_number"),
        train_iteration=train_iteration,
        text_preview=_required_str(sample_payload, "text_preview"),
        full_text=_optional_str(sample_payload, "full_text"),
        token_ids=token_ids,
        unique_token_ids=unique_token_ids,
        non_finite_token_positions=non_finite_token_positions,
        non_finite_token_ids=non_finite_token_ids,
    )


def build_token_span_audit_result(
    *,
    source_status_json_path: Path,
    sample: TokenSpanSample,
) -> TokenSpanAuditResult:
    """Build the full deterministic audit result for one canonical sample."""
    layout = infer_layout(sample)
    current_text_span_only = build_current_text_span_only_window(sample=sample, layout=layout)
    current_legacy_codec_span = build_legacy_codec_span_window(sample=sample, layout=layout)
    intended_semantic_text_span = build_intended_semantic_text_span(sample=sample, layout=layout)
    leakage = build_leakage(
        sample=sample,
        current_text_span_only=current_text_span_only,
        intended_semantic_text_span=intended_semantic_text_span,
    )
    synthetic_regression_case = build_synthetic_regression_case()
    return TokenSpanAuditResult(
        generated_at=utc_now_iso(),
        source_status_json_path=source_status_json_path.as_posix(),
        sample=sample,
        layout=layout,
        current_text_span_only=current_text_span_only,
        current_legacy_codec_span=current_legacy_codec_span,
        intended_semantic_text_span=intended_semantic_text_span,
        leakage=leakage,
        requires_explicit_position_mask=intended_semantic_text_span.start_index != 0,
        recommended_correction_family=(
            "Explicit position mask builder in dataset collation so only positions "
            "8..(eos-1) stay trainable."
        ),
        synthetic_regression_case=synthetic_regression_case,
    )


def infer_layout(sample: TokenSpanSample) -> TokenSpanLayout:
    """Infer the current collated-row layout from one failing sample token sequence."""
    token_ids = sample.token_ids
    if len(token_ids) <= SEMANTIC_TEXT_START_INDEX:
        raise SystemExit("Sample token sequence was too short to infer the Qwen collated layout.")
    pad_token_id = token_ids[PREFIX_PAD_START_INDEX]
    if token_ids[PREFIX_PAD_START_INDEX:PREFIX_PAD_END_INDEX_EXCLUSIVE] != (pad_token_id,) * 4:
        raise SystemExit("Canonical sample did not match the expected four-slot prefix pad block.")
    first_trailing_pad_position = _find_first_trailing_pad_position(
        token_ids=token_ids,
        pad_id=pad_token_id,
    )
    eos_position = first_trailing_pad_position - 1
    if eos_position <= BOS_INDEX:
        raise SystemExit("Could not infer one valid EOS boundary for the canonical sample.")
    tts_eos_token_id = token_ids[eos_position]
    inferred_text_ids_len = eos_position - 5
    inferred_codec_ids_len = len(token_ids) - 8 - inferred_text_ids_len
    if inferred_text_ids_len <= 0:
        raise SystemExit("Inferred `text_ids_len` was not positive.")
    if inferred_codec_ids_len < 0:
        raise SystemExit("Inferred `codec_ids_len` was negative.")
    return TokenSpanLayout(
        token_count=len(token_ids),
        inferred_text_ids_len=inferred_text_ids_len,
        inferred_codec_ids_len=inferred_codec_ids_len,
        prefix_special_positions=(0, 1, 2),
        prefix_pad_positions=(3, 4, 5, 6),
        bos_position=BOS_INDEX,
        eos_position=eos_position,
        first_trailing_pad_position=first_trailing_pad_position,
        tts_pad_token_id=pad_token_id,
        tts_bos_token_id=token_ids[BOS_INDEX],
        tts_eos_token_id=tts_eos_token_id,
    )


def _find_first_trailing_pad_position(*, token_ids: tuple[int, ...], pad_id: int) -> int:
    """Return the first position in the trailing all-pad suffix."""
    for position in range(SEMANTIC_TEXT_START_INDEX, len(token_ids)):
        if all(token_id == pad_id for token_id in token_ids[position:]):
            return position
    raise SystemExit("Could not infer the first trailing pad suffix for the canonical sample.")


def build_current_text_span_only_window(
    *,
    sample: TokenSpanSample,
    layout: TokenSpanLayout,
) -> TokenSpanWindow:
    """Build the currently trainable `text_span_only` window for one sample."""
    current_span = resolve_active_text_embedding_span(
        policy=TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
        text_ids_len=layout.inferred_text_ids_len,
        codec_ids_len=layout.inferred_codec_ids_len,
    )
    return build_window(
        token_ids=sample.token_ids,
        start_index=current_span.start_index,
        end_index_exclusive=current_span.end_index_exclusive,
    )


def build_legacy_codec_span_window(
    *,
    sample: TokenSpanSample,
    layout: TokenSpanLayout,
) -> TokenSpanWindow:
    """Build the legacy prefix window that reaches through the codec tail."""
    legacy_span = resolve_active_text_embedding_span(
        policy=LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY,
        text_ids_len=layout.inferred_text_ids_len,
        codec_ids_len=layout.inferred_codec_ids_len,
    )
    return build_window(
        token_ids=sample.token_ids,
        start_index=legacy_span.start_index,
        end_index_exclusive=legacy_span.end_index_exclusive,
    )


def build_intended_semantic_text_span(
    *,
    sample: TokenSpanSample,
    layout: TokenSpanLayout,
) -> TokenSpanWindow:
    """Build the intended semantic text-only span for one collated sample."""
    return build_window(
        token_ids=sample.token_ids,
        start_index=SEMANTIC_TEXT_START_INDEX,
        end_index_exclusive=layout.eos_position,
    )


def build_window(
    *,
    token_ids: tuple[int, ...],
    start_index: int,
    end_index_exclusive: int,
) -> TokenSpanWindow:
    """Build one immutable token window from positional bounds."""
    positions = tuple(range(start_index, end_index_exclusive))
    window_token_ids = tuple(token_ids[position] for position in positions)
    return TokenSpanWindow(
        start_index=start_index,
        end_index_exclusive=end_index_exclusive,
        positions=positions,
        token_ids=window_token_ids,
        unique_token_ids=tuple(sorted(set(window_token_ids))),
    )


def build_leakage(
    *,
    sample: TokenSpanSample,
    current_text_span_only: TokenSpanWindow,
    intended_semantic_text_span: TokenSpanWindow,
) -> TokenSpanLeakage:
    """Compute the non-semantic positions still included by the current span."""
    intended_position_set = set(intended_semantic_text_span.positions)
    current_position_set = set(current_text_span_only.positions)
    leaked_positions = tuple(
        position
        for position in current_text_span_only.positions
        if position not in intended_position_set
    )
    leaked_token_ids = tuple(sample.token_ids[position] for position in leaked_positions)
    non_finite_position_set = set(sample.non_finite_token_positions)
    leaked_non_finite_positions = tuple(
        position for position in leaked_positions if position in non_finite_position_set
    )
    current_trainable_non_finite_count = sum(
        1 for position in current_position_set if position in non_finite_position_set
    )
    intended_semantic_non_finite_count = sum(
        1 for position in intended_position_set if position in non_finite_position_set
    )
    return TokenSpanLeakage(
        leaked_positions=leaked_positions,
        leaked_token_ids=leaked_token_ids,
        leaked_unique_token_ids=tuple(sorted(set(leaked_token_ids))),
        leaked_non_finite_positions=leaked_non_finite_positions,
        leaked_non_finite_count=len(leaked_non_finite_positions),
        current_trainable_non_finite_count=current_trainable_non_finite_count,
        intended_semantic_non_finite_count=intended_semantic_non_finite_count,
    )


def build_synthetic_regression_case() -> dict[str, object]:
    """Build one small synthetic case that proves the current helper is prefix-only."""
    synthetic_token_ids = (
        1001,
        1002,
        1003,
        9000,
        9000,
        9000,
        9000,
        9001,
        2001,
        2002,
        2003,
        9002,
        9000,
        9000,
        9000,
    )
    sample = TokenSpanSample(
        row_id="synthetic#line1",
        manifest_path="synthetic.jsonl",
        manifest_line_number=1,
        train_iteration=1,
        text_preview="synthetic",
        full_text="synthetic semantic text",
        token_ids=synthetic_token_ids,
        unique_token_ids=tuple(sorted(set(synthetic_token_ids))),
        non_finite_token_positions=tuple(range(0, 14)),
        non_finite_token_ids=synthetic_token_ids[:14],
    )
    layout = infer_layout(sample)
    current_text_span_only = build_current_text_span_only_window(sample=sample, layout=layout)
    intended_semantic_text_span = build_intended_semantic_text_span(sample=sample, layout=layout)
    leakage = build_leakage(
        sample=sample,
        current_text_span_only=current_text_span_only,
        intended_semantic_text_span=intended_semantic_text_span,
    )
    return {
        "token_count": len(sample.token_ids),
        "current_text_span_only_length": len(current_text_span_only.positions),
        "intended_semantic_length": len(intended_semantic_text_span.positions),
        "leaked_positions": list(leakage.leaked_positions),
        "leaked_unique_token_ids": list(leakage.leaked_unique_token_ids),
        "requires_explicit_position_mask": intended_semantic_text_span.start_index != 0,
    }


def build_report_markdown(report: TokenSpanAuditResult) -> str:
    """Render one concise operator-facing markdown report."""
    lines = [
        "# Story 29 Token-Span Audit",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Source status JSON: `{report.source_status_json_path}`",
        f"- Row id: `{report.sample.row_id}`",
        f"- Manifest line: `{report.sample.manifest_line_number}`",
        f"- Train iteration: `{report.sample.train_iteration}`",
        f"- Token count: `{report.layout.token_count}`",
        f"- Inferred text_ids_len: `{report.layout.inferred_text_ids_len}`",
        f"- Inferred codec_ids_len: `{report.layout.inferred_codec_ids_len}`",
        "",
        "## Current vs Intended Span",
        "",
        (
            "- `legacy_codec_span` trainable positions: "
            f"`0..{report.current_legacy_codec_span.end_index_exclusive - 1}`"
        ),
        (
            "- `text_span_only` trainable positions: "
            f"`{report.current_text_span_only.start_index}"
            f"..{report.current_text_span_only.end_index_exclusive - 1}`"
        ),
        (
            "- intended semantic positions: "
            f"`{report.intended_semantic_text_span.start_index}"
            f"..{report.intended_semantic_text_span.end_index_exclusive - 1}`"
        ),
        (
            "- current `text_span_only` unique token ids: "
            f"`{len(report.current_text_span_only.unique_token_ids)}`"
        ),
        (
            "- intended semantic unique token ids: "
            f"`{len(report.intended_semantic_text_span.unique_token_ids)}`"
        ),
        "",
        "## Leakage",
        "",
        (
            "- leaked non-semantic positions still trainable today: "
            f"`{len(report.leakage.leaked_positions)}`"
        ),
        f"- leaked positions: `{list(report.leakage.leaked_positions)}`",
        f"- leaked token ids: `{list(report.leakage.leaked_token_ids)}`",
        f"- leaked unique token ids: `{list(report.leakage.leaked_unique_token_ids)}`",
        (
            "- leaked positions with non-finite input gradients in the canonical "
            f"failure: `{report.leakage.leaked_non_finite_count}`"
        ),
        (
            "- current trainable non-finite positions in the canonical failure: "
            f"`{report.leakage.current_trainable_non_finite_count}`"
        ),
        (
            "- intended semantic non-finite positions in the canonical failure: "
            f"`{report.leakage.intended_semantic_non_finite_count}`"
        ),
        "",
        "## Interpretation",
        "",
        (
            "- The current `text_span_only` helper now resolves to the same "
            "semantic text positions used by the explicit audit contract."
        ),
        "- The intended semantic text span starts at position `8`, not at position `0`.",
        (
            "- Leakage should therefore stay at zero unless a future change "
            "reintroduces prefix or EOS positions into the trainable mask."
        ),
        f"- Requires explicit position mask: `{report.requires_explicit_position_mask}`",
        f"- Recommended correction family: {report.recommended_correction_family}",
        "",
        "## Synthetic Regression Case",
        "",
        (
            "- current_text_span_only_length: "
            f"`{report.synthetic_regression_case['current_text_span_only_length']}`"
        ),
        (
            "- intended_semantic_length: "
            f"`{report.synthetic_regression_case['intended_semantic_length']}`"
        ),
        f"- leaked_positions: `{report.synthetic_regression_case['leaked_positions']}`",
        (
            "- leaked_unique_token_ids: "
            f"`{report.synthetic_regression_case['leaked_unique_token_ids']}`"
        ),
    ]
    return "\n".join(lines)


def write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string from a generic JSON object."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Expected `{key}` to be one string.")
    return value


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    """Return one optional string from a generic JSON object."""
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer from a generic JSON object."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Expected `{key}` to be one integer.")
    return value


def _required_int_tuple(payload: dict[str, object], key: str) -> tuple[int, ...]:
    """Return one required integer sequence from a generic JSON object."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, int) for item in value):
        raise SystemExit(f"Expected `{key}` to be one integer list.")
    return tuple(int(item) for item in value)


def main(argv: list[str] | None = None) -> int:
    """Run the offline Story 29 token-span audit and persist deterministic artifacts."""
    settings = parse_args(argv)
    report_json_path, report_md_path = prepare_output_paths(settings.output_root)
    sample = load_sample_from_status(
        status_json_path=settings.status_json_path,
        manifest_line_number=settings.manifest_line_number,
        train_iteration=settings.train_iteration,
    )
    report = build_token_span_audit_result(
        source_status_json_path=settings.status_json_path,
        sample=sample,
    )
    write_json(report_json_path, asdict(report))
    write_markdown(report_md_path, build_report_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
