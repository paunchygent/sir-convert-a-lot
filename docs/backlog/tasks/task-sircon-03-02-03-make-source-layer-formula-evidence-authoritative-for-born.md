---
type: task
id: TASK-SIRCON-03-02-03
title: Make source-layer formula evidence authoritative for born-digital PDFs
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
story: ST-SIRCON-03-02
task_kind: story
acceptance_criteria:
- Born-digital/source-backed formula regions preserve source-layer evidence unless
  a generated formula candidate passes a source-backed acceptance gate.
- Source-layer authority is applied only after the evidence model classifies the region
  as `usable`; `partial_or_unusable` and `absent` evidence remain explicit states
  with governed fallback behavior.
- Every encountered source-backed formula page window has an explicit best-effort
  artifact representation decision; the accepted terminal Markdown uses deterministic
  `formula-not-decoded` placeholders plus safe authority metadata instead of hallucinated
  generated formula text.
- Accurate table mode can run without automatically committing generative formula
  VLM output.
- No-source/raster formula regions still have a governed formula VLM path with the
  Task 344 stop/compile runtime controls intact.
- Result/replay metadata tells the caller whether formula VLM was skipped, advisory,
  accepted, rejected, or fell back, and why. The initial Task 342 terminal status/result/manifest
  presentation slice now surfaces that metadata without adding a second authority
  policy.
- The pages `13-16` incident replay contains no accepted-output recurrence of the
  known leaked `</formula`, `\mathbmath`, repeated `\mathbf`, or pre-remediation corrupted
  formula/prose markers when source-layer evidence is usable.
- Any remaining Granite/ROCm latency is explicitly attributed as residual model-throughput
  work for Task 343/Task 74, not mistaken for successful formula-authority remediation.
- Docs index and validation gates pass.
retired_ids:
- task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs
---

## Context

State the bounded implementation or proof need and the parent story behavior it
supports.

## Decision And Assumption Ledger

Every material implementation choice must already be closed by an accepted
source before scaffolding this task.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

## Story Contract Slice

Define the single-responsibility implementation or proof slice derived from the
parent story. Name the exact surfaces this task may change.

## Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this task.

## Plan

State the smallest implementation approach that satisfies the story slice and
acceptance criteria.

## Implementation Steps

List ordered steps small enough to execute and verify without inventing scope.

## Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

## Validation

List the exact focused and repository gates required before closeout and retain
concise results after they run.

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to planning.

## Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

## Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

## Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

## Implementation Review

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

## Historical Source Summary

Task 345 establishes the quality-preserving authority policy for formula output in
born-digital PDFs. Usable source-layer evidence is authoritative; generated formula
VLM output is skipped or remains advisory unless a governed source-backed quality
gate proves fidelity. Evidence states are `usable`, `partial_or_unusable`, and
`absent`; the latter two require explicit best-effort fallback and must never drop
a formula region.

### Ownership and sequencing

Task 345 owns source-layer extraction, evidence classification, authority decisions,
artifact representation, reconciliation, and safe runtime metadata. Task 342 only
presents the metadata in CLI/manifest/status surfaces. Task 343 consumes evidence and
timings for conversion decisions and performance attribution. Task 344 owns generation
stability and replay harnesses, while Task 346 evaluates specialist candidates before
any production replacement. No later task may create a second extractor or authority
policy.

The implementation sequence is: evidence/authority substrate; best-effort
representation ladder; page-window or region reconciliation; runtime metadata;
Task 342 presentation; Task 343 consumption; and accepted-artifact replay.

### Evidence and decisions

The governing incident was Docling/Granite formula enrichment: stop controls fixed a
page-14 non-returning generation loop, but pages 13-16 still contained leaked
`</formula`, repeated `\\mathbf`, `\\mathbmath`, and corrupted formula/prose.
OCR was disabled, so the defect was in formula enrichment rather than classic OCR.
PyMuPDF and PDF text probes showed coordinate-backed source material, while embedded
font and Poppler failures demonstrated that extraction quality varies by region and
extractor. Source authority is therefore classified per region/window, not assumed
globally.

`auto` remains quality-first. Do not add raw backend/OCR/table/formula flags, a
slow/fast remediation lane, a PyMuPDF-only route, or handwritten complexity
heuristics. PyMuPDF is evidence/localization/fallback substrate, not a final
semantic LaTeX converter. Source-backed regions prefer preserved source evidence;
absent or unusable regions may use the governed VLM ladder. Rejected candidates still
produce explicit artifact representation, warnings, and safe metadata.

### Implementation and proof state

The source evidence model, PyMuPDF adapter, authority policy, Docling fallback guard,
best-effort page-window representation, and structured authority metadata are
implemented. Accurate table mode remains enabled while usable source-backed formula
VLM enrichment is skipped. No-source paths retain the CodeFormulaV2/Granite ladder;
runtime-unavailable paths emit explicit fallback metadata. Accepted pages 13-16 replay
reported `formula_authority.action=skipped`, `source_evidence_state=usable`, zero
formula-VLM calls, and no recurrence of known leakage markers; non-generative regions
use deterministic `formula-not-decoded` placeholders.

Remaining governed work is Task 343 conversion-decision consumption and final docs
index/validation gates. Task 342 owns any remaining presentation alignment.
