---
id: task-326-run-openai-mini-nano-answer-key-evaluation-gate-before-provider-promotion
title: Run OpenAI mini/nano answer-key evaluation gate before provider promotion
type: task
status: in_progress
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
- Preserve raw diagnostic eval artifacts for adjudication under ignored
  `build/verification/` output roots. Raw API keys, owner metadata, student
  data, and committed docs/fixtures must still never contain secrets.
- Use a sanctioned OpenAI credential source only. If credentials are unavailable,
  this task remains blocked and Task 325 cannot be completed or promote an
  OpenAI default.

## Deliverables

- [x] Eval-harness support for selecting OpenAI provider profiles by manifest or
  runtime profile ID without model-name branches.
- [x] A raw diagnostic eval run for `gpt-5.4-mini-2026-03-17`.
- [x] A raw diagnostic eval run for `gpt-5.4-nano-2026-03-17`.
- [x] A comparison report against the current local Qwen3.6 baseline with the
  same correctness and failure categories used by local-model evaluations.
- [x] A promotion recommendation: mini, nano, local-only, or no promotion.

## Acceptance Criteria

- [ ] Both OpenAI snapshots are evaluated against the same corpus boundary,
  expected-answer set, scoring categories, and manual-follow-up semantics as the
  local model evaluations.
- [ ] The comparison baseline is the retained Review 18 Qwen3.6 result: 41
  correct, 3 wrong-but-valid, 0 manual-follow-up, and 273 skipped items.
- [ ] The report includes at least correct, wrong-but-valid, manual-follow-up,
  invalid-schema, refusal, timeout, provider-failure, latency, and token-budget
  counts for each OpenAI profile and the current Qwen3.6 baseline.
- [ ] The report retains provider-run metadata for provider family, provider
  profile ID, pinned model snapshot, schema version, output mode, route
  decision, settings version, code revision, and corpus revision.
- [ ] Wrong-but-valid answers remain the primary safety metric. An OpenAI
  profile with unacceptable wrong-but-valid behavior is not promoted even if it
  has fewer manual-follow-up outcomes.
- [ ] Raw diagnostic eval artifacts are retained only under ignored
  `build/verification/` roots; committed docs and fixtures retain summaries,
  hashes, and aggregate metrics only.
- [ ] No API key, owner metadata, student data, or other secret appears in eval
  artifacts, logs, fixtures, or docs.
- [ ] If live OpenAI execution cannot run through the sanctioned credential path,
  the task records the blocker and remains incomplete; Task 325 remains blocked
  from done/promotion.

## Test Requirements

- Focused tests or proof commands showing the eval harness can select each
  OpenAI profile by profile ID and that the selected profile injects model,
  output mode, capability, `reasoning_effort=none`, text verbosity, sampling,
  timeout, and token-budget metadata without model-name branches.
- Capture/privacy checks proving raw diagnostic eval evidence excludes API keys,
  owner metadata, student data, and other secrets.
- Comparison-report checks proving both OpenAI profiles and the local Qwen3.6
  baseline use the same scoring categories.

## Stop Conditions

- Stop if eval-harness changes would require provider-specific branches inside
  answer-key orchestration or provider result validation.
- Stop if live OpenAI execution would require writing raw API keys, owner
  metadata, student data, or other secrets into docs, env mirrors, tests,
  reports, logs, or fixtures.
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

## Implementation Checkpoint - Raw OpenAI Eval Runner

Task 326 implementation started on 2026-05-18 with the recommended open
question answers:

- Use the retained Review 18 Qwen3.6 baseline as the comparison baseline: 41
  correct, 3 wrong-but-valid, 0 manual-follow-up, and 273 skipped items.
- Use raw diagnostic eval artifacts under ignored `build/verification/` roots,
  not sanitized eval artifacts. Raw API keys, owner metadata, student data, and
  other secrets remain forbidden everywhere.
- Keep OpenAI model selection profile-driven through the pinned Task 325
  profiles. The runner selects `openai-gpt-5.4-mini-2026-03-17` and
  `openai-gpt-5.4-nano-2026-03-17` by profile ID without adding model-name
  branches to answer-key orchestration.
- Support OpenAI Responses multimodal input for the 44-row vision-aware corpus
  boundary by sending image inputs as data URLs through the generic Responses
  payload builder.
- Classify OpenAI refusals and request timeouts as explicit provider failure
  categories for eval reporting.

Commands attempted on 2026-05-18:

```bash
pdm run answer-key-live-validation digiexam run-openai-advisory-corpus --openai-provider-profile openai-gpt-5.4-mini-2026-03-17
pdm run answer-key-live-validation digiexam run-openai-advisory-corpus --openai-provider-profile openai-gpt-5.4-nano-2026-03-17
```

The initial direct `pdm run answer-key-live-validation ...` calls stopped at the
sanctioned credential gate because this shell did not source `.env`. The live
runs were then executed through the sanctioned `.env`-loading wrapper with
`--api-key-env OPENAI_API_KEY`:

```bash
pdm run run-local-pdm answer-key-live-validation digiexam run-openai-advisory-corpus --openai-provider-profile openai-gpt-5.4-mini-2026-03-17 --api-key-env OPENAI_API_KEY
pdm run run-local-pdm answer-key-live-validation digiexam run-openai-advisory-corpus --openai-provider-profile openai-gpt-5.4-nano-2026-03-17 --api-key-env OPENAI_API_KEY
```

The first live pass exposed an OpenAI-only harness gap: two eligible
asset-bearing rows were marked `unsupported_assets` even though the local
Qwen3.6 eval covered them. Root cause was the shared candidate planner's
asset-bearing item eligibility check: it required the `llama_cpp_chat_completions`
endpoint instead of the provider capability `supports_multimodal_vision`. Task
326 corrected that local gate and added a regression test proving the OpenAI
Responses planner emits `data:image/png;base64,...` image parts for a retained
vision corpus row.

The golden evaluator was also corrected to align with production artifact roots:
`evaluate-advisory-corpus --output-root <run-root>` now reads
`<run-root>/advisory-corpus-reports` unless `--reports-root` is explicitly
provided. Before this fix, the evaluator could write an OpenAI output file while
reading the provider-default local reports root, producing stale
manual-follow-up counts.

Corrected Task 326 results after the coverage/evaluator fixes, the fresh
2026-05-18 rerun using output roots suffixed `rerun-2026-05-18`, and
teacher adjudication of the mini failure rows:

| Profile | Correct | Wrong-but-valid | Manual follow-up | Skipped | Coverage |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen3.6 retained baseline | 41 | 3 | 0 | 273 | 44/44 eligible |
| `gpt-5.4-mini-2026-03-17` | 43 | 1 | 0 | 273 | 44/44 eligible |
| `gpt-5.4-nano-2026-03-17` | 36 | 8 | 0 | 273 | 44/44 eligible |

Active analysis state: mini now clears the retained Qwen3.6 result on the
corrected golden set, with one remaining wrong-but-valid item. Nano remains
materially worse. This is not yet a task closeout; the remaining discussion is
whether mini's one miss and the corrected golden semantics are acceptable for
the Task 326 promotion gate.

Wrong-but-valid investigation notes:

- `1776888013-ak7-lag-och-ratt.dxe`, `item-002` was a golden error for mini:
  `Fotboja` is a valid sanction/påföljd in this teacher-review context and is
  now accepted.
- `1776888013-ak7-lag-och-ratt.dxe`, `item-001` and
  `1792907597-manniskokroppen-prov-e-vt-26.dxe`, `item-003` are Qwen3.6 and
  nano misses but mini now gets them right. These still indicate ambiguous
  role/term presentation, not an OpenAI-only defect.
- `1811577114-ekologiprov-v-49-25d-e.dxe`, `item-013` was a golden-shape error
  for mini: a teacher reviewing the enrichment would accept the definitions as
  valid keys alongside the letter labels. The golden now accepts both labels
  and definition/concept forms. A future OCR enrichment slice may still improve
  image-backed prompt presentation.
- `1821017157-prov-biologi-genetik-v2.dxe`, `item-016` remains mini's one
  genuine miss after adjudication: `baser` is related but target-invalid where
  the teacher key expects `baspar`.
- `1821017157-prov-biologi-genetik-v2.dxe`, `item-017` was accepted as valid
  for mini under the constraints: without textbook or lecture context, the
  model's `arvsmassan` answer is a defensible key for the cloze.
- Prompt text must not ask the model to choose `manual_follow_up`; manual
  follow-up is a backend/product state. The model-owned answer schema should
  stay answer-only, while unsupported assets and parser gaps are decided by
  production code before or after decoding.

### Fresh rerun wrong-item evaluation after adjudication

The 2026-05-18 rerun plus teacher adjudication leaves 9 unique
wrong-but-valid items across mini and nano, only one of which belongs to mini:

| Source / item | Profiles | Evaluation |
| --- | --- | --- |
| `1776888013-ak7-lag-och-ratt.dxe` / `item-001` | nano | Legal-role gap fill. Nano swaps `polis`/`åklagare`/`advokat` on investigative and prosecution actions. Mini now gets this right; the item remains role-ambiguous enough that weaker models drift. |
| `1776888013-ak7-lag-och-ratt.dxe` / `item-002` | nano | Multiple-response sanctions item. Golden now accepts `Fotboja`; nano still selects all choices, including non-sanctions such as `Indragen veckopeng` and `Kvarsittning`. |
| `1792907597-manniskokroppen-prov-e-vt-26.dxe` / `item-003` | nano | Cell organelle gap fill. Nano answers `kärnan` where the golden accepts `cellkärna/cellkärnan`. This is likely a golden-alias review item, not a production-schema issue. |
| `1811577114-ekologiprov-v-49-25d-e.dxe` / `item-013` | cleared | Image-backed ecology matching item. Golden now accepts definitions/concepts alongside `a`-`e` labels because a teacher would accept either during key enrichment. This remains an OCR-enrichment candidate, but not a mini failure. |
| `1813537086-25c-manniskokroppen-prov-eca.dxe` / `item-009` | nano | Text matching item says to write the correct number, but nano returns the matched terms. This is answer-format instruction following, not an image/OCR gap. |
| `1813567093-23c-e-syror-oh-baser-vt-26.dxe` / `item-007` | nano | Classification gap fill asks for `stark/svag syra/bas`; nano returns the example substances. The model follows row labels instead of the visible answer class bank. |
| `1815387758-23c-energi-och-effekt-e.dxe` / `item-002` | nano | Single-choice physics item. Nano chooses an incorrect formula-like distractor for mechanics' golden rule. This is a straightforward model error. |
| `1821017157-prov-biologi-genetik-v2.dxe` / `item-005` | nano | Single-choice biology term fragment. Correct answer is `skräddarsydda grödor`; nano selects `varierad odlingsföljd`. The stem is fragmentary, but the miss is mostly model selection quality. |
| `1821017157-prov-biologi-genetik-v2.dxe` / `item-016` | mini | Genetics gap fill. Mini answers `baser` where golden expects `baspar`. The answer is related but target-invalid; this remains the only mini wrong-but-valid item after adjudication. |
| `1821017157-prov-biologi-genetik-v2.dxe` / `item-017` | nano | Golden now accepts `arvsmassan` for both gaps; nano still has one wrong gap with `DNA`. |

Promotion decision: mini is accepted as the temporary default provider for dev
and Hemma production so the Qwen3.6 container can be stopped to save GPU VRAM.
This is a provider-default decision, not an automatic answer-key application
decision: suggestions remain advisory unless a later governed task changes the
teacher-review contract. Nano remains below the bar at 36 correct, 8
wrong-but-valid, 0 manual follow-up. The useful follow-up is still not a
general answer-domain extractor; image OCR enrichment is the only
extractor-like slice worth considering from these findings.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
