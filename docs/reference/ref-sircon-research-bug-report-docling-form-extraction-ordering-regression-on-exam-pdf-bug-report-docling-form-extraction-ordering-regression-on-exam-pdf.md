---
type: reference
id: REF-SIRCON-RESEARCH-bug-report-docling-form-extraction-ordering-regression-on-exam-pdf
title: 'Bug report: Docling form extraction ordering regression on exam PDF'
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: research
retired_ids:
- REF-docling-form-ordering-exam-pdf-2026-02-16
summary: 'Bug report: Docling form extraction ordering regression on exam PDF'
---


## Research Purpose And Boundary

State the question, the later decision or contract this research may inform,
the evidence boundary, and explicit exclusions.

## Evidence And Sources

List each repository source, retained artifact, experiment, external source, or
observation with enough provenance to verify it. Distinguish observed,
inherited, inferred, and unresolved evidence.

## Findings And Interpretation

Record findings supported by the evidence, their practical meaning, conflicts,
and limitations. Keep facts separate from interpretation.

## Evidence Gaps And Follow-Up

State missing evidence, why it matters, and the owning research, decision,
backlog, ADR, or runbook follow-up. Do not use this section as implementation
status or authority.

## Source Body Preservation

## Purpose
Capture reproducible evidence that question/option ordering defects for the target exam PDF are primarily upstream Docling extraction ordering behavior, not strict markdown normalization side effects.
## Target Input
- `data/conversion-inputs/Prövning i litteraturhistoria 2024.pdf`
## Environment Snapshot
- `docling==2.73.1`
- `docling-core==2.65.1`
- `pypdfium2==5.4.0`
- `pymupdf4llm==0.3.4`
- `pymupdf==1.27.1`
- Service default layout key:
`SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL=docling_layout_egret_large`
## Reproduction Summary
1. Convert the target PDF with Docling and `normalize=none`. 1. Convert the same PDF with PyMuPDF direct extraction. 1. Compare question-order and numbering continuity (Q2/Q3/Q13 exemplars). 1. Run isolated Docling ordering monkey-patch variants:
   - baseline
   - `_sort_clusters` only
   - `_sort_cells` only
   - `_sort_clusters + _sort_cells`
## Findings
1. Baseline Docling output shows option-before-question and trailing question number tokens for exam-form sections. 1. Same defect family is present before strict normalization; this excludes strict normalizer as primary cause. 1. PyMuPDF extraction preserves ordering significantly better for the same regions. 1. Isolated source patch behavior:
   - `_sort_clusters` only: insufficient.
   - `_sort_cells` only: partial.
   - `_sort_clusters + _sort_cells`: full fix in Heron isolation run.
1. Under current service default model (`egret_large`), patched output improves but still leaves a residual Q13 defect on this PDF, requiring quality-gated fallback policy.
## Upstream Code Hypothesis
Docling layout postprocessor currently uses PDF cell-index ordering in form assembly paths where geometric ordering is needed for this PDF class:
- `docling/utils/layout_postprocessor.py`:
  - `_process_special_clusters` sorts contained form clusters with
`_sort_clusters(..., mode=\"id\")`.
  - `_sort_cells` uses `cell.index` ordering.
This ordering strategy is consistent with observed trailing-number tokens and option-before-question grouping when PDF object emission order diverges from visual reading order.
## External Signals
- Open Docling issue on form handling order:
  - `docling-project/docling#2899`
- Open Docling ordering regression reports:
  - `docling-project/docling#2971`
  - `docling-project/docling#3004`
- v2.50.0 introduced Heron as default layout model; ordering behavior changed
relative to earlier defaults.
## Local Evidence Artifacts
- `build/pymupdf-ab-20260216T180200Z/`
- `build/docling-source-ab-20260216T181624Z/`
- `build/docling-monkeypatch-ab-20260216T182728Z/`
- `build/docling-isolated-ordering-ab-20260216T184204Z/`
- `build/docling-isolated-ordering-egret-ab-20260216T184833Z/`
## Operational Conclusion
Treat this as an upstream extraction-ordering bug class with local mitigation:
1. Integrate deterministic source-order patching in backend path. 1. Add structural quality gate + deterministic fallback to alternate layout profile when source ordering score fails. 1. Keep strict MCQ heuristics as temporary safety net only until source policy and quality gate are proven stable on Hemma lanes.

