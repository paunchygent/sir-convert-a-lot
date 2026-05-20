---
type: reference
id: REF-digiexam-jspdf-export-shape-and-examnet-migration-research
title: DigiExam jsPDF Export Shape And Exam.net Migration Research
status: active
created: 2026-04-24
updated: 2026-05-12
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
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/tasks/task-277-implement-digiexam-exam-net-oriented-pdf-renderer-and-live-validation.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
---

## Purpose

This reference records the initial DigiExam source-adapter PDF research for Sir
Convert-a-Lot's exam artifact conversion and authoring work. It records the
observable shape of exam PDFs exported from DigiExam, the open questions about
Exam.net ingestion, and the renderer architecture that should be governed by
`EPIC-10`.

DigiExam evidence here must not be read as the whole product boundary. It is
one source adapter feeding Sir Convert's intermediary exam shape before target
renderers produce Exam.net PDF-to-exam converter PDFs and schema-valid QTI
packages.

The canonical source for what each DigiExam artifact and item type contains or
does not contain is
`docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`.

No parser, renderer, or service behavior change is approved by this reference
alone. Stories and tasks under `EPIC-10` decide implementation.

## Sample Corpus

Two source PDFs were inspected on 2026-04-24 and copied into this repo as
DigiExam export examples on 2026-04-25:

- `inputs/examples/digiexam-exports/_-25cEkologiprov51-55.pdf`
  - biology/ecology exam, 3 A4 pages, 15 items, all open-ended written response
    with some `a)`/`b)`/`c)` subparts.
- `inputs/examples/digiexam-exports/_-Kemikapitel2ht2525dECA.pdf`
  - chemistry exam, 3 A4 pages, 12 items: 3 multiple-choice items, 1
    matching-like visual PDF row (`Para ihop`) now treated as
    unsupported/non-canonical in the DigiExam parser path, and 8 open-ended
    written-response items.

Sample size is two. Heuristics derived here must be revalidated against a
larger corpus before a bulk pipeline is locked in.

Additional teacher-export evidence was inspected on 2026-05-07 and is recorded
in `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`:

- `1772718003-test samma prov i digiexam.dxe`
  - DigiExam JSON export with one exam, seven questions, structured
    single-choice, multiple-response, free-text, and gap-fill question data.
- `DigiExam-Test-som-nedladdningsbar.pdf`
  - blank/student-view jsPDF export of the same exam.
- `2026_05_07-Test-OlofLarsson.pdf`
  - graded student-result jsPDF export for the same exam, including correct
    answer labels, student-selected answers, gap-fill keys, and awarded points.

## Current State: DigiExam Artifact Evidence

`docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md` owns the
artifact evidence registry, item-type matrix, teacher source policy, and parser
contract implications. Keep item-type containment statements there so later
tasks can link one source of truth instead of duplicating partial evidence.

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

Preferred default for non-localized import smoke tests:

```text
Points: 4
```

Preferred Swedish-friendly renderer default:

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
```

Swedish-friendly score and type variant:

```text
Fråga {number}
Poängvärde: {points}
Typ: Fritext
{prompt}
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

## Forward Renderer Profile

Task 277's first Exam.net PDF renderer was built from the measured 2026-05-11
student/key printout experiments below. On 2026-05-12, additional empirical
work promoted a Swedish-first PDF-to-exam profile for future renderer work:

```text
Fråga N
Poängvärde: N
Typ: [Flerval | Kort svar | Fritext | Matcha ihop]
```

Use
`docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md` as the
canonical forward renderer profile. It owns the Swedish labels, exact-text
answer-key syntax, `Flerval`, `Kort svar`, `Fritext`, and `Matcha ihop`
profiles, plus the gap-fill experiment boundary.

Do not implement labelled multiple-choice or other weaker fallback layouts in
the production renderer. Items without an empirically promoted Exam.net
PDF-converter target shape should be flagged for manual rebuild or later
structured-import handling, not rendered through a weaker PDF pattern. This is
a renderer target-proof boundary; it is not a parser or IR limitation.

The English control-line examples in this reference remain historical Task 277
evidence, not the current default for new Exam.net-oriented authoring surfaces.

## Task 277 Renderer Implementation Contract

Story 43 / Task 277 implements the first production renderer for this target
shape. The renderer consumes Sir Convert's DigiExam IR rather than reading
`.dxe` JSON directly, and it remains separate from QTI/native import, service
routes, bulk workflow, and Exam.net browser/upload automation.

The renderer implementation shape is deliberately modular:

- `digiexam_examnet_pdf_contracts.py` defines target status, warnings, item,
  document, and asset-file value objects.
- `digiexam_examnet_pdf_assets.py` validates canonical IR asset payloads,
  verifies hash/length identity, and prepares local asset files.
- `digiexam_examnet_pdf_prompt.py` sanitizes DigiExam prompt HTML and rewrites
  `data-image-id` references to local image paths.
- `digiexam_examnet_pdf_items.py` renders supported item sections into the
  promoted Exam.net PDF-converter text shape.
- `digiexam_examnet_pdf_html.py` assembles the final HTML document consumed by
  WeasyPrint.
- `digiexam_examnet_pdf.py` remains a thin domain coordinator.
- `infrastructure/digiexam_examnet_pdf_renderer.py` materializes HTML, assets,
  and the final PDF through the existing WeasyPrint wrapper.

Task 277 emits Exam.net PDF-converter text only for free text, single-answer
multiple choice, multiple response, and one-gap short-answer items. Parser and
IR layers may still preserve richer source structures such as matching pairs.
Those structures block only at this renderer when no governed PDF-converter
target shape exists, or when machine-marked output lacks source-proven answer
key data.

Later renderer tasks may promote matching output and Swedish machine-marked
labels only through
`docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md` and fresh
fixture-backed import proof.

Live validation for this renderer must generate a real PDF and inspect it with
PyMuPDF for:

- `Fråga N`, `Poängvärde: N`, free-text `Typ: Fritext`, and target-safe
  machine-marked type markers;
- visible prompt text;
- embedded image presence for asset-bearing IR;
- absence of unresolved `data-image-id` placeholders in the materialized HTML.

## Target Architecture

End-state: Sir Convert ingests teacher-provided DigiExam `.dxe` files, with
optional graded student-result PDFs for correct-answer enrichment, and emits
artifacts that Exam.net imports cleanly, plus a parity report teachers can
review before upload.

Proposed architecture, pending target research:

- Parser stage: DigiExam `.dxe` to structured item stream, using typed JSON
  contracts and explicit provenance for question structure, prompt content,
  item types, scores, alternatives, and gaps.
- Optional result-PDF enrichment stage: graded DigiExam result PDF to
  correct-answer evidence for machine-marked items only. Incorrect student
  answers and student-performance history are discarded.
- Optional parity stage: blank/student-view DigiExam PDF to visual and text
  parity evidence when teachers can supply it.
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
1. DigiExam `.dxe` parser and optional graded-result PDF answer-key enrichment
   contract.
1. Sir Convert intermediary exam shape and source-adapter manifest schema.
1. Exam.net-targeted renderer.
1. Bulk conversion workflow and parity report.

## Risks And Gaps

- Artifact and item-type containment claims belong in
  `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`; this
  research reference should not restate them.
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
