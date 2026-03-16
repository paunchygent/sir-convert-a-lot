"""Markdown rendering helpers for the Story 29 proof surfaces.

Purpose:
    Render deterministic operator-facing plan and checklist markdown for the
    bounded Story 29 proof packages without mixing those concerns into artifact
    path/config loading.

Relationships:
    - Used by `t197_proof.py` during proof-package preparation.
    - Consumes `Story29ProofConfig` plus launch-root helpers from
      `t197_proof_artifacts.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_artifacts import (
    remote_fallback_eval_output_root,
    remote_fallback_launch_root,
    remote_gate_launch_root,
    remote_window_launch_root,
)

if TYPE_CHECKING:
    from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_artifacts import (
        Story29ProofConfig,
    )


def render_plan_markdown(
    config: Story29ProofConfig,
    *,
    window_command: list[str],
    status_window_command: list[str],
    fallback_command: list[str],
    status_fallback_command: list[str],
    fallback_eval_command: list[str],
    status_fallback_eval_command: list[str],
    gate_command: list[str],
    status_gate_command: list[str],
) -> str:
    """Render one concise markdown plan for the prepared Story 29 proof."""
    return "\n".join(
        [
            f"# {config.task_label} Proof Plan",
            "",
            f"- proof_id: `{config.proof_id}`",
            f"- local_proof_root: `{config.local_proof_root}`",
            f"- remote_training_output_root: `{config.remote_training_output_root}`",
            f"- source_launch_root: `{config.source_launch_root}`",
            f"- source_checkpoint_path: `{config.source_checkpoint_path}`",
            f"- text_embedding_mask_policy: `{config.text_embedding_mask_policy}`",
            f"- gradient_accumulation_steps: `{config.gradient_accumulation_steps}`",
            (
                f"- bounded_window: `{config.window_start_optimizer_step} -> "
                f"{config.window_end_optimizer_step}`"
            ),
            f"- fallback_gate_step: `{config.fallback_max_steps}`",
            f"- preferred_gate_step: `{config.gate_max_steps}`",
            f"- gate_checkpoint_interval_steps: `{config.gate_checkpoint_interval_steps}`",
            f"- gate_eval_interval_steps: `{config.gate_eval_interval_steps}`",
            f"- required_scratch_free_bytes: `{config.required_scratch_free_bytes}`",
            "",
            "## Wrapper Commands",
            "",
            f"- prepare: `pdm run {config.command_name} prepare --proof-id {config.proof_id}`",
            (
                f"- launch-window: `pdm run {config.command_name} launch-window "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- status-window: `pdm run {config.command_name} status-window "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- launch-gate1500: `pdm run {config.command_name} launch-gate1500 "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- status-gate1500: `pdm run {config.command_name} status-gate1500 "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- launch-fallback1470: `pdm run {config.command_name} launch-fallback1470 "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- status-fallback1470: `pdm run {config.command_name} status-fallback1470 "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- launch-fallback-eval: `pdm run {config.command_name} launch-fallback-eval "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- status-fallback-eval: `pdm run {config.command_name} status-fallback-eval "
                f"--proof-id {config.proof_id}`"
            ),
            "",
            "## Raw Remote Commands",
            "",
            f"- bounded replay: `{' '.join(window_command)}`",
            f"- replay status: `{' '.join(status_window_command)}`",
            f"- 1500 gate: `{' '.join(gate_command)}`",
            f"- 1500 status: `{' '.join(status_gate_command)}`",
            f"- fallback 1470 replay: `{' '.join(fallback_command)}`",
            f"- fallback 1470 status: `{' '.join(status_fallback_command)}`",
            f"- fallback eval launch: `{' '.join(fallback_eval_command)}`",
            f"- fallback eval status: `{' '.join(status_fallback_eval_command)}`",
        ]
    )


def render_checklist_markdown(config: Story29ProofConfig) -> str:
    """Render the operator checklist for one prepared Story 29 proof."""
    window_launch_root = remote_window_launch_root(config)
    fallback_launch_root = remote_fallback_launch_root(config)
    fallback_eval_output_root = remote_fallback_eval_output_root(config)
    gate_launch_root = remote_gate_launch_root(config)
    return "\n".join(
        [
            f"# {config.task_label} Proof Checklist",
            "",
            "## Preflight",
            "",
            "- [ ] Confirm Hemma repo `HEAD` matches the intended local revision before launch.",
            f"- [ ] Confirm the source launch root exists: `{config.source_launch_root}`",
            f"- [ ] Confirm the source checkpoint exists: `{config.source_checkpoint_path}`",
            (
                f"- [ ] Confirm `text_embedding_mask_policy={config.text_embedding_mask_policy}` "
                f"and `gradient_accumulation_steps={config.gradient_accumulation_steps}` "
                "are the active overrides."
            ),
            (
                f"- [ ] Confirm the bounded replay target is exactly optimizer steps "
                f"`{config.window_start_optimizer_step} -> {config.window_end_optimizer_step}`."
            ),
            (
                f"- [ ] Confirm Hemma scratch free space is at least "
                f"`{config.required_scratch_free_bytes}` bytes before launch."
            ),
            "",
            "## Window Gate",
            "",
            (
                f"- [ ] Launch the bounded replay with `pdm run {config.command_name} "
                f"launch-window --proof-id {config.proof_id}`"
            ),
            (
                f"- [ ] Inspect status with `pdm run {config.command_name} status-window "
                f"--proof-id {config.proof_id}`"
            ),
            f"- [ ] Verify the replay launch root: `{window_launch_root}`",
            (
                f"- [ ] Pass condition: detached run exits `0`, replays optimizer steps "
                f"`{config.window_start_optimizer_step} -> {config.window_end_optimizer_step}`, "
                "and does not surface a non-finite trigger."
            ),
            (
                f"- [ ] Fail condition: the run fails before step "
                f"`{config.window_end_optimizer_step}` or surfaces a new first bad "
                "tensor/gradient path."
            ),
            "",
            "## 1500 Gate",
            "",
            (
                f"- [ ] Launch only after the window gate passes: "
                f"`pdm run {config.command_name} launch-gate1500 --proof-id {config.proof_id}`"
            ),
            (
                f"- [ ] Inspect status with `pdm run {config.command_name} status-gate1500 "
                f"--proof-id {config.proof_id}`"
            ),
            f"- [ ] Verify the continuation launch root: `{gate_launch_root}`",
            (
                f"- [ ] Pass condition: detached run exits `0`, reaches optimizer step "
                f"`{config.gate_max_steps}`, and records the scheduled eval there."
            ),
            (
                f"- [ ] Fail condition: the run fails before `{config.gate_max_steps}`; if so, "
                "prepare the fallback `1470 + standalone eval` lane."
            ),
            "",
            "## Fallback 1470 Gate",
            "",
            (
                f"- [ ] Launch the bounded fallback replay with `pdm run {config.command_name} "
                f"launch-fallback1470 --proof-id {config.proof_id}`"
            ),
            (
                f"- [ ] Inspect fallback status with `pdm run {config.command_name} "
                f"status-fallback1470 --proof-id {config.proof_id}`"
            ),
            f"- [ ] Verify the fallback replay launch root: `{fallback_launch_root}`",
            (
                f"- [ ] Pass condition: detached run exits `0`, reaches optimizer step "
                f"`{config.fallback_max_steps}`, and mints a truthful durable checkpoint."
            ),
            (
                f"- [ ] Fail condition: the run fails before `{config.fallback_max_steps}`; "
                "restart remains blocked."
            ),
            "",
            "## Fallback Standalone Eval",
            "",
            (
                f"- [ ] Launch detached standalone eval only after fallback replay passes: "
                f"`pdm run {config.command_name} launch-fallback-eval --proof-id {config.proof_id}`"
            ),
            (
                f"- [ ] Inspect detached fallback eval with `pdm run {config.command_name} "
                f"status-fallback-eval --proof-id {config.proof_id}`"
            ),
            f"- [ ] Verify the fallback eval output root: `{fallback_eval_output_root}`",
            (
                "- [ ] Pass condition: detached eval exits `0` and writes a standalone "
                "`report.json` with `eval_summary`."
            ),
            "",
            "## Close-Out",
            "",
            "- [ ] Record the outcome in the training reference ledger and Story 29 docs.",
            (
                "- [ ] If the proof passes, treat `text_span_only` as the winning "
                "mitigation for the preferred gate."
            ),
            (
                "- [ ] If the proof falls back, record the `1470` checkpoint and standalone "
                "eval result before touching `T199`."
            ),
        ]
    )
