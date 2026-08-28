---
type: reference
id: REF-SIRCON-GENERAL-exam-net-qti-import-contract-empirical-observations
title: Exam.net QTI import contract empirical observations
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-29'
status: active
reference_kind: general
summary: 'Empirically confirmed Exam.net QTI 2.1 importer contract from the 2026-08-28 probe campaign: confirmed lanes, refuted constructions, writer obligations, and open unknowns'
---

## Overview

This reference is the authoritative Exam.net QTI 2.1 import contract for the
export writer. It records what Exam.net's importer actually does, established
by a live probe campaign on 2026-08-28 (family-isolated probe packages
`P001`–`P050`, refined suite `R2*`, combined seven-family package `ALL07`,
standalone short-written-response differential `SWR001`–`SWR010`, simple-answer
placement differential `ESA001`–`ESA007`, and interaction-boundary package
`BND001`–`BND008`; boundary ledger sha256
`9ff8e1602cae0351f41fcf78c4949b1356d0a8422c21e6c91d0bc891134f3060`).

Exam.net's public documentation carries no QTI import contract at all: the
importer is early access and vendor-undocumented. This reference is therefore
the only contract source, and importer behavior may change without notice.
The probe-derived regression fixtures in
`tests/sir_convert_a_lot/exam/test_examnet_qti_contract_rules.py` guard the
writer against silent drift; a future importer change surfaces as a live
import failure, not a fixture failure, and must be re-probed.

This reference supersedes the vendor-reported planning content of
`REF-SIRCON-GENERAL-exam-net-qti-import-contract-and-validation-strategy`,
whose validation-ladder framing predates live importer access.
`TASK-SIRCON-REP-0029` aligned the production writer with this contract.

## Facts And Semantics

Package shape (proven accepted):

- Zip containing `imsmanifest.xml`, one `assessment.xml`
  (`assessmentTest`, resource type `imsqti_test_xmlv2p1`), per-item
  `items/<id>.xml` (`imsqti_item_xmlv2p1`), optional `resources/` media.
- The test resource declares one `<dependency identifierref="...">` per item
  resource. `assessmentTest` wraps one linear/individual `testPart` with one
  visible `assessmentSection` of `assessmentItemRef` entries.
- Item-relative media references resolve as `../resources/<file>` from
  `items/`; package-root-style references fail and leave alt text.

Cross-cutting importer behavior (confirmed):

- `assessmentItem` is the reliable grouping boundary. `assessmentSection`
  nesting, titles, and section-level `rubricBlock` content are discarded.
  Sibling and rubric content inside one item stays attached to that item as
  visible blocks; candidate and scorer views render alike.
- The question stem must live inside the interaction's own `<prompt>` element
  (first interaction child) for choice, matching, and free-text items; images
  for those items go inside the prompt after the stem text (P048). Stem text
  emitted as sibling body content instead splits into a parent information
  block with the interaction nested under it as a promptless sub-question
  that Exam.net flags with a missing-prompt warning (P006; live-confirmed on
  a production package 2026-08-29). Sibling attachment is for genuinely
  supplementary content only, never the stem.
- `correctResponse` supplies the visible answer key for keyed choice and
  matching items. Positive `mapping` entries (with `map_response`) supply
  scoring rules and totals. A mapping without `correctResponse` on a keyed
  item imports scoring with no visible key (an unusable "orphaned" rule).
- `match_correct` does not establish points for multiple-response, matching,
  or gap items. A single negative mapped value can invalidate the item's
  entire scoring contract.
- Exam.net preserves imported source order and ignores the QTI interaction
  `shuffle` attribute; delivery-time shuffling is an Exam.net global or
  section setting.

Confirmed item lanes:

| Exam.net family              | QTI construction                           | Scoring lane                                                                                                                                                                                                                              |
| ---------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Single-choice MCQ (radio)    | `choiceInteraction` single cardinality     | `correctResponse` + one positive mapEntry + `map_response`                                                                                                                                                                                |
| Multi-choice MCQ (checkbox)  | `choiceInteraction` multiple cardinality   | Positive mapEntry per correct id; Exam.net generates additive threshold rules                                                                                                                                                             |
| Matching                     | `matchInteraction` directedPair            | `correctResponse` pairs + positive pair mappings; many-left-to-one and unmatched right distractors work; every displayed left choice needs at least one correct association or the item is rejected on save                               |
| Gap text (Lucktext)          | inline `textEntryInteraction`              | Mapping alone yields accepted variants and per-gap scoring, with or without `responseProcessing`; one and two gaps proven                                                                                                                 |
| Selectable gap (specialized) | `inlineChoiceInteraction`                  | `correctResponse` + positive mapping + `map_response`; not a default authoring family                                                                                                                                                     |
| Free text (Fritext, manual)  | `extendedTextInteraction`                  | Each mapped entry becomes one cumulative manual criterion at its mapped value; criterion wording is Exam.net count text, not the map keys; the non-inflating pattern is one mapped criterion at the full item score plus visible guidance |
| Information block            | Content-only item, optional packaged image | No response, no scoring                                                                                                                                                                                                                   |

Refuted constructions (do not build, emit, or re-probe):

- `hottextInteraction` (single and multiple) and the tested generic
  foreign-namespace `customInteraction`: rejected at upload.
- `uploadInteraction`: interaction dropped; only a static information shell
  survives. Static-shell survival never implies interaction support.
- Native `Enkelt svar` via any portable QTI 2.1 construction:
  `textEntryInteraction` becomes Lucktext under every tested placement and
  `extendedTextInteraction` becomes Fritext under every tested differential;
  no third core written-response interaction exists in QTI 2.1. The native
  lane, if any, requires an Exam.net-specific signal or a real prior
  successful archive to diff.
- `gapMatchInteraction` imports only as a reclassified Lucktext dropdown
  (drag-and-drop lost) — a reclassification, not native support.
- QTI `shuffle` as a delivery control; `match_correct` as the scoring
  mechanism for multiple-response, matching, or gaps; SCORE/MAXSCORE outcome
  metadata or `rubricBlock` as criteria/point sources for free text.

Open unknowns (narrow; expansion needs explicit user authorization):

1. Save-and-reopen persistence for the six surviving boundary item shells.
2. Candidate-side execution and grading of the additive multi-response rules
   (`BND002` two-correct/no-wrong submission).
3. A corrected one-left-to-many matching probe where every displayed left row
   is keyed.
4. The Exam.net-specific native `Enkelt svar` signal (requires an actual
   earlier successful archive or vendor export to diff).

## Decisions And Interpretation

Writer obligations derived from this contract (enforced by
`examnet_qti_validation.py` content validators and the regression fixtures):

- Always emit the `assessmentTest` resource with complete dependency wiring.
- Choice, matching, and free-text items carry a non-empty `<prompt>` as the
  interaction's first child holding the stem (and any images); no block
  sibling precedes the interaction in `itemBody`. Gap items keep their
  inline gap text as the body.
- Keyed choice and matching items always emit `correctResponse`, positive
  mappings, and `map_response`; never `match_correct`.
- Never emit negative mapped values, mappings without `correctResponse` on
  keyed choice/matching items, or the `shuffle` attribute.
- Matching emission guarantees every displayed left choice at least one
  correct association.
- Gap items split the item score equally across gaps through per-gap
  mappings; all accepted variants of a gap share its value.
- Free-text items with a machine-usable score emit exactly one mapped
  criterion worth the full item score (non-inflating pattern); manual
  preservation items stay bare.
- Multi-response partial-credit thresholds are Exam.net-generated from the
  additive mappings; the tolerated one-wrong-selection higher threshold is
  accepted behavior until candidate-side grading proof (open unknown 2) says
  otherwise.

Implementation authority for changes to the writer stays with backlog tasks;
this reference records the importer contract, not work state. The raw probe
ledger and builder scripts remain diagnostic evidence in the retained
session; this document is the durable distillation.
