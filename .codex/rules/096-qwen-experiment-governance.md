---
trigger: always_on
rule_id: RULE-096
title: Qwen Experiment Governance
status: active
created: '2026-03-17'
updated: '2026-03-17'
owners:
  - platform
tags:
  - qwen
  - ml
  - governance
  - experiments
scope: repo
---

- Every active Qwen Qwen pilot run must belong to exactly one experiment class:
  - `provenance`
  - `mechanism`
  - `recovery`
- One run answers one primary question. If a planned run would answer more
  than one question, split it into separate runs and ledger entries.
- The single live result ledger for active Qwen Task 101 work is:
  `docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md`.
- Every future active run recorded in that ledger must declare this full state
  vector before the repo treats it as comparable evidence:
  - `experiment_class`
  - `question_answered`
  - `surface_name`
  - `code_revision`
  - `image`
  - `bundle_root`
  - `sampler_or_batching_policy`
  - `seed_or_shuffle_policy`
  - `batch_size`
  - `gradient_accumulation_steps`
  - `text_embedding_assembly_mode`
  - `text_embedding_mask_policy`
  - `stabilizer_variant`
  - `max_steps`
  - `eval_policy`
  - `input_artifact_roots`
  - `expected_promotion_target`
  - `status`
  - `result_interpretation`
- Use one-factor-at-a-time changes only inside the same lane when making
  causal claims. If code, bundle root, sampler/batching, seed/shuffle,
  assembly mode, mask policy, or stabilizer variant changed together, do not
  describe the result as isolated causal evidence.
- Use this promotion ladder:
  local gate -> short bounded fresh-start run -> longer governed proof.
- If a lane cannot answer its designated question cleanly, classify the lane as
  historical evidence only and stop using it as the active next-step surface.
- Current status vocabulary:
  - `active`
  - `legacy-readonly`
  - `deprecated`
- Current active surface matrix:
  - `qwen-historical-pilot-control`: `provenance` / `active`
  - `qwen-stability-lab`: `mechanism` / `active`
  - governed `qwen-train launch/status` fresh-start proof lane:
    `recovery` / `active but blocked until promotion`
  - `qwen-freshstart-proof`: `mechanism` / `legacy-readonly`
  - `qwen-backward-lineage`: `mechanism` / `legacy-readonly`
  - `qwen-fallback-proof`: `mechanism` / `deprecated`
  - `qwen-fallback-accumulation-proof`: `mechanism` / `deprecated`
