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
  - `T225` complete: exact parity contract defined
  - `T226` complete: committed parity-probe surface delivered
  - `T219` is now recorded as completed negative evidence without promotion
  - `T228` is now complete as the ranked closure of `task219-20260317t180700z-a1`
  - `T229` is now complete as the narrowed rerun under
    `task229-20260318t064712z-a1`
  - the target `sub_talker_loss` family localizes to
    `talker_core.layer_16.input_layernorm`
  - `T230` is now the active bounded normalization-entry micro-family slice
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
- `T226` now lands the committed local parity-probe surface:
  - `pdm run qwen-story31-parity-probe run`
  - writes `current-path.json`, `intended-path.json`, `results.json`, and
    `results.md` under `build/verification/qwen-story31-parity-probe/`
  - compares the real `execute_train_iteration` window against the
    reconstructed shared-forward optimizer-boundary window on the exact `T225`
    microbatch family
- New contingent follow-on package now exists for the case where `T219` closes
  negative, and `T219` is now backfilled as already failed:
  - `T228`: complete; close the failed handoff family with one ranked matrix
  - `T229`: complete; localize the shifted seam to one earliest sub-boundary
  - `T230`: test the diagnosed normalization-entry micro-family only
  - `T231`: freeze the bounded promotion contract before any governed proof
  - `T232`: make one Story 31 lane decision from the bounded promotion result

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
  - `T225`: completed parity contract after `T221`
  - `T226`: committed local parity-probe surface now implemented
  - `T227`: next mechanism remediation / decision task after the live parity
    result is captured
  - `T219`: now backfilled as negative bounded stabilizer evidence
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
1. Treat the live in-image `T226` result under
   `task226-20260317t224307Z` as the current mechanism truth:
   `first_divergence_classification = no_meaningful_divergence_found`.
1. Keep `T219` recorded as negative bounded evidence without promotion.
1. Keep `T228` complete as the ranked closure of `task219-20260317t180700z-a1`.
1. Keep `T229` recorded as the truthful narrowed rerun under
   `task229-20260318t064712z-a1`.
1. Run `T230` next as the bounded pre-`input_layernorm`
   normalization-entry micro-family:
   ranked `T219` baseline plus the `1e3` and `1e2` entry-rescale variants.
1. Keep `T227` contingent only if a later verified trainer/runtime divergence
   appears.
1. Keep `T217` blocked until a mechanism candidate passes the local promotion
   gate and `T231` freezes the bounded promotion contract.
1. Keep Story 29 and Story 30 surfaces available as historical references, not
   as the primary operator flow.
1. Record future active runs in
   `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`
   using the canonical experiment-spec template.

## Validation State

- `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_story31_parity_probe.py -q`: passed
- `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_stability_lab.py -q`: passed
- `pdm run test-ml`: passed
- `pdm run typecheck-ml`: passed
- `pdm run validate-tasks`: passed
- `pdm run validate-docs`: passed
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`: passed
- `pdm run qwen-story31-parity-probe --help`: passed
- `pdm run qwen-story31-stability-lab --help`: passed
- `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task229-20260318t064712z-a1 --skip-build --hook-profile talker_core_handoff_sub_boundary --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`: blocked because the remote Hemma checkout still exposes the older `backward_lineage_probe.py` parser

The docs/index validations should be rerun after any further docs change
touching Story 31, Story 32, the live ledger, or the operator runbook.
