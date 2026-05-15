---
id: task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion
title: Run service-backed auth-public-edge mirror validation for answer-key completion
type: task
status: proposed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-310-add-validation-only-force-eval-mode-for-source-keyed-answer-key-live-validation.md
  - docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
  - docs/runbooks/runbook-hemma-service-ops.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
labels:
  - answer-key-completion
  - service-backed
  - auth-public-edge
  - hemma
  - live-validation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the strict service-backed mirror validation for answer-key completion after
Task 309's initial Hemma in-process plus service-smoke validation succeeds and
after Task 310 defines any needed validation-only force-eval mode.

Unlike Task 309's first pass, this task intentionally includes deployed service
behavior, authentication, public-edge readiness, provider reachability from the
running app, and operator/user-facing alpha-readiness concerns. The goal is to
prove the same answer-key safety properties through the real service path, not
to compare model candidates.

## PR Scope

- Use the persistent Granite/vLLM localhost-only provider established by Task
  309 unless a governed operator decision changes the provider lane.
- Run the versioned DigiExam DXE fixture corpus through the deployed service
  path rather than the in-process job executor.
- Include authenticated service access and public-edge readiness checks needed
  for real alpha testing.
- If Task 310 is complete, run validation-only force-eval over source-keyed
  items as a preflight or separate report before the production/auth-edge mirror
  execution.
- Mirror Task 309's report metrics: valid suggestion, manual follow-up,
  wrong-but-valid answer, unknown IDs, duplicate IDs, partial gap answers,
  latency, tokens/sec, backend failure code, and resource state.
- Compare service-backed output against Task 309's in-process baseline and
  explain any service-path differences.
- Keep generated reports outside git and promote only sanitized summaries into
  governed docs.

## Out Of Scope

- Model bake-off or GGUF candidate comparison.
- Replacing the Task 309 persistent Granite/vLLM provider with a different
  model or runtime.
- Prompt-engineering around a specific failed item.
- Weakening auth/public-edge policy to make validation easier.

## Deliverables

- [ ] Strict service-backed launch/status command surface.
- [ ] Auth/public-edge readiness preflight report.
- [ ] Service-backed full-corpus mirror validation JSON report and Markdown
  summary retained outside git.
- [ ] Optional validation-only force-eval report when Task 310 is complete.
- [ ] Comparison summary against Task 309's in-process baseline.
- [ ] Alpha-readiness recommendation for persistent live testing against real
  test users at work.

## Acceptance Criteria

- [ ] The validation runs through the deployed service path, not the in-process
  executor.
- [ ] Authenticated access and public-edge readiness are explicitly proven or
  the task records a blocking failure.
- [ ] The persistent Granite/vLLM provider is reachable only through the
  intended service/local-provider path and is not publicly exposed.
- [ ] Reports retain zero raw prompts and zero raw provider responses.
- [ ] Source IR and effective IR mutation semantics match Task 309 and Task
  306 contracts.
- [ ] Wrong-but-valid remains the primary safety metric; manual follow-up is
  acceptable, plausible wrong keys are not.
- [ ] Unknown IDs and duplicate IDs are zero for any mirror-success claim.
- [ ] Service-backed differences from the in-process baseline are explained
  before any alpha-readiness recommendation.

## Test Requirements

- [ ] Service preflight checks cover deployed app health, provider reachability,
  auth/public-edge readiness, and request logging posture.
- [ ] Mirror runner tests or dry-run checks prove it cannot silently fall back
  to in-process execution.
- [ ] Report comparison tests cover in-process baseline versus service-backed
  mirror differences.
- [ ] Access-policy tests or probes prove public/auth behavior matches the
  governed route policy.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
