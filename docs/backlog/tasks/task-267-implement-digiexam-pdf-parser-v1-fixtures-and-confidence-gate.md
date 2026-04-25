---
id: task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate
title: Implement DigiExam PDF parser v1 fixtures and confidence gate
type: task
status: proposed
priority: high
created: '2026-04-25'
last_updated: '2026-04-25'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
  - inputs/examples/digiexam-exports/README.md
labels:
  - exam-migration
  - digiexam
  - pdf
  - parser
  - tests
  - confidence
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first production-bound DigiExam parser slice: fixture-backed PDF
extraction for the two tracked jsPDF samples and a confidence gate that prevents
unknown or degraded item shapes from being treated as renderer-ready.

## PR Scope

- Add a small SRP-focused parser module under the Sir Convert code surface for
  DigiExam jsPDF exports. Keep module files below the repo size limit and add
  Google-style module docstrings.
- Use the existing PDF extraction stack where available; do not introduce an ad
  hoc converter script or a renderer-specific shortcut.
- Define typed parser result objects for:
  - source document metadata;
  - item blocks;
  - item type classification;
  - point marker evidence;
  - source spans or page/line evidence;
  - confidence and warning details;
  - answer-key provenance state.
- Add regression fixtures/tests for:
  - `inputs/examples/digiexam-exports/_-25cEkologiprov51-55.pdf`;
  - `inputs/examples/digiexam-exports/_-Kemikapitel2ht2525dECA.pdf`.
- Assert the research-baseline expectations:
  - ecology sample has 15 open-ended items;
  - chemistry sample includes multiple-choice, matching, and open-ended items;
  - `Max poäng : N` markers are captured where present;
  - multiple-choice and matching answer keys are reported as absent when the PDF
    does not contain them.
- Add a fail-closed confidence gate for unknown shapes, lossy Swedish text
  extraction, missing required anchors, or unsupported item structures.
- Update EPIC-10, Story 38, the research reference only if implementation
  changes the documented parser contract.

## Deliverables

- [ ] DigiExam parser v1 module and typed result contract.
- [ ] Fixture-backed parser tests for both tracked sample PDFs.
- [ ] Confidence/warning model covering high-confidence parses, degraded
  extraction, unknown shapes, and missing answer-key provenance.
- [ ] Documentation closeout in the governing backlog/reference docs if the
  implementation changes accepted parser semantics.

## Acceptance Criteria

- [ ] Parser output is deterministic for both tracked PDFs.
- [ ] Item counts and item-type breakdowns match the research baseline.
- [ ] Parsed item results carry traceable source evidence.
- [ ] Missing answer keys are represented as provenance state, not reconstructed
  from prompts or options.
- [ ] Swedish diacritics are checked; degraded extraction fails closed or emits
  a blocking warning.
- [ ] Unknown item shapes do not proceed as renderer-ready output.
- [ ] New code avoids `Any`, casts, `type: ignore`, lint ignores, and large
  god modules.
- [ ] The focused parser tests and repo docs gates pass.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
