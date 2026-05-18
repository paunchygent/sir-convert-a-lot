---
id: task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract
title: Define unified source-neutral exam authoring correction apply contract
type: task
status: completed
priority: critical
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-322-add-points-scoring-correction-producer-dto-before-pr-0332.md
  - docs/backlog/tasks/task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket.md
  - docs/backlog/tasks/task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - exam-authoring-ir
  - correction-contract
  - source-neutral
  - skriptoteket
  - api-contract
---

Producer-owned contract slice for the next clean teacher-correction API.

## Objective

Define one source-neutral Sir Convert correction/apply contract for teacher exam
authoring so downstream products do not accumulate one route per original
source family or one route per item type.

The current Task 324 matching route is historical bridge work for the producer
route that exists today. It must not become the target architecture or a
long-lived compatibility surface. Task 324 exists because matching lacked a
neutral producer route while choice, gap/open-cloze, review decisions,
item-content repair, and point correction still had legacy DigiExam-overlay
producer paths that Skriptoteket could already submit through the reviewed
overlay/application flow. That is historical implementation asymmetry, not a
product boundary.

This task is the producer-owned prerequisite for the real Skriptoteket
`PR-0332` teacher overlay implementation beyond the already-built Task 324
historical bridge. It must give Skriptoteket one contract for the correction
fields promised by `PR-0332` without coupling teacher authoring to DigiExam
overlay names, source-adapter labels, or the Task 324 matching-specific route.
New PR-0332 producer/consumer work must not be steered back into the abandoned
adapter or route-per-item pattern.

## PR Scope

- Define the canonical v2 route shape for source-neutral teacher corrections:
  `POST /v2/exam-authoring/corrections/apply`.
- Define typed correction entries for:
  - item text, stem, prompt, visible option text, or other teacher-visible
    item patching;
  - point correction;
  - manual choice answer key;
  - manual gap/open-cloze accepted values;
  - manual matching answer key;
  - review decision and candidate suppression.
- Define review and candidate-suppression semantics explicitly:
  - candidate suppression rejects or hides an advisory candidate and must not
    apply a key, create manual-unkeyed state, clear target readiness blockers,
    or masquerade as accepted current-state export;
  - review decisions are submitted producer-visible correction entries with
    explicit state transitions, not browser-local UI flags;
  - accepted candidate application, teacher-authored replacement, and
    candidate suppression remain distinct in request, report, effective state,
    and target-readiness projection.
- Define the source-bound envelope that lets source adapters remain ingestion
  details while Sir Convert validates corrections against producer-returned
  state, source fingerprints, source schema versions, item/interaction IDs, and
  item-type compatibility.
- Define the binding invariant for every correction entry: source file or
  source bundle identity, source IR schema/version, item ID, item sequence,
  item type, source item fingerprint when present in producer state, and
  interaction/choice/gap/matching IDs where the correction touches a nested
  interaction. Stale, missing, or mismatched binding fails before rendering or
  target readiness.
- Define the response projection Skriptoteket needs after apply:
  effective `ExamAuthoringIR v1` or effective source-bound authoring state,
  accepted/rejected correction report, target readiness, and artifact
  availability.
- Keep HuleEdu and Skriptoteket as consumers of the single route through the
  authenticated `/sir-convert` edge. HuleEdu should proxy the route; it should
  not create item-specific Gateway endpoints as the long-term shape.
- Preserve source-adapter boundaries: DigiExam, Exam.net, future CSV/importer,
  DOCX, Markdown, or other adapters may provide source-specific parse models,
  but the teacher correction API must not expose source-specific overlay names
  as its product surface.
- Define hard-cut migration from existing `digiexam_ingestion_overlay_v2` and
  Task 324 matching apply semantics into the unified contract without silently
  changing correction semantics.
- Define the follow-up implementation slice shape for the hard cut:
  - add the unified `POST /v2/exam-authoring/corrections/apply` runtime route;
  - move matching semantics into a typed `manual_matching_answer_key`
    correction entry;
  - remove the Task 324
    `POST /v2/exam-authoring/matching/manual-answer-key/apply` route,
    route registration, request/response-only dead code, OpenAPI path exposure,
    and route-specific tests that no longer describe the canonical contract;
  - preserve the reusable matching DTO/domain validation semantics only where
    they remain part of the unified correction-entry implementation;
  - prove the hard cut without preserving the old route as an adapter, shim,
    alias, wrapper, or compatibility layer.
- Tighten the PR-0332 sequencing contract:
  - Task 324 remains historical bridge evidence only;
  - the unified route implementation must remove or replace
    `POST /v2/exam-authoring/matching/manual-answer-key/apply` in the same
    governed implementation slice;
  - no adapter, shim, alias, wrapper, or compatibility layer may keep the
    matching-specific route callable after the unified correction route lands;
  - new PR-0332 teacher-correction work may target the unified
    `/v2/exam-authoring/corrections/apply` contract only after this task closes,
    ADR-0011 is accepted through the retained review/acceptance path, and the
    runtime or consumer work is governed by its own implementation slice;
  - no consumer, HuleEdu proxy, or Sir Convert route should add another
    source-adapter or item-specific correction apply surface unless a later
    governed task proves the unified contract cannot cover it.

This task was contract-first and ran under then-proposed ADR-0011. Runtime
implementation, HuleEdu proxy work, and Skriptoteket UI migration each require
separate governed implementation slices after ADR-0011 acceptance and this
contract.

For this task, "implementation" means implementation of the governed contract
documentation and follow-up plan only. It does not authorize Python route code,
OpenAPI runtime generation, router registration changes, test rewrites, or dead
code removal. Those belong to the later unified-route implementation slice, which
must add `POST /v2/exam-authoring/corrections/apply` and remove the Task 324
matching-specific route and dead code in the same governed change.

## Out of Scope

- Implementing the new route.
- Runtime removal of the Task 324 matching route or the existing DigiExam
  overlay path in this contract-only task. The follow-up unified-route
  implementation must perform a governed hard cut for the Task 324 route rather
  than preserving it through a wrapper, alias, shim, adapter, or compatibility
  layer.
- Editing Python runtime modules, generated OpenAPI artifacts, router
  registration code, request/response DTOs, or tests for the hard cut.
- Skriptoteket UI changes.
- HuleEdu Gateway implementation changes.
- New inference of answer keys, point values, rubrics, candidate decisions, or
  item text from source labels, prompt text, renderer output, or LLM candidates
  without trusted source, teacher, or reviewed evidence.
- Changing target renderer behavior or QTI/PDF readiness policy.

## Deliverables

- [x] Contract documentation for
  `POST /v2/exam-authoring/corrections/apply`.
- [x] Typed correction-entry taxonomy covering item text, points, choice keys,
  gap/open-cloze accepted values, matching keys, review decisions, and
  candidate suppression.
- [x] Per-entry validation matrix for supported, blocked, and
  upstream-required correction shapes, including item-type compatibility and
  nested interaction binding rules.
- [x] Review-decision and candidate-suppression state-machine semantics that
  keep candidate rejection separate from accepted current-state export and
  teacher-authored replacement keys.
- [x] Source-bound request envelope and producer-state validation rules.
- [x] Effective-state/readiness/report response contract, including how
  accepted corrections appear in effective IR and how rejected or blocked
  corrections appear in reports without unlocking files.
- [x] Hard-cut migration plan that names Task 324 as historical bridge work,
  maps matching semantics into the unified entry type, and prevents route
  proliferation for future item families without a wrapper, alias, shim,
  adapter, or compatibility layer.
- [x] Follow-up unified-route implementation slice is explicitly shaped: add
  `POST /v2/exam-authoring/corrections/apply`, remove
  `POST /v2/exam-authoring/matching/manual-answer-key/apply` and its route-only
  dead code, retain only reusable validation semantics, and prove no adapter,
  shim, alias, wrapper, or compatibility layer remains.
- [x] PR-0332 guardrail that prevents new consumer work from targeting the
  abandoned adapter/route-per-item pattern after Task 327, while still requiring
  ADR-0011 acceptance and a governed runtime or consumer implementation slice
  before the unified contract is treated as runtime-ready.
- [x] Consumer migration notes for HuleEdu `/sir-convert` proxying and
  Skriptoteket teacher-correction API usage.
- [x] ADR-0011 references were synchronized and implementation planning used
  conditional language while ADR-0011 remained proposed at Task 327 closeout.

## Acceptance Criteria

- [x] The task defines one product-facing correction/apply route and explicitly
  rejects the target pattern of one route per item type.
- [x] The contract is source-neutral: no request or response type requires a
  consumer to know whether the original item came from DigiExam, Exam.net,
  CSV, DOCX, Markdown, or a future importer.
- [x] Source adapters remain responsible for ingestion and source-native parse
  models; Sir Convert remains responsible for correction validation,
  effective-state projection, target readiness, and artifact availability.
- [x] The correction entry union covers the currently known teacher correction
  families without collapsing their validation rules into a weak generic
  payload.
- [x] Prompt/stem and visible-option patches, point corrections, choice keys,
  gap/open-cloze accepted values, matching keys, review decisions, and
  candidate suppression all have named request fields or typed union variants;
  none are left to untyped JSON blobs or source-adapter-specific overlay
  fields.
- [x] Candidate suppression is defined as advisory-candidate suppression only
  unless a separate explicit review-decision entry says otherwise; suppression
  never creates answer-key provenance, never accepts unkeyed export, and never
  unlocks PDF/QTI artifacts by itself.
- [x] Accepted candidate application and teacher-authored replacement
  corrections are distinguishable in request payloads, effective state,
  correction reports, and audit/provenance fields.
- [x] Source binding is fail-closed for every correction entry before effective
  state, target readiness, or artifact availability is projected.
- [x] Existing Task 322/323/324 behavior is mapped into unified correction-entry
  semantics, not erased or misrepresented as the final architecture.
- [x] PR-0332 sequencing is tightened: already-built Task 324 matching behavior
  is historical bridge evidence only, and new teacher-correction
  producer/consumer work can target the unified contract only after ADR-0011 is
  accepted and the work is attached to its own governed implementation slice,
  rather than the old adapter path or matching-specific route.
- [x] The task clearly distinguishes contract completion from runtime
  implementation: no code or generated OpenAPI runtime artifacts are changed in
  Task 327, and the later hard-cut implementation slice is required to add the
  unified route and remove the Task 324 matching route/dead code atomically.
- [x] ADR-0011 remained proposed at Task 327 closeout until a separate
  review/acceptance task closed the decision.
- [x] HuleEdu/Skriptoteket follow-up sequencing is explicit: Sir Convert
  contract first, authenticated edge proxy second, Skriptoteket consumer
  migration third.
- [x] The route response gives consumers enough producer-owned state to keep
  browser-local drafts non-authoritative: local edits cannot unlock files until
  this route returns accepted effective state/readiness.
- [x] Privacy/provenance rules remain at least as strict as the DigiExam overlay
  and matching apply contracts: no raw `.dxe`, raw PDF text, raw overlay JSON,
  raw provider data, student-result data, credentials, identity markers,
  earned scores, wrong selections, free-text student answers, or
  per-student performance history in the correction contract or reports.

## Implementation Evidence

Completed on 2026-05-18 as a docs-only contract slice.

- Created `docs/converters/exam-authoring-corrections-apply-contract.md` as the
  draft unified source-neutral correction/apply contract under then-proposed
  ADR-0011.
- Defined `exam_authoring_corrections_apply_request_v1` and
  `exam_authoring_corrections_apply_result_v1` as the initial request/response
  schema names for the future route.
- Defined the request envelope, source-binding invariants, sanitized
  producer-returned source state, typed correction-entry union, validation
  matrix, effective-state/readiness/report response projection, privacy rules,
  and HuleEdu/Skriptoteket sequencing.
- Mapped Task 322/323/324 and `digiexam_ingestion_overlay_v2` semantics into the
  unified entry taxonomy without promising a runtime compatibility layer.
- Recorded the hard-cut follow-up implementation shape: the later runtime slice
  must add `POST /v2/exam-authoring/corrections/apply` and remove
  `POST /v2/exam-authoring/matching/manual-answer-key/apply`, route
  registration, route-only dead code, OpenAPI path exposure, and obsolete
  route-specific tests in the same governed change.
- Preserved ADR-0011 as proposed at Task 327 closeout; the later Review 23
  acceptance step owns the decision status change. This task did not implement
  runtime route code.
- Validation passed with `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Validation Plan

- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Checklist

- [x] Contract implementation complete
- [x] Validation complete
- [x] Docs updated
