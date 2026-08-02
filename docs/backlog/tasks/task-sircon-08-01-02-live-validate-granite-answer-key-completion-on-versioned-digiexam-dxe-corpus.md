---
type: task
id: TASK-SIRCON-08-01-02
title: Live-validate Granite answer-key completion on versioned DigiExam DXE corpus
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-08-01
task_kind: story
acceptance_criteria:
- The validation corpus uses only the versioned pure DigiExam DXE fixture set at `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/`.
- The moved raw `.dxe` files are committed as the versioned fixture corpus; manifest-only
  validation is not an acceptable substitute.
- Every scored item has a teacher-verified golden; schema success without a golden
  is reported separately and is not counted as correctness.
- Multiple-choice and multiple-response requests use vLLM `choice` values whenever
  candidate selection is clear and bounded.
- Hemma preflight proves remote revision, ROCm/GPU state, scratch-backed cache path,
  port `8017`, vLLM `/v1/models`, disabled request logging, localhost-only exposure,
  and no CPU fallback.
- Long-run execution uses a committed detached runner/status surface and retains structured
  reports outside git.
- The persistent Granite/vLLM container is left running after validation, with status,
  hardening evidence, and explicit stop instructions documented for later operator
  use.
- The full corpus validation runs in-process first, and a small deployed service-backed
  smoke proves the service path without making auth/public-edge readiness a first-pass
  variable.
- A successful first pass produces or updates the follow-up plan for a strict service-backed
  mirror validation where auth/public-edge readiness is intentionally included.
- Task 309's initial run does not use force-eval over source-keyed items; any force-eval
  mode is reserved for the later service-backed mirror validation and must be explicit.
- Detached resource monitoring runs alongside the live validation and is linked from
  the retained report.
- Advisory mode produces no source IR mutation and no effective IR mutation.
- Retained artifacts contain zero raw prompts and zero raw provider responses.
- Malformed output is never counted as success.
- Unknown IDs and duplicate IDs are counted explicitly and must be zero for promotion.
- Wrong-but-valid answers are the primary safety metric; promotion should require
  zero wrong-but-valid answers unless a later governed decision accepts a narrower
  risk posture.
- Manual follow-up is acceptable and safer than plausible wrong answer-key completion.
- Persistent failure paths are documented across the run without item-specific prompt
  tweaking. Any retry policy must be generalized by item type or failure class in
  a later governed task.
- The reviewed-apply probe proves apply mode does not call the provider and writes
  only effective answer-key provenance and candidate lineage.
retired_ids:
- task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Run the first live validation of the completed structured-provider and
answer-key completion path against the real Hemma Granite/vLLM stack.

This is not the Task 300 model bake-off. Task 300 remains deferred until the
full application path is working and deployed. This task validates whether the
current interim provider can safely support the production advisory contract
over a versioned pure DigiExam `.dxe` corpus.

The starting corpus is the local DigiExam export package:

```text
inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/
```

This task owns the explicit retention decision that supersedes Task 281 for
this one corpus only: keep those pure `.dxe` exports in a versioned DigiExam
DXE fixture location, derive item fingerprints and source SHA values, and keep
all ignored/private or non-DigiExam corpus material out of this validation.
The moved `.dxe` files themselves are committed as the governed fixture corpus;
this is not a manifest-only promotion.

The first validation pass runs the full corpus through the in-process
production job path on Hemma, plus a small deployed service-backed smoke. If
that initial pass succeeds, the required follow-up is a strictly service-backed
mirror validation with auth/public-edge readiness intentionally in scope. Task
310 owns the optional validation-only force-eval mode over source-keyed items;
Task 311 owns the strict production service-backed mirror.

### PR Scope

- Move the OneDrive DigiExam `.dxe` exports into a versioned fixture root such
  as `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/`.
- Freeze a validation-corpus manifest for the moved corpus with, at minimum:
  source SHA-256, item fingerprint, item type, answer-key provenance state,
  live-validation eligibility, skip reason, embedded-asset presence, and source
  file binding.
- Keep private/ignored or non-promoted corpus material optional and excluded
  from the required live-validation manifest.
- Commit the moved raw `.dxe` fixture files after the move. The metadata scan
  records retention evidence and flags any repo-nonnegotiable secret/student
  PII concern; it is not a default reason to fall back to manifest-only
  validation.
- Create the teacher-verified expected-answer manifest for every item selected
  for scoring. For straightforward grade 7-9 multiple-choice,
  multiple-response, and gap/open-cloze items, the implementer is responsible
  for deriving the expected answers from the fixture content. Surface only
  genuinely ambiguous, difficult, or hard-to-understand cases for user
  adjudication.
- Do not use the model under validation to create or correct goldens.
- Prefer vLLM `structured_outputs.choice` values for all multiple-choice or
  multiple-response items where candidate selection can be represented as a
  clear bounded value. This avoids asking the model to generate a JSON wrapper
  and reduces the output failure surface.
- Still run provider microprobes for `choice`, JSON Schema choice object, and
  JSON Schema gap-fill object so the harness capability surface is proven.
- Add a committed detached runner/status surface before the long Hemma run.
  The surface must use named wrappers, retain JSON/Markdown reports outside
  git, and record runtime lane, repo revision, manifest SHA, and GPU state.
- Run Hemma preflight through the governed runtime/runbook lane: remote repo
  revision, `rocminfo`, `rocm-smi`, scratch/cache path, port `8017`, vLLM
  `/v1/models`, request logging disabled, no public exposure, and no CPU
  fallback.
- Start or reuse a named persistent Granite/vLLM container as the local
  provider. It must bind only to localhost on port `8017`, disable request
  logging, record image/model/cache/revision state, and remain running after
  validation until the operator explicitly asks for stop or cleanup.
- Run a detached lightweight resource monitor beside the validation using the
  same committed detached monitor pattern already used for Hemma runtime work.
- Execute the full-corpus production advisory path in-process on Hemma over all
  eligible DXE items with `local_llm_suggest_missing_machine_marked`, then run
  a small deployed service-backed smoke against the same provider.
- Evaluate reports against goldens for valid suggestion, manual follow-up,
  wrong-but-valid answer, unknown IDs, duplicate IDs, partial gap answers,
  latency, tokens/sec, and backend failure code.
- After advisory validation, run a small reviewed-apply probe using submitted
  overlay data from known valid candidates. The apply probe must prove Task
  306's contract again: apply mode does not call the provider and writes only
  effective provenance and lineage.
- If the initial in-process plus service-smoke validation succeeds, record the
  next governed follow-up as a strictly service-backed mirror run with
  auth/public-edge readiness in scope. That follow-up may add a validation-only
  force-eval mode over source-keyed items before the production/auth-edge
  mirror run; Task 309's initial advisory run must not use force-eval. Task
  310 and Task 311 are the governed follow-up scaffolds.

### Out Of Scope

- Running a comparative GGUF/vLLM model bake-off.
- Expanding the corpus beyond the pure DigiExam `.dxe` exports named above.
- Prompt-engineering around one-off difficult items or tailoring instructions
  to a specific failed question.
- Treating malformed provider output, parser repair, or plausible-but-wrong
  keys as success.
- Sending raw full exams, result PDFs, student data, owner metadata, artifact
  paths, or raw prompts/responses to retained reports.
- Stopping or removing the persistent Granite/vLLM local-provider container as
  normal Task 309 closeout.
- Running validation-only force-eval during the initial Task 309 advisory run.
- Running the strict auth/public-edge service-backed mirror before the initial
  in-process plus service-smoke validation has succeeded.

### Deliverables

- [x] Versioned DigiExam DXE fixture root containing the promoted OneDrive
  `.dxe` exports as tracked fixtures and an explicit retention note.
- [x] Validation-corpus manifest with source SHA, item fingerprints, item type,
  eligibility, skip reason, and source binding for every item.
- [x] Teacher-verified expected-answer manifest for every scored eligible item,
  with an adjudication list for only genuinely ambiguous cases. A tracked
  expected-answer manifest now covers all 42 eligible items.
- [x] Committed detached launch/status command surface for the Hemma live run.
- [x] Persistent Granite/vLLM provider launch/status surface for later
  deployed-app/live-user testing. Live Hemma evidence that the container is
  still running remains part of the live execution pass.
- [x] Detached resource-monitor launch/status/summary artifacts for the live
  validation window.
- [x] Provider microprobe report covering vLLM `choice`, JSON Schema choice
  object, and JSON Schema gap-fill object.
- [x] In-process full-corpus advisory live-validation JSON report and Markdown
  summary retained outside git with manifest/revision/runtime provenance.
- [ ] Small deployed service-backed smoke report against the same persistent
  Granite/vLLM provider.
- [ ] Reviewed-apply probe report proving no provider call in apply mode and
  effective-only provenance/lineage changes.
- [x] Follow-up gate recorded for a strictly service-backed mirror validation
  with auth/public-edge readiness and validation-only force-eval policy.
- [x] Concise docs closeout in this task and the local-model reference with the
  result, failure-path summary, and next recommended action.

### Acceptance Criteria

- [ ] The validation corpus uses only the versioned pure DigiExam DXE fixture
  set at
  `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/`.
- [ ] The moved raw `.dxe` files are committed as the versioned fixture corpus;
  manifest-only validation is not an acceptable substitute.
- [ ] Every scored item has a teacher-verified golden; schema success without a
  golden is reported separately and is not counted as correctness.
- [ ] Multiple-choice and multiple-response requests use vLLM `choice` values
  whenever candidate selection is clear and bounded.
- [x] Hemma preflight proves remote revision, ROCm/GPU state, scratch-backed
  cache path, port `8017`, vLLM `/v1/models`, disabled request logging,
  localhost-only exposure, and no CPU fallback.
- [x] Long-run execution uses a committed detached runner/status surface and
  retains structured reports outside git.
- [x] The persistent Granite/vLLM container is left running after validation,
  with status, hardening evidence, and explicit stop instructions documented
  for later operator use.
- [ ] The full corpus validation runs in-process first, and a small deployed
  service-backed smoke proves the service path without making auth/public-edge
  readiness a first-pass variable.
- [x] A successful first pass produces or updates the follow-up plan for a
  strict service-backed mirror validation where auth/public-edge readiness is
  intentionally included.
- [ ] Task 309's initial run does not use force-eval over source-keyed items;
  any force-eval mode is reserved for the later service-backed mirror
  validation and must be explicit.
- [x] Detached resource monitoring runs alongside the live validation and is
  linked from the retained report.
- [ ] Advisory mode produces no source IR mutation and no effective IR mutation.
- [ ] Retained artifacts contain zero raw prompts and zero raw provider
  responses.
- [ ] Malformed output is never counted as success.
- [x] Unknown IDs and duplicate IDs are counted explicitly and must be zero for
  promotion.
- [x] Wrong-but-valid answers are the primary safety metric; promotion should
  require zero wrong-but-valid answers unless a later governed decision accepts
  a narrower risk posture.
- [x] Manual follow-up is acceptable and safer than plausible wrong answer-key
  completion.
- [x] Persistent failure paths are documented across the run without
  item-specific prompt tweaking. Any retry policy must be generalized by item
  type or failure class in a later governed task.
- [ ] The reviewed-apply probe proves apply mode does not call the provider and
  writes only effective answer-key provenance and candidate lineage.

### Test Requirements

- [x] Unit or focused integration tests cover validation manifest generation
  and expected-answer worklist generation.
- [x] Provider tests cover vLLM `choice` request construction for clear
  candidate-selection items.
- [x] Provider tests cover JSON Schema object request construction for choice
  and gap-fill output specs.
- [ ] Runner tests or dry-run checks distinguish in-process full-corpus mode,
  small service-backed smoke mode, and later service-backed mirror mode.
- [x] Runner/status checks prove the vLLM provider is persistent by default and
  is not stopped as ordinary validation cleanup.
- [ ] Report-evaluation tests cover wrong-but-valid, manual follow-up,
  unknown IDs, duplicate IDs, partial gap answers, malformed output, and
  backend failure-code aggregation. The live evaluator surface now reports
  these metrics, but focused automated evaluator tests remain to be added.
- [ ] Apply-probe tests prove submitted overlay data does not trigger provider
  calls and cannot mutate source IR.

### Stop Conditions

- Stop and surface immediately if the fixture move exposes secrets or student
  PII that would violate repo non-negotiables; otherwise commit the moved raw
  `.dxe` fixture corpus.
- Stop if Hemma cannot prove GPU execution without CPU fallback.
- Stop if vLLM is exposed outside localhost or request logging cannot be
  disabled.
- Stop if goldens cannot be derived or adjudicated for the items being scored.
- Stop if the implementation would tear down the Granite/vLLM provider as
  default closeout instead of leaving it running for later deployed-app tests.
- Stop if force-eval is enabled in the initial Task 309 advisory run.
- Stop if the strict service-backed auth/public-edge mirror is attempted before
  the initial in-process plus service-smoke validation succeeds.
- Stop before attempting a model bake-off or candidate comparison beyond the
  Granite/vLLM interim provider.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [x] Docs updated

### Implementation Notes

- Task 309 is `in_progress`. The 23 pure DigiExam fixtures are staged under
  `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/` with a
  317-item corpus manifest, 42 default advisory rows, 31 vLLM-choice rows, and
  11 JSON-Schema gap-fill rows. Teacher-verified goldens cover 44 rows,
  including the two embedded-image cases.
- The `pdm run answer-key-live-validation` surface supports manifest/status
  inspection, provider launch/status, Hemma preflight, microprobes,
  request-shape preview, advisory execution, and redacted golden evaluation.
  Provider prompts/responses and uploaded content are not retained.
- The Granite/vLLM Hemma run passed provider preflight and all three structured
  output probes but scored only 12 correct of 36 suggested rows (24
  wrong-but-valid); Granite was demoted on 2026-05-16. A later Devstral run
  scored 34 correct, 8 wrong-but-valid, and 2 manual follow-ups. The retained
  Qwen3.6 llama.cpp baseline scored 41 correct, 3 wrong-but-valid, and 273
  skipped source-bound rows; the zero-wrong promotion gate remains unmet.
- Runtime profiles now include `granite-vllm`, `llama-cpp-json-schema`, and
  `llama-cpp-gbnf`. Vision evaluation is opt-in for `qwen36-llama-cpp`; it
  exports PNG/JPEG assets, sends text-plus-image message parts, and records
  only redacted asset/request metadata. The final Hemma provider proof reports
  readiness, expected model, required llama arguments, no CPU fallback, and a
  successful vision microprobe.
- The Hemma launch also established operational constraints: passwordless
  `sudo -n docker`, the Docker-visible scratch cache path, numeric GPU groups,
  localhost-only provider exposure, disabled request logging, and no CPU
  fallback. A later Devstral image rebuild was blocked when Hemma became
  unreachable; this is an infrastructure block, not a model result.
- Retained Qwen3.6 evidence covers 23 per-file reports, 317/317 manifest rows,
  44/44 eligible rows, and zero missing/unexpected references. Follow-up Task
  318 owns provider-profile metadata alignment; Task 319 owns final live-provider
  proof. Suggestions remain advisory until teacher review or a governed change.

### Validation Evidence

- Focused manifest, provider-harness, live-validation, and embedded-image tests
  passed in the retained evidence. Formatting, lint, typecheck, docs-sync,
  docs-validate, skills-validate, handoff-validate, and coverage gates were run
  during the live-validation updates.
- Retained corpus summaries include Granite, Qwen3.6, and Devstral result counts;
  the Qwen3.6 proof SHA-256 is
  `79a6d3349fe43c1add67b515b1070cbc797184fb5da6cbe18bba633c5cfcf551`.
- Required proof commands remain the focused `answer-key-live-validation`
  manifest/provider/status/preflight/microprobe/advisory/evaluation commands,
  the focused `pytest-root` suites, and the standard format/lint/typecheck/docs
  gates listed by the repository workflow. Do not treat provider launch or
  model-quality evidence as promotion authority without the stated gates.
