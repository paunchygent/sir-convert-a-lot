"""Task 309 provider-free request-shape preview artifacts.

Purpose:
    Build local evidence for the exact model-facing request shape before any
    live Granite/vLLM validation run is launched.

Relationships:
    - Reuses the Task 312 answer-key candidate planner and provider payload
      builder so previewed requests match the live advisory path.
    - Complements Task 309 live execution by catching bad prompt projection,
      missing item-type instructions, and provider-mode mismatches without
      calling Hemma.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task309_granite_provider_contracts import (
    DEFAULT_PROVIDER_MODEL,
    DEFAULT_PROVIDER_URL,
)
from scripts.sir_convert_a_lot.devops.task309_structured_provider_profiles import (
    DEFAULT_TASK309_PROVIDER_RUNTIME,
    Task309StructuredProviderRuntime,
    build_task309_provider_profile,
)
from scripts.sir_convert_a_lot.devops.task309_vision_assets import (
    Task309VisionCandidatePlanner,
    export_task309_vision_assets,
    vision_item_assets_by_id,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    answer_key_candidate_planner_for_profile,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_manifest import (
    Task309AssetEvalPolicy,
    build_task309_live_validation_manifest,
    write_task309_json,
)
from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamItemType
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIrItem,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import StructuredLLMOutputMode
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_structured_llm_payload,
)

TASK309_REQUEST_SHAPE_PREVIEW_SCHEMA_VERSION = "task309_request_shape_preview_v1"


@dataclass(frozen=True)
class Task309RequestShapeItem:
    """One provider-free request-shape preview row."""

    source_filename: str
    item_id: str
    sequence: int
    item_type: str
    ok: bool
    issues: tuple[str, ...]
    system_prompt: str | None
    user_message_json: str | None
    provider_payload_json: str | None
    output_mode: str | None
    output_contract_json: str | None
    raw_item_context_json: str
    asset_eligible: bool
    preview_artifact_path: str | None
    multimodal_request: bool

    def to_payload(self) -> dict[str, object]:
        """Return JSON-safe preview item payload."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class Task309RequestShapePreview:
    """Provider-free preview for all Task 309 model-facing requests."""

    schema_version: str
    corpus_root: str
    provider_url: str
    model: str
    provider_runtime: str
    item_count: int
    manifest_eligible_item_count: int
    attempted_item_count: int
    ok: bool
    issue_count: int
    issue_counts: tuple[dict[str, object], ...]
    items: tuple[Task309RequestShapeItem, ...]

    def to_payload(self) -> dict[str, object]:
        """Return JSON-safe preview payload."""

        return _json_object(asdict(self))


def build_task309_request_shape_preview(
    *,
    corpus_root: Path,
    provider_url: str = DEFAULT_PROVIDER_URL,
    model: str = DEFAULT_PROVIDER_MODEL,
    provider_runtime: Task309StructuredProviderRuntime = DEFAULT_TASK309_PROVIDER_RUNTIME,
    vision_media_path: Path = Path(
        "build/verification/task-309-request-shape-preview/vision-assets"
    ),
) -> Task309RequestShapePreview:
    """Build a provider-free preview of the exact live request shape."""

    profile = build_task309_provider_profile(runtime=provider_runtime, model=model)
    base_planner = answer_key_candidate_planner_for_profile(profile)
    vision_policy = Task309AssetEvalPolicy(
        allow_supported_embedded_assets=profile.capabilities.supports_multimodal_vision
    )
    manifest = build_task309_live_validation_manifest(
        corpus_root,
        asset_eval_policy=vision_policy,
    )
    eligible_keys = {
        (file_entry.filename, item.item_id)
        for file_entry in manifest.files
        for item in file_entry.items
        if item.eligible
    }
    parser = DigiExamDxeParser()
    rows: list[Task309RequestShapeItem] = []
    item_count = 0
    for source_path in sorted(corpus_root.glob("*.dxe")):
        exam = build_digiexam_intermediate_exam(parser.parse_file(source_path))
        vision_export = (
            export_task309_vision_assets(
                exam=exam,
                source_filename=source_path.name,
                media_path=vision_media_path,
            )
            if profile.capabilities.supports_multimodal_vision
            else None
        )
        planner = Task309VisionCandidatePlanner(
            base_planner=base_planner,
            item_assets_by_id=vision_item_assets_by_id(vision_export) if vision_export else {},
        )
        item_count += len(exam.items)
        for item in exam.items:
            plan = planner.plan_candidate(
                job_id=f"task309-preview:{source_path.stem}",
                item=item,
                profile=profile,
            )
            if plan is None:
                if (source_path.name, item.item_id) in eligible_keys:
                    rows.append(
                        Task309RequestShapeItem(
                            source_filename=source_path.name,
                            item_id=item.item_id,
                            sequence=item.sequence,
                            item_type=item.item_type.value,
                            ok=False,
                            issues=("manifest_eligible_item_missing_candidate_plan",),
                            system_prompt=None,
                            user_message_json=None,
                            provider_payload_json=None,
                            output_mode=None,
                            output_contract_json=None,
                            raw_item_context_json=_raw_item_context_json(item),
                            asset_eligible=bool(item.embedded_assets),
                            preview_artifact_path=None,
                            multimodal_request=False,
                        )
                    )
                continue
            user_payload = _load_user_payload(plan.request.user_payload)
            provider_payload = build_structured_llm_payload(
                profile=plan.provider_profile or profile,
                request=plan.request,
            )
            vision_assets = (
                vision_item_assets_by_id(vision_export).get(item.item_id)
                if vision_export is not None
                else None
            )
            preview_path = (
                vision_assets.preview.relative_path
                if vision_assets is not None and vision_assets.preview is not None
                else None
            )
            issues = _shape_issues(
                item=item,
                user_payload=user_payload,
                provider_payload=provider_payload,
                output_mode=(
                    plan.provider_profile.output_mode.value
                    if plan.provider_profile is not None
                    else None
                ),
                system_prompt=plan.request.system_prompt,
            )
            output_contract = {
                "schema_name": plan.request.output_spec.schema_name,
                "schema_version": plan.request.output_spec.schema_version,
                "json_schema": plan.request.output_spec.json_schema,
                "gbnf_grammar": plan.request.output_spec.gbnf_grammar,
                "choice_values": plan.request.output_spec.choice_values,
            }
            rows.append(
                Task309RequestShapeItem(
                    source_filename=source_path.name,
                    item_id=item.item_id,
                    sequence=item.sequence,
                    item_type=item.item_type.value,
                    ok=not issues,
                    issues=issues,
                    system_prompt=plan.request.system_prompt,
                    user_message_json=_canonical_json(user_payload),
                    provider_payload_json=_canonical_json(provider_payload),
                    output_mode=(
                        plan.provider_profile.output_mode.value
                        if plan.provider_profile is not None
                        else None
                    ),
                    output_contract_json=_canonical_json(output_contract),
                    raw_item_context_json=_raw_item_context_json(item),
                    asset_eligible=bool(item.embedded_assets),
                    preview_artifact_path=preview_path,
                    multimodal_request=bool(plan.request.user_content_parts),
                )
            )
    issue_counts = Counter(issue for row in rows for issue in row.issues)
    return Task309RequestShapePreview(
        schema_version=TASK309_REQUEST_SHAPE_PREVIEW_SCHEMA_VERSION,
        corpus_root=corpus_root.as_posix(),
        provider_url=provider_url,
        model=model,
        provider_runtime=provider_runtime.value,
        item_count=item_count,
        manifest_eligible_item_count=len(eligible_keys),
        attempted_item_count=len(rows),
        ok=all(row.ok for row in rows),
        issue_count=sum(issue_counts.values()),
        issue_counts=tuple(
            {"issue": issue, "count": issue_counts[issue]} for issue in sorted(issue_counts)
        ),
        items=tuple(rows),
    )


def write_task309_request_shape_preview(
    *,
    output_root: Path,
    preview: Task309RequestShapePreview,
) -> tuple[Path, Path]:
    """Write JSON and Markdown request-shape preview artifacts."""

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "request-shape-preview.json"
    markdown_path = output_root / "request-shape-preview.md"
    write_task309_json(preview.to_payload(), json_path)
    markdown_path.write_text(_markdown(preview).rstrip() + "\n", encoding="utf-8")
    return json_path, markdown_path


def _shape_issues(
    *,
    item: DigiExamIrItem,
    user_payload: Mapping[str, object],
    provider_payload: Mapping[str, object],
    output_mode: str | None,
    system_prompt: str,
) -> tuple[str, ...]:
    issues: list[str] = []
    task = user_payload.get("task")
    if not isinstance(task, dict) or not isinstance(task.get("instruction"), str):
        issues.append("missing_user_item_type_instruction")
    if "prompt_html" in user_payload or "prompt_lines" in user_payload:
        issues.append("raw_parser_prompt_fields_in_user_message")
    if item.item_type in _CHOICE_TYPES:
        issues.extend(_choice_issues(user_payload, provider_payload, output_mode, system_prompt))
    if item.item_type == DigiExamItemType.GAP_FILL:
        issues.extend(_gap_issues(item, user_payload, provider_payload, output_mode, system_prompt))
    return tuple(issues)


def _choice_issues(
    user_payload: Mapping[str, object],
    provider_payload: Mapping[str, object],
    output_mode: str | None,
    system_prompt: str,
) -> tuple[str, ...]:
    issues: list[str] = []
    item_payload = user_payload.get("item")
    choices = user_payload.get("choices")
    if not isinstance(item_payload, dict) or not isinstance(item_payload.get("stem"), str):
        issues.append("choice_missing_consumer_friendly_stem")
    if not isinstance(choices, list) or not choices:
        issues.append("choice_missing_consumer_friendly_choices")
    else:
        for choice in choices:
            if not isinstance(choice, dict):
                issues.append("choice_entry_not_object")
                continue
            if not isinstance(choice.get("choice_value"), str) or not isinstance(
                choice.get("text"), str
            ):
                issues.append("choice_missing_value_or_text")
    issues.extend(
        _provider_constraint_issues(
            provider_payload=provider_payload,
            output_mode=output_mode,
            item_kind="choice",
        )
    )
    if "For choice items" not in system_prompt:
        issues.append("choice_missing_system_guidance")
    return tuple(issues)


def _gap_issues(
    item: DigiExamIrItem,
    user_payload: Mapping[str, object],
    provider_payload: Mapping[str, object],
    output_mode: str | None,
    system_prompt: str,
) -> tuple[str, ...]:
    issues: list[str] = []
    item_payload = user_payload.get("item")
    cloze_text = item_payload.get("cloze_text") if isinstance(item_payload, dict) else None
    if not isinstance(cloze_text, str) or not cloze_text.strip():
        issues.append("gap_missing_consumer_friendly_cloze_text")
    elif "dxWordGap" in cloze_text or "<span" in cloze_text:
        issues.append("gap_cloze_text_contains_raw_html")
    elif sum(cloze_text.count(f"[{index}]") for index in range(1, len(item.gaps) + 1)) != len(
        item.gaps
    ):
        issues.append("gap_marker_count_mismatch")
    gaps = user_payload.get("gaps")
    if not isinstance(gaps, list) or len(gaps) != len(item.gaps):
        issues.append("gap_missing_gap_rows")
    issues.extend(
        _provider_constraint_issues(
            provider_payload=provider_payload,
            output_mode=output_mode,
            item_kind="gap",
        )
    )
    if "For gap-fill items" not in system_prompt:
        issues.append("gap_missing_system_guidance")
    return tuple(issues)


def _provider_constraint_issues(
    *,
    provider_payload: Mapping[str, object],
    output_mode: str | None,
    item_kind: str,
) -> tuple[str, ...]:
    if output_mode == StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE.value:
        if "structured_outputs" in provider_payload and "response_format" not in provider_payload:
            return ()
        return (f"{item_kind}_provider_payload_missing_structured_outputs",)
    if output_mode in {
        StructuredLLMOutputMode.JSON_SCHEMA.value,
        StructuredLLMOutputMode.VLLM_JSON_SCHEMA.value,
    }:
        if "response_format" in provider_payload and "structured_outputs" not in provider_payload:
            return ()
        return (f"{item_kind}_provider_payload_missing_response_format",)
    if output_mode == StructuredLLMOutputMode.GBNF.value:
        if "grammar" in provider_payload and "response_format" not in provider_payload:
            return ()
        return (f"{item_kind}_provider_payload_missing_grammar",)
    return (f"{item_kind}_unsupported_output_mode",)


def _raw_item_context_json(item: DigiExamIrItem) -> str:
    return _canonical_json(
        {
            "item_id": item.item_id,
            "sequence": item.sequence,
            "item_type": item.item_type.value,
            "title": item.title,
            "alternatives": [
                {"alternative_id": alternative.id, "text": alternative.title}
                for alternative in item.alternatives
            ],
            "gaps": [gap.guid for gap in item.gaps],
            "embedded_asset_count": len(item.embedded_assets),
            "warning_codes": [warning.code.value for warning in item.warnings],
        }
    )


def _markdown(preview: Task309RequestShapePreview) -> str:
    lines = [
        "# Task 309 Request Shape Preview",
        "",
        f"- corpus_root: `{preview.corpus_root}`",
        f"- provider_url: `{preview.provider_url}`",
        f"- model: `{preview.model}`",
        f"- provider_runtime: `{preview.provider_runtime}`",
        f"- item_count: `{preview.item_count}`",
        f"- manifest_eligible_item_count: `{preview.manifest_eligible_item_count}`",
        f"- attempted_item_count: `{preview.attempted_item_count}`",
        f"- ok: `{preview.ok}`",
        f"- issue_count: `{preview.issue_count}`",
    ]
    if preview.issue_counts:
        lines.extend(["", "## Issues"])
        for issue in preview.issue_counts:
            lines.append(f"- `{issue['issue']}`: `{issue['count']}`")
    lines.extend(["", "## Request Rows"])
    for item in preview.items:
        lines.extend(
            [
                "",
                f"### {item.source_filename} {item.item_id}",
                "",
                f"- item_type: `{item.item_type}`",
                f"- ok: `{item.ok}`",
                f"- issues: `{','.join(item.issues) if item.issues else 'none'}`",
                f"- output_mode: `{item.output_mode}`",
            ]
        )
        _append_block(lines, "System Prompt", "text", item.system_prompt)
        _append_block(lines, "User Message JSON", "json", item.user_message_json)
        _append_block(lines, "Provider Payload JSON", "json", item.provider_payload_json)
        _append_block(lines, "Output Contract JSON", "json", item.output_contract_json)
        _append_block(lines, "Raw Item Context JSON", "json", item.raw_item_context_json)
    return "\n".join(lines)


def _append_block(lines: list[str], title: str, language: str, value: str | None) -> None:
    if value is None:
        lines.append(f"- {title}: `not_applicable`")
        return
    lines.extend([f"- {title}:", f"```{language}", value, "```"])


def _load_user_payload(payload: str) -> dict[str, object]:
    decoded = json.loads(payload)
    if not isinstance(decoded, dict):
        raise ValueError("Task 309 user payload must decode to an object.")
    return {str(key): value for key, value in decoded.items()}


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("Task 309 request-shape preview must serialize to an object.")
    return {str(key): _json_value(child) for key, child in value.items()}


def _json_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported Task 309 request-shape value: {type(value).__name__}")


_CHOICE_TYPES = frozenset(
    {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }
)
