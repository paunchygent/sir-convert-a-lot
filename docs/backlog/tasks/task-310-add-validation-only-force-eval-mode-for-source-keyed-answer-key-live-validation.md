---
id: task-310-add-validation-only-force-eval-mode-for-source-keyed-answer-key-live-validation
title: Add validation-only force-eval mode for source-keyed answer-key live validation
type: task
status: proposed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
labels:
  - answer-key-completion
  - force-eval
  - validation-only
  - digiexam
  - service-mirror
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add an explicit validation-only force-eval mode for source-keyed DigiExam items
after Task 309's initial in-process plus service-smoke validation succeeds and
before Task 311's strict service-backed mirror.

The mode exists only to measure model behavior against items where trusted
source keys already exist. It must not become production advisory behavior, it
must not weaken source-bound answer-key precedence, and it must never expose
the source answer key to the provider request.

## PR Scope

- Add a validation-only force-eval selection path for eligible source-keyed
  choice, multiple-response, gap/open-cloze, and later matching items.
- Require an explicit validation command/flag; the default production route
  must continue to skip source-keyed items.
- Withhold source-bound answer keys from the provider prompt/payload and use
  them only in the evaluator/golden comparison stage.
- Reuse Task 309's versioned DigiExam DXE fixture corpus, item fingerprints,
  source SHA values, and expected-answer/golden manifest.
- Keep vLLM `choice` values preferred for clear bounded MCQ/MCW candidate
  selection; use JSON Schema only where the output shape requires it.
- Emit validation-only reports that separate source-keyed force-eval metrics
  from missing-key production advisory metrics.
- Preserve the no raw prompt/response artifact policy and the no source/effective
  IR mutation policy.

## Out Of Scope

- Enabling force-eval in normal production conversion requests.
- Applying force-eval provider output as answer keys.
- Running the strict auth/public-edge service mirror; that belongs to Task 311.
- Prompt-engineering around a specific failed item.

## Deliverables

- [ ] Validation-only force-eval command or runner mode.
- [ ] Item eligibility manifest fields that distinguish production advisory
  eligibility from validation-only force-eval eligibility.
- [ ] Report evaluator support for source-keyed force-eval metrics.
- [ ] Focused tests proving source keys are withheld from provider payloads and
  used only for evaluation.
- [ ] Documentation closeout linking Task 310 as the precondition for Task 311's
  strict service-backed mirror if force-eval is used there.

## Acceptance Criteria

- [ ] Force-eval cannot run unless explicitly requested by a validation command
  or validation-only flag.
- [ ] Default production advisory behavior still skips source-keyed items.
- [ ] Provider prompts/payloads never contain the trusted source answer key.
- [ ] Source IR and effective IR remain unchanged.
- [ ] Force-eval metrics are reported separately from Task 309 missing-key
  advisory metrics.
- [ ] Malformed output, unknown IDs, duplicate IDs, and wrong-but-valid answers
  are evaluated with the same strict safety semantics as Task 309.
- [ ] The mode is suitable for Task 311's service-backed mirror preflight but is
  not exposed as a public user feature.

## Test Requirements

- [ ] Unit tests cover source-keyed item selection and skip reasons.
- [ ] Provider payload tests prove answer keys are withheld.
- [ ] Evaluator tests cover correct, wrong-but-valid, manual follow-up,
  malformed, duplicate ID, unknown ID, and partial gap-answer outcomes.
- [ ] Route or runner tests prove production conversion cannot accidentally
  enable force-eval.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
