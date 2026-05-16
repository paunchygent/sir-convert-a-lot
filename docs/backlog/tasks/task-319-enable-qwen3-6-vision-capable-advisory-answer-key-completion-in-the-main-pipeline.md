---
id: task-319-enable-qwen3-6-vision-capable-advisory-answer-key-completion-in-the-main-pipeline
title: Enable Qwen3.6 vision-capable advisory answer-key completion in the main pipeline
type: task
status: completed
priority: high
created: '2026-05-16'
last_updated: '2026-05-16'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/runbooks/runbook-answer-key-local-model-operator-guide.md
labels:
  - answer-key-completion
  - qwen
  - llama-cpp
  - vision
  - digiexam
  - structured-output
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Enable Qwen3.6 vision-capable advisory answer-key completion in the main
`digiexam_dxe -> examnet_migration_bundle` pipeline.

Task 309 proved the eval-only vision path over the versioned DigiExam corpus:
the `qwen36-llama-cpp` profile can export supported embedded PNG/JPEG assets,
send llama.cpp multimodal `image_url` parts, and score 44 items instead of the
text-only 42. Qwen3.6 is the current local model of choice right now, but its
output remains guarded advisory because the final Task 309 result still had 3
wrong-but-valid suggestions.

This task owns moving reusable Task 309 vision behavior into production-owned
domain/infrastructure code while preserving source-bound parser provenance,
teacher review, and default source-evidence-only behavior.

## PR Scope

- Move reusable vision asset handling out of Task 309 devops code into
  production-owned code.
- Validate embedded images before provider use:
  - PNG/JPEG only;
  - base64 decodes successfully;
  - byte length and SHA-256 match IR metadata;
  - asset references resolve to actual embedded assets.
- Build provider-facing image files under the job artifact working directory
  with stable relative paths suitable for llama.cpp `image_url` use.
- Add provider config support for multimodal vision capability and Qwen3.6
  runtime settings needed by the main service path.
- Wire advisory answer-key completion so image-bearing items are eligible only
  when the selected local provider supports vision.
- Keep reusable provider/live-validation files source-neutral; DigiExam-specific
  corpus, preview, evaluation, and runner files use the `digiexam_` prefix.
- Keep text-only providers, disabled structured-LLM config, default
  `source_evidence_only`, and reviewed-apply mode behavior unchanged.
- Keep advisory suggestions out of accepted answer keys unless a teacher review
  overlay or later governed decision authorizes application.

## Deliverables

- [x] Production-owned vision asset export/candidate-planner helper.
- [x] Structured provider config fields for multimodal vision capability and
  Qwen3.6 request temperature.
- [x] Main advisory completion runtime wired to pass vision-capable requests
  only when provider capability allows it.
- [x] Route and domain tests for image-bearing advisory items.
- [x] Docs closeout in this task, Task 309, Task 317, and the local model
  runbook/reference.

## Acceptance Criteria

- [x] Qwen3.6 is documented as the current local model of choice, with guarded
  advisory status preserved.
- [x] Image-bearing DigiExam items can produce advisory completion requests
  when all referenced embedded assets are supported and the configured local
  provider supports multimodal vision.
- [x] Text-only providers still mark embedded-asset items as unsupported and do
  not call the provider for those rows.
- [x] Invalid assets or unresolved references do not call the provider and
  produce manual follow-up rather than unsafe provider input.
- [x] Normal retained completion reports contain no raw/base64 images, raw
  prompts, raw provider responses, full exam text, student data, or owner
  metadata.
- [x] Source IR, effective IR, PDF, and QTI artifacts are not mutated by
  advisory suggestions.
- [x] Default `source_evidence_only` jobs still make no structured-provider
  calls.

## Test Requirements

- [x] Config tests cover `supports_multimodal_vision` and provider temperature.
- [x] Candidate-planning tests cover image-bearing items with and without
  vision support.
- [x] Asset-validation tests cover unsupported media, invalid base64, SHA
  mismatch, missing payload, and broken references.
- [x] Route tests prove advisory completion builds a report for an
  image-bearing DigiExam item.
- [x] Privacy tests prove no raw/base64 images, raw prompts, or raw provider
  responses are retained in normal reports.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Closeout

Implemented Qwen3.6 vision-capable advisory completion in the main DigiExam
pipeline. Reusable provider profile settings now live in
`scripts/sir_convert_a_lot/infrastructure/answer_key_local_model_profiles.py`,
with Qwen3.6 carrying a 32k context window, 4k output budget, 0.15
temperature, and multimodal vision capability. Production DigiExam vision asset
handling now validates supported PNG/JPEG embedded assets and writes
provider-facing files under the job artifact working directory without
retaining raw/base64 payloads in normal reports.

The source split is explicit: provider-only runtime files keep the
`answer_key_` prefix, while DigiExam-specific live-validation corpus,
request-preview, evaluation, and runner files use the `digiexam_` prefix.
`pdm run answer-key-live-validation` is now a source-routed command with the
initial `digiexam` lane.

Validation:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_live_validation_manifest.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py tests/sir_convert_a_lot/test_structured_llm_provider_composition.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_advisory_completion_allows_valid_embedded_image_item tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_advisory_completion_report_does_not_mutate_artifacts tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_default_artifact_route_does_not_call_structured_llm`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `pdm run answer-key-live-validation digiexam status --output-root inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe`
