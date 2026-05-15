---
id: task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary
title: Define source-neutral ExamAuthoringIR v1 and adapter boundary
type: task
status: done
priority: critical
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md
labels:
  - exam-authoring-ir
  - source-adapter
  - architecture
  - hard-blocker
  - parser-boundary
---

Architecture proof slice before widening source parser coverage.

## Objective

Define the first `ExamAuthoringIR v1` source-neutral contract slice by
extracting matching interaction definitions from the current
`DigiExamIntermediateExam` adapter-shaped contracts.

This task prevents the current DigiExam adapter shape from becoming the
implicit universal exam model. `DigiExamIntermediateExam` is not a future
source-neutral IR; it is the existing DigiExam parser adapter shape, built
mostly from DigiExam `.dxe` concepts. The task should pull the matching item
contract out into the first source-neutral authoring IR slice so later
developers have a concrete pattern for the intended architecture:

`source parser -> adapter -> ExamAuthoringIR v1 -> target validators/exporters`.

This is not the full target-flow cutover. Current DigiExam target flow may
continue to use the existing DigiExam adapter shape until the remaining
source-independent item concepts are ready to extract. The next known
prerequisite for that broader extraction is Task 305 for gapped/open-cloze
accepted values.

Canonical DigiExam `.dxe` sources do not carry matching items. Matching is the
exception that should be source-neutral now because it has no DigiExam-native
source items to parse. Matching-capable fixtures for this architecture must
come from source families that actually support matching, such as Exam.net PDF
artifacts or teacher-authored structured DOCX/Markdown, not from synthetic
DigiExam matching assumptions.

## Hard Blocker

No new Exam.net PDF source parser, teacher-provided structured DOCX parser, or
teacher-provided structured Markdown parser may be implemented until this task
is completed or explicitly superseded by an approved architecture decision.

New source parser tasks may be planned, researched, and fixture-inventoried,
but implementation must stop before production parser logic if it would emit a
source-specific parse model directly into target exporters or duplicate
DigiExam parsing logic.

## Required Architecture

- Source parsers own extraction and source evidence only.
- Source adapters map source-native parse results into `ExamAuthoringIR v1`.
- Target validators/exporters should ultimately consume `ExamAuthoringIR v1`,
  not `DigiExamIntermediateExam`, Exam.net PDF extraction DTOs, or DOCX
  extraction DTOs directly.
- The current `DigiExamIntermediateExam` construction remains the DigiExam
  adapter shape for now. This task extracts only the matching interaction
  contract into `ExamAuthoringIR v1`; later tasks extract the remaining
  source-independent authoring concepts once the DigiExam adapter covers them.
- Future Exam.net PDF and teacher-authored DOCX/Markdown parsers must produce
  their own source-native parse models and then map through the same neutral
  adapter boundary.
- Keyed matching QTI export must be implemented through the neutral
  `ExamAuthoringIR v1 -> QTI` path, not through a speculative
  `DigiExamIntermediateExam -> ExamNetQtiMatchPair` adapter.

## PR Scope

- Define the first `ExamAuthoringIR v1` contract shape and version authority for
  matching interactions.
- Move matching reusable concepts into the neutral contract:
  - matching source choices;
  - matching target choices;
  - per-choice association bounds;
  - unmatched target distractors;
  - directed answer pairs;
  - answer-key provenance;
  - source evidence hooks and validation provenance needed by future adapters.
- Keep matching answer-key provenance as a whole-key trust state in this
  slice. Aggregate `mixed` provenance must fail validation until a future
  governed matching-pair contract adds per-pair provenance and evidence.
- Define source evidence/span semantics that can represent DigiExam `.dxe`,
  layout PDF, DOCX, Markdown, and future source families without faking a
  DigiExam source shape.
- Refactor matching contract definitions out of DigiExam-named adapter modules
  where they are source-neutral.
- Document that the DigiExam adapter does not emit keyed matching interactions
  from `.dxe`; matching examples and QTI match-pair bridging must use real
  matching-capable source fixtures.
- Document the later extraction path for choices, gaps/open-cloze, provenance,
  evidence spans, warnings, manual-follow-up state, validators, and exporters.
- Do not cut current DigiExam PDF/QTI/readiness runtime flow to
  `ExamAuthoringIR v1` in this slice unless the implementation can do so without
  widening beyond the matching-contract proof.

## Deliverables

- [x] First `ExamAuthoringIR v1` contract document and schema/version authority
  for matching interactions.
- [x] Source-adapter boundary documentation for DigiExam, Exam.net PDF, DOCX,
  and Markdown source families.
- [x] Matching contract definitions extracted from the DigiExam adapter-shaped
  contracts into source-neutral `ExamAuthoringIR v1` names.
- [x] Neutral matching examples that model real matching-capable source shapes
  without synthetic DigiExam matching fixtures, plus a QTI bridge plan for
  later real source adapters.
- [x] Later target-validator/exporter migration plan showing how the full
  authoring IR extraction should proceed after Task 305.
- [x] Architecture guard or review checklist that blocks new source parsers
  from bypassing the neutral IR boundary.

## Out of Scope

- Implementing Exam.net PDF source parsing.
- Implementing teacher-authored DOCX or Markdown source parsing.
- Implementing a DigiExam keyed matching QTI bridge.
- Refactoring choice, gap/open-cloze, free-text, warnings, manual-follow-up, or
  exporter logic out of `DigiExamIntermediateExam` before Task 305 closes the
  gapped/open-cloze contract.
- Rewriting unrelated DigiExam parser internals that are only extraction
  helpers and do not leak into target-facing contracts.
- Adding compatibility aliases that make source-native DTOs look like the
  neutral IR without an explicit adapter.
- Cutting current DigiExam target validators/exporters to the full
  `ExamAuthoringIR v1` before the remaining source-independent item concepts
  are extracted in later tasks.

## Acceptance Criteria

- [x] A governed first-slice `ExamAuthoringIR v1` matching contract exists with
  schema/version authority and docs.
- [x] `DigiExamIntermediateExam` is documented as the current DigiExam adapter
  shape, not the future source-neutral authoring IR.
- [x] Matching source choices, target choices, association bounds,
  distractors, directed pairs, provenance, and evidence hooks are represented
  in source-neutral terms.
- [x] Tests prove the neutral matching contract validates QTI-permissive
  matching shapes and current Exam.net PDF target constraints without requiring
  DigiExam matching fixtures.
- [x] The later extraction path after Task 305 is documented without forcing a
  full target-validator/exporter cutover in this slice.
- [x] A static or review-enforced guard prevents new source parsers from
  bypassing the source-adapter-to-neutral-IR boundary.

## Test Requirements

- [x] Contract tests for first-slice `ExamAuthoringIR v1` matching
  serialization and versioning.
- [x] Tests prove DigiExam `.dxe` keyed matching remains absent and no DigiExam
  parser path is required to exercise neutral matching.
- [x] Neutral matching tests use source-neutral examples that reflect Exam.net
  PDF or teacher-authored structured DOCX/Markdown matching shapes, not
  synthetic DigiExam matching assumptions.
- [x] Target-profile tests prove neutral matching association bounds can express
  QTI-permissive shapes, reject malformed negative or impossible bound shapes,
  and preserve the current Exam.net PDF one-to-one-plus-distractor constraint.
- [x] Contract tests prove aggregate `mixed` matching provenance fails closed
  while reviewed whole-key provenance remains valid.
- [x] Architecture guard or review checklist test proving new source parser
  tasks must target `ExamAuthoringIR v1`.

## Implementation Evidence

- Added `domain.exam_authoring_ir_contracts` and
  `domain.exam_authoring_schema_versions` as the source-neutral matching
  contract/version authority.
- Neutral validation rejects malformed interaction and per-choice association
  bounds before target-profile validators interpret the pair set.
- Neutral validation rejects aggregate `mixed` matching provenance because
  current matching pairs do not carry per-pair provenance/evidence.
- Removed DigiExam-owned matching structures, overlay payloads, effective-item
  patch fields, target-readiness matching rows, and OpenAPI matching overlay
  components from the DigiExam migration path.
- Updated DigiExam PDF/IR tests so matching-like `Para ihop` PDF rows are
  preserved as visible source lines but classified as unsupported/unknown
  DigiExam evidence.
- Updated Skriptoteket review consumers so DigiExam IR review parsing and
  fixtures no longer expect a `matching` field.

## Stop Conditions

- Stop if the neutral IR starts copying DigiExam field names that do not make
  sense for Exam.net PDF, DOCX, or Markdown sources.
- Stop if this slice tries to refactor the full `DigiExamIntermediateExam`
  surface before Task 305 lands.
- Stop if matching is reintroduced as a DigiExam parser capability or requires
  synthetic DigiExam matching fixtures.
- Stop if a DigiExam keyed matching QTI adapter is proposed; DigiExam `.dxe`
  does not carry matching items.

## Close-Out

- Update Story 45 and any future source-parser tasks to list this task as a
  prerequisite.
- Refresh generated docs indexes with `pdm run docs-sync`.
- Run `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
