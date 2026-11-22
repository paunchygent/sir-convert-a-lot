"""Literal-alias narrowing guards for stored preprocessing payloads.

Purpose:
    Narrow parsed JSON scalars into the pipeline's ``Literal`` aliases through
    ``TypeGuard`` membership checks so spool hydration needs no ``cast`` or
    ignore comment.

Relationships:
    - Used by `preprocessing.storage` and `preprocessing.canonical_root` when
      hydrating durable spool-row payloads.
"""

from __future__ import annotations

from typing import TypeGuard, get_args

from scripts.sir_convert_a_lot.ml.qwen.common.models import ManifestFamily
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import (
    AdmissionDecision,
    QualityTier,
    SpeakerQualityGate,
)


def is_manifest_family(value: object) -> TypeGuard[ManifestFamily]:
    """Report whether a value is one canonical manifest-family literal."""
    return value in get_args(ManifestFamily)


def is_quality_tier(value: object) -> TypeGuard[QualityTier]:
    """Report whether a value is one quality-tier literal."""
    return value in get_args(QualityTier)


def is_speaker_quality_gate(value: object) -> TypeGuard[SpeakerQualityGate]:
    """Report whether a value is one speaker-quality-gate literal."""
    return value in get_args(SpeakerQualityGate)


def is_admission_decision(value: object) -> TypeGuard[AdmissionDecision]:
    """Report whether a value is one admission-decision literal."""
    return value in get_args(AdmissionDecision)
