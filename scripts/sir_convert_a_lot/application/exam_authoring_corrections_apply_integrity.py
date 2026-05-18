"""Integrity helpers for exam authoring correction application.

Purpose:
    Produce canonical digests for source-authoring state and advisory answer-key
    payloads used by the unified correction apply route.

Relationships:
    - Used by `application.exam_authoring_corrections_apply_contracts` before
      applying correction batches.
    - Used by `application.exam_authoring_correction_source_state_issuer` when
      issuing signed producer source-state bundles.
    - Shared with route tests so producer-state and candidate-lineage proofs use
      the same canonical JSON contract.
"""

from __future__ import annotations

import hashlib
import hmac
import json

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceBindingV1,
    ExamAuthoringCorrectionSourceStateV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionsApplyRequestV1,
    ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
    ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
)

_SOURCE_STATE_SIGNATURE_PREFIX = "hmac-sha256:"


def stable_json_sha256(payload: dict[str, object]) -> str:
    """Return a stable `sha256:` digest for a JSON object payload."""

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def source_state_content_digest(state: ExamAuthoringCorrectionSourceStateV1) -> str:
    """Return the canonical digest for submitted producer authoring state."""

    return stable_json_sha256(
        {
            "schema_version": state.schema_version,
            "source_authoring_schema_version": state.source_authoring_schema_version,
            "items": tuple(item.model_dump(mode="json") for item in state.items),
        }
    )


def request_source_state_content_digest(
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
) -> str:
    """Return the canonical digest for a correction request's source state."""

    return source_state_content_digest(request_body.source_authoring_state)


def matching_answer_key_payload_digest(
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
) -> str:
    """Return the advisory payload digest for a matching answer-key correction."""

    return stable_json_sha256(
        {
            "kind": "matching",
            "pairs": tuple(pair.model_dump(mode="json") for pair in correction.pairs),
        }
    )


def choice_answer_key_payload_digest(
    correction: ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
) -> str:
    """Return the advisory payload digest for a choice answer-key correction."""

    return stable_json_sha256(
        {
            "kind": "choice",
            "correct_choice_ids": correction.correct_choice_ids,
        }
    )


def gap_open_cloze_answer_key_payload_digest(
    correction: ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
) -> str:
    """Return the advisory payload digest for a gap/open-cloze key correction."""

    return stable_json_sha256(
        {
            "kind": "gap_open_cloze",
            "gap_answers": tuple(
                {
                    "gap_id": answer.gap_id,
                    "accepted_values": answer.accepted_values,
                }
                for answer in correction.gap_answers
            ),
        }
    )


def source_state_authority_payload(
    binding: ExamAuthoringCorrectionSourceBindingV1,
) -> dict[str, object]:
    """Return the signed producer-state authority payload for a source binding."""

    return {
        "authority_version": "exam_authoring_source_state_authority_v1",
        "source_authoring_schema_version": binding.source_authoring_schema_version,
        "source_state_sha256": binding.source_state_sha256,
        "source_bundle_id": binding.source_bundle_id,
        "source_file_sha256": binding.source_file_sha256,
    }


def source_state_authority_signature(
    *,
    binding: ExamAuthoringCorrectionSourceBindingV1,
    secret: str,
) -> str:
    """Return the server signature for a producer-owned source binding."""

    payload_digest = stable_json_sha256(source_state_authority_payload(binding))
    digest = hmac.new(
        secret.encode("utf-8"),
        payload_digest.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{_SOURCE_STATE_SIGNATURE_PREFIX}{digest}"


def source_state_authority_signature_matches(
    *,
    binding: ExamAuthoringCorrectionSourceBindingV1,
    secret: str,
) -> bool:
    """Return whether the submitted source-state signature matches server truth."""

    expected = source_state_authority_signature(binding=binding, secret=secret)
    return hmac.compare_digest(expected, binding.source_state_signature)
