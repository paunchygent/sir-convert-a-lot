---
type: reference
id: REF-digiexam-jspdf-export-shape-and-examnet-migration-research
title: DigiExam jsPDF Export Shape And Exam.net Migration Research
status: active
created: 2026-04-24
updated: 2026-04-25
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

Two source PDFs were inspected on 2026-04-24 and copied into this repo as
Digiexam export examples on 2026-04-25:

- `inputs/examples/digiexam-exports/_-25cEkologiprov51-55.pdf`
  - biology/ecology exam, 3 A4 pages, 15 items, all open-ended written response
    with some `a)`/`b)`/`c)` subparts.
- `inputs/examples/digiexam-exports/_-Kemikapitel2ht2525dECA.pdf`
  - chemistry exam, 3 A4 pages, 12 items: 3 multiple-choice items, 1 matching
    item (`Para ihop`), and 8 open-ended written-response items.

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

### Chemistry Fixture Baseline

Task 267 parser tests must treat the chemistry sample as this exact ordered
item stream:

| Order | Header/title | Expected type | Point marker | Notes |
|---|---|---|---|---|
| 1 | `Materia` | multiple choice | absent | options are prompt-visible only; answer key is absent |
| 2 | `Para ihop` | matching | absent | carries numbered left prompts, lettered right options, and blank-row evidence |
| 3 | `Grundämnen` | multiple choice | absent | option text crosses a page boundary in layout extraction |
| 4 | `Atomen` | open ended | `Max poäng : 4` | subparts `a)` through `d)` |
| 5 | `Ämnen` | open ended | `Max poäng : 4` | subparts `a)` through `c)` |
| 6 | `Joner` | multiple choice | absent | options are prompt-visible only; answer key is absent |
| 7 | `Emulsion` | open ended | `Max poäng : 2` | single prompt |
| 8 | `Separera` | open ended | `Max poäng : 3` | subparts plus instruction line |
| 9 | `Reaktion` | open ended | `Max poäng : 3` | subparts `a)` through `c)` |
| 10 | `Förklara` | open ended | `Max poäng : 3` | single prompt |
| 11 | `Te` | open ended | `Max poäng : 3` | single prompt |
| 12 | `Dela upp färg` | open ended | `Max poäng : 3` | subparts `a)` through `c)` |

Chemistry fixture tests must assert:

- total item count is 12;
- ordered headers/titles match the table above;
- item-type breakdown is 3 multiple-choice, 1 matching, and 8 open-ended;
- point-marker evidence is present exactly where the table lists a marker;
- multiple-choice and matching answer-key provenance is `absent`;
- the `Para ihop` item preserves the matching blank-row evidence separately
  from any future renderer-ready match-pair schema.

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

Research retrieval date: 2026-04-24.

Exam.net has a PDF conversion feature named `Convert PDF` in English and
`Konvertera PDF` in Swedish. It is distinct from `Upload PDF`:

- `Convert PDF` attempts to parse a PDF into Exam.net structured question
  types.
- `Upload PDF` creates a PDF-based exam where students answer in a writing
  area. It can preserve the visual form of a Digiexam export, but it does not
  create editable native items or automatic marking by itself.

Public Help Center snippets say the PDF converter supports:

- multiple choice,
- simple answer,
- free text.

If the converter cannot interpret a question, public Help Center wording says
it becomes a free text question. Exam.net's native editor supports more item
types than this list, including fill gaps, match answers, grid/categorise,
attachment, and free text, but public documentation does not say that PDF
conversion recognises those richer structures.

No public parser heuristic specification was found. Treat recognition of
`Fråga N`, `Max poäng`, `poäng`, `Question N`, `Points`, option markers,
answer-key pages, typography, or point notation as empirical behaviour, not
official contract.

No public Exam.net REST API, GraphQL API, CLI, SDK, developer documentation,
bulk import endpoint, auth model, rate limit, upload endpoint, import-job
schema, or job-status endpoint was found. A third-party product page says
Exam.net does not offer an API. Swedish procurement material suggests some
technical documentation may be non-public or treated as trade-secret material.

QTI may be the better engineering target if Exam.net support can enable or
document it, because QTI can represent item types, point values, response
declarations, and correct responses explicitly. However, public Exam.net
materials do not expose QTI version, package structure, manifest requirements,
supported interactions, points/outcome mapping, correct-answer mapping, batch
process, or whether import is self-service or vendor-assisted. A Swedish
procurement/implementation document says exams can be imported in QTI or PDF as
part of implementation if the previous supplier exports in that format; treat
that as possible vendor-assisted route evidence, not a public API guarantee.

No public Exam.net help article, blog post, press release, migration guide, or
support article was found that names Digiexam as a supported migration source.

## Measured Exam.net PDF Converter Target

Target-format findings come from comparing Exam.net v2 student/empty and
solution/key printouts after PDF conversion experiments.

Experiment summary:

- Source items: 60.
- Imported items: 53.
- Missing items: 7.
- Imported multiple-choice answer keys were generally stored correctly.
- Multi-answer multiple-choice items were correctly represented in the solution
  key.
- No-label multiple-choice alternatives worked better than expected.
- Semicolon-separated short-answer keys appeared in the solution key.
- Free-text items preserved large writing boxes only with certain type labels.
- Rubrics did not reliably attach to large free-text items.

### Promoted Score Markers

Use one of these score markers:

- `Points: N`
- `Poängvärde: N`
- `[N points]`
- `(N p)`
- `poäng: N`
- `Max poäng: N`

Preferred default:

```text
Points: 4
```

Preferred Swedish-friendly alternative:

```text
Poängvärde: 4
```

Avoid `Marks: N` as a default. It mostly worked, but failed once in a
multi-answer item.

Ban these score markers:

- `Score: N`
- `Totalpoäng: N`

### Multiple-Choice Option Invariant

The migration renderer must never label multiple-choice alternatives.
Alternative labels are owned by Exam.net's item shell, and Exam.net reshuffles
alternatives by default. Source-side labels such as `A.`, `B.`, `a)`, or `1.`
are imported as part of the alternative text, where they become misleading
after reshuffle.

The production option shape is no visible labels, indented alternatives, and
exact-text answer keys.

Do not generate:

- any source-side multiple-choice labels,
- lower-case `a)`, `b)`, `c)`, `d)` alternatives,
- dash-indented alternatives,
- checkbox-glyph alternatives,
- blank lines between every alternative,
- `Option:` prefixes,
- Word automatic lists,
- hanging indentation for alternatives.

### Promoted Item Schemas

#### Single-Answer Multiple Choice, No Visible Labels

```text
Fråga {number}
Points: {points}
Type: Multiple choice
Choose one answer
{prompt}
    {option_1}
    {option_2}
    {option_3}
    {option_4}
Correct answer: {exact_correct_option_text}
```

Validation after import:

- `Flera val` is off.
- Score equals `{points}`.
- Exactly one correct answer is selected.
- No option-label text leaked into the alternatives.

Single-answer multiple-choice remains structurally usable but not safe for
unattended bulk import until `Flera val` can be forced off or reliably checked.

#### Multiple-Answer Multiple Choice, No Visible Labels

```text
Fråga {number}
Points: {points}
Type: Multiple response
Choose all correct answers
{prompt}
    {option_1}
    {option_2}
    {option_3}
    {option_4}
Correct answers: {exact_correct_option_text_1}; {exact_correct_option_text_2}
```

Validation after import:

- All intended correct answers are selected.
- No unintended answers are selected.
- Score equals `{points}`.
- No option-label text leaked into the alternatives.

#### Short Answer With Accepted Variants

```text
Fråga {number}
Points: {points}
Type: Short answer
{prompt}
Correct answers: {accepted_answer_1}; {accepted_answer_2}; {accepted_answer_3}
```

Alternative wording that also remains acceptable:

```text
Fråga {number}
Points: {points}
Type: Simple answer
{prompt}
Accepted answers: {accepted_answer_1}; {accepted_answer_2}; {accepted_answer_3}
```

Validation after import:

- Student printout has a compact answer field.
- Key line does not leak into the student printout.
- Score equals `{points}`.
- The editor is checked to see whether semicolon-separated variants became
  separate accepted answers or one literal string.

Do not promote Swedish `Typ: Enkelt svar` plus `Rätt svar:` for short-answer
items yet; one such item disappeared in experiments.

#### Free Text / Essay

```text
Fråga {number}
Points: {points}
Type: Free text
{prompt}
{student_writing_instruction}
```

Swedish-friendly score and type variant:

```text
Fråga {number}
Poängvärde: {points}
Typ: Fritext
{prompt}
{student_writing_instruction}
```

Sidecar-only rubric shape:

```text
teacher_rubric: {rubric_text}
```

Validation after import:

- Student printout has a large free-text field.
- Score equals `{points}`.
- Writing instructions remain visible in the prompt.
- Rubric is not expected to attach through PDF conversion.

For long-form answers, do not try to force rubric import through the PDF
converter. Keep rubric data in the migration sidecar until Exam.net offers a
structured route or a manual setup step.

## Production Renderer Target

Bottom-line production target:

```text
Fråga N
Points: N
Type: Multiple choice | Multiple response | Short answer | Free text
[Visible prompt, including student instructions]
    [Option text]
    [Option text]
    [Option text]
    [Option text]
Correct answer(s): [exact answer text]
```

Do not implement labelled multiple-choice or other weaker fallback layouts in
the production renderer. Failed or unsupported source items should be flagged
for manual rebuild or structured-import handling, not rendered through a weaker
PDF pattern.

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
