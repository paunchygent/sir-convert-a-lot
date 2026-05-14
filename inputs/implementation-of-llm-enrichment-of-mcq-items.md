# Sir Convert-a-Lot × Skriptoteket answer-key enrichment blueprint

This is the implementation shape we have converged on:

```text
.dxe + optional graded result PDF
  ↓
source-bound DigiExam parser result
  ↓
source-bound DigiExam IR
  ↓
optional Skriptoteket teacher/item overlay
  ↓
optional local-first machine-marked answer-key completion
  ↓
effective DigiExam IR
  ↓
Exam.net artifacts, QTI package, reports, manifest, named artifact API
```

The key shift is that this should no longer be framed as **MCQ enrichment only**. The correct abstraction is:

```text
machine-marked answer-key completion
```

That covers:

```text
single_choice
multiple_choice
multiple_response
gap_fill
matching
```

The model output must remain bounded and non-explanatory:

```text
no confidence
no rationale
no reasons
no model-authored provenance
no raw prompt artifact
```

The producer owns provenance, artifact semantics, privacy policy, route behavior, and final validation.

---

# 1. Core design decisions

## 1.1 Parser provenance is immutable

The DigiExam parser remains source-bound.

It may derive answer keys only from:

```text
.dxe source fields
graded result PDF source evidence
validated teacher/manual overlay
```

It must not classify LLM output as parser evidence.

The existing provenance meanings remain strict:

```text
absent
dxe_populated_key
graded_result_pdf_correct_labels
manual_teacher_key
not_applicable
```

LLM output is not any of these unless the teacher later accepts the suggestion in Skriptoteket and resubmits it as a manual teacher key.

## 1.2 Sir Convert owns the producer route

The route remains:

```text
digiexam_dxe -> examnet_migration_bundle
```

Skriptoteket may supply:

```text
UI-authored item context
teacher/item metadata
manual answer keys
enrichment request options
```

But Sir Convert owns:

```text
input validation
source binding
overlay validation
LLM candidate building
provider policy
remote fallback policy
artifact ownership
manifest semantics
named artifact exposure
public/authenticated access control
```

## 1.3 There are two IR concepts

Keep the original IR source-bound:

```text
ir_json
```

Add a second artifact when overlays or applied LLM completion change the renderer input:

```text
effective_ir_json
```

This avoids changing the meaning of the existing `ir_json`.

```text
source IR      = what the .dxe + source evidence proved
effective IR   = what renderers used after teacher overlay and/or applied completion
```

## 1.4 LLM completion is local-first and policy-gated

Default route behavior remains:

```text
source_evidence_only
remote_provider_policy = forbidden
```

Remote fallback must not happen unless explicitly allowed by authenticated policy or a future signed public grant version. An explicit deny must be terminal.

## 1.5 Teacher overlay precedes LLM completion

The order matters:

```text
source parse
  ↓
source IR
  ↓
teacher/Skriptoteket overlay
  ↓
LLM answer-key completion
```

The LLM should operate on the best item-local structure available, including validated teacher-supplied task instructions or item patches.

---

# 2. End-to-end runtime flow

Recommended producer flow inside:

```text
scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py
```

Conceptually:

```python
answer_evidence = maybe_extract_result_pdf_answer_evidence(job)

parse_result = DigiExamDxeParser().parse_file(
    job.upload_path,
    answer_evidence=answer_evidence,
)

source_exam = build_digiexam_intermediate_exam(parse_result)
source_ir_manifest = build_digiexam_ir_manifest(source_exam)

overlay_result = apply_digiexam_ingestion_overlay_if_present(
    source_exam=source_exam,
    job=job,
    overlay_path=digiexam_ingestion_overlay_path_for_upload(job.upload_path),
)

candidate_exam = overlay_result.effective_exam

completion_result = maybe_complete_missing_machine_marked_answer_keys(
    exam=candidate_exam,
    job=job,
    policy=resolved_answer_key_completion_policy,
    enricher=answer_key_completion_service,
)

effective_exam = apply_answer_key_completion_result(
    exam=candidate_exam,
    completion_result=completion_result,
)

render_examnet_pdf(effective_exam)
render_qti_package(effective_exam)
write_source_ir(source_exam)
write_effective_ir_if_changed(effective_exam)
write_overlay_report(overlay_result)
write_answer_key_completion_report(completion_result)
write_bundle_manifest(...)
```

The parser does not know about LLMs. Renderers do not know about provider details. Artifact routes do not mutate anything.

---

# 3. LLM harness wiring

## 3.1 Extract a generic structured-output provider

From Skriptoteket, reuse the provider abstraction and Dishka wiring pattern, but avoid edit-op-specific hardcoding.

Replace the editor-specific concept:

```text
OpenAIChatOpsProvider
```

with a generic provider:

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

The output spec is supplied by the domain operation:

```python
@dataclass(frozen=True)
class StructuredOutputSpec:
    name: str
    json_schema: dict[str, object]
    chat_response_format: dict[str, object]
    responses_text_format: dict[str, object]
    llama_gbnf: str | None
    max_output_tokens: int
    parser_profile: str
```

That lets the same provider serve:

```text
Skriptoteket editor edit-ops
Sir Convert choice answer completion
Sir Convert gap-fill answer completion
Sir Convert matching answer completion
```

without copying provider code.

## 3.2 Provider set

Use a provider set with explicit capabilities:

```python
@dataclass(frozen=True)
class StructuredChatProviderSet:
    primary: StructuredChatProviderProtocol
    fallback: StructuredChatProviderProtocol | None
```

Recommended concrete providers:

```text
primary:
  local llama.cpp OpenAI-compatible endpoint
  grammar/json-schema capable
  remote = false

fallback:
  OpenAI-compatible API provider
  endpoint mode = responses or chat_completions
  remote = true
  disabled unless policy allows
```

Do not infer GBNF support from a port number. Configure it:

```env
LLM_PRIMARY_ENDPOINT_KIND=chat_completions
LLM_PRIMARY_SUPPORTS_GBNF=true
LLM_PRIMARY_SUPPORTS_JSON_SCHEMA=true
LLM_PRIMARY_REMOTE=false

LLM_FALLBACK_ENDPOINT_KIND=responses
LLM_FALLBACK_SUPPORTS_GBNF=false
LLM_FALLBACK_SUPPORTS_JSON_SCHEMA=true
LLM_FALLBACK_REMOTE=true
```

## 3.3 Payload shaping

The provider must keep three payload paths separate.

### OpenAI Chat Completions

Use:

```json
{
  "model": "...",
  "messages": [...],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "digiexam_choice_answer_key_decision",
      "strict": true,
      "schema": {}
    }
  }
}
```

OpenAI’s current structured-output documentation distinguishes schema-adherent Structured Outputs from plain JSON mode and shows Chat Completions using `response_format` with `type: "json_schema"`, `strict: true`, and `additionalProperties: false` in the schema. ([developers.openai.com][1])

### OpenAI Responses

Use:

```json
{
  "model": "...",
  "input": [...],
  "text": {
    "format": {
      "type": "json_schema",
      "name": "digiexam_choice_answer_key_decision",
      "strict": true,
      "schema": {}
    }
  }
}
```

OpenAI’s migration guide states that Structured Outputs moved from `response_format` in Chat Completions to `text.format` in the Responses API. ([developers.openai.com][1])

### Local llama.cpp

Prefer explicit local constrained decoding.

Use one of these, depending on the configured server capability:

```json
{
  "model": "...",
  "messages": [...],
  "grammar": "root ::= ..."
}
```

or:

```json
{
  "model": "...",
  "messages": [...],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "schema": {}
    }
  }
}
```

The llama.cpp grammar documentation states that llama-server completion endpoints accept a `grammar` body field, and that llama.cpp can convert a subset of JSON Schema to GBNF, including for `/chat/completions` through `response_format`. It also warns that the schema constrains output but is not injected into the prompt, so the expected structure still needs to be described in the prompt. ([GitHub][2])

## 3.4 Output schemas are per item type

Do not use one large union schema unless absolutely necessary.

Use separate output specs:

```text
digiexam_choice_answer_key_decision_v1
digiexam_gap_fill_answer_key_decision_v1
digiexam_matching_answer_key_decision_v1
```

This keeps:

```text
GBNF simpler
JSON Schema simpler
backend validation simpler
error handling clearer
tests smaller
```

## 3.5 Prompt budgeting

Reuse Skriptoteket’s budgeting pattern:

```text
available_prompt_tokens =
    context_window
    - max_output_tokens
    - safety_margin
```

For this route, the prompt should be single-turn and item-local:

```text
system prompt
+ one compact JSON input object
```

No chat history.

No full exam.

No result PDF content.

No raw `.dxe`.

No owner metadata.

No student data.

If an item exceeds budget:

```text
do not call the provider
mark item manual_follow_up_required
backend code: over_budget
```

## 3.6 Tokenizer selection

Use the same resolver pattern as Skriptoteket:

```text
GPT/OpenAI-family model     -> tiktoken or provider-specific counter
Mistral/Devstral-family     -> Tekken if available
unknown/local model         -> conservative heuristic
```

The budgeter is a safety preflight, not a precise accounting oracle.

## 3.7 Failover routing

Failover decision inputs:

```python
@dataclass(frozen=True)
class LLMRoutePolicy:
    remote_provider_policy: RemoteProviderPolicy
    allow_remote_fallback: bool | None
    authenticated_owner: bool
    public_grant_allows_remote: bool
```

Remote provider policy:

```python
class RemoteProviderPolicy(StrEnum):
    FORBIDDEN = "forbidden"
    ALLOWED_WITH_SIGNED_CONSENT = "allowed_with_signed_consent"
```

Routing rules:

| State                                                               | Behavior                                     |
| ------------------------------------------------------------------- | -------------------------------------------- |
| Local available                                                     | Use local primary.                           |
| Local unavailable, fallback local                                   | Use fallback if healthy.                     |
| Local unavailable, fallback remote, policy forbidden                | Do not route remote.                         |
| Local unavailable, fallback remote, consent missing                 | Return `remote_fallback_required` / blocked. |
| Local unavailable, fallback remote, explicit false                  | Do not route remote.                         |
| Local unavailable, fallback remote, explicit true and policy allows | Use remote fallback.                         |

The important bug to avoid is treating `False` like “not specified.” Explicit false means no remote fallback.

## 3.8 Capture policy

Default production capture:

```text
raw prompt: off
raw model response: off
raw stem: off
raw alternatives/gaps/matching text: off
success capture: off
error capture: metadata-only
```

Allowed metadata:

```json
{
  "job_id": "job_...",
  "item_id": "item-003",
  "item_type": "gap_fill",
  "provider_profile_id": "local-llama-cpp-answer-key-v1",
  "remote_used": false,
  "schema_version": "digiexam_gap_fill_answer_key_decision_v1",
  "prompt_template_version": "digiexam-answer-key-completion-v1",
  "status": "manual_follow_up_required",
  "backend_failure_code": "llm_output_invalid"
}
```

Raw prompt/response capture should require a separate governed evaluation mode, not a route default.

---

# 4. Sir Convert route/API changes

## 4.1 Multipart inputs

Current DigiExam route accepts:

```text
file
job_spec
graded_result_pdf
parity_pdf
```

Add:

```text
digiexam_ingestion_overlay
```

Allowed parts become:

```python
_ALLOWED_DIGIEXAM_PART_NAMES = {
    "file",
    "job_spec",
    "graded_result_pdf",
    "parity_pdf",
    "digiexam_ingestion_overlay",
}
```

The new part is optional JSON.

Validation:

```text
must be referenced by job spec when present
must decode as JSON object
must validate against digiexam_ingestion_overlay_v1
must be size-bounded
must be source-bound by sha256/fingerprint fields
must not contain raw files or base64 assets
```

## 4.2 Job spec options

Extend `DigiExamMigrationOptionsV2`.

Recommended shape:

```python
class DigiExamIngestionOverlayPolicyV2(StrEnum):
    NONE = "none"
    APPLY_TEACHER_OVERLAY = "apply_teacher_overlay"


class DigiExamAnswerKeyCompletionModeV2(StrEnum):
    SOURCE_EVIDENCE_ONLY = "source_evidence_only"
    TEACHER_OVERLAY_ONLY = "teacher_overlay_only"
    LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED = (
        "local_llm_suggest_missing_machine_marked"
    )
    LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW = (
        "local_llm_apply_missing_machine_marked_with_review"
    )


class DigiExamRemoteProviderPolicyV2(StrEnum):
    FORBIDDEN = "forbidden"
    ALLOWED_WITH_SIGNED_CONSENT = "allowed_with_signed_consent"


class DigiExamAnswerKeyCompletionOptionsV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: DigiExamAnswerKeyCompletionModeV2 = (
        DigiExamAnswerKeyCompletionModeV2.SOURCE_EVIDENCE_ONLY
    )
    remote_provider_policy: DigiExamRemoteProviderPolicyV2 = (
        DigiExamRemoteProviderPolicyV2.FORBIDDEN
    )
    eligible_item_types: tuple[DigiExamItemType, ...] = (
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
        DigiExamItemType.MATCHING,
    )


class DigiExamMigrationOptionsV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graded_result_pdf_filename: str | None = None
    parity_pdf_filename: str | None = None

    ingestion_overlay_filename: str | None = None
    ingestion_overlay_policy: DigiExamIngestionOverlayPolicyV2 = (
        DigiExamIngestionOverlayPolicyV2.NONE
    )

    answer_key_completion: DigiExamAnswerKeyCompletionOptionsV2 = Field(
        default_factory=DigiExamAnswerKeyCompletionOptionsV2
    )

    result_pdf_usage: DigiExamResultPdfUsageV2 = (
        DigiExamResultPdfUsageV2.CORRECT_MACHINE_MARKED_ANSWERS_ONLY
    )
    manual_follow_up_policy: DigiExamManualFollowUpPolicyV2 = (
        DigiExamManualFollowUpPolicyV2.EMIT_ITEM_ADDRESSABLE_REPORT
    )
```

Defaults preserve current behavior.

## 4.3 Job persistence and idempotency

Add companion-path helper:

```python
def digiexam_ingestion_overlay_json_path_for_upload(upload_path: Path) -> Path:
    return upload_path.parent / "digiexam_ingestion_overlay.json"
```

Persist the overlay bytes beside the upload.

Include overlay digest in idempotency:

```text
normalized job spec
.dxe sha256
graded_result_pdf sha256
parity_pdf sha256
digiexam_ingestion_overlay sha256
```

This ensures the same `.dxe` with a different teacher overlay is a different conversion request.

---

# 5. IR and provenance contracts

## 5.1 Source IR remains source-bound

Existing:

```text
digiexam_intermediate_exam_v2
```

can remain source-bound.

Its answer-key provenance means only source evidence unless a teacher manual key has been applied as an explicit overlay in the effective path.

## 5.2 Add effective IR artifact

When overlay or applied LLM completion changes renderer input, write:

```text
digiexam-effective-ir.json
```

with artifact key:

```text
effective_ir_json
```

The effective IR can initially reuse the same schema if the current fields are sufficient.

For matching applied answer keys, add IR v3.

## 5.3 Add item fingerprints

Add a stable item fingerprint to source IR manifest item summaries.

Purpose:

```text
Skriptoteket can round-trip item edits safely.
Sir Convert can reject stale overlays.
```

Example:

```json
{
  "item_id": "item-003",
  "sequence": 3,
  "item_type": "gap_fill",
  "source_item_fingerprint": "sha256:..."
}
```

Fingerprint input should include stable source structure:

```text
item type
title
prompt text
alternative ids/text
gap ids/order
matching left/right columns
asset hashes
```

Do not include answer keys. The fingerprint is for structural binding.

## 5.4 Effective answer-key provenance

For applied overlays/completion, source provenance alone is not enough.

Add:

```python
class DigiExamEffectiveAnswerKeyProvenance(StrEnum):
    NONE = "none"
    SOURCE_BOUND = "source_bound"
    TEACHER_OVERLAY = "teacher_overlay"
    LLM_INFERRED_FROM_ITEM_TEXT = "llm_inferred_from_item_text"
```

Possible answer-key structure:

```python
@dataclass(frozen=True)
class DigiExamIrAnswerKey:
    source_provenance: DigiExamAnswerKeyProvenance
    effective_provenance: DigiExamEffectiveAnswerKeyProvenance
    correct_alternative_ids: tuple[int, ...]
    correct_gap_answers: tuple[DigiExamGapAnswer, ...]
    correct_matching_pairs: tuple[DigiExamMatchingAnswerPair, ...] = ()
```

A smaller first tranche can avoid this IR change by keeping LLM output advisory-only.

## 5.5 Matching needs an answer-key field

Current matching structure has left/right columns, but applied matching answer keys need explicit pairs:

```python
@dataclass(frozen=True)
class DigiExamMatchingAnswerPair:
    left_id: str
    right_id: str
```

Then:

```python
correct_matching_pairs: tuple[DigiExamMatchingAnswerPair, ...]
```

This is the main reason matching should start as advisory unless an IR contract update is included.

---

# 6. Skriptoteket ingestion overlay contract

The overlay is the bridge from Skriptoteket UI to Sir Convert.

It is not a raw JSON Patch. It is a bounded, route-owned contract.

## 6.1 Top-level overlay

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

## 6.2 Overlay item

```json
{
  "item_id": "item-003",
  "sequence": 3,
  "source_item_fingerprint": "sha256:...",
  "teacher_context": {
    "task_instructions": "Use the terminology from the unit on ecosystems.",
    "language": "sv",
    "additional_item_context": "The intended concept is taught in the section on photosynthesis."
  },
  "effective_item_patch": null,
  "manual_answer_key": null
}
```

## 6.3 Teacher context

Teacher context is used for candidate building, but it does not itself become an answer key.

```json
{
  "task_instructions": "Fill in the missing word.",
  "language": "sv",
  "additional_item_context": "Students have studied cell respiration and photosynthesis."
}
```

Privacy rule:

```text
Do not include student data.
Do not include full exam-level metadata.
Do not include files or assets.
```

## 6.4 Effective item patch

This is how Skriptoteket can supply additional item/test metadata that mutates the effective ingestion format.

Use bounded type-specific patches:

```json
{
  "kind": "gap_fill",
  "stem_with_gap_markers": "Plants produce glucose through [blank-001].",
  "gaps": [
    {
      "gap_id": "blank-001"
    }
  ]
}
```

For matching:

```json
{
  "kind": "matching",
  "stem": "Match each concept with the correct definition.",
  "left_prompts": [
    {
      "left_id": "left_001",
      "label": "A",
      "text": "Photosynthesis"
    },
    {
      "left_id": "left_002",
      "label": "B",
      "text": "Cell respiration"
    }
  ],
  "right_options": [
    {
      "right_id": "right_001",
      "label": "1",
      "text": "Conversion of light energy into chemical energy"
    },
    {
      "right_id": "right_002",
      "label": "2",
      "text": "Breakdown of glucose to release energy"
    }
  ]
}
```

For choice:

```json
{
  "kind": "choice",
  "stem": "Which process produces glucose in plants?",
  "alternatives": [
    {
      "alternative_id": 1,
      "label": "A",
      "text": "Cell respiration"
    },
    {
      "alternative_id": 2,
      "label": "B",
      "text": "Photosynthesis"
    }
  ]
}
```

Rules:

```text
The patch mutates effective IR only.
The source IR remains unchanged.
The patch must match the source item fingerprint.
The patch must be type-compatible unless an explicit type-repair policy is added.
The patch provenance is teacher_overlay.
```

## 6.5 Manual answer key

A manual key is teacher-authored/teacher-accepted. It is authoritative.

Choice:

```json
{
  "kind": "choice",
  "selected_alternative_ids": [2]
}
```

Gap-fill:

```json
{
  "kind": "gap_fill",
  "gap_answers": [
    {
      "gap_id": "blank-001",
      "accepted_values": ["fotosyntes"]
    }
  ]
}
```

Matching:

```json
{
  "kind": "matching",
  "pairs": [
    {
      "left_id": "left_001",
      "right_id": "right_001"
    },
    {
      "left_id": "left_002",
      "right_id": "right_002"
    }
  ]
}
```

When applied, manual answer keys become:

```text
effective_provenance = teacher_overlay
source/provenance meaning = manual_teacher_key only if represented in the effective/manual layer
```

---

# 7. LLM candidate input contracts

The LLM should receive only the item-local input needed to decide the answer key.

No full IR.

No job owner.

No result PDF.

No raw `.dxe`.

No student data.

No artifact paths.

## 7.1 Choice input

```json
{
  "schema_version": "digiexam_choice_answer_key_input_v1",
  "item_id": "item-001",
  "item_type": "single_choice",
  "stem": "Which process produces glucose in plants?",
  "task_instructions": "Choose one alternative.",
  "alternatives": [
    {
      "id": 1,
      "label": "A",
      "text": "Cell respiration"
    },
    {
      "id": 2,
      "label": "B",
      "text": "Photosynthesis"
    }
  ],
  "selection_rule": {
    "min_selected": 1,
    "max_selected": 1
  }
}
```

## 7.2 Gap-fill input

```json
{
  "schema_version": "digiexam_gap_fill_answer_key_input_v1",
  "item_id": "item-004",
  "item_type": "gap_fill",
  "stem_with_gap_markers": "Plants produce glucose through [blank-001].",
  "task_instructions": "Fill in the missing word.",
  "gaps": [
    {
      "gap_id": "blank-001"
    }
  ]
}
```

The important part is preserving the gap location. A plain stem plus a list of gap IDs is too weak.

## 7.3 Matching input

```json
{
  "schema_version": "digiexam_matching_answer_key_input_v1",
  "item_id": "item-007",
  "item_type": "matching",
  "stem": "Match each concept with the correct definition.",
  "task_instructions": "Connect each item in the left column to one item in the right column.",
  "left_prompts": [
    {
      "left_id": "left_001",
      "label": "A",
      "text": "Photosynthesis"
    },
    {
      "left_id": "left_002",
      "label": "B",
      "text": "Cell respiration"
    }
  ],
  "right_options": [
    {
      "right_id": "right_001",
      "label": "1",
      "text": "Conversion of light energy into chemical energy"
    },
    {
      "right_id": "right_002",
      "label": "2",
      "text": "Breakdown of glucose to release energy"
    }
  ],
  "matching_rule": {
    "each_left_prompt_requires_one_right_option": true,
    "right_option_reuse_allowed": false
  }
}
```

---

# 8. LLM output contracts

The model output is deliberately austere.

No confidence.

No rationale.

No explanation.

No evidence.

No provenance.

## 8.1 Shared enums

```python
class AnswerKeyDecisionStatus(StrEnum):
    ANSWERED = "answered"
    MANUAL_FOLLOW_UP_REQUIRED = "manual_follow_up_required"


class ManualFollowUpCode(StrEnum):
    AMBIGUOUS_OR_INSUFFICIENT = "ambiguous_or_insufficient"
    UNSUPPORTED_INPUT = "unsupported_input"
    MALFORMED_INPUT = "malformed_input"
```

Backend-only failure codes may be richer:

```text
llm_output_invalid
over_budget
provider_unavailable
remote_fallback_forbidden
source_item_fingerprint_mismatch
unsupported_renderer_target
```

But those are not model-authored.

## 8.2 Choice decision

```json
{
  "schema_version": "digiexam_choice_answer_key_decision_v1",
  "status": "answered",
  "selected_alternative_ids": [2],
  "manual_follow_up_code": null
}
```

Manual follow-up:

```json
{
  "schema_version": "digiexam_choice_answer_key_decision_v1",
  "status": "manual_follow_up_required",
  "selected_alternative_ids": [],
  "manual_follow_up_code": "ambiguous_or_insufficient"
}
```

## 8.3 Gap-fill decision

```json
{
  "schema_version": "digiexam_gap_fill_answer_key_decision_v1",
  "status": "answered",
  "gap_answers": [
    {
      "gap_id": "blank-001",
      "accepted_values": ["photosynthesis"]
    }
  ],
  "manual_follow_up_code": null
}
```

Manual follow-up:

```json
{
  "schema_version": "digiexam_gap_fill_answer_key_decision_v1",
  "status": "manual_follow_up_required",
  "gap_answers": [],
  "manual_follow_up_code": "ambiguous_or_insufficient"
}
```

## 8.4 Matching decision

```json
{
  "schema_version": "digiexam_matching_answer_key_decision_v1",
  "status": "answered",
  "pairs": [
    {
      "left_id": "left_001",
      "right_id": "right_001"
    },
    {
      "left_id": "left_002",
      "right_id": "right_002"
    }
  ],
  "manual_follow_up_code": null
}
```

Manual follow-up:

```json
{
  "schema_version": "digiexam_matching_answer_key_decision_v1",
  "status": "manual_follow_up_required",
  "pairs": [],
  "manual_follow_up_code": "ambiguous_or_insufficient"
}
```

---

# 9. Backend validation rules

The backend treats the model output as a proposal.

## 9.1 Shared validation

For `answered`:

```text
manual_follow_up_code must be null
answer payload must be non-empty
all IDs must exist in candidate input
no duplicate IDs unless explicitly allowed
```

For `manual_follow_up_required`:

```text
answer payload must be empty
manual_follow_up_code must be non-null
```

Extra properties are rejected.

Malformed output becomes:

```text
manual_follow_up_required
backend_failure_code = llm_output_invalid
```

No semantic repair of an invalid answer.

## 9.2 Choice validation

For single-choice / multiple-choice:

```text
len(selected_alternative_ids) == 1
selected ID exists
```

For multiple-response:

```text
len(selected_alternative_ids) >= 1
all selected IDs exist
selection count satisfies item choice limits
```

## 9.3 Gap-fill validation

Rules:

```text
every returned gap_id exists
no unknown gap_id
no duplicate gap_id
accepted_values non-empty for answered
accepted values are bounded strings
accepted values are normalized for whitespace
```

Do not let the model decide scoring policy. It may provide accepted values only.

Backend owns whether matching is:

```text
case-sensitive
case-insensitive
trimmed
accent-insensitive
regex-based
exact-string
```

A first implementation should use literal accepted values and leave scoring policy unchanged.

## 9.4 Matching validation

Rules:

```text
every left_id exists
every right_id exists
no duplicate left_id
all required left_ids covered when answered
right_id reuse follows matching_rule
```

Default:

```text
one right option per left prompt
right option reuse not allowed
```

unless the source/overlay explicitly says otherwise.

---

# 10. Business logic

## 10.1 Priority order

Answer-key sources rank as:

```text
1. Source-bound .dxe answer key
2. Source-bound graded result PDF answer evidence
3. Teacher/Skriptoteket manual overlay
4. LLM completion
5. Manual follow-up
```

Source-bound evidence wins over everything except an explicit teacher override policy, which should be a separate deliberate option.

## 10.2 Eligibility

Eligible for machine-marked answer-key completion:

```text
single_choice
multiple_choice
multiple_response
gap_fill
matching
```

Not eligible:

```text
open_ended
unknown
items without enough structure after overlay
items with source-bound answer keys
items blocked by parser warnings that make item structure unreliable
items requiring non-text assets unless a future local multimodal policy exists
```

## 10.3 Overlay application

Overlay application can:

```text
add task instructions
add teacher context
repair effective item structure
add manual answer keys
add matching/gap structure for effective use
```

It cannot:

```text
mutate source IR
change source provenance
inject raw files
bypass owner checks
bypass public grant restrictions
```

## 10.4 LLM completion modes

### `source_evidence_only`

Current behavior.

```text
No overlay application unless separately requested.
No LLM calls.
```

### `teacher_overlay_only`

Applies validated Skriptoteket/teacher overlay.

```text
No LLM calls.
Effective IR may change.
Manual teacher keys may remove manual follow-up.
```

### `local_llm_suggest_missing_machine_marked`

Advisory mode.

```text
Runs local-first LLM on eligible missing machine-marked keys.
Writes answer_key_completion_report.
Does not change effective answer keys.
Manual follow-up remains.
```

This should be the first shipped LLM mode.

### `local_llm_apply_missing_machine_marked_with_review`

Applied-with-review mode.

```text
Runs local-first LLM.
Validated answers are written to effective IR.
Source provenance remains absent.
Effective provenance is llm_inferred_from_item_text.
Manual follow-up becomes llm_answer_key_verification_required.
Bundle remains partial/review-required until teacher acceptance.
```

This mode requires careful IR/report semantics and matching support may require IR v3.

## 10.5 Teacher acceptance loop

When the teacher accepts an LLM suggestion in Skriptoteket:

```text
Skriptoteket resubmits the answer as manual_answer_key in the overlay.
Sir Convert validates it.
Effective provenance becomes teacher_overlay / manual_teacher_key.
The LLM suggestion is no longer the authority.
```

This is the clean path from “best effort suggestion” to “teacher-owned answer key.”

---

# 11. Artifact and manifest changes

## 11.1 New artifact keys

Add route-owned named artifacts:

```python
INGESTION_OVERLAY_REPORT = "ingestion_overlay_report"
ANSWER_KEY_COMPLETION_REPORT = "answer_key_completion_report"
EFFECTIVE_IR_JSON = "effective_ir_json"
```

Suggested files:

```text
ingestion-overlay-report.json
answer-key-completion-report.json
digiexam-effective-ir.json
```

Do not expose raw overlay JSON as a named artifact by default.

Do not expose LLM capture logs as named artifacts.

## 11.2 Ingestion overlay report

Example:

```json
{
  "schema_version": "digiexam_ingestion_overlay_report_v1",
  "mode": "apply_teacher_overlay",
  "items": [
    {
      "item_id": "item-004",
      "source_item_fingerprint": "sha256:...",
      "status": "applied",
      "applied_changes": [
        "teacher_context",
        "manual_answer_key"
      ],
      "backend_failure_code": null
    },
    {
      "item_id": "item-005",
      "source_item_fingerprint": "sha256:...",
      "status": "rejected",
      "applied_changes": [],
      "backend_failure_code": "source_item_fingerprint_mismatch"
    }
  ]
}
```

No raw prompt text required.

## 11.3 Answer-key completion report

Example:

```json
{
  "schema_version": "digiexam_answer_key_completion_report_v1",
  "mode": "local_llm_suggest_missing_machine_marked",
  "provider": {
    "lane": "local",
    "provider_profile_id": "local-llama-cpp-answer-key-v1",
    "remote_used": false
  },
  "items": [
    {
      "item_id": "item-001",
      "item_type": "single_choice",
      "source_answer_key_provenance": "absent",
      "input_source": "source_ir_plus_teacher_overlay",
      "status": "answered",
      "application_state": "suggestion_only",
      "selected_alternative_ids": [2],
      "manual_follow_up_code": null,
      "backend_failure_code": null
    },
    {
      "item_id": "item-004",
      "item_type": "gap_fill",
      "source_answer_key_provenance": "absent",
      "input_source": "source_ir_plus_teacher_overlay",
      "status": "answered",
      "application_state": "suggestion_only",
      "gap_answers": [
        {
          "gap_id": "blank-001",
          "accepted_values": ["photosynthesis"]
        }
      ],
      "manual_follow_up_code": null,
      "backend_failure_code": null
    },
    {
      "item_id": "item-007",
      "item_type": "matching",
      "source_answer_key_provenance": "absent",
      "input_source": "source_ir_plus_teacher_overlay",
      "status": "manual_follow_up_required",
      "application_state": "manual_follow_up_required",
      "pairs": [],
      "manual_follow_up_code": "ambiguous_or_insufficient",
      "backend_failure_code": null
    }
  ]
}
```

This report may include selected IDs and accepted values because those are the artifact’s purpose. It should not include confidence, rationale, raw prompts, or raw provider responses.

## 11.4 Manifest availability

For new artifacts:

```text
available       artifact exists
not_requested   mode did not request it
blocked         requested but could not be produced safely
```

Example:

```json
{
  "artifact_key": "answer_key_completion_report",
  "filename": "answer-key-completion-report.json",
  "content_type": "application/json",
  "availability": "available",
  "size_bytes": 2048,
  "sha256": "sha256:...",
  "download_path": "/v2/convert/jobs/job_123/artifacts/answer_key_completion_report"
}
```

If local LLM is unavailable and remote is forbidden:

```json
{
  "artifact_key": "answer_key_completion_report",
  "availability": "blocked",
  "blocker_code": "local_llm_unavailable_remote_forbidden"
}
```

The overall job can still complete with a partial/review-required bundle.

---

# 12. Ownership and public/authenticated access

## 12.1 Authenticated jobs

Authenticated jobs continue to use:

```text
InternalIdentityContextV1
```

The overlay and completion artifacts inherit:

```text
job owner
retention window
artifact authorization
named artifact API v2 access checks
```

No separate job or side-channel should be created for LLM completion.

## 12.2 Public Exam Converter lane

The current public lane should remain:

```text
ingestion_overlay_policy = none
answer_key_completion.mode = source_evidence_only
remote_provider_policy = forbidden
```

Do not allow overlays or LLM completion under the existing public grant.

A future public grant version would need explicit signed fields:

```text
allowed_ingestion_overlay_policy
allowed_answer_key_completion_mode
allowed_remote_provider_policy
overlay_digest, if applicable
```

Those fields must affect the public owner digest / authorization envelope.

## 12.3 Public artifact read lease

If the public lane ever supports these artifacts, the read lease must name the exact artifact key:

```text
ingestion_overlay_report
answer_key_completion_report
effective_ir_json
```

A lease for one artifact must not imply access to all new artifacts.

---

# 13. Skriptoteket consumer-side changes

Skriptoteket should stay a thin consumer. It should not couple UI logic to provider details.

## 13.1 Initial parse/conversion request

Skriptoteket can first call Sir Convert with:

```text
mode = source_evidence_only
ingestion_overlay_policy = none
```

Then fetch:

```text
ir_json
ir_manifest
manual_follow_up_report
warnings_report
bundle_manifest
```

This gives the UI source-bound item structure and missing-answer-key state.

## 13.2 UI item editor

The Skriptoteket UI should display item-addressable records:

```text
item_id
sequence
item_type
source_item_fingerprint
stem/prompt
alternatives
gaps
matching columns
source answer-key provenance
manual follow-up state
```

The UI can let the teacher add:

```text
task instructions
language/context notes
gap markers
matching columns
manual answer keys
accept/reject LLM suggestions
```

## 13.3 Overlay creation

When the teacher edits items, Skriptoteket creates:

```text
digiexam_ingestion_overlay_v1
```

and sends it as the `digiexam_ingestion_overlay` multipart part.

The overlay must include:

```text
source file sha256
source IR sha256, when available
item_id
source_item_fingerprint
bounded item patch/manual answer key/context
```

## 13.4 Calling LLM completion through Sir Convert

Skriptoteket requests completion by setting job options, not by calling the LLM harness directly.

For suggestion mode:

```json
{
  "digiexam_migration_options": {
    "ingestion_overlay_filename": "digiexam-ingestion-overlay.json",
    "ingestion_overlay_policy": "apply_teacher_overlay",
    "answer_key_completion": {
      "mode": "local_llm_suggest_missing_machine_marked",
      "remote_provider_policy": "forbidden"
    }
  }
}
```

For applied-with-review mode:

```json
{
  "digiexam_migration_options": {
    "ingestion_overlay_filename": "digiexam-ingestion-overlay.json",
    "ingestion_overlay_policy": "apply_teacher_overlay",
    "answer_key_completion": {
      "mode": "local_llm_apply_missing_machine_marked_with_review",
      "remote_provider_policy": "forbidden"
    }
  }
}
```

Skriptoteket does not need to know whether the local provider is llama.cpp, whether GBNF was used, or whether Chat Completions/Responses payloads were shaped differently.

## 13.5 Displaying suggestions

Skriptoteket reads:

```text
answer_key_completion_report
```

and maps suggestions back to item UI by:

```text
item_id
alternative_id
gap_id
left_id/right_id
```

The UI should label these as suggestions or verification-required answers, not source-proven answers.

## 13.6 Teacher acceptance

When a teacher accepts a suggestion:

```text
Skriptoteket sends it back as manual_answer_key in the overlay.
```

That is the moment it becomes teacher-owned.

Do not treat the previous LLM suggestion report as durable answer-key authority.

## 13.7 Consumer API client updates

Skriptoteket’s Sir Convert client needs support for:

```text
new multipart part: digiexam_ingestion_overlay
new job spec options: ingestion_overlay_policy, answer_key_completion
new artifact keys: ingestion_overlay_report, answer_key_completion_report, effective_ir_json
```

It should also persist the relevant source binding information between conversion attempts:

```text
source_file_sha256
source_ir_sha256
item_id
source_item_fingerprint
```

---

# 14. Producer-side file/module changes

## 14.1 Sir Convert domain

Add:

```text
scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay.py
scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion.py
```

Contracts:

```python
@dataclass(frozen=True)
class DigiExamAnswerKeyCompletionCandidate:
    item_id: str
    item_type: DigiExamItemType
    input_schema_version: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class DigiExamAnswerKeyCompletionDecision:
    item_id: str
    item_type: DigiExamItemType
    status: AnswerKeyDecisionStatus
    selected_alternative_ids: tuple[int, ...] = ()
    gap_answers: tuple[DigiExamGapAnswer, ...] = ()
    matching_pairs: tuple[DigiExamMatchingAnswerPair, ...] = ()
    manual_follow_up_code: ManualFollowUpCode | None = None
```

## 14.2 Sir Convert application

Add:

```text
scripts/sir_convert_a_lot/application/digiexam_ingestion_overlay_application.py
scripts/sir_convert_a_lot/application/digiexam_answer_key_completion_flow.py
```

Responsibilities:

```text
validate overlay
apply overlay to effective exam
build LLM candidates
call answer-key completion service
validate decisions
apply/report decisions
```

## 14.3 Sir Convert infrastructure

Add:

```text
scripts/sir_convert_a_lot/infrastructure/llm/
  structured_provider.py
  provider_sets.py
  failover_router.py
  prompt_budget.py
  token_counter_resolver.py
  capture.py
  openai/
    payloads.py
    answer_key_schemas.py
    answer_key_grammars.py
    structured_chat_provider.py
```

Or reuse/extract this from Skriptoteket into a shared internal package.

## 14.4 HTTP route modules

Update:

```text
scripts/sir_convert_a_lot/interfaces/http_digiexam_migration_request_v2.py
scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py
scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py
scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
```

Add overlay bytes, digest, validation, storage, and idempotency.

## 14.5 Bundle artifacts

Update:

```text
scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py
scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py
scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_manifest.py
```

Add:

```text
overlay report
answer-key completion report
effective IR
manifest entries
```

---

# 15. Prompt templates

Keep prompts short and schema-aligned.

## 15.1 Shared system prompt

```text
You are a DigiExam machine-marked answer-key completion component.

You receive exactly one exam item as JSON.

Return only JSON matching the required schema.

Do not include explanations, confidence, rationale, evidence, or provenance.

Do not invent item IDs, alternative IDs, gap IDs, left IDs, or right IDs.

Return answered only when the supplied item text and structure support one valid answer object.

Return manual_follow_up_required when the input is ambiguous, malformed, unsupported, or insufficient.
```

## 15.2 Choice-specific instruction

```text
For choice items, select only from the provided alternative IDs.
Respect selection_rule.min_selected and selection_rule.max_selected.
```

## 15.3 Gap-fill-specific instruction

```text
For gap-fill items, provide accepted literal values for the provided gap IDs.
Do not create new gaps.
Do not describe scoring policy.
```

## 15.4 Matching-specific instruction

```text
For matching items, pair provided left IDs with provided right IDs.
Respect the matching_rule.
Do not create new left or right IDs.
```

---

# 16. Tests

## 16.1 Producer route/API tests

```text
test_digiexam_route_accepts_optional_ingestion_overlay_part
test_unknown_multipart_part_still_rejected
test_overlay_filename_must_match_job_spec
test_overlay_json_must_validate_schema
test_overlay_sha_changes_idempotency_fingerprint
test_source_evidence_only_default_unchanged
test_public_grant_defaults_to_no_overlay_no_llm
test_public_grant_rejects_overlay_without_explicit_new_grant_fields
```

## 16.2 Overlay tests

```text
test_overlay_requires_source_binding
test_overlay_requires_matching_source_item_fingerprint
test_overlay_rejects_unknown_item_id
test_overlay_rejects_unknown_alternative_id
test_overlay_rejects_unknown_gap_id
test_overlay_rejects_unknown_matching_id
test_teacher_context_does_not_create_answer_key
test_manual_choice_key_applies_as_teacher_overlay
test_manual_gap_fill_key_applies_as_teacher_overlay
test_manual_matching_key_is_report_only_until_ir_support_exists
test_overlay_does_not_mutate_source_ir
test_overlay_writes_overlay_application_report
```

## 16.3 LLM wiring tests

```text
test_openai_chat_payload_uses_response_format_json_schema
test_openai_responses_payload_uses_text_format_json_schema
test_local_llama_payload_uses_grammar_when_configured
test_local_llama_payload_does_not_depend_on_port_number
test_structured_output_spec_is_supplied_by_domain_not_provider
test_prompt_budget_overflow_blocks_provider_call
test_remote_fallback_forbidden_blocks_remote_provider
test_remote_fallback_explicit_false_never_routes_remote
test_remote_fallback_missing_consent_returns_blocked
test_capture_metadata_only_by_default
```

## 16.4 Decision parser tests

```text
test_choice_output_rejects_confidence
test_choice_output_rejects_rationale
test_choice_output_rejects_extra_fields
test_choice_answered_requires_one_valid_id_for_single_choice
test_multiple_response_requires_valid_nonempty_ids
test_gap_fill_answered_requires_known_gap_ids
test_gap_fill_rejects_duplicate_gap_ids
test_matching_answered_requires_known_left_and_right_ids
test_matching_rejects_duplicate_left_ids
test_manual_follow_up_requires_empty_answer_payload
test_invalid_llm_output_becomes_manual_follow_up_backend_failure
```

## 16.5 Business-flow tests

```text
test_source_bound_answer_key_skips_llm
test_teacher_manual_key_skips_llm
test_llm_suggest_mode_does_not_change_effective_answer_key
test_llm_apply_mode_sets_effective_llm_provenance
test_llm_apply_mode_keeps_verification_required_followup
test_teacher_acceptance_resubmitted_as_manual_key_removes_llm_provenance
test_answer_key_completion_report_contains_no_confidence_or_rationale
test_answer_key_completion_report_contains_no_raw_prompt
test_effective_ir_written_only_when_changed
test_renderers_use_effective_ir
test_source_ir_artifact_remains_source_bound
```

---

# 17. Recommended implementation sequence

## Phase 1: Contract-safe overlay lane

Deliver:

```text
digiexam_ingestion_overlay multipart part
overlay route options
overlay storage and idempotency
source item fingerprints
overlay validation
overlay application report
teacher manual choice/gap-fill keys
```

No LLM yet.

This unlocks Skriptoteket UI round-tripping.

## Phase 2: Generic structured-output LLM harness

Deliver:

```text
StructuredOutputSpec
generic structured provider
OpenAI Chat payload builder
OpenAI Responses payload builder
local llama.cpp grammar/json-schema path
budget preflight
remote fallback policy
metadata-only capture
```

Port this from Skriptoteket but remove editor-specific schema coupling.

## Phase 3: Advisory answer-key completion

Deliver:

```text
choice completion
gap-fill completion
matching completion advisory report
answer_key_completion_report artifact
no effective IR mutation from LLM
```

This gives users best-effort suggestions without weakening provenance.

## Phase 4: Applied-with-review completion

Deliver:

```text
effective answer-key provenance
effective_ir_json
applied choice/gap-fill answers
llm_answer_key_verification_required follow-up state
```

Matching applied mode waits until matching pairs exist in IR.

## Phase 5: Teacher acceptance loop

Deliver:

```text
Skriptoteket accept suggestion
resubmit as manual_answer_key overlay
Sir Convert applies as teacher/manual key
manual follow-up resolved
```

This converts an LLM suggestion into teacher-owned answer evidence.

---

# 18. Final architecture in one diagram

```text
Skriptoteket UI
  ├─ initial source-only conversion request
  ├─ reads source IR + manual follow-up report
  ├─ teacher edits item context / structure / keys
  ├─ submits digiexam_ingestion_overlay
  ├─ optionally requests local LLM suggestion/apply-with-review
  └─ accepts suggestions by resubmitting them as manual keys

Sir Convert API v2
  ├─ validates multipart parts
  ├─ validates job spec
  ├─ persists .dxe + companion files + overlay
  ├─ binds owner/public grant
  └─ exposes named artifacts

Sir Convert producer runtime
  ├─ parses .dxe
  ├─ extracts source-bound result-PDF evidence
  ├─ builds source IR
  ├─ applies teacher/Skriptoteket overlay
  ├─ builds item-local LLM candidates
  ├─ runs local-first structured-output completion
  ├─ validates decisions
  ├─ writes source/effective IR
  ├─ renders Exam.net/QTI artifacts
  └─ writes reports + terminal manifest

LLM harness
  ├─ generic StructuredOutputSpec
  ├─ local llama.cpp provider
  ├─ optional API provider
  ├─ Chat Completions payload path
  ├─ Responses payload path
  ├─ GBNF / JSON Schema constrained decoding
  ├─ budget preflight
  ├─ failover router
  └─ metadata-only capture
```

The central invariant is:

```text
Source provenance stays source-bound.
Teacher overlay is teacher-owned.
LLM completion is bounded, validated, local-first, and never silently promoted to source evidence.
```

[1]: https://developers.openai.com/api/docs/guides/migrate-to-responses "Migrate to the Responses API | OpenAI API"
[2]: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/grammars/README.md "raw.githubusercontent.com"
