"""Correction replay artifact identity contract.

Purpose:
    Define the replay-scoped artifact keys and filenames Sir Convert returns
    after applying source-bound exam-authoring corrections.

Relationships:
    - Used by correction apply rendering to persist corrected target bytes.
    - Used by named artifact resolution so HuleEdu/Skriptoteket can download
      only Sir Convert-authorized replay artifacts.
    - Complements `exam_authoring_corrections_apply_models` target readiness
      rows without aliasing original migration artifact keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionTargetV1,
)

ExamAuthoringCorrectionReplayArtifactKey = Literal[
    "correction_replay_examnet_pdf",
    "correction_replay_qti_package",
]


@dataclass(frozen=True)
class ExamAuthoringCorrectionReplayArtifactDefinition:
    """Static replay artifact identity for one corrected target."""

    artifact_key: ExamAuthoringCorrectionReplayArtifactKey
    content_type: str
    filename: str
    target: ExamAuthoringCorrectionTargetV1


EXAM_AUTHORING_CORRECTION_REPLAY_ARTIFACT_DEFINITIONS: tuple[
    ExamAuthoringCorrectionReplayArtifactDefinition,
    ...,
] = (
    ExamAuthoringCorrectionReplayArtifactDefinition(
        artifact_key="correction_replay_examnet_pdf",
        content_type="application/pdf",
        filename="corrected-examnet-import.pdf",
        target="examnet_pdf",
    ),
    ExamAuthoringCorrectionReplayArtifactDefinition(
        artifact_key="correction_replay_qti_package",
        content_type="application/zip",
        filename="corrected-qti-package.zip",
        target="qti_package",
    ),
)


def replay_artifact_definition_for_key(
    artifact_key: str,
) -> ExamAuthoringCorrectionReplayArtifactDefinition | None:
    """Return the replay artifact definition for an artifact key."""

    for definition in EXAM_AUTHORING_CORRECTION_REPLAY_ARTIFACT_DEFINITIONS:
        if definition.artifact_key == artifact_key:
            return definition
    return None


def replay_artifact_definition_for_target(
    target: ExamAuthoringCorrectionTargetV1,
) -> ExamAuthoringCorrectionReplayArtifactDefinition:
    """Return the replay artifact definition for a corrected target."""

    for definition in EXAM_AUTHORING_CORRECTION_REPLAY_ARTIFACT_DEFINITIONS:
        if definition.target == target:
            return definition
    raise ValueError(f"Unsupported correction replay target: {target}")
