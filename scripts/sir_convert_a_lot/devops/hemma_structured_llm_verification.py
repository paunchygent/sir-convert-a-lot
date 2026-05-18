"""Hemma structured LLM deploy verification.

Purpose:
    Prove that the production Sir Convert container can reach its configured
    structured answer-key provider and receive constrained JSON output.

Relationships:
    - Called by `hemma_deploy_and_verify` before OCR-heavy smoke tests so
      provider readiness is recorded independently.
    - Executes the network probe from inside `sir_convert_a_lot_prod`, where
      production environment variables and provider credentials are present.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from scripts.sir_convert_a_lot.devops.hemma_deploy_verification_contracts import (
    VerificationContractError,
)

RemoteRunner = Callable[..., str]

_PROBE_CODE = r"""
import asyncio
import json
import os

import httpx

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMRequest,
    StructuredOutputSpec,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    structured_llm_runtime_config_from_env,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision_state": {"type": "string", "enum": ["answered"]},
        "correct_alternative_ids": {"type": "array", "items": {"type": "integer"}},
        "manual_follow_up_code": {"type": ["string", "null"]},
    },
    "required": ["decision_state", "correct_alternative_ids", "manual_follow_up_code"],
}


async def main():
    config = structured_llm_runtime_config_from_env(os.environ)
    profile = None if config.provider_set is None else config.provider_set.primary
    report = {
        "provider_profile_id": None if profile is None else profile.provider_id,
        "provider_model": None if profile is None else profile.model,
        "provider_endpoint_kind": None if profile is None else profile.endpoint_kind.value,
        "provider_is_remote": None if profile is None else profile.is_remote,
        "models_reachable": False,
        "structured_probe_passed": False,
        "failure": None,
    }
    if profile is None:
        report["failure"] = "structured provider set is not configured"
        print(json.dumps(report, sort_keys=True))
        return
    request = StructuredLLMRequest(
        job_id="deploy-structured-llm-probe",
        item_id="deploy-probe-item",
        item_type="single_choice",
        prompt_template_version="deploy_structured_llm_probe_v1",
        system_prompt="Return only the constrained answer.",
        user_payload="{\"answer\":2}",
        output_spec=StructuredOutputSpec(
            schema_name="deploy_structured_llm_probe",
            schema_version="deploy_structured_llm_probe_v1",
            json_schema=SCHEMA,
        ),
        estimated_input_tokens=32,
        max_output_tokens=256,
        allow_remote_fallback=None,
    )
    async with httpx.AsyncClient() as client:
        provider = HttpStructuredChatProvider(client=client, connections=config.connections)
        response = await provider.complete_structured_chat(request=request, profile=profile)
    report["models_reachable"] = True
    report["structured_probe_passed"] = (
        response.content.get("decision_state") == "answered"
        and response.content.get("correct_alternative_ids") == [2]
    )
    print(json.dumps(report, sort_keys=True))

try:
    asyncio.run(main())
except Exception as exc:
    report = {
        "provider_profile_id": None,
        "provider_model": None,
        "provider_endpoint_kind": None,
        "provider_is_remote": None,
        "models_reachable": False,
        "structured_probe_passed": False,
        "failure": f"{type(exc).__name__}: {exc}",
    }
    print(json.dumps(report, sort_keys=True))
"""


def structured_llm_check_defaults() -> dict[str, object]:
    """Return deploy report check defaults for provider verification."""

    return {
        "structured_llm_models_reachable": False,
        "structured_llm_microprobe_passed": False,
    }


def record_structured_llm_report(report: dict[str, object], payload: dict[str, object]) -> None:
    """Attach provider verification evidence to a deploy report."""

    report["structured_llm"] = payload
    checks = report.get("checks")
    if isinstance(checks, dict):
        checks["structured_llm_models_reachable"] = payload.get("models_reachable") is True
        checks["structured_llm_microprobe_passed"] = payload.get("structured_probe_passed") is True


def verify_structured_llm_provider(run_remote: RemoteRunner) -> dict[str, object]:
    """Run the provider probe from inside the production app container."""

    raw = run_remote(
        [
            "sudo",
            "-n",
            "docker",
            "exec",
            "sir_convert_a_lot_prod",
            "python",
            "-c",
            _PROBE_CODE,
        ],
        label="remote structured LLM provider probe",
    )
    payload = _parse_probe_payload(raw)
    if payload.get("models_reachable") is not True:
        raise VerificationContractError(
            "Structured LLM provider model endpoint was not reachable from "
            f"sir_convert_a_lot_prod: {payload.get('failure')}"
        )
    if payload.get("structured_probe_passed") is not True:
        raise VerificationContractError(
            "Structured LLM provider microprobe failed from sir_convert_a_lot_prod: "
            f"{payload.get('failure')}"
        )
    return payload


def _parse_probe_payload(raw: str) -> dict[str, object]:
    try:
        parsed: object = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        raise VerificationContractError(
            "Structured LLM provider probe returned invalid JSON."
        ) from exc
    if not isinstance(parsed, dict):
        raise VerificationContractError("Structured LLM provider probe payload is not an object.")
    return parsed
