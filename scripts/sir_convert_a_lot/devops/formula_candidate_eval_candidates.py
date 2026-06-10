"""Formula candidate evaluation adapter facade.

Purpose:
    Preserve the public import surface for the Task 346/350 formula candidate
    harness while routing declarations, execution, and output parsing to
    focused modules.

Relationships:
    - Used by `formula_candidate_eval` and focused tests.
    - Delegates behavior to SRP modules so candidate evaluation remains
      maintainable before any future DeepSeek integration task.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_commands import (
    command_blocker,
    deepseek_batch_command,
    deepseek_command,
    paddle_command,
)
from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_execution import (
    blocked_candidate,
    build_candidate_command,
    first_existing_output,
    run_batch_candidate,
    run_batch_external_command,
    run_candidate_input,
    run_external_candidate,
    run_granite_baseline,
    run_one_external_input,
    run_source_layer_baseline,
)
from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_outputs import (
    BAD_MARKERS,
    baseline_elapsed_ms,
    candidate_output_text,
    collect_marker_counts,
    executable_exists,
    is_candidate_text_artifact,
    json_text_fragments,
    read_json_object,
    sum_marker_counts,
    tail_text,
    timeout_text,
)
from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_specs import (
    CandidateSpec,
    candidate_sources,
    default_external_candidates,
)

__all__ = [
    "BAD_MARKERS",
    "CandidateSpec",
    "baseline_elapsed_ms",
    "blocked_candidate",
    "build_candidate_command",
    "candidate_output_text",
    "candidate_sources",
    "collect_marker_counts",
    "command_blocker",
    "deepseek_batch_command",
    "deepseek_command",
    "default_external_candidates",
    "executable_exists",
    "first_existing_output",
    "is_candidate_text_artifact",
    "json_text_fragments",
    "paddle_command",
    "read_json_object",
    "run_batch_candidate",
    "run_batch_external_command",
    "run_candidate_input",
    "run_external_candidate",
    "run_granite_baseline",
    "run_one_external_input",
    "run_source_layer_baseline",
    "sum_marker_counts",
    "tail_text",
    "timeout_text",
]
