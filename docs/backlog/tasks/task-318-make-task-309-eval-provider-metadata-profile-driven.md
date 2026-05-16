---
id: task-318-make-task-309-eval-provider-metadata-profile-driven
title: Make Task 309 eval provider metadata profile-driven
type: task
status: completed
priority: high
created: '2026-05-16'
last_updated: '2026-05-16'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-312-make-answer-key-candidate-planning-provider-protocol-driven.md
  - docs/backlog/tasks/task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/runbooks/runbook-answer-key-local-model-operator-guide.md
labels:
  - answer-key-completion
  - live-validation
  - structured-output
  - provider-policy
  - llama-cpp
  - vllm
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make Task 309 advisory-corpus evaluation artifacts report the actual provider
profile and model-runtime settings used for the retained reports, without
hardcoding Granite, Qwen, llama.cpp, vLLM, or any future model name in the
evaluator.

The trigger is the 2026-05-16 Qwen3.6 Hemma validation where
`evaluate-advisory-corpus` correctly scored the retained Qwen/llama.cpp reports
but still wrote `model_settings_json` for the older Granite/vLLM defaults. That
metadata drift is not a scoring bug, but it is an evidence-chain bug: future
model comparisons need the evaluation packet to say exactly which profile,
runtime, output-mode policy, capabilities, sampling settings, token budgets,
and vision media path produced the reports being adjudicated.

## PR Scope

- Introduce a provider-run metadata contract for Task 309 live validation
  artifacts. The contract must be profile-driven and serializable, not a
  helper that reconstructs one provider from constants.
- Extend the Task 309 provider profile/defaults surface as needed so one
  profile object can describe:
  - provider profile name;
  - provider URL and expected model id;
  - endpoint kind and provider runtime;
  - default output mode and item-type output-mode policy;
  - provider capabilities, including JSON Schema, GBNF, vLLM structured
    choice, and multimodal vision support;
  - temperature, max output tokens, context window, and model-specific request
    settings that are injected when the selected profile changes;
  - launch/runtime settings that matter for evidence, including
    `--media-path` / vision media path when present.
- Persist that provider-run metadata from `run-advisory-corpus` and make
  `evaluate-advisory-corpus` consume it from the adjacent run artifact or an
  explicit CLI argument. Evaluation must not silently invent metadata when the
  run artifact is missing.
- Preserve backward compatibility for existing consumers of
  `model_settings_json` if necessary, but populate it from the real provider-run
  metadata. Prefer adding a clearer field such as
  `provider_run_metadata_json`.
- Keep the design SOLID: model-specific settings belong in profile/default
  value objects or strategy/policy classes, not in evaluator `if model == ...`
  branches.
- Keep Task 317's broader domain-classification cleanup separate. This task is
  only about live-validation provider/runtime evidence alignment.
- Do not rerun model quality experiments as part of implementation unless the
  changed metadata path needs a smoke against retained reports.

## Deliverables

- [x] Task 309 provider-run metadata contract/value object.
- [x] Profile-driven metadata generation from the selected provider profile,
  runtime, output mode, capabilities, sampling settings, max tokens, context
  window, and vision media path.
- [x] `run-advisory-corpus` writes the metadata beside the retained run report.
- [x] `evaluate-advisory-corpus` carries the same metadata into JSON and
  Markdown evaluation artifacts without hardcoded provider defaults.
- [x] Tests proving Qwen/llama.cpp evaluation cannot report Granite/vLLM
  metadata, and Granite/vLLM evaluation still reports Granite only when that
  profile is selected.
- [x] Runbook/reference note explaining that model comparison evidence is
  artifact-driven from provider-run metadata.

## Acceptance Criteria

- [x] The evaluator contains no model-name or provider-name branching for
  Granite, Qwen, Devstral, llama.cpp, vLLM, or future model families.
- [x] Adding or switching a model changes one provider profile/default object
  and automatically changes launch, request, run-report, and evaluation
  metadata.
- [x] Evaluation artifacts include provider profile, provider URL, expected
  model id, endpoint kind, provider runtime, output mode policy, capabilities,
  temperature, max output tokens, context window, and vision media path when
  applicable.
- [x] If evaluation is run against reports without provider-run metadata, the
  artifact says metadata is unavailable or the CLI blocks with an explicit
  operator-facing error; it must not fall back to Granite or any other default.
- [x] Retained reports still avoid raw prompts, raw provider responses, student
  data, owner metadata, and raw full-exam content outside existing
  validation-only artifact rules.
- [x] The 2026-05-16 Qwen3.6 retained reports can be re-evaluated cheaply
  without another full model run and produce metadata naming
  `qwen36-llama-cpp`, `qwen3.6-27b-q6k`, `llama-cpp-json-schema`, JSON Schema
  output mode, multimodal support, and the configured `vision-assets` media
  path.
- [x] The implementation stays within the provider-harness boundary and does
  not couple evaluation to the DigiExam parser, renderer, or source-specific
  item adapters.

## Closeout

Implemented a profile-driven Task 309 provider-run metadata contract in
`scripts/sir_convert_a_lot/devops/task309_provider_run_metadata.py`.
`run-advisory-corpus` now writes the selected provider profile/runtime
metadata into `in-process-advisory-corpus-run.json`, and
`evaluate-advisory-corpus` carries that artifact-sourced metadata into both
`provider_run_metadata_json` and the backward-compatible `model_settings_json`
field. Legacy Task 309 run reports without the new metadata are upgraded only
when their recorded model, URL, and runtime match a configured provider profile;
otherwise the evaluation records explicit unavailable metadata instead of
falling back to Granite or any other default.

Validation:

- `pdm run pytest-root tests/sir_convert_a_lot/test_task309_answer_key_live_validation_manifest.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task309_answer_key_live_validation_manifest.py tests/sir_convert_a_lot/test_structured_llm_provider_harness.py tests/sir_convert_a_lot/test_run_hemma_wrapper.py tests/sir_convert_a_lot/test_hemma_server_command_guards.py`
- `pdm run typecheck-all`

## Design Notes

Prefer a small immutable metadata value object built from the existing provider
profile/defaults and any launch/runtime additions. A clean shape is:

```text
Task309ProviderRunMetadata
  profile_name
  provider_url
  expected_model_id
  endpoint_kind
  provider_runtime
  output_mode_policy
  capabilities
  request_settings
  launch_settings
  artifact_paths
```

`run-advisory-corpus` should construct this once from injected profile/default
objects and write it into the run report. `evaluate-advisory-corpus` should
read it from the run report or explicit metadata path. The evaluator's job is
adjudication, not provider reconstruction.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
