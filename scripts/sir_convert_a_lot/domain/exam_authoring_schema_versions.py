"""Source-neutral exam authoring schema version authority.

Purpose:
    Centralize schema identifiers for source-neutral exam authoring contracts
    that sit between source adapters and target validators/exporters.

Relationships:
    - Used by `domain.exam_authoring_ir_contracts` and
      `domain.exam_authoring_gap_contracts` for source-neutral interaction
      slices.
    - Complements DigiExam-specific schema versions while reusable authoring
      concepts are extracted from adapter-shaped contracts.
"""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

ExamAuthoringIrSchemaVersion: TypeAlias = Literal["exam_authoring_ir_v1"]

EXAM_AUTHORING_IR_SCHEMA_VERSION: Final[ExamAuthoringIrSchemaVersion] = "exam_authoring_ir_v1"
