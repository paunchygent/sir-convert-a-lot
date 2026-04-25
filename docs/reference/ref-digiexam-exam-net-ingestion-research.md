---
id: REF-digiexam-exam-net-ingestion-research
title: Digiexam to Exam.net ingestion research
type: reference
status: active
created: '2026-04-25'
last_updated: '2026-04-25'
owners:
  - platform
labels:
  - digiexam
  - exam-net
  - migration
  - pdf
  - qti
related:
  - docs/backlog/tasks/task-238-repair-exam-net-docx-paragraph-fidelity-in-docx-to-markdown-v2-route.md
---

## Evidence Boundaries

Research retrieval date: 2026-04-24.

Several Exam.net Help Center pages were discoverable through public search
snippets but rendered as a Salesforce CSS error when opened directly in the
research environment. Treat the indexed Help Center snippets as strong but
incomplete evidence. Before engineering final parser assumptions, capture live
screenshots from an authenticated Exam.net account with the relevant feature
enabled.

No Context7 check was available in the research environment, so the SDK/API
scan used public web search. No public Exam.net SDK, REST API, GraphQL API, CLI,
or developer documentation mirror was found.

This reference intentionally records ingestion and product-capability findings
only. Target PDF rendering and parser-heuristic experiments belong in a
separate, measured target-format analysis. The measured target-format findings
below come from comparing Exam.net v2 student/empty and solution/key printouts
after PDF conversion experiments.

## Confirmed Public Ingestion Paths

Exam.net has a PDF conversion feature. The English Help Center name is
`Convert PDF`; the Swedish Help Center name is `Konvertera PDF`. Marketing
describes the capability as turning a PDF into auto-marked questions.

`Convert PDF` is distinct from `Upload PDF`:

- `Convert PDF` attempts to parse an uploaded PDF into Exam.net structured
  question types.
- `Upload PDF` creates a PDF-based exam where students answer in a writing
  area. It can preserve the visual form of a Digiexam export, but it does not
  itself create editable native items or automatic marking.

The published `Convert PDF` workflow is:

1. Click `New exam`.
2. In exam-format selection, click `Convert PDF`.
3. Drag and drop a PDF or choose a local PDF file.
4. Exam.net converts the PDF into an exam using question types.
5. Review converted questions, including marking rules and correct answers.

No public source found exact limits for file size, page count, item count,
option count, images, total points, supported fonts, supported languages, or
PDF tagging requirements.

## Supported PDF Conversion Types

Public Exam.net Help Center snippets say the PDF converter supports:

- multiple choice,
- simple answer,
- free text.

If Exam.net cannot interpret a question, the public Help Center wording says it
is converted into a free text question.

Exam.net's native authoring platform supports more question types than the PDF
converter publicly claims, including multiple choice, simple answer, fill gaps,
match answers, grid/categorise, attachment, and free text. Public
documentation does not say that PDF conversion recognises fill gaps, matching,
ordering, image hotspots, subpart structures, or other richer structures.

Known conversion-risk posture:

- Open-ended essay or medium written response can be represented as native free
  text, but free text is not auto-marked.
- Short direct answers and numeric answers may be suitable for native simple
  answer, but correct-answer extraction from PDF is unverified.
- Multiple choice is publicly supported, but option-marker conventions,
  multi-select behaviour, and answer-key preservation are not documented.
- True/false has no dedicated native type; Exam.net documents workarounds using
  grid or multiple choice.
- Matching, ordering, and gap-fill exist or have native workarounds, but public
  PDF conversion support for them was not found.
- Image-based item handling through `Convert PDF` is unverified, while
  `Upload PDF` should preserve the image visually as part of the document.
- Items with subparts such as `a)`, `b)`, and `c)` are unverified and may be
  confused with answer-option markers.

## Parser Heuristics Are Unspecified

No public parser heuristic specification was found. Treat all of the following
as unverified until measured in an Exam.net account:

- recognition of Swedish markers such as `Fraga N`, `Fråga N`, `Max poäng`,
  `poäng`, or `p`,
- recognition of English markers such as `Question N` or `Points`,
- preferred point annotation form,
- multiple-choice option detection from bullets, `A.`, `A)`, `a)`, checkboxes,
  radio-style glyphs, or typography,
- preservation of point values,
- encoding or preservation of correct answers,
- detection of answer-key pages,
- template PDFs, Word templates, or style guides for best-practice ingest.

Exam.net tells teachers to check converted marking rules and correct answers.
That is a strong signal that automatic conversion is not treated as
authoritative.

DigiExam QTI/import marker rules are not Exam.net PDF conversion rules. Do not
assume Exam.net recognises DigiExam conventions such as numbered questions,
`a)` options, `*` for correct answers, `[ ]` / `[*]` for multiple-response
answers, or `###` for free-text responses.

## Correct Answers And Marking Rules

Correct-answer preservation via PDF is high risk. Public research did not find
an Exam.net PDF convention for encoding answer keys. The Digiexam jsPDF exports
observed for this lane do not contain embedded answer keys, so PDF conversion
alone cannot reliably preserve auto-marking keys.

For migrated exams, treat Exam.net PDF conversion as an assisted authoring
shortcut that requires teacher or operator review of:

- item count,
- item boundaries,
- item type,
- points,
- accepted answers,
- correct options,
- marking rules,
- whether answer-key text leaked into student-facing content.

## QTI And Other Native Import Signals

The only clearly public self-service external-ingestion path into native
questions found in this research was `Convert PDF`.

QTI may be the better engineering target if Exam.net support can enable or
document it, because QTI can represent item types, point values, response
declarations, and correct responses explicitly. However, public Exam.net
materials do not expose:

- QTI version,
- package structure,
- manifest requirements,
- supported interactions,
- points and outcome mapping,
- correct-answer mapping,
- batch import process,
- whether import is self-service or vendor-assisted,
- customer-facing endpoint or UI path.

A Swedish procurement/implementation document says exams can be imported in QTI
or PDF as part of implementation if the previous supplier exports in that
format. Treat this as evidence for a possible vendor-assisted route, not as a
public API or guaranteed tenant feature.

Public sources did not confirm Exam.net support for Moodle XML, GIFT, Markdown,
JSON, proprietary `.exam`, `.docx` file upload, IMS Common Cartridge,
CSV/Excel, XML, HTML, or TXT as self-service exam import formats.

## API And Bulk Import

No public Exam.net REST API, GraphQL API, CLI, SDK, developer documentation,
bulk import endpoint, auth model, rate limit, upload endpoint, import-job
schema, or job-status endpoint was found.

A third-party product page states that Exam.net does not offer an API. Exam.net
public technology pages describe integrations with Google Classroom, Microsoft
Teams, answer export to Google Drive/OneDrive/LMS/computer, and similar product
integrations, but not a developer API.

The Swedish procurement material suggests some technical documentation may be
non-public or treated as trade-secret material.

## Feature Status And Pricing

Feature status appears to have changed over time:

- In December 2024, Exam.net described PDF-to-auto-marked conversion as
  `coming soon`.
- A May 2025 Swedish procurement document described PDF-to-self-marking
  conversion as an internal/pilot project with no production release date at
  that time.
- Current Help Center snippets use present-tense workflow language, which
  strongly indicates the feature is now available in the product UI.

No public source found an exact GA date, beta label, rollout condition, tenant
flag, country restriction, trial-account availability rule, or account-level
enablement condition.

Exam.net's public pricing page says there is no free plan except a 30-day
school trial, licensing is school/organisation-based, and Exam.net does not
have different plans because it wants the full feature range available to
everyone. No public source found a `Convert PDF` add-on fee, quota, per-PDF
charge, per-exam conversion cap, or plan tier that excludes `Convert PDF`.

## Digiexam-Specific Migration Evidence

No public Exam.net help article, blog post, press release, migration guide, or
support article was found that names Digiexam as a supported migration source.

Public comparison pages exist for Digiexam versus Exam.net, but they are
product comparisons, not migration guides.

DigiExam documents QTI import into DigiExam, including QTI v1.2,
Common Cartridge/content package formats, and question syntax for
Word/Pages-to-QTI workflows. That is useful as evidence that DigiExam has
QTI-related tooling, but it does not prove that DigiExam exports QTI in a form
Exam.net can import.

## Engineering Implications

Treat Exam.net PDF conversion as a convenience importer requiring manual
review, not as a deterministic bulk migration path.

Until Exam.net confirms QTI or another structured import route, the migration
pipeline should preserve a structured intermediate model with item type,
points, options, known correct answers, and original Digiexam identifiers, and
should provide an Exam.net-friendly PDF only when the source item can be
rendered in the promoted production schema. Unsupported item shapes must be
flagged for manual rebuild or structured-import handling.

Minimum support request to Exam.net:

1. Accepted import formats and exact versions, especially QTI.
2. Whether import is self-service or handled by Exam.net implementation/support.
3. Package structure and manifest requirements.
4. Supported item types and mappings.
5. How point values are represented.
6. How correct answers are represented.
7. Whether matching, multiple-response multiple choice, gap-fill, and free
   text are supported.
8. Whether Swedish labels and characters are supported.
9. Maximum package size, item count, and batch size.
10. Whether there is any public or customer-only API/import endpoint.

## Measured Exam.net PDF Converter Target Format

The current best renderer target comes from analysis of two Exam.net v2 exports:

- student/empty printout,
- solution/key printout.

The key export materially changed the assessment of the converter: Exam.net
parsed correct answers well for imported multiple-choice items, including
no-label options and multi-answer cases. Remaining problems are item survival,
score-marker reliability, option-label leakage, single-choice cardinality, and
free-text rubric handling.

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

### Multiple-Choice Option Layout

The strongest production candidate is no visible labels, indented alternatives,
and exact-text answer keys.

Hard invariant: the migration renderer must never label multiple-choice
alternatives. Alternative labels are owned by Exam.net's item shell, and
Exam.net reshuffles alternatives by default. Source-side labels such as `A.`,
`B.`, `a)`, or `1.` are imported as part of the alternative text, where they
become misleading after reshuffle.

```text
Fråga 1
Points: 4
Type: Multiple choice
Choose one answer
Which thesis statement best evaluates how short videos influence political discussion?
    Political discussion happens on many platforms today.
    This essay will talk about politics and videos.
    Although short videos can broaden access to political information, they may also distort debate by rewarding speed over evidence.
    Social media often rewards quick reactions rather than careful argument.
Correct answer: Although short videos can broaden access to political information, they may also distort debate by rewarding speed over evidence.
```

This avoids visible option-label leakage. When `A.`, `B.`, `C.`, and `D.`
labels are retained, Exam.net may shuffle alternatives while preserving the
old labels, producing misleading printed labels.

Experimental only; do not use for the production renderer:

- no-label alternatives under a `Svarsalternativ` or `answer choices` header,
- bullet-indented alternatives,
- radio-glyph alternatives,
- any manually typed labels such as `A.`, `B.`, `C.`, `D.`, `A)`, `B)`,
  `A:`, `B:`, `a)`, `b)`, or numbered labels.

Do not generate:

- any source-side multiple-choice labels,
- lower-case `a)`, `b)`, `c)`, `d)` alternatives,
- dash-indented alternatives,
- checkbox-glyph alternatives,
- blank lines between every alternative,
- `Option:` prefixes,
- Word automatic lists,
- hanging indentation for lettered alternatives.

### Multiple-Choice Correct Answers

For labelled single-answer items, this worked in experiments but must not be
used by the production renderer. Labels are Exam.net-owned shell presentation,
not source content. If the source PDF labels alternatives, Exam.net imports
those labels into the alternative text and can then reshuffle the shell labels
around them:

```text
Correct answer: B
```

For labelled multi-answer items, this worked in experiments but must not be
used by the production renderer:

```text
Correct answers: A, C
```

For no-label options, exact option text worked and is preferred:

```text
Correct answer: The claim weighs one benefit against one risk and gives a clear judgement.
```

For no-label multi-answer items, use semicolon-separated exact option text:

```text
Correct answers: It uses relevant evidence.; It connects evidence to the main claim.
```

### Single-Choice Cardinality

Single-answer multiple-choice items imported with one correct answer selected,
but the experiments did not prove that any source phrasing reliably disables
`Flera val` in the Exam.net builder. Tested phrasings included English and
Swedish variants of `choose one`, `only one answer`, `select the best answer`,
`multiple answers: no`, and `Flera val: nej`.

Production rule: every single-answer multiple-choice item imported through PDF
conversion requires builder validation that `Flera val` is off.

### Multiple-Answer Multiple Choice

Multiple-answer multiple choice is now a strong capability when the item
imports. Prefer no-label options with exact-text keys:

```text
Fråga 2
Points: 5
Type: Multiple response
Choose all correct answers
Which features usually strengthen a source-critical answer about online information?
    It begins with a clear topic sentence.
    It includes relevant evidence.
    It explains how the evidence supports the claim.
    It introduces an unrelated topic.
Correct answers: It begins with a clear topic sentence.; It explains how the evidence supports the claim.
```

Validate that all correct answers and no incorrect answers are selected, and
that the score is preserved.

### Short Written Response

Short-answer import is strong, but semicolon splitting remains unverified. The
solution key printed semicolon-separated variants, which confirms the key line
is consumed and does not leak into the student printout, but it does not prove
whether Exam.net stores each variant separately or one literal string.

Promote:

```text
Fråga 3
Points: 3
Type: Short answer
Which molecule is the main energy currency used by cells?
Correct answers: ATP; adenosine triphosphate; adenosintrifosfat
```

Also acceptable:

```text
Type: Simple answer
Accepted answers: ATP; adenosine triphosphate; adenosintrifosfat
```

Do not promote Swedish `Typ: Enkelt svar` plus `Rätt svar:` for short-answer
items yet; one such item disappeared in the experiment.

### Free Text And Rubrics

For large free-text fields, promote:

```text
Fråga 4
Points: 9
Type: Free text
How can renewable energy projects create both environmental benefits and local conflicts?
Write 250-400 words. Use examples and develop your reasoning.
```

or:

```text
Fråga 4
Poängvärde: 9
Typ: Fritext
How can renewable energy projects create both environmental benefits and local conflicts?
Write 250-400 words. Use examples and develop your reasoning.
```

Do not rely on PDF-converted rubrics for free-text items. Configurations such
as `Type: Essay` plus `Correct answer:` sometimes attached rubric-like text to
the solution key, but produced a short-answer-like student field. Use
`Type: Free text` or `Typ: Fritext`, preserve the points, and carry rubrics in
the migration sidecar/audit model for manual setup or a future structured
import route.

Put writing instructions inside the visible prompt body. Do not place them as a
metadata-like line after the type declaration; experiments showed such lines
may be stripped.

### Renderer Blacklist

Do not generate these patterns:

```text
Score: N
Totalpoäng: N
a) option
b) option
c) option
d) option
- option
☐ option
Option: option text
```

Also avoid blank lines between every alternative, Word automatic lists, hanging
indents for alternatives, and essay rubric patterns that use `Type: Essay` plus
`Correct answer:`.

### Promoted Item Schemas

#### Single-Answer Multiple Choice, No Visible Labels

Use this as the primary single-answer multiple-choice schema. It is parser
friendly and avoids visible option-label leakage. It still requires builder
validation that `Flera val` is off.

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

#### Multiple-Answer Multiple Choice, No Visible Labels

Use this as the primary multiple-answer schema when more than one option is
correct.

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

Use this for compact written responses with known accepted answers. Semicolon
variant splitting still needs editor verification.

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

#### Free Text / Essay

Use this for long-form written answers. Keep writing instructions in the prompt
body, not as metadata lines. Keep rubrics outside the conversion PDF.

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

### Current Capability Classification

High confidence:

- detecting multiple-choice items when option layout is clean,
- preserving multiple-choice correct answers,
- preserving multiple correct multiple-choice answers,
- preserving multiple-choice scores with promoted score markers,
- importing short-answer items,
- printing semicolon answer variants in the solution key,
- preserving free-text scores with promoted score markers,
- preventing answer-key leakage into the tested student printouts.

Medium-high confidence:

- using exact option text as answer keys,
- importing no-label indented alternatives,
- importing large free-text items with `Type: Free text` or `Typ: Fritext`.

Low or unresolved confidence:

- stripping visible option labels consistently,
- forcing single-select multiple-choice,
- proving semicolon short-answer variants become separate accepted answers,
- attaching rubrics to large free-text items.

Bottom-line production renderer target:

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

Do not implement labelled multiple-choice or other fallback layouts in the
production renderer. Failed or unsupported source items should be flagged for
manual rebuild or structured-import handling, not rendered through a weaker PDF
pattern.

For long-form answers, use `Type: Free text`, preserve points, keep rubric data
outside the conversion PDF, and require manual or structured-import follow-up
for rubric setup.
