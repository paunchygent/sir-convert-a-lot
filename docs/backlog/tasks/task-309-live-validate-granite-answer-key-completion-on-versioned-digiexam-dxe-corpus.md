---
id: task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus
title: Live-validate Granite answer-key completion on versioned DigiExam DXE corpus
type: task
status: in_progress
priority: high
created: '2026-05-15'
last_updated: '2026-05-16'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-281-classify-digiexam-dxe-validation-corpus-and-add-parser-regression-gate.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/backlog/tasks/task-310-add-validation-only-force-eval-mode-for-source-keyed-answer-key-live-validation.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/backlog/tasks/task-312-make-answer-key-candidate-planning-provider-protocol-driven.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - docs/runbooks/runbook-hemma-conversion-benchmarks.md
labels:
  - answer-key-completion
  - digiexam
  - dxe
  - fixture-corpus
  - granite
  - hemma
  - vllm
  - live-validation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

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

## PR Scope

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

## Out Of Scope

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

## Deliverables

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
- [ ] Follow-up gate recorded for a strictly service-backed mirror validation
  with auth/public-edge readiness and validation-only force-eval policy.
- [ ] Concise docs closeout in this task and the local-model reference with the
  result, failure-path summary, and next recommended action.

## Acceptance Criteria

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
- [ ] A successful first pass produces or updates the follow-up plan for a
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

## Test Requirements

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

## Stop Conditions

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

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Implementation Notes

- Task 309 is now `in_progress`.
- Moved the 23 pure DigiExam `.dxe` exports into
  `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/`.
- Added `validation-corpus-manifest.json` with 317 items, 42 eligible
  production-advisory items, 31 vLLM-choice rows, and 11 JSON Schema gap-fill
  rows.
- Added `expected-answer-worklist.json` for the 42 eligible items that need
  teacher-verified goldens before scoring.
- Added the initial `pdm run task-309-answer-key-live` command surface for
  manifest preparation and status inspection.
- Task 312 is the required pre-task for live execution: the advisory
  answer-key path now uses a provider-protocol candidate planner so
  Granite/vLLM can use bounded `structured_outputs.choice` for choice rows and
  vLLM JSON Schema for gap-fill rows without grafting vLLM conditionals into
  orchestration.
- Filled and validated `expected-answer-manifest.json` for the 42 eligible
  scored items. The manifest is teacher-verified by repository review, not
  model-generated.
- Extended `pdm run task-309-answer-key-live` with the live-run execution
  surface:
  `launch-provider`, `provider-status`, `hemma-preflight`, `microprobes`, and
  `run-advisory-corpus`.
- `launch-provider` is dry-run by default and requires `--execute` to start the
  named persistent Granite/vLLM container. The planned container binds
  `127.0.0.1:8017`, uses the scratch-backed Hugging Face cache, disables vLLM
  request logging, has no `--rm`, and uses `--restart unless-stopped` so it is
  left running until the operator explicitly stops it.
- `microprobes` runs the three required provider probes: vLLM
  `structured_outputs.choice`, JSON Schema choice object, and JSON Schema
  gap-fill object. Reports retain only redacted metadata, latency, usage, and
  failure code; raw prompts and raw provider responses are not retained.
- `run-advisory-corpus` executes the production in-process advisory path over
  the versioned fixture corpus and writes per-file answer-key completion
  reports plus a redacted corpus summary outside git.
- The live Hemma launch exposed two Hemma-specific Docker corrections that are
  now folded into the runner: use passwordless `sudo -n docker`, bind the
  Docker-visible scratch cache path
  `/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface`, and use
  numeric Hemma GPU groups `44` and `993` instead of container-local group
  names.
- Launched the persistent Granite/vLLM provider on Hemma at
  `127.0.0.1:8017`. The first successful startup took the normal cold
  load/compile/warmup path and left the container running.
- Hemma preflight passed at `2026-05-15T21:31:34Z` for remote revision
  `2da7bc8a78cbed36811308108c2ae50a924db0ac`, manifest SHA
  `sha256:b540aa3deaf847ce060144eff5d257e6b5545d80c617a6e22b9d5d8a67d4e674`,
  ROCm probes, cache paths, localhost-only provider exposure, disabled request
  logging, and no CPU fallback.
- Provider microprobes passed all three output modes:
  `vllm_structured_choice` latency `1450.088ms`, JSON Schema choice-object
  latency `889.837ms`, and JSON Schema gap-object latency `1345.627ms`.
- Detached resource monitor `task116-resource-20260515t213207z` ran beside the
  corpus validation, then stopped by request. It recorded 11 samples with GPU
  busy median/max `100%`, GPU memory median/max `94%`, host CPU median `18%`,
  and host memory median `51%`.
- In-process advisory corpus run completed over 23 files and 317 items in
  `86919.444ms`: 36 suggested, 8 manual follow-up, 273 skipped, with backend
  failure counts `provider_content_not_json=3`, `llm_output_invalid=2`,
  `missing_candidate_structure=1`, `unsupported_assets=2`, and
  `source_bound_answer_key_exists=273`.
- Added and ran the redacted golden-evaluation surface. It found 36 suggested
  items, 12 correct suggestions, 24 wrong-but-valid suggestions, 8 manual
  follow-ups, 0 unknown IDs, 0 duplicate IDs, 0 malformed successes, 0 partial
  gap answers, and 2 non-skipped manual-follow-up items without goldens. This
  blocks promotion and intentionally does not trigger item-specific prompt
  engineering.
- After the first live run, the persistent provider remained running for later
  deployed-app and service-smoke work as originally requested. The resource
  monitor was stopped after the corpus run completed.
- Follow-up direct probes using improved consumer-friendly item prompts did not
  rescue the provider-quality concern: a 10-item sample from the failed
  first-evaluation rows produced only 1 correct result, with 3 wrong-but-valid
  and 6 invalid-output results across gap-fill, multiple-response, and
  single-choice rows. A separate temperature `0.1` chat experiment on a
  word-bank gap-fill row reached only 7/10 in full-question framing and 1/10
  when segmented gap-by-gap. The errors remained plausible wrong keys rather
  than only wrapper/schema failures.
- On 2026-05-16 the Granite/vLLM model was demoted for the answer-key
  completion lane. The schema/protocol path is proven useful, but the live
  evidence does not support carrying Granite 4.1 8B FP8 forward as an interim
  provider candidate.
- Per operator request, the Task 309 Granite/vLLM container and other
  GPU-loaded model/service containers were stopped on Hemma to clear capacity
  for a Devstral Small on `llama.cpp` diagnostic probe. Stopped containers:
  `sir-convert-task309-granite-vllm`, `huleedu_rst_parser_service`,
  `huleedu_essay_embed_offload`, and `sir_convert_a_lot_prod`.
- Post-stop Hemma verification showed GPU use `0%`, VRAM `0%`, no KFD PIDs,
  no matching Task 309/model-service containers running, and no matching
  `vllm`/`llama`/`devstral`/`granite` model processes.
- The live-validation command surface now accepts explicit structured-provider
  runtimes for `preview-request-shape`, `microprobes`, and
  `run-advisory-corpus`: `granite-vllm`, `llama-cpp-json-schema`, and
  `llama-cpp-gbnf`. The llama.cpp runtimes are restricted to constrained JSON
  output only: either Chat Completions `response_format.type=json_schema` or
  the validated Skriptoteket-style Chat Completions `grammar` request field
  with GBNF that still emits JSON objects for the normal advisory decoder.
- A local request-shape smoke for `--provider-runtime llama-cpp-gbnf` built all
  42 eligible model requests with zero shape issues; retained payloads contain
  `grammar` and omit both `response_format` and vLLM `structured_outputs`.
- A first live Devstral Small launch attempt on 2026-05-16 found Hemma's
  `active.gguf` pointing at
  `Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf`, but the supervised
  `llama-server-rocm.service` was inactive and its required
  `llama.cpp-rocm:7.2.0` image was missing. The remote Dockerfile's pinned
  ROCm/llama.cpp commit no longer resolved, so the canonical BuildKit rebuild
  was retried with ROCm/llama.cpp `68717eac3c081eec00bbb961c0e0e3c129a1790f`.
  The build progressed into HIP compilation, then Hemma became unreachable over
  Tailscale/SSH before the image loaded and before any live Devstral request or
  corpus validation could run. This is an infrastructure block, not a model
  result.

## Validation Evidence

- `pdm run task-309-answer-key-live prepare-manifests --output-root inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe`
- `pdm run task-309-answer-key-live status --output-root inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe`
- `pdm run task-309-answer-key-live validate-goldens --output-root build/verification/task-309-granite-answer-key-live --fail-on-blocked`
- `pdm run task-309-answer-key-live launch-provider --output-root build/verification/task-309-granite-answer-key-live`
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation launch-provider --execute --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live --fail-on-blocked`
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation provider-status --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live --timeout-seconds 20 --fail-on-blocked`
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation hemma-preflight --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live --timeout-seconds 20 --fail-on-blocked`
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation microprobes --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live --timeout-seconds 60 --fail-on-blocked`
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task116_hemma_resource_monitor launch --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live/resource-monitor --runtime-kind rocm --interval-seconds 10 --duration-seconds 3600`
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation run-advisory-corpus --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live --reports-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live/advisory-corpus-reports --timeout-seconds 90 --fail-on-blocked`
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation evaluate-advisory-corpus --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live --reports-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live/advisory-corpus-reports --fail-on-blocked`
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task116_hemma_resource_monitor stop --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-granite-answer-key-live/resource-monitor`
- `ssh hemma "sudo docker stop sir-convert-task309-granite-vllm"`
- `ssh hemma "sudo docker stop huleedu_rst_parser_service huleedu_essay_embed_offload sir_convert_a_lot_prod"`
- `ssh hemma "rocm-smi --showuse --showmemuse --showpidgpus 2>/dev/null || true"`
- `ssh hemma "sudo docker ps --format '{{.Names}} {{.Status}}' | grep -E 'sir-convert-task309|rst_parser|essay_embed|sir_convert_a_lot_prod' || true"`
- `ssh hemma "ps -eo pid,comm,args | grep -E 'vllm|llama|devstral|granite|rst_parser|essay_scoring|offload.server|sir_convert_a_lot.service' | grep -v grep || true"`
- `pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation preview-request-shape --provider-runtime llama-cpp-gbnf --output-root build/verification/task-309-llama-cpp-shape-smoke --corpus-root inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe`
- `ssh hemma "readlink -f /home/paunchygent/models/active.gguf && cat /home/paunchygent/models/active-model.txt"`
- `ssh hemma "systemctl status --no-pager llama-server-rocm.service || true"`
- `ssh hemma "cd /home/paunchygent/llama.cpp-rocm && sudo docker buildx build --load -t llama.cpp-rocm:7.2.0 --build-arg LLAMA_CPP_COMMIT=68717eac3c081eec00bbb961c0e0e3c129a1790f ."`
- `ssh -o ConnectTimeout=10 hemma 'echo ping'`
- `ping -c 1 -W 3000 hemma.tail730aa2.ts.net`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py tests/sir_convert_a_lot/test_structured_llm_provider_harness.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task309_answer_key_live_validation_manifest.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task309_answer_key_live_validation_manifest.py tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py tests/sir_convert_a_lot/test_structured_llm_provider_harness.py tests/sir_convert_a_lot/test_structured_llm_provider_execution.py`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py::test_examnet_pdf_document_accepts_current_state_for_item_013_multigap`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_live_onedrive_dxe_corpus_subset`
