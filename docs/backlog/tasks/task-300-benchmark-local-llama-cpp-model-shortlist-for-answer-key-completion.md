---
id: task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion
title: Benchmark local model shortlist for answer-key completion
type: task
status: proposed
priority: high
created: '2026-05-14'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
labels:
  - llama-cpp
  - gguf
  - benchmark
  - answer-key-completion
  - structured-output
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the comparative local model benchmark harness for the answer-key
completion shortlist after the full application path is working and deployed.
The benchmark matrix compares the settled vLLM Granite FP8 interim provider
against the GGUF shortlist on real teacher/DigiExam items.

Task 309 is the first live Granite/vLLM validation precursor. Do not use this
task for a Granite-only production-path validation run, and do not start the
model bake-off until Task 309 has reported the current provider's correctness,
wrong-but-valid behavior, and failure paths on the versioned DigiExam DXE
fixture corpus.

## PR Scope

- Build a DI-backed benchmark harness with clear domain/application/
  infrastructure boundaries.
- Load a real-data corpus of classic multiple choice, multiple response,
  matching, and open cloze/gap-fill items with expected answer keys. Reuse the
  Task 309 versioned fixture/golden surfaces where they remain valid, but keep
  this task's model-comparison corpus decision explicit.
- Run each candidate through `llama.cpp` constrained decoding only: GBNF or JSON
  Schema restrictions, no relaxed normal-prompting fallback.
- Run the settled vLLM Granite FP8 provider through vLLM `structured_outputs`
  constraints, preferring `choice` values for MCQ/MCW items with clear bounded
  candidate selection and using JSON Schema/grammar modes only where the
  provider harness proves support.
- Require non-thinking/direct-output mode where model families support thinking
  traces, especially Qwen3.5 candidates.
- Evaluate structured call success, backend-valid decision rate, correctness,
  wrong-but-valid rate, manual-follow-up rate, item-type breakdowns, latency,
  tokens/sec, and memory footprint.
- Emit deterministic JSON report plus Markdown summary.

Mandatory first-pass candidates:

| Model | Quant | Required role |
|---|---|---|
| `ibm-granite/granite-4.1-8b-fp8` on vLLM | `FP8` | Settled interim provider benchmark baseline |
| `unsloth/Qwen3.5-4B-GGUF` | `UD-Q6_K_XL` | Default-primary candidate |
| `unsloth/gemma-4-E4B-it-GGUF` | `Q6_K` | Alternate-primary candidate |
| `unsloth/granite-4.1-8b-GGUF` | `Q6_K` | Tool-call compliance comparator |
| `unsloth/Qwen3.5-9B-GGUF` | `Q6_K` | Quality fallback candidate |
| `unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF` | `UD-Q6_K_XL` | Edge/agentic comparison candidate |

## Deliverables

- [ ] Domain models for benchmark candidates, quant profiles, item fixtures,
  structured decisions, validation outcomes, and benchmark reports.
- [ ] Application services for matrix planning, per-item execution,
  correctness evaluation, and report aggregation.
- [ ] Infrastructure adapters for `llama.cpp` server/process lifecycle and
  structured provider requests.
- [ ] Dishka providers for runtime profiles, corpus loaders, report sinks,
  clocks/IDs, and provider adapters where composition benefits from DI.
- [ ] Deterministic JSON and Markdown report outputs.

## Acceptance Criteria

- [ ] Every candidate is evaluated with grammar/schema-constrained output only.
- [ ] vLLM Granite FP8 is evaluated with vLLM `structured_outputs` constraints
  and compared against the GGUF candidates.
- [ ] No test path accepts malformed JSON, parser repair, rationale text, or
  "use JSON" fallback output as success.
- [ ] Results report wrong-but-valid answers as the primary safety metric.
- [ ] The matrix is not run as a model bake-off until the full app path is
  working and deployed and Task 309 has completed its live Granite/vLLM
  validation.
- [ ] Item-type breakdowns distinguish classic choice, multiple response,
  matching, and open cloze/gap-fill.
- [ ] The report can recommend no model if all candidates exceed the
  wrong-but-valid risk threshold.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
