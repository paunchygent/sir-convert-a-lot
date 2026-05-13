"""Deterministic Task 280 QTI sample package inputs.

Purpose:
    Provide small, governed sample item sets for Exam.net QTI 2.1 package and
    validation-report generation.

Relationships:
    - Uses the reusable QTI contracts instead of DigiExam-specific parser
      fixtures.
    - Feeds the Task 280 sample-package CLI and regression tests.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchPair,
    ExamNetQtiUnsupportedResource,
)

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@dataclass(frozen=True)
class ExamNetQtiSamplePackage:
    """One deterministic QTI sample package input."""

    name: str
    package_filename: str
    report_filename: str
    items: tuple[ExamNetQtiItem, ...]


def examnet_qti_task_280_samples() -> tuple[ExamNetQtiSamplePackage, ...]:
    """Return the deterministic Task 280 sample package set."""

    return (
        _single_choice_sample(),
        _multiple_response_sample(),
        _free_text_sample(),
        _image_single_choice_sample(),
        _image_free_text_sample(),
        _matching_proof_gated_sample(),
        _unsupported_resource_omission_sample(),
    )


def _single_choice_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "single-choice-mcq",
        _choice_item(
            item_id="item_001",
            sequence=1,
            title="Flerval ett svar",
            prompt="Vilket svar kopplar beläggen tydligast till huvudfrågan?",
            interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
            correct=("choice_002",),
        ),
    )


def _multiple_response_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "multiple-response-mcq",
        _choice_item(
            item_id="item_001",
            sequence=1,
            title="Flerval flera svar",
            prompt="Vilka drag stärker ett källkritiskt svar?",
            interaction_type=ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
            correct=("choice_001", "choice_002", "choice_004"),
        ),
    )


def _free_text_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "free-text",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Fritext",
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_lines=(
                "Resonera kring hur sociala medier både kan förbättra "
                "tillgången till information och förvränga debatten.",
            ),
            max_score=9,
        ),
    )


def _image_single_choice_sample() -> ExamNetQtiSamplePackage:
    item = _choice_item(
        item_id="item_001",
        sequence=1,
        title="Flerval med bild",
        prompt="Vilken etikett passar bäst till bilden?",
        interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
        correct=("choice_002",),
        image_resources=(_image("image_001", "Exempelbild för flervalsfråga"),),
    )
    return _sample("image-single-choice-mcq", item)


def _image_free_text_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "image-free-text",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Fritext med bild",
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_lines=("Beskriv vad bilden visar och motivera din tolkning.",),
            max_score=6,
            image_resources=(_image("image_001", "Exempelbild för fritextfråga"),),
        ),
    )


def _matching_proof_gated_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "matching-proof-gated",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Matcha ihop",
            interaction_type=ExamNetQtiInteractionType.MATCHING,
            prompt_lines=("Para ihop varje cellstruktur med rätt funktion.",),
            max_score=4,
            match_pairs=(
                ExamNetQtiMatchPair("left_001", "kloroplast", "right_001", "fotosyntes"),
                ExamNetQtiMatchPair("left_002", "mitokondrie", "right_002", "ATP-produktion"),
                ExamNetQtiMatchPair("left_003", "ribosom", "right_003", "proteinsyntes"),
                ExamNetQtiMatchPair(
                    "left_004",
                    "cellkärna",
                    "right_004",
                    "genetisk information",
                ),
            ),
        ),
    )


def _unsupported_resource_omission_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "unsupported-resource-omission",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Fritext med externt ljud",
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_lines=("Lyssna på lärarens ljudfil och sammanfatta huvudpoängen.",),
            max_score=5,
            unsupported_resources=(
                ExamNetQtiUnsupportedResource(
                    resource_id="audio_001",
                    resource_type="audio",
                    label="teacher-audio.mp3",
                ),
            ),
        ),
    )


def _choice_item(
    *,
    item_id: str,
    sequence: int,
    title: str,
    prompt: str,
    interaction_type: ExamNetQtiInteractionType,
    correct: tuple[str, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...] = (),
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id=item_id,
        sequence=sequence,
        title=title,
        interaction_type=interaction_type,
        prompt_lines=(prompt,),
        max_score=4,
        choices=(
            ExamNetQtiChoice("choice_001", "Svaret använder relevanta belägg."),
            ExamNetQtiChoice("choice_002", "Svaret kopplar beläggen till huvudfrågan."),
            ExamNetQtiChoice("choice_003", "Svaret byter ämne mitt i resonemanget."),
            ExamNetQtiChoice("choice_004", "Svaret skiljer fakta från värdering."),
        ),
        correct_choice_identifiers=correct,
        image_resources=image_resources,
    )


def _image(asset_id: str, alt_text: str) -> ExamNetQtiImageResource:
    return ExamNetQtiImageResource(
        asset_id=asset_id,
        filename=f"{asset_id}.png",
        media_type="image/png",
        payload=_ONE_PIXEL_PNG,
        alt_text=alt_text,
        source_reference="task-280-deterministic-sample",
    )


def _sample(name: str, item: ExamNetQtiItem) -> ExamNetQtiSamplePackage:
    return ExamNetQtiSamplePackage(
        name=name,
        package_filename="qti-package.zip",
        report_filename="qti-validation-report.json",
        items=(item,),
    )
