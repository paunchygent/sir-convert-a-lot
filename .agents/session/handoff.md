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
  - `T230` is now complete as the negative bounded normalization-entry rerun
    under `task230-20260318t082049z-a1`
  - `T231` is now complete as the explicit no-winner promotion decision
  - `T232` is now complete as the lane decision to stay in mechanism
  - `T233` is now complete as the normalization-internal rerun under
    `task233-20260318t112544z-a1`
  - the first verified internal surface is now
    `talker_core.layer_16.input_layernorm.output`
  - `T234` is now complete under `task234-20260318t123644z-a1`
  - no variant stayed finite or earned promotion; the strongest `0p5` member
    shifted the pair and `line-13` `sub_talker_loss` cases to
    `talker_core.layer_15.output`, while `line-4` still first broke at
    `talker_core.layer_16.input_layernorm`
  - `T235` is now complete under `task235-20260318t140352z-a1`
  - the mixed `sub_talker_loss` result is repeatable: pair and `line-13`
    stay at `talker_core.layer_15.output`, while `line-4` stays at
    `talker_core.layer_16.input_layernorm`
  - `T236` is now complete under `task236-20260318t145434z-a1`
  - the outlier is a genuine row-local seam difference: pair and `line-13`
    stay at `talker_core.layer_15.output`, while `line-4` stays at
    `talker_core.layer_16.input_layernorm.output`
  - `T237` is now complete under `task237-20260318t154708z-a1`
  - the `1e3` fp32-output-cap winner converged pair, `line-13`, and `line-4`
    `sub_talker_loss` to `talker_core.layer_15.output`
  - `T240` is now complete under `task240-20260318t165458z-a1`
  - all three normative `sub_talker_loss` rows first broke at
    `talker_core.layer_15.output`, so the convergence class is
    `converged_layer15_output`
  - `T241` is now complete under `task241-20260318t175714z-a1`
  - all three normative `sub_talker_loss` rows still first broke at
    `talker_core.layer_15.output`, so the classification is
    `converged_layer15_output_residual`
  - `T242` is now complete as the permanent Hemma bind-root contract:
    the repo-rendered service is installed and active, `status` now proves the
    home roots are mounted onto the canonical `/srv/scratch` trees, and
    `probe` confirms Docker must use
    `/home/paunchygent/.data/sir-convert-a-lot/{build,cache}` as the
    effective bind roots
  - `T243` is now complete under `task243-20260318t190832z-a1`
  - all three normative `sub_talker_loss` rows first broke at
    `talker_core.layer_15.output`, so the classification is
    `converged_layer15_output_return`
  - `T244` is now complete under `task244-20260318t193736z-a1`
  - all three normative `sub_talker_loss` rows still first broke at
    `talker_core.layer_15.output`, so the classification is
    `converged_output_return`
  - `T245` is now the active diagnosis-only mechanism slice
  - `T245` must confirm or split the fixed winner-specific `layer15_out_0p5`
    attenuation multiply before any new stabilizer family is considered
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
  - `T230`: complete; close the diagnosed normalization-entry family negative
  - `T231`: complete; record the explicit no-winner promotion decision
  - `T232`: complete; keep Story 31 in mechanism and open `T233`
  - `T233`: complete; resolve the earliest internal surface to
    `talker_core.layer_16.input_layernorm.output`
  - `T234`: complete; close the diagnosed post-normalization output-scale
    family without promotion
  - `T235`: complete; confirm the post-`T234` disagreement is repeatable
  - `T236`: complete; classify the `line-4` disagreement as a genuine
    row-local seam difference
  - `T237`: complete; fp32-output-cap `1e3` winner converged downstream
  - `T240`: complete; confirmed `talker_core.layer_15.output` as the first
    converged downstream seam
  - `T241`: complete; the converged seam stayed at `talker_core.layer_15.output`
  - `T243`: complete; `task243-20260318t190832z-a1` kept all three normative
    `sub_talker_loss` rows at the returned `layer_15.output`
  - `T244`: complete; `task244-20260318t193736z-a1` kept all three normative
    `sub_talker_loss` rows at the emitted `layer_15.output`
  - `T245`: confirm or split the fixed winner-specific `layer15_out_0p5`
    attenuation multiply

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
1. Keep `T230` recorded as the negative bounded normalization-entry rerun
   under `task230-20260318t082049z-a1`.
1. Keep `T231` recorded as the explicit no-winner promotion decision.
1. Keep `T232` recorded as the lane decision to stay in mechanism.
1. Keep `T233` recorded as the truthful normalization-internal rerun under
   `task233-20260318t112544z-a1`.
1. Keep `T234` recorded as the no-promotion output-scale rerun under
   `task234-20260318t123644z-a1`.
1. Keep `T235` recorded as the truthful disagreement-resolution rerun under
   `task235-20260318t140352z-a1`.
1. Keep `T236` recorded as the truthful row-local classification rerun under
   `task236-20260318t145434z-a1`.
1. Keep `T243` recorded as the truthful residual/output split under
   `task243-20260318t190832z-a1`.
1. Run `T245` next as one diagnosis-only causal-confirmation slice at the
   fixed winner-specific `layer15_out_0p5` attenuation multiply.
1. Before new Hemma Qwen runs, use:
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
   and
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`.
1. Keep `T227` contingent only if a later verified trainer/runtime divergence
   appears.
1. Keep `T217` blocked until a mechanism candidate passes the local promotion
   gate.
1. Keep Story 29 and Story 30 surfaces available as historical references, not
   as the primary operator flow.
1. Record future active runs in
   `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`

## Service Image Layering Note (2026-03-18)

- A Hemma deploy attempt for the Exam.net DOCX paragraph-repair service patch
  was intentionally aborted after the root service image spent an excessive
  amount of time rebuilding the full dependency stack.
- The remote `dev-recreate` / BuildKit / `pdm sync` process chain was stopped,
  BuildKit cache was pruned, and the old live service was left healthy in
  place:
  - `sir_convert_a_lot_prod` still healthy on `470e44af...`
  - remote repo `HEAD` had already moved to `6d89e273...`
- `task-239` is now the canonical next slice for the service image redesign:
  split stable system/dependency layers from the thin app layer and stop
  installing CUDA-flavoured torch packages during the service dependency build
  only to replace them with ROCm wheels later.
- Current implementation direction for `task-239`:
  - layered root `Dockerfile`
  - filtered prod requirements export for the service image
  - canonical service-image build-contract helper that reads ROCm pins from
    `pyproject.toml`
  - thin final runtime layer that copies only the service runtime package
    surface plus `templates/`
  - root `.dockerignore` that whitelists only the service-image copy surface
    so BuildKit does not ingest large unrelated repo directories on code-only
    deploys
  - Hemma GPU runtime verification that probes the container with `python`
    directly instead of assuming `pdm` exists inside the image
  - unchanged single-service `/readyz` / revision contract
    using the canonical experiment-spec template.

## Validation State

- `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_story31_parity_probe.py -q`: passed
- `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_stability_lab.py -q`: passed
- `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_story30_backward_lineage_hooks.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_input_layernorm_internal_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_stability_lab.py -q`: passed
- `pdm run test-ml`: passed
- `pdm run typecheck-ml`: passed
- `pdm run typecheck-all`: passed
- `pdm run format-all`: passed
- `pdm run lint-fix`: passed
- `pdm run validate-tasks`: passed
- `pdm run validate-docs`: passed
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`: passed
- `pdm run coverage-gate`: passed
- `pdm run pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_service_image_build_contract.py tests/sir_convert_a_lot/test_verify_hemma_gpu_runtime.py -q`: passed
- `pdm run qwen-story31-parity-probe --help`: passed
- `pdm run qwen-story31-stability-lab --help`: passed
- `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_trace.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_post_t237_downstream_convergence_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_story31_stability_lab.py -q`: passed
- `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task240-20260318t165458z-a1 --skip-build --hook-profile talker_core_post_t237_downstream_convergence --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`: passed
- `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task233-20260318t112544z-a1 --skip-build --hook-profile talker_core_input_layernorm_internal --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`: passed
- `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task234-20260318t123644z-a1 --skip-build --hook-profile talker_core_boundary --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p75,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`: passed

The docs/index validations should be rerun after any further docs change
touching Story 31, Story 32, the live ledger, or the operator runbook.
