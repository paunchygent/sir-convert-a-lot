---
type: reference
id: REF-digiexam-machine-marked-answer-key-completion-architecture
title: DigiExam Machine-marked Answer-key Completion Architecture
status: active
created: 2026-05-14
updated: 2026-05-15
owners:
  - platform
tags:
  - digiexam
  - examnet
  - answer-key-completion
  - llm
  - skriptoteket
  - huleedu
links:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
---

## Purpose

This reference captures the accepted planning shape from
`inputs/implementation-of-llm-enrichment-of-mcq-items.md` and translates it into
Sir Convert-a-Lot docs-as-code authority. It deliberately renames the capability
from "MCQ enrichment" to **machine-marked answer-key completion** because the
domain surface covers single choice, multiple choice, multiple response,
gap-fill, and matching items.

The reference is not implementation approval by itself. `EPIC-11` owns the
delivery plan, and the linked stories/tasks decide which contract or runtime
slice is allowed to change.

## Core Decision

The DigiExam parser remains source-bound. It may derive answer keys only from
`.dxe` source fields, graded-result PDF correct-answer evidence, or validated
teacher/manual overlay. LLM output is never parser evidence and must not be
stored under parser provenance values such as `dxe_populated_key`,
`graded_result_pdf_correct_labels`, `manual_teacher_key`, `absent`, or
`not_applicable`.

Sir Convert owns the producer route and v2 bundle contract:

```text
digiexam_dxe -> examnet_migration_bundle
bundle: digiexam_migration_bundle_v2
```

Skriptoteket may submit bounded item patches, manual answer keys, review
decisions, and completion options. Sir Convert owns validation, source binding,
provider policy, artifact semantics, manifests, named artifact exposure, and
access control.

## End-to-End Shape

```text
.dxe + optional graded result PDF
  -> source-bound DigiExam parser result
  -> source-bound DigiExam IR
  -> optional local-first machine-marked answer-key completion
  -> optional Skriptoteket teacher edit/review overlay on a later request
  -> digiexam_effective_exam_v1 when renderer input changes
  -> Exam.net artifacts, QTI package, reports, manifest, named artifact API
```

The existing `ir_json` remains the source IR: what source evidence proved. A
new `effective_ir_json` artifact uses `digiexam_effective_exam_v1` and is
emitted only when teacher overlay or applied completion changes renderer input.
This prevents renderer and consumer code from silently changing the meaning of
the existing source-bound IR artifact.

## Overlay Contract

The overlay bridge from Skriptoteket is a route-owned JSON contract, not a raw
JSON Patch. It is optional, size-bounded, source-bound, and free from raw files,
caller-supplied raw asset payloads, student data, and full exam-level metadata.
Teacher-visible images remain available through Sir Convert-owned source IR,
effective exam, named artifact, or asset-reference surfaces.

Required top-level shape:

```json
{
  "schema_version": "digiexam_ingestion_overlay_v1",
  "source_binding": {
    "source_file_sha256": "sha256:...",
    "source_ir_schema_version": "digiexam_intermediate_exam_v2",
    "source_ir_sha256": "sha256:..."
  },
  "items": []
}
```

Each item binds to `item_id`, `sequence`, and a
`source_item_fingerprint`. The fingerprint must be derived from stable source
structure such as item type, prompt/title text, alternatives, gap IDs/order,
matching columns, and asset hashes. Answer keys are excluded from the
fingerprint because the fingerprint protects structural freshness, not answer
content.

Overlay item payloads may include:

- `effective_item_patch`: a type-specific choice, gap-fill, or matching patch
  that mutates only the effective IR.
- `manual_answer_key`: a teacher-authored or teacher-accepted key that is
  authoritative in the effective layer.
- `review_decision`: a teacher decision about the current item state, such as
  accepting a missing machine-marked answer key for export without adding an
  answer. Review decisions are not answer keys, do not change parser
  provenance, and must be bound to the item ID, sequence, type, and source item
  fingerprint.

Source-derived item context for the first enrichment pass comes from `.dxe`
fields already represented in source IR, such as exam metadata, item title,
prompt/body HTML, alternatives, gaps, matching columns, grading policy, and
asset references. It is not a Skriptoteket overlay field and does not become
answer-key evidence.

## Target Readiness And Accepted Current State

Skriptoteket cannot make PDF or QTI downloadable by flipping a local review
flag. Target readiness belongs to Sir Convert because only Sir Convert knows
which effective items each renderer/importer can safely produce.

The accepted-current-state path is therefore:

```text
Skriptoteket teacher decision
  -> source-bound overlay review_decision
  -> Sir Convert validates source binding and item type
  -> Sir Convert recomputes effective exam and target readiness
  -> Sir Convert emits available artifacts or precise blockers
  -> Skriptoteket enables only rows Sir Convert marks available
```

Accepted current state may allow a target-specific best-effort output only when
that target has a governed renderer/import policy for the unresolved item. It
must not:

- synthesize answer keys;
- mutate `ir_json` or parser provenance;
- bypass QTI validation;
- treat unsupported target shapes as accepted missing answer keys; or
- mark a named artifact as downloadable unless bytes were actually created and
  validated.

Target readiness must remain per-target and per-item. It must distinguish at
least:

- `ready`;
- `ready_after_accepted_current_state`;
- `needs_teacher_answer_key`;
- `needs_teacher_review_decision`;
- `unsupported_target_shape`, for example multi-gap gap-fill without governed
  PDF/QTI representation;
- `target_validation_failed`, for example QTI package validation;
- `provider_unavailable`;
- `not_requested`; and
- `not_implemented`.

Every readiness row must carry enough consumer detail for Skriptoteket to render
the next action without re-implementing conversion policy: target, item binding
when item-specific, reason code, `export_enabled`, `teacher_action`,
`retryable`, and a localized message key.

## Completion Modes

Default completion/provider policy:

```text
mode = source_evidence_only
remote_provider_policy = forbidden
```

Allowed modes are planned as:

- `source_evidence_only`: current source-bound route behavior.
- `teacher_overlay_only`: apply validated overlay, no LLM call.
- `local_llm_suggest_missing_machine_marked`: create advisory completion report
  only, leaving renderers on source/overlay evidence.
- `local_llm_apply_missing_machine_marked_with_review`: apply validated
  completion into the effective IR with explicit review/provenance semantics.

Source-bound evidence wins over LLM completion. A teacher override policy that
can supersede source-bound evidence must be a separate governed decision.

## Provider Harness

The reusable provider abstraction should be generic structured output, not
editor edit-ops. Skriptoteket already has useful pieces: a Dishka-wired provider
set, local/remote fallback flags, token budgeting, and an OpenAI-compatible
chat-ops provider. The Sir Convert task should extract or mirror the shape
without copying editor-specific patch semantics.

Target protocol shape:

```python
class StructuredChatProviderProtocol(Protocol):
    async def complete_structured(
        self,
        request: LLMChatRequest,
        *,
        system_prompt: str,
        output_spec: StructuredOutputSpec,
    ) -> StructuredLLMResponse:
        ...
```

`StructuredOutputSpec` owns per-operation schema names, JSON Schema payloads,
Chat Completions `response_format`, Responses API `text.format`, optional
llama.cpp GBNF, vLLM `structured_outputs`, max output tokens, and parser
profile.

Provider configuration must expose capabilities explicitly. Do not infer GBNF
or JSON Schema support from a port number:

```text
LLM_PRIMARY_ENDPOINT_KIND=chat_completions
LLM_PRIMARY_STRUCTURED_OUTPUT_MODE=vllm_structured_outputs
LLM_PRIMARY_SUPPORTS_CHOICE=true
LLM_PRIMARY_SUPPORTS_GBNF=false
LLM_PRIMARY_SUPPORTS_JSON_SCHEMA=true
LLM_PRIMARY_REMOTE=false
LLM_PRIMARY_MODEL=ibm-granite/granite-4.1-8b-fp8

LLM_FALLBACK_ENDPOINT_KIND=responses
LLM_FALLBACK_SUPPORTS_GBNF=false
LLM_FALLBACK_SUPPORTS_JSON_SCHEMA=true
LLM_FALLBACK_REMOTE=true
```

## Upstream API Notes

Context7 was checked on 2026-05-14 for the relevant third-party syntax.

- OpenAI Chat Completions structured output uses `response_format` with
  `type: "json_schema"`, a `json_schema` object containing `name`, `strict`,
  and `schema`, and schemas should set `additionalProperties: false` for strict
  bounded outputs.
- OpenAI Responses structured output uses `text.format` with
  `type: "json_schema"`, `name`, `strict`, and `schema`.
- llama.cpp `llama-server` supports OpenAI-compatible `/v1/chat/completions`
  constrained output with `response_format.type = "json_schema"`, and its
  grammar tooling supports GBNF / JSON Schema conversion for constrained
  outputs. Prompt text must still describe the expected structure; schema
  constraint alone is not prompt content.
- vLLM exposes an OpenAI-compatible server via `vllm serve`, with configurable
  `--host`, `--port`, and `--api-key`. The current Hemma smoke proved
  Chat Completions `extra_body.structured_outputs.choice` on
  `ibm-granite/granite-4.1-8b-fp8`; JSON Schema and grammar modes remain
  provider-harness test targets before they are used for gap-fill or matching
  application.

## Interim Local Provider Decision

Use vLLM with `ibm-granite/granite-4.1-8b-fp8` as the local structured provider
for the first implementation of this feature.

This is an engineering settlement, not final model promotion. It lets Task 296
and the advisory completion work target one concrete local OpenAI-compatible
runtime while Task 300 stays available for later comparative benchmarks against
the GGUF shortlist.

Interim constraints:

- use Hemma localhost only; do not expose the provider through public routes;
- use `127.0.0.1:8017` only after proving the port is free;
- start with `--gpu-memory-utilization 0.70` on the shared host;
- use the canonical scratch-backed Hugging Face cache documented in
  `docs/runbooks/runbook-hemma-devops-and-gpu.md`;
- use `structured_outputs.choice` for first MCQ/MCW decisions;
- require explicit provider-harness tests before relying on vLLM JSON Schema or
  grammar modes for gap-fill and matching;
- keep all model output advisory/proposal-shaped until backend validation and
  teacher review apply it to the effective IR.

## HuleEdu LLM Provider Assessment

The HuleEdu LLM Provider Service is valuable prior art and a possible future
HTTP provider, but it is not the easiest first implementation target for Sir
Convert answer-key completion.

Current observed HuleEdu shape:

- queue-first `POST /api/v1/comparison` returning `202 + queue_id`;
- Kafka callback delivery with `LLMComparisonResultV1`;
- comparison-specific result fields such as `winner`, `justification`, and
  `confidence`;
- provider/model manifest and OpenAI Chat Completions structured-output support;
- no immediate synchronous structured-output HTTP endpoint for item-local
  schema-specific completions.

Recommendation: first implement a Sir Convert service-backed provider harness
using the Skriptoteket local-first pattern and explicit provider capabilities.
Create a later HuleEdu task only if we want LLM Provider Service to expose a new
bounded synchronous or callback-backed **generic structured completion** API
that accepts a schema name/schema payload, returns only schema-valid JSON or a
typed failure, and preserves Sir Convert's privacy/capture policy.

## Prompt And Capture Rules

The completion prompt must be single-turn and item-local:

- system prompt;
- one compact JSON input object;
- no chat history;
- no full exam;
- no result PDF content;
- no raw `.dxe`;
- no owner metadata;
- no student data;
- no artifact paths.

If an item exceeds budget, do not call the provider. Emit
`manual_follow_up_required` with backend failure code `over_budget`.

Default production capture is metadata-only. Do not capture raw prompts, raw
model responses, raw stems, raw alternatives, raw gap text, or raw matching
text unless a separate governed evaluation mode authorizes it.

Allowed metadata includes job ID, item ID, item type, provider profile ID,
remote-used flag, schema version, prompt template version, status, and backend
failure code.

## Output Contract

Model output is deliberately austere:

- no confidence;
- no rationale;
- no reasons;
- no model-authored provenance;
- no raw prompt artifact.

Use item-type-specific schemas instead of one large union:

- `digiexam_choice_answer_key_decision_v1`;
- `digiexam_gap_fill_answer_key_decision_v1`;
- `digiexam_matching_answer_key_decision_v1`.

Backend validation treats model output as a proposal. For `answered`, answer
payloads must be non-empty, all IDs must exist in the candidate input, and
manual follow-up code must be null. For `manual_follow_up_required`, answer
payloads must be empty and the follow-up code must be non-null. Malformed output
becomes `manual_follow_up_required` with backend failure code
`llm_output_invalid`; there is no semantic repair.

## Runtime Insertion Point

The planned insertion point is the DigiExam migration bundle builder. Conceptual
flow:

```text
extract optional result-PDF correct-answer evidence
parse .dxe into source parse result
build source IR and source IR manifest
apply optional validated ingestion overlay
complete missing machine-marked answer keys according to policy
apply completion result only in modes that allow effective IR changes
render Exam.net PDF, QTI package, reports, and manifests from effective exam
write source IR, effective IR if changed, overlay report, completion report
```

Parser code must not know about LLMs. Renderers must not know about provider
details. Artifact routes must not mutate jobs or IR.
