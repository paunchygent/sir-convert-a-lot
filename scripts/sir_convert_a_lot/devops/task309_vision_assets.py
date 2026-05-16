"""Task 309 eval-only vision asset export.

Purpose:
    Materialize supported DigiExam embedded images for the Task 309 Qwen3.6
    llama.cpp vision-evaluation lane without persisting raw base64 in reports.

Relationships:
    - Reuses the renderer-neutral DigiExam IR asset and prompt-rendering
      contracts.
    - Feeds Task 309 request-shape preview and live advisory execution with
      llama.cpp `file://` image URLs rooted under `--media-path`.
    - Keeps production advisory behavior text-only unless a Task 309 vision
      policy explicitly opts in.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    DigiExamAnswerKeyCandidatePlannerProtocol,
    DigiExamCompletionCandidatePlan,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_assets import (
    prepare_examnet_pdf_assets,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfAssetFile,
    DigiExamExamNetPdfWarningCode,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_prompt import (
    render_examnet_prompt_html,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMImageURLContentPart,
    StructuredLLMProviderProfile,
    StructuredLLMTextContentPart,
)

TASK309_VISION_ASSET_SCHEMA_VERSION = "task309_vision_assets_v1"


@dataclass(frozen=True)
class Task309VisionAssetMetadata:
    """Metadata for one exported vision asset without raw payload bytes."""

    asset_id: str
    sha256: str
    media_type: str
    width_px: int
    height_px: int
    relative_path: str


@dataclass(frozen=True)
class Task309VisionPreview:
    """One per-item human-review HTML preview."""

    item_id: str
    relative_path: str
    warning_codes: tuple[str, ...]
    renderable: bool


@dataclass(frozen=True)
class Task309VisionItemAssets:
    """Exported assets and preview metadata for one DigiExam item."""

    item_id: str
    assets: tuple[Task309VisionAssetMetadata, ...]
    preview: Task309VisionPreview | None

    @property
    def image_urls(self) -> tuple[str, ...]:
        """Return llama.cpp media-path-relative `file://` URLs."""

        return tuple(f"file://{asset.relative_path}" for asset in self.assets)


@dataclass(frozen=True)
class Task309VisionAssetExport:
    """Export result for one source `.dxe` file."""

    schema_version: str
    source_filename: str
    media_path: str
    items: tuple[Task309VisionItemAssets, ...]

    def to_payload(self) -> dict[str, object]:
        """Return JSON-safe metadata with no raw image bytes."""

        return {
            "schema_version": self.schema_version,
            "source_filename": self.source_filename,
            "media_path": self.media_path,
            "items": [asdict(item) for item in self.items],
        }


def export_task309_vision_assets(
    *,
    exam: DigiExamIntermediateExam,
    source_filename: str,
    media_path: Path,
) -> Task309VisionAssetExport:
    """Write supported embedded assets and per-item preview HTML."""

    source_stem = Path(source_filename).stem
    preparation = prepare_examnet_pdf_assets(exam)
    items: list[Task309VisionItemAssets] = []
    for item in exam.items:
        if not item.embedded_assets:
            continue
        assets = tuple(
            _metadata(item=item, source_stem=source_stem, relative_path=relative_path)
            for relative_path, item_asset_id in _item_asset_paths(
                item=item,
                source_stem=source_stem,
            )
            for _asset in item.embedded_assets
            if _asset.asset_id == item_asset_id
        )
        _write_item_assets(
            preparation_assets=preparation.asset_files,
            item=item,
            media_path=media_path,
            source_stem=source_stem,
        )
        preview = _write_preview(
            item=item,
            media_path=media_path,
            source_stem=source_stem,
            asset_paths_by_reference={
                key: f"{source_stem}/{item_id}/assets/{Path(path).name}"
                for key, path in preparation.asset_paths_by_reference.items()
                for item_id in (key[0],)
            },
        )
        items.append(Task309VisionItemAssets(item_id=item.item_id, assets=assets, preview=preview))
    return Task309VisionAssetExport(
        schema_version=TASK309_VISION_ASSET_SCHEMA_VERSION,
        source_filename=source_filename,
        media_path=media_path.as_posix(),
        items=tuple(items),
    )


def supported_task309_vision_asset_item(item: DigiExamIrItem) -> bool:
    """Return whether one item can enter the eval-only vision lane."""

    if not item.embedded_assets:
        return False
    if item.warnings and any(warning.blocking for warning in item.warnings):
        return False
    referenced_asset_ids = {reference.asset_id for reference in item.embedded_asset_references}
    asset_ids = {asset.asset_id for asset in item.embedded_assets}
    if referenced_asset_ids != asset_ids:
        return False
    supported_media = {"image/png", "image/jpeg"}
    return all(
        asset.media_type in supported_media and asset.content_base64
        for asset in item.embedded_assets
    )


def vision_item_assets_by_id(
    export: Task309VisionAssetExport,
) -> dict[str, Task309VisionItemAssets]:
    """Return exported item assets keyed by item id."""

    return {item.item_id: item for item in export.items}


@dataclass(frozen=True)
class Task309VisionCandidatePlanner:
    """Attach exported image URLs to base answer-key candidate requests."""

    base_planner: DigiExamAnswerKeyCandidatePlannerProtocol
    item_assets_by_id: dict[str, Task309VisionItemAssets]

    def plan_candidate(
        self,
        *,
        job_id: str,
        item: DigiExamIrItem,
        profile: StructuredLLMProviderProfile | None,
    ) -> DigiExamCompletionCandidatePlan | None:
        """Build a base plan, then add llama.cpp vision content parts when present."""

        plan = self.base_planner.plan_candidate(job_id=job_id, item=item, profile=profile)
        if plan is None or not item.embedded_assets:
            return plan
        if profile is None or not profile.capabilities.supports_multimodal_vision:
            return None
        item_assets = self.item_assets_by_id.get(item.item_id)
        if item_assets is None or item_assets.preview is None or not item_assets.preview.renderable:
            return None
        if not item_assets.image_urls:
            return None
        request = replace(
            plan.request,
            user_content_parts=(
                StructuredLLMTextContentPart(plan.request.user_payload),
                *(StructuredLLMImageURLContentPart(url) for url in item_assets.image_urls),
            ),
        )
        return replace(plan, request=request)


def _item_asset_paths(
    *,
    item: DigiExamIrItem,
    source_stem: str,
) -> tuple[tuple[str, str], ...]:
    media_suffix = {"image/png": ".png", "image/jpeg": ".jpg"}
    return tuple(
        (
            f"{source_stem}/{item.item_id}/assets/{asset.asset_id}{media_suffix[asset.media_type]}",
            asset.asset_id,
        )
        for asset in item.embedded_assets
        if asset.media_type in media_suffix
    )


def _metadata(
    *,
    item: DigiExamIrItem,
    source_stem: str,
    relative_path: str,
) -> Task309VisionAssetMetadata:
    asset_id = Path(relative_path).stem
    asset = next(asset for asset in item.embedded_assets if asset.asset_id == asset_id)
    return Task309VisionAssetMetadata(
        asset_id=asset.asset_id,
        sha256=f"sha256:{asset.sha256}",
        media_type=asset.media_type,
        width_px=asset.width_px,
        height_px=asset.height_px,
        relative_path=relative_path,
    )


def _write_item_assets(
    *,
    preparation_assets: tuple[DigiExamExamNetPdfAssetFile, ...],
    item: DigiExamIrItem,
    media_path: Path,
    source_stem: str,
) -> None:
    item_asset_ids = {asset.asset_id for asset in item.embedded_assets}
    for asset_file in preparation_assets:
        if asset_file.asset_id not in item_asset_ids:
            continue
        relative = Path(asset_file.relative_path)
        destination = media_path / source_stem / item.item_id / "assets" / relative.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(asset_file.payload)


def _write_preview(
    *,
    item: DigiExamIrItem,
    media_path: Path,
    source_stem: str,
    asset_paths_by_reference: dict[tuple[str, int], str],
) -> Task309VisionPreview:
    prompt_render = render_examnet_prompt_html(
        item=item,
        asset_paths_by_reference=asset_paths_by_reference,
    )
    warning_codes = tuple(warning.code.value for warning in prompt_render.warnings)
    preview_relative_path = f"{source_stem}/{item.item_id}/preview.html"
    preview_path = media_path / preview_relative_path
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        _preview_html(item=item, body_html=prompt_render.html), encoding="utf-8"
    )
    renderable = (
        DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_REFERENCE_MISSING.value not in warning_codes
    )
    return Task309VisionPreview(
        item_id=item.item_id,
        relative_path=preview_relative_path,
        warning_codes=warning_codes,
        renderable=renderable,
    )


def _preview_html(*, item: DigiExamIrItem, body_html: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="sv">\n'
        '<head><meta charset="utf-8"><title>'
        f"{item.item_id} vision preview"
        "</title></head>\n"
        "<body>\n"
        f'<main data-item-id="{item.item_id}">{body_html}</main>\n'
        "</body>\n"
        "</html>\n"
    )
