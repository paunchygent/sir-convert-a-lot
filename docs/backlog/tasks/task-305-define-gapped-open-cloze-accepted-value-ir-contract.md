---
id: task-305-define-gapped-open-cloze-accepted-value-ir-contract
title: Define gapped open-cloze accepted-value IR contract
type: task
status: done
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
labels:
  - effective-ir
  - answer-key-completion
  - gap-fill
  - open-cloze
  - ir-contract
  - source-adapter
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and implement the accepted-value contract for gapped and open-cloze
items as source-neutral `ExamAuthoringIR v1` concepts before any teacher
overlay, LLM advisory output, reviewed application, QTI export, or PDF renderer
claims such items can be machine-evaluated.

This task is the gapped/open-cloze sibling of Task 298. It closes the
source-adapter-to-authoring-IR contract shape for gap identifiers and accepted
values. It does not implement LLM provider calls, advisory completion, reviewed
application, or model selection.

Task 307's architecture boundary is controlling: this task must not deepen
`DigiExamIntermediateExam` into the universal exam model. It may update the
current DigiExam migration route where needed, but the contract language and
implementation shape must say that gap/open-cloze concepts map cleanly into
`ExamAuthoringIR v1`; DigiExam is only one source adapter.

Sir Convert preserves exam intent. Target exporters declare capability and
degradation. They do not erase source semantics.

Unsupported by a target export is not the same as unavailable from Sir Convert.
If Exam.net PDF, general QTI, future Exam.net QTI, or another target cannot
emit a native gap/open-cloze shape, that is a target-readiness/degradation
warning, not an IR restriction.

QTI support must remain distinct from Exam.net import claims. QTI 3 documents
`qti-gap-match-interaction`, QTI 2.1 includes `gapMatchInteraction`, and
Exam.net publicly advertises fill-the-gaps in its authoring UI. Sir Convert
must still avoid claiming native Exam.net gap import/export support until there
is a governed Exam.net import/export proof path.

The current `Para ihop` chemistry PDF fixture is best treated as a likely
matching-styled gap/open-cloze workaround: it has gap-like visible answer slots
and matching-like source/target structure. Task 305 treats this as neutral
source intent, not as a DigiExam matching parser feature. If source evidence
supports it, a future source adapter may emit a gapped/open-cloze interaction
with source evidence; later target validators/exporters can remap that neutral
structure to matching, manual/free-text, omission, or manual recreation
guidance according to target capability.

## PR Scope

- Define stable gap identifiers, visible gap order, prompt binding, and source
  evidence/spans for each source-neutral gapped/open-cloze item.
- Represent accepted values per gap as first-class structured authoring
  answer-key data.
- Define a neutral gap/open-cloze interaction shape with at least:
  - `gap_id`;
  - `display_order`;
  - prompt/body binding;
  - `accepted_values`;
  - `normalization_profile`;
  - `required_for_auto_evaluation`;
  - answer-key provenance;
  - source evidence/span.
- Define value normalization policy explicitly, including case, whitespace,
  punctuation, spelling variants, and whether normalization is target-specific
  or only used for validation.
- Define multi-gap completeness rules: which gaps must have trusted accepted
  values before the item can be automatically evaluated.
- Preserve source-bound parser provenance separately from teacher/manual or
  reviewed effective answer-key provenance.
- Preserve observed source gap IDs and avoid inventing values when no source,
  teacher/manual, or reviewed evidence exists.
- Keep DigiExam-specific `DigiExamGap`/`DigiExamGapAnswer` as adapter/source
  data only where current runtime still needs it; do not define new reusable
  gap concepts in DigiExam-named contracts.
- Update manifest, parity, manual-follow-up, target-readiness, PDF, QTI, and
  `ExamAuthoringIR v1` contract docs where they depend on gap accepted-value
  shape.
- Keep applied gapped/open-cloze completion disabled until this contract and
  its validators are implemented.
- Preserve teacher choice in target-readiness rows: include as degraded
  manual/free-text, remove from export, or use the item as a copy source for
  manual recreation in Exam.net's web UI where a target cannot safely emit a
  native item.

## Deliverables

- [x] Gapped/open-cloze accepted-value `ExamAuthoringIR v1` contract.
- [x] Gap accepted-value validation rules and target-profile issue semantics.
- [x] Manifest/report shape for source-neutral gap answer-key provenance.
- [x] Renderer/QTI gate documentation proving gap/open-cloze remains
  manual/unkeyed, degraded, omitted, or manual-recreation-only unless trusted
  accepted values and target support exist.
- [x] Target-readiness contract rows that distinguish unsupported target
  export from unavailable source intent.
- [x] DigiExam route update plan showing which current DigiExam gap fields map
  into the neutral authoring contract and which stay source-specific.
- [x] Planning note for matching-styled gapped items that keeps parser/adapters
  source-neutral and lets target validators decide matching/manual/free-text
  remapping.
- [x] Focused tests for gap ID binding, missing gaps, duplicate/conflicting
  values, normalization, multi-gap completeness, source/effective provenance,
  and target readiness.

## Acceptance Criteria

- [x] Gap accepted values are first-class structured `ExamAuthoringIR v1` data,
  not prompt text, renderer labels, or provider-specific output.
- [x] Source IR remains source-owned: missing accepted values stay absent
  unless the source adapter or trusted evidence supplies them.
- [x] Neutral authoring/effective data can carry teacher/manual or later
  reviewed accepted values without rewriting source-adapter provenance.
- [x] Gapped/open-cloze PDF/QTI output can distinguish source-proven,
  teacher/manual, reviewed effective, and absent answer-key provenance.
- [x] Multi-gap items are unavailable for automatic evaluation until every
  required gap has trusted accepted values under the governed completeness
  policy.
- [x] Task 303 manual/unkeyed preservation remains available where
  schema/profile validation allows it.
- [x] Target readiness reports target limitations as target capability or
  degradation, not as a reason to remove gap/open-cloze semantics from the
  source-neutral IR.
- [x] Teachers can see whether the target can include a degraded/manual/free-text
  representation, omit the item, or use the item as a manual recreation source.
- [x] QTI 2.1/3.0 gap interaction support is documented separately from
  Exam.net-native gap import/export claims.
- [x] Matching-styled gap/open-cloze source shapes are not promoted to DigiExam
  matching. They remain source-neutral gap/open-cloze authoring structures, and
  only target validators/exporters decide whether matching remapping is safe.
- [x] Reviewed application and LLM advisory tasks can consume the contract but
  are not implemented here.

## Implemented Shape

Task 305 adds the gap/open-cloze authoring slice in:

- `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py`.

`ExamAuthoringGapOpenClozeInteraction` uses the existing
`exam_authoring_ir_v1` schema version; no public schema-version bump was
needed because this is an additive source-neutral authoring slice rather than
a change to the DigiExam API payload schemas.

The neutral interaction owns:

- stable `gap_id`;
- one-based `display_order`;
- typed prompt binding (`html_attribute` or `source_locator`);
- `required_for_auto_evaluation`;
- per-gap accepted values, with typed value-level provenance and evidence;
- normalization profile;
- derived source-neutral answer-key provenance summary;
- optional source evidence records.

The validator separates three states that must not be collapsed:

1. `valid`: the source-neutral contract is structurally valid.
1. `automatic_evaluation_ready`: every required gap has trusted accepted
   values under the selected normalization profile.
1. `target_export_ready`: a target profile can emit the interaction without
   unsupported target degradation.

Missing accepted values on required gaps keep the interaction structurally
valid but not automatically evaluable. Duplicate gap IDs, blank IDs, unknown
IDs, blank accepted values, duplicate normalized values, duplicate display
orders, accepted values with absent or value-level mixed provenance, and
accepted values whose typed provenance contradicts known evidence origin are
contract failures.

Per-value provenance is the validation authority. Accepted values must carry a
concrete trust state: `source_provided`, `teacher_provided`, or `reviewed`. The
aggregate answer-key provenance is a derived summary only: it is `absent` when
no accepted values exist, a single provenance when all values share it, and
`mixed` when a multi-gap or multi-value key combines source-provided,
teacher-provided, or reviewed accepted values.

Normalization is explicit and validation-owned:

- `exact_trim_case_sensitive`;
- `trim_case_insensitive`;
- `trim_case_punctuation_insensitive`.

Spelling variants are not inferred by normalization. They must be represented
as separate accepted values supplied by source, teacher/manual, or reviewed
evidence.

The DigiExam adapter maps existing source-specific gap data into the neutral
contract:

- `DigiExamIrItem.gaps[].guid` -> `ExamAuthoringGap.gap_id`;
- `.dxe` `bodyHTML` `span dx-wg-id` -> prompt binding;
- `answer_key.correct_gap_answers[]` -> ID-bound accepted values with
  value-level provenance;
- `.dxe` populated validations and sanitized result-PDF correct labels ->
  source-provided neutral provenance;
- manual overlay keys -> teacher-provided neutral provenance.

DigiExam remains a source adapter. This task does not make
`DigiExamIntermediateExam` the universal authoring model, does not introduce a
DigiExam matching item type, and does not make QTI/PDF exporters consume the
neutral IR as their primary runtime input yet. Task 307 remains the later
architecture cutover authority for target validators/exporters consuming
`ExamAuthoringIR v1` directly.

## DXE Evidence

Task 305 rechecked every `.dxe` file available under `inputs/` on
2026-05-15, including tracked fixtures, local-private evidence, and the ignored
OneDrive validation corpus:

- 27 `.dxe` files parsed successfully;
- 340 parsed items;
- 21 gap-fill items;
- 113 total gap placeholders;
- every observed gap placeholder was represented in `.dxe` `blanks[]`;
- every observed `blanks[]` entry used only `guid` and `validations`;
- every observed `validations` array was empty;
- every observed gap GUID was bound back into `bodyHTML` through a
  `span dx-wg-id` prompt binding.

The committed tests preserve this as metadata-only evidence. They do not print
raw prompt text, raw `.dxe` payloads, user metadata, or embedded assets.

## Target-Profile Planning Decision

Task 305 implements a layered contract:

1. The `ExamAuthoringIR v1` layer preserves gapped/open-cloze source intent,
   gap IDs, display order, prompt binding, accepted values, normalization
   profile, completeness rules, provenance, and evidence.
1. Target validators decide what can be exported. Unsupported native export is
   expressed through target-readiness rows and teacher choices, not by
   weakening the neutral IR.
1. General QTI validation may support QTI 2.1/3.0 gap interactions. Exam.net
   native import/export support remains unclaimed until there is an Exam.net
   proof path.
1. Matching-styled gap/open-cloze items may be remapped by target exporters
   only when the neutral IR has enough structure and validation evidence. That
   remapping belongs in target conversion logic, not source parser heuristics.

Source notes:

- QTI 3 Best Practices and Implementation Guide documents
  `qti-gap-match-interaction` as source choices paired into text gaps:
  <https://www.imsglobal.org/spec/qti/v3p0/impl/>
- QTI 2.1 binding includes `gapMatchInteraction`:
  <https://www.imsglobal.org/question/qtiv2p1/imsqti_bindv2p1.html>
- Exam.net publicly advertises fill-the-gaps as an authoring question type,
  but this is not a shipped Sir Convert import/export proof:
  <https://exam.net/how-it-works>

## Likely Implementation Surface

Minimum Sir Convert update surface:

- `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py`;
- `scripts/sir_convert_a_lot/domain/exam_authoring_schema_versions.py` if the
  neutral schema version needs an explicit revision;
- `scripts/sir_convert_a_lot/domain/digiexam_contracts.py` and
  `scripts/sir_convert_a_lot/domain/digiexam_ir_contracts.py` only where the
  current DigiExam route must map existing `.dxe` gap data into the neutral
  contract;
- `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay_contracts.py`
  and `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay.py` for any
  public manual accepted-value payload cutover;
- `scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf_items.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_examnet_qti_adapter.py`;
- generated OpenAPI if public overlay/effective/readiness fields change;
- focused neutral contract, DigiExam gap mapping, target-readiness, OpenAPI,
  and migration-bundle tests.

Minimum documentation update surface:

- `docs/converters/exam-authoring-ir-v1-contract.md`;
- `docs/converters/digiexam-intermediate-exam-representation-contract.md`;
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`;
- `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`;
- `docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md`;
- `docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md`;
- `.codex/handoff.md` if the next-action pointer changes.

## Stop Conditions

- Stop if accepted values cannot be represented as exact gap-ID-bound data.
- Stop if the implementation would infer accepted values from visible prompt
  text without trusted source, teacher/manual, or reviewed evidence.
- Stop if QTI/PDF rendering would need target-specific labels inside the
  source-neutral authoring contract.
- Stop if normalization semantics would change source evidence or hide a
  teacher review decision.
- Stop if target limitations are encoded as parser or IR restrictions instead
  of target-readiness/export validation.
- Stop if the implementation deepens DigiExam-specific DTOs into reusable
  source-neutral gap/open-cloze contracts.
- Stop if matching-styled gap/open-cloze shapes require a DigiExam matching
  item type or source-parser remapping to matching.
- Stop if Exam.net gap import/export support would be claimed without a
  governed vendor proof path.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
