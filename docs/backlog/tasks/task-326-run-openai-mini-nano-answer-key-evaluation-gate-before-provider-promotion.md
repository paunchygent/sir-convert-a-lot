---
id: task-326-run-openai-mini-nano-answer-key-evaluation-gate-before-provider-promotion
title: Run OpenAI mini/nano answer-key evaluation gate before provider promotion
type: task
status: proposed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-318-make-task-309-eval-provider-metadata-profile-driven.md
  - docs/backlog/tasks/task-325-add-openai-responses-provider-and-hot-swappable-operator-routing-for-answer-key-completion.md
  - docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
labels:
  - answer-key-completion
  - structured-llm
  - openai
  - eval
  - model-selection
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the existing answer-key completion model-evaluation harness/corpus against
the two OpenAI model snapshots introduced by Task 325, then compare their
quality and failure behavior against the current local Qwen3.6 baseline before
any OpenAI profile can be promoted as an operator-selectable production default.

This task owns the eval run and any eval-harness modifications needed to make
the comparison provider-profile driven. Task 325 owns the provider/routing
implementation and cannot be marked done until this task completes.

## PR Scope

- Use the same versioned DigiExam answer-key evaluation corpus and scoring
  semantics used by the local model evaluations.
- Evaluate `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17` through the
  OpenAI Responses provider profile path implemented by Task 325.
- Keep model selection profile-driven. Do not add model-name conditionals to the
  evaluator, answer-key orchestration service, provider harness, or report
  writer.
- Record comparable metrics against the current local Qwen3.6 baseline,
  including correct, wrong-but-valid, manual-follow-up, invalid-schema, refusal,
  timeout, provider-failure, latency, and token-budget outcomes.
- Preserve the existing privacy posture: no raw prompts, item text, raw
  provider responses, raw provider request payloads, API keys, owner metadata,
  student data, or artifact paths in retained reports, logs, fixtures, or docs.
- Use a sanctioned OpenAI credential source only. If credentials are unavailable,
  this task remains blocked and Task 325 cannot be completed or promote an
  OpenAI default.

## Deliverables

- [ ] Eval-harness support for selecting OpenAI provider profiles by manifest or
  runtime profile ID without model-name branches.
- [ ] A sanitized eval run for `gpt-5.4-mini-2026-03-17`.
- [ ] A sanitized eval run for `gpt-5.4-nano-2026-03-17`.
- [ ] A comparison report against the current local Qwen3.6 baseline with the
  same correctness and failure categories used by local-model evaluations.
- [ ] A promotion recommendation: mini, nano, local-only, or no promotion.

## Acceptance Criteria

- [ ] Both OpenAI snapshots are evaluated against the same corpus boundary,
  expected-answer set, scoring categories, and manual-follow-up semantics as the
  local model evaluations.
- [ ] The report includes at least correct, wrong-but-valid, manual-follow-up,
  invalid-schema, refusal, timeout, provider-failure, latency, and token-budget
  counts for each OpenAI profile and the current Qwen3.6 baseline.
- [ ] The report retains provider-run metadata for provider family, provider
  profile ID, pinned model snapshot, schema version, output mode, route
  decision, settings version, code revision, and corpus revision.
- [ ] Wrong-but-valid answers remain the primary safety metric. An OpenAI
  profile with unacceptable wrong-but-valid behavior is not promoted even if it
  has fewer manual-follow-up outcomes.
- [ ] No raw prompt, item text, raw provider response, raw provider request
  payload, API key, owner metadata, student data, or artifact path appears in
  retained reports, logs, fixtures, or docs.
- [ ] If live OpenAI execution cannot run through the sanctioned credential path,
  the task records the blocker and remains incomplete; Task 325 remains blocked
  from done/promotion.

## Test Requirements

- Focused tests or proof commands showing the eval harness can select each
  OpenAI profile by profile ID and that the selected profile injects model,
  output mode, capability, `reasoning_effort=none`, text verbosity, sampling,
  timeout, and token-budget metadata without model-name branches.
- Capture/privacy checks proving retained eval evidence is metadata-only and
  excludes raw prompts, item text, raw provider payloads/responses, API keys,
  owner metadata, student data, and artifact paths.
- Comparison-report checks proving both OpenAI profiles and the local Qwen3.6
  baseline use the same scoring categories.

## Stop Conditions

- Stop if eval-harness changes would require provider-specific branches inside
  answer-key orchestration or provider result validation.
- Stop if live OpenAI execution would require writing raw API keys into docs,
  env mirrors, tests, reports, logs, or fixtures.
- Stop if the corpus or goldens differ from the local-model evaluation boundary
  without a separate governed methodology task.
- Stop before making a production-default recommendation from partial runs.

## Source Notes

- OpenAI model pages checked on 2026-05-18:
  `https://developers.openai.com/api/docs/models/gpt-5.4-mini` and
  `https://developers.openai.com/api/docs/models/gpt-5.4-nano` list the pinned
  snapshots `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`.
- Task 309 and Task 318 preserve the local-model evaluation precedent and the
  requirement that provider-run metadata be profile-driven.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
