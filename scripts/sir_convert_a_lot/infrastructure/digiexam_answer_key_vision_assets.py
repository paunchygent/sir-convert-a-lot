"""Provider-facing DigiExam answer-key vision asset preparation.

Purpose:
    Materialize validated DigiExam embedded images for multimodal advisory
    answer-key completion without putting raw image bytes into retained
    completion reports.

Relationships:
    - Reuses renderer-neutral DigiExam IR assets and the Exam.net PDF asset
      validation surface.
    - Wraps the domain answer-key candidate planner with multimodal
      Chat Completions content parts when the selected provider supports
      vision.
    - Called by the DigiExam migration bundle runtime only for explicitly
      requested advisory completion.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    DigiExamAnswerKeyCandidatePlannerProtocol,
    DigiExamCompletionCandidatePlan,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_assets import (
    prepare_examnet_pdf_assets,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfAssetFile,
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

_SUPPORTED_VISION_MEDIA_TYPES = frozenset({"image/png", "image/jpeg"})


@dataclass(frozen=True)
class DigiExamAnswerKeyVisionAsset:
    """Metadata for one provider-facing vision asset."""

    asset_id: str
    sha256: str
    media_type: str
    width_px: int
    height_px: int
    relative_path: str


@dataclass(frozen=True)
class DigiExamAnswerKeyVisionItemAssets:
    """Provider-facing vision assets for one DigiExam item."""

    item_id: str
    assets: tuple[DigiExamAnswerKeyVisionAsset, ...]

    @property
    def image_urls(self) -> tuple[str, ...]:
        """Return llama.cpp media-path-relative file URLs."""

        return tuple(f"file://{asset.relative_path}" for asset in self.assets)


def export_digiexam_answer_key_vision_assets(
    *,
    exam: DigiExamIntermediateExam,
    media_path: Path,
    relative_path_prefix: str = "",
) -> dict[str, DigiExamAnswerKeyVisionItemAssets]:
    """Write supported embedded images and return metadata keyed by item id."""

    normalized_prefix = _normalized_relative_path_prefix(relative_path_prefix)
    preparation = prepare_examnet_pdf_assets(exam)
    warnings_by_item = {
        warning.item_id for warning in preparation.warnings if warning.item_id is not None
    }
    asset_files_by_id = {asset_file.asset_id: asset_file for asset_file in preparation.asset_files}
    item_assets: dict[str, DigiExamAnswerKeyVisionItemAssets] = {}
    for item in exam.items:
        if not _vision_item_can_use_assets(item, warnings_by_item=warnings_by_item):
            continue
        files = tuple(
            asset_files_by_id[asset.asset_id]
            for asset in item.embedded_assets
            if asset.asset_id in asset_files_by_id
        )
        if len(files) != len(item.embedded_assets):
            continue
        item_assets[item.item_id] = _write_item_assets(
            item=item,
            asset_files=files,
            media_path=media_path,
            relative_path_prefix=normalized_prefix,
        )
    return item_assets


@dataclass(frozen=True)
class DigiExamVisionCandidatePlanner:
    """Attach provider-facing image URLs to answer-key candidate requests."""

    base_planner: DigiExamAnswerKeyCandidatePlannerProtocol
    item_assets_by_id: dict[str, DigiExamAnswerKeyVisionItemAssets]

    def plan_candidate(
        self,
        *,
        job_id: str,
        item: DigiExamIrItem,
        profile: StructuredLLMProviderProfile | None,
    ) -> DigiExamCompletionCandidatePlan | None:
        """Build a candidate plan with image content parts when supported."""

        plan = self.base_planner.plan_candidate(job_id=job_id, item=item, profile=profile)
        if plan is None:
            return None
        if not (item.embedded_assets or item.embedded_asset_references):
            return plan
        if profile is None or not profile.capabilities.supports_multimodal_vision:
            return None
        item_assets = self.item_assets_by_id.get(item.item_id)
        if item_assets is None or not item_assets.image_urls:
            return None
        request = replace(
            plan.request,
            user_content_parts=(
                StructuredLLMTextContentPart(plan.request.user_payload),
                *(StructuredLLMImageURLContentPart(url) for url in item_assets.image_urls),
            ),
        )
        return replace(plan, request=request)


def _vision_item_can_use_assets(
    item: DigiExamIrItem,
    *,
    warnings_by_item: set[str],
) -> bool:
    if not item.embedded_assets:
        return False
    if item.item_id in warnings_by_item:
        return False
    if item.warnings and any(warning.blocking for warning in item.warnings):
        return False
    referenced_asset_ids = {reference.asset_id for reference in item.embedded_asset_references}
    asset_ids = {asset.asset_id for asset in item.embedded_assets}
    if referenced_asset_ids != asset_ids:
        return False
    return all(
        asset.media_type in _SUPPORTED_VISION_MEDIA_TYPES and asset.content_base64
        for asset in item.embedded_assets
    )


def _write_item_assets(
    *,
    item: DigiExamIrItem,
    asset_files: tuple[DigiExamExamNetPdfAssetFile, ...],
    media_path: Path,
    relative_path_prefix: str,
) -> DigiExamAnswerKeyVisionItemAssets:
    assets: list[DigiExamAnswerKeyVisionAsset] = []
    item_assets_by_id = {asset.asset_id: asset for asset in item.embedded_assets}
    for asset_file in asset_files:
        source_asset = item_assets_by_id[asset_file.asset_id]
        relative_path = _prefixed_relative_path(
            relative_path_prefix,
            f"{item.item_id}/assets/{Path(asset_file.relative_path).name}",
        )
        destination = media_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(asset_file.payload)
        assets.append(
            DigiExamAnswerKeyVisionAsset(
                asset_id=source_asset.asset_id,
                sha256=f"sha256:{source_asset.sha256}",
                media_type=source_asset.media_type,
                width_px=source_asset.width_px,
                height_px=source_asset.height_px,
                relative_path=relative_path,
            )
        )
    return DigiExamAnswerKeyVisionItemAssets(
        item_id=item.item_id,
        assets=tuple(assets),
    )


def _normalized_relative_path_prefix(value: str) -> str:
    if value == "":
        return ""
    if "\\" in value:
        raise ValueError("Vision asset relative path prefixes must be POSIX paths.")
    stripped = value.strip("/")
    parts = PurePosixPath(stripped).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Vision asset relative path prefixes must stay within the media root.")
    return "/".join(parts)


def _prefixed_relative_path(prefix: str, relative_path: str) -> str:
    if prefix == "":
        return relative_path
    return f"{prefix}/{relative_path}"
