# Session Handoff

## Current State

- Active epic: Epic 08 Qwen Swedish language expansion on Hemma.
- Active governance story:
  `docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md`.
- Active mechanism story:
  `docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md`.
- New governing rule:
  `.agents/rules/096-qwen-experiment-governance.md`.
- Single live result ledger for active Qwen Task 101 work:
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.

Story 32 is now the operator-facing mental model:

- `provenance`
  - active surface: `qwen-t221-historical-control`
  - latest resolved result: `T221` negative recreated-control evidence
- `mechanism`
  - active surface: `qwen-story31-stability-lab`
  - next bounded slice: `T219`
- `recovery`
  - active surface: governed `qwen-train launch/status` fresh-start proof
  - current status: blocked at `T217` until a mechanism candidate is promoted

Historical surfaces are intentionally preserved because they tell the causal
story of how the lane evolved, but they are no longer the active next-step
workflow:

- `qwen-story30-freshstart-proof`: `legacy-readonly`
- `qwen-story30-backward-lineage`: `legacy-readonly`
- `qwen-t197-proof`: `deprecated` for new work, preserved as Story 29
  evidence
- `qwen-t198-proof`: `deprecated` for new work, preserved as Story 29
  evidence

Story 28 remains operating policy:

- `RULE-095` keeps the Qwen package split and `400` LoC hot-path cap.
- `RULE-096` now governs experiment taxonomy, one-question-per-run discipline,
  one-factor-at-a-time causal interpretation, the promotion ladder, and the
  single-ledger contract.

## What Landed

- Story 32 landed as a short docs/control-plane consolidation slice.
- New backlog package landed:
  - `docs/backlog/tasks/task-222-define-the-qwen-experiment-taxonomy-surface-status-matrix-and-short-freeze-rule.md`
  - `docs/backlog/tasks/task-223-publish-the-canonical-qwen-experiment-spec-and-single-ledger-update-contract.md`
  - `docs/backlog/tasks/task-224-reroute-qwen-operator-docs-through-the-active-surface-matrix-and-demote-legacy-proof-workflows.md`
- Epic 08, Story 31, `current.md`, the Qwen runbook, the Qwen skill, and the
  Task 101 ledger were all rerouted through the same provenance /
  mechanism / recovery matrix.
- The live ledger now contains:
  - one active surface matrix
  - one canonical Qwen Experiment Spec contract
  - one reusable per-run ledger entry template
- Existing CLI surfaces remain callable in this slice; the change is
  governance and docs alignment, not command removal.

## Latest Task 101 Truth

- Preserved-lane historical truth still matters:
  - `state-step-00001236` remains the canonical held-out eval baseline
  - `state-step-00001238` remains the canonical no-projection RCA checkpoint
  - `state-step-00001406` remains the canonical later RCA checkpoint for the
    preserved lane
  - Story 29 and Story 30 remain important historical evidence and design
    selection context
- `T206` landed the explicit token-span position-mask correction and the
  offline audit proved zero leaked positions, zero leaked token ids, and zero
  leaked non-finite rows in the audited prepared bundle.
- `T206` still failed as a final preserved-lane proof at optimizer step `1407`,
  which closed Story 29 as bounded negative evidence for that lane.
- Story 30 selected Candidate 1 as the preferred fresh-start design lane, with
  Candidate 3 retained as contingency.
- `T211-T214` localized the fresh-start failure family into the talker core,
  with the dominant pair seam narrowed to
  `talker_core.layer_16.mlp.gated_product`.
- Story 31 exploration then produced:
  - `T215`: local gate and first matrix surface
  - `T216`: first bounded stabilization surface
  - `T218`: negative exploration evidence
  - `T219`: next mechanism-owned slice, not yet executed
- `T220` delivered the exact-control runtime surface but did not answer the
  historical-control question because the run drifted from the documented
  March 13 contract.
- `T221` then recreated the documented historical contract and closed as the
  strongest current provenance result:
  - run id: `task221-20260317t193125z-a1`
  - failed at optimizer step `1` / train iteration `4`
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - no checkpoint minted
  - no eval executed
  - interpretation: stronger than `T220`, but still not byte-for-byte March 13
    attribution because the run uses the current trainer/runtime posture

## Operator Rules

- Use the Task 101 reference ledger as the only live ledger for active Qwen
  experiment work.
- Every future active run must declare the full Story 32 experiment spec before
  it is treated as comparable evidence:
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
- Do not make causal claims across runs that changed code, bundle root,
  sampler, seed/shuffle, assembly mode, mask policy, or stabilizer together.
- Use the promotion ladder:
  local gate -> short bounded fresh-start run -> longer governed proof.
- If a lane stops answering its designated question cleanly, keep it as
  historical evidence only and stop using it as the active next-step surface.

## Immediate Next Step

1. Keep `T221` classified as provenance evidence only.
1. Resume Story 31 through `T219` as the next mechanism-owned bounded slice.
1. Keep `T217` blocked until a mechanism candidate passes the local promotion
   gate.
1. Keep Story 29 and Story 30 surfaces available as historical references, not
   as the primary operator flow.
1. Record future active runs in
   `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`
   using the canonical experiment-spec template.

## Validation State

- `pdm run validate-tasks`: passed
- `pdm run validate-docs`: passed
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`: passed

All three validations should be rerun after any further docs change touching
Story 31, Story 32, the live ledger, or the operator runbook.
