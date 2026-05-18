---
id: task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract
title: Define unified source-neutral exam authoring correction apply contract
type: task
status: proposed
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

The current Task 324 matching route is a necessary bridge for the producer route
that exists today. It should not become the target architecture. Task 324
exists because matching lacked a neutral producer route while choice, gap/open
cloze, review decisions, item-content repair, and point correction still had
legacy DigiExam-overlay producer paths that Skriptoteket could already submit
through the reviewed overlay/application flow. That is historical
implementation asymmetry, not a product boundary.

This task is the producer-owned prerequisite for the real Skriptoteket
`PR-0332` teacher overlay implementation. It must give Skriptoteket one
contract for the correction fields promised by `PR-0332` without coupling
teacher authoring to DigiExam overlay names or to the temporary Task 324
matching bridge route.

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
- Define migration compatibility from existing `digiexam_ingestion_overlay_v2`
  and Task 324 matching apply semantics into the unified contract without
  silently changing current PR-0332 consumer behavior.

This task is contract-first and runs under proposed ADR-0011. Runtime
implementation, HuleEdu proxy work, and Skriptoteket UI migration each require
separate governed implementation slices after ADR-0011 and this contract are
accepted.

## Out of Scope

- Implementing the new route.
- Removing the Task 324 matching route or the existing DigiExam overlay path.
- Skriptoteket UI changes.
- HuleEdu Gateway implementation changes.
- New inference of answer keys, point values, rubrics, candidate decisions, or
  item text from source labels, prompt text, renderer output, or LLM candidates
  without trusted source, teacher, or reviewed evidence.
- Changing target renderer behavior or QTI/PDF readiness policy.

## Deliverables

- [ ] Contract documentation for
  `POST /v2/exam-authoring/corrections/apply`.
- [ ] Typed correction-entry taxonomy covering item text, points, choice keys,
  gap/open-cloze accepted values, matching keys, review decisions, and
  candidate suppression.
- [ ] Per-entry validation matrix for supported, blocked, and
  upstream-required correction shapes, including item-type compatibility and
  nested interaction binding rules.
- [ ] Review-decision and candidate-suppression state-machine semantics that
  keep candidate rejection separate from accepted current-state export and
  teacher-authored replacement keys.
- [ ] Source-bound request envelope and producer-state validation rules.
- [ ] Effective-state/readiness/report response contract, including how
  accepted corrections appear in effective IR and how rejected or blocked
  corrections appear in reports without unlocking files.
- [ ] Compatibility plan that names Task 324 as bridge work and prevents route
  proliferation for future item families.
- [ ] Consumer migration notes for HuleEdu `/sir-convert` proxying and
  Skriptoteket teacher-correction API usage.
- [ ] ADR-0011 references are synchronized and any implementation plan uses
  conditional language until ADR-0011 is accepted.

## Acceptance Criteria

- [ ] The task defines one product-facing correction/apply route and explicitly
  rejects the target pattern of one route per item type.
- [ ] The contract is source-neutral: no request or response type requires a
  consumer to know whether the original item came from DigiExam, Exam.net,
  CSV, DOCX, Markdown, or a future importer.
- [ ] Source adapters remain responsible for ingestion and source-native parse
  models; Sir Convert remains responsible for correction validation,
  effective-state projection, target readiness, and artifact availability.
- [ ] The correction entry union covers the currently known teacher correction
  families without collapsing their validation rules into a weak generic
  payload.
- [ ] Prompt/stem and visible-option patches, point corrections, choice keys,
  gap/open-cloze accepted values, matching keys, review decisions, and
  candidate suppression all have named request fields or typed union variants;
  none are left to untyped JSON blobs or source-adapter-specific overlay
  fields.
- [ ] Candidate suppression is defined as advisory-candidate suppression only
  unless a separate explicit review-decision entry says otherwise; suppression
  never creates answer-key provenance, never accepts unkeyed export, and never
  unlocks PDF/QTI artifacts by itself.
- [ ] Accepted candidate application and teacher-authored replacement
  corrections are distinguishable in request payloads, effective state,
  correction reports, and audit/provenance fields.
- [ ] Source binding is fail-closed for every correction entry before effective
  state, target readiness, or artifact availability is projected.
- [ ] Existing Task 322/323/324 behavior is mapped as compatibility input, not
  erased or misrepresented as the final architecture.
- [ ] ADR-0011 remains proposed unless a separate review/acceptance task closes
  the decision.
- [ ] HuleEdu/Skriptoteket follow-up sequencing is explicit: Sir Convert
  contract first, authenticated edge proxy second, Skriptoteket consumer
  migration third.
- [ ] The route response gives consumers enough producer-owned state to keep
  browser-local drafts non-authoritative: local edits cannot unlock files until
  this route returns accepted effective state/readiness.
- [ ] Privacy/provenance rules remain at least as strict as the DigiExam overlay
  and matching apply contracts: no raw `.dxe`, raw PDF text, raw overlay JSON,
  raw provider data, student-result data, credentials, identity markers,
  earned scores, wrong selections, free-text student answers, or
  per-student performance history in the correction contract or reports.

## Validation Plan

- [ ] `pdm run docs-sync`
- [ ] `pdm run docs-validate`
- [ ] `pdm run skills-validate`
- [ ] `pdm run handoff-validate`
- [ ] `git diff --check`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
