---
type: reference
id: REF-digiexam-jspdf-export-shape-and-examnet-migration-research
title: DigiExam jsPDF Export Shape And Exam.net Migration Research
status: active
created: 2026-04-24
updated: 2026-04-24
owners:
  - platform
tags:
  - exam-migration
  - digiexam
  - exam-net
  - pdf
  - parser
links:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
---

## Purpose

This reference is the research baseline for the Sir Convert-a-Lot DigiExam to
Exam.net migration epic. It records the observable shape of exam PDFs exported
from DigiExam, the open questions about Exam.net ingestion, and the conversion
architecture that should be governed by `EPIC-10`.

No parser, renderer, or service behavior change is approved by this reference
alone. Stories and tasks under `EPIC-10` decide implementation.

## Sample Corpus

Two source PDFs were inspected on 2026-04-24 from the HuleEduOS classroom
materials repo:

- `/Users/olofs_mba/Documents/Repos/html_to_pdf_handout_templates/input/_-25cEkologiprov51-55.pdf`
  - biology/ecology exam, 3 A4 pages, 15 items, all open-ended written response
    with some `a)`/`b)`/`c)` subparts.
- `/Users/olofs_mba/Documents/Repos/html_to_pdf_handout_templates/input/_-Kemikapitel2ht2525dECA.pdf`
  - chemistry exam, 3 A4 pages, mixed item types: multiple choice, matching
    (`Para ihop`), and open-ended written response.

Sample size is two. Heuristics derived here must be revalidated against a
larger corpus before a bulk pipeline is locked in.

## Current State: DigiExam PDF Shape

### Container Metadata

Both sample files share the following container fingerprint from `pdfinfo`:

- `Producer: jsPDF 2.5.1`, which indicates client-side browser PDF generation
  rather than a server-tagged export.
- `PDF version: 1.3`, A4 page size, untagged, no AcroForm, no JavaScript, no
  encryption, no metadata stream, and no embedded images in `pdfimages -list`.
- Fonts are PDF base14 Type 1 families plus one embedded CID TrueType font named
  `hebrew` with `Identity-H` encoding, apparently used as a fallback glyph
  source for Swedish characters.

Practical consequence: the files are untagged, imageless, A4, and machine-text
heavy. Parser design should use layout-aware text extraction through Sir
Convert's PDF extraction stack, not structural PDF tags.

### Item Anatomy

An item in a DigiExam export is a vertical block with this observed structure:

1. Header line:
   - numbered form: `Fråga <N>` where `<N>` is a 1-indexed integer;
   - titled form: a short free-text title on its own line, such as `Materia`,
     `Grundämnen`, `Atomen`, `Joner`, or `Para ihop`.
1. Optional point marker: `Max poäng : <N>`. It appears on every observed
   open-ended item and is absent on observed multiple-choice and matching
   items.
1. Prompt body in Swedish prose, sometimes with subparts introduced by `a)`,
   `b)`, or `c)`.
1. Response region rendered as vertical whitespace. Blank lines are therefore
   not reliable delimiters; the next item header is the reliable boundary.

### Item Types Observed

- Open-ended written response: header, optional point marker, prompt text, and
  blank answer space.
- Multiple choice: titled header, no observed point marker, prompt, then options
  on separate indented lines. The correct answer is not present in the PDF.
- Matching / fill-in-the-letter (`Para ihop`): numbered prompts, lettered
  answer options, and a trailing DigiExam answer-blank artifact row such as
  `1 = 1.   2= 2.   3= 3.   4= 4.`.

No ruled tables, inline images, math notation, true/false items, ordering
items, or gap-fill items were observed in the two samples.

### Robust Parsing Anchors

Ordered from strongest to weakest on the observed samples:

1. `^Fråga \d+\s*$` on its own line.
1. `^Max poäng\s*:\s*\d+\s*$`, usually immediately below an open-response
   header.
1. Lettered subpart prefixes `^[a-z]\)\s` at line start inside an item body.
1. Isolated short title lines followed by either a point marker or a prompt plus
   option list.
1. Matching-answer blank row `^(\d+\s*=\s*\d+\.\s*)+$`, used only as a
   confirmation signal for matching items.

## Current State: Exam.net Ingestion Target

Known:

- Exam.net is the target platform.
- The exact PDF-to-digital-exam ingestion heuristics, supported item types,
  point-value markers, answer-key import behavior, and any native import formats
  are not yet documented in this repo.

Open research questions for the first story under `EPIC-10`:

- Does Exam.net recognize Swedish markers such as `Fråga N` and
  `Max poäng : N`, or does it require another heading/point convention?
- How should point values be encoded for the most reliable ingest?
- Which multiple-choice option conventions are recognized?
- Where can correctness data come from: separate answer-key upload, inline
  marking, native import format, or manual tagging after import?
- Which item classes map to native Exam.net item types, and which collapse to
  text-only items?
- Does Exam.net accept a non-PDF native format that preserves points and answer
  keys more reliably than PDF?
- What item-count, item-type, and point-total fidelity is achieved by
  round-tripping the two sample PDFs through Exam.net?

## Target Architecture

End-state: Sir Convert ingests a folder of DigiExam jsPDF exports and emits
artifacts that Exam.net imports cleanly, plus a parity report teachers can
review before upload.

Proposed architecture, pending target research:

- Parser stage: DigiExam PDF to structured item stream, using layout-aware PDF
  extraction and explicit parse-confidence evidence.
- Intermediate representation: structured item stream to a Sir Convert exam
  migration schema with item type, prompt body, option/matching structures,
  point values, source spans, extraction warnings, and answer-key provenance.
- Renderer stage: intermediate representation to the selected Exam.net target,
  either a tuned PDF or a native import format if one proves more faithful.
- Bulk workflow: directory-level CLI/API route that emits artifacts and a
  parity report with item count, item type breakdown, point totals, warnings,
  and manual follow-up notes.

## Planned Work

1. Exam.net ingestion research and target-format decision.
1. DigiExam PDF parser v1 with regression fixtures.
1. Sir Convert intermediate exam representation and manifest schema.
1. Exam.net-targeted renderer.
1. Bulk conversion workflow and parity report.

## Risks And Gaps

- Only two sample PDFs are available today.
- Observed multiple-choice and matching items carry no correct-answer metadata
  in the PDF.
- The embedded `hebrew` / `Identity-H` font causes Poppler warnings and could
  produce lossy extraction on future exports.
- Renderer decisions made before Exam.net ingestion research are likely to be
  reworked.

## Validation Expectations

- Re-extract both sample PDFs and confirm that all item headers and all
  `Max poäng : N` markers used by this reference are still present.
- Parser v1 must test expected item counts and item-type breakdowns against the
  observed samples.
- Character extraction must include a Swedish diacritic coverage check and a
  documented OCR fallback path when extraction degrades.
- Exam.net renderer work must include round-trip evidence and per-item fidelity
  notes before bulk use.
