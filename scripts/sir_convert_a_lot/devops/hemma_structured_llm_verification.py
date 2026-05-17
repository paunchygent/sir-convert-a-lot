"""Hemma structured LLM deploy verification.

Purpose:
    Prove that the production Sir Convert container can reach the container
    native Qwen3.6 answer-key provider and receive constrained JSON output.

Relationships:
    - Called by `hemma_deploy_and_verify` before OCR-heavy smoke tests so
      provider readiness is recorded independently.
    - Executes the network probe from inside `sir_convert_a_lot_prod`, where
      Docker service DNS for `sir_convert_qwen_answer_key` is valid.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from scripts.sir_convert_a_lot.devops.hemma_deploy_verification_contracts import (
    VerificationContractError,
)

PROVIDER_URL = "http://sir_convert_qwen_answer_key:8082"

RemoteRunner = Callable[..., str]

_PROBE_CODE = r"""
import json
import urllib.request

base_url = "http://sir_convert_qwen_answer_key:8082"
report = {
    "provider_url": base_url,
    "models_reachable": False,
    "structured_probe_passed": False,
    "failure": None,
}
try:
    with urllib.request.urlopen(base_url + "/v1/models", timeout=30) as response:
        json.loads(response.read().decode("utf-8"))
    report["models_reachable"] = True
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision_state": {"type": "string", "enum": ["answered"]},
            "correct_alternative_ids": {"type": "array", "items": {"type": "integer"}},
            "manual_follow_up_code": {"type": ["string", "null"]},
        },
        "required": ["decision_state", "correct_alternative_ids", "manual_follow_up_code"],
    }
    payload = {
        "model": "qwen3.6-27b-q6k-mtp",
        "stream": False,
        "temperature": 0.15,
        "max_tokens": 256,
        "messages": [
            {"role": "system", "content": "Return only the constrained answer."},
            {"role": "user", "content": "{\"answer\":2}"},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "task320_choice_probe", "schema": schema},
        },
    }
    request = urllib.request.Request(
        base_url + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    content = response_payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    report["structured_probe_passed"] = (
        parsed.get("decision_state") == "answered"
        and parsed.get("correct_alternative_ids") == [2]
    )
except Exception as exc:
    report["failure"] = f"{type(exc).__name__}: {exc}"
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
