---
type: reference
id: REF-digiexam-exam-artifact-item-type-evidence
title: DigiExam Exam Artifact Item Type Evidence
status: active
created: 2026-05-07
updated: 2026-05-15
owners:
  - platform
tags: []
links:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-40-digiexam-dxe-source-parser-and-answer-key-provenance.md
  - docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md
  - docs/backlog/tasks/task-281-classify-digiexam-dxe-validation-corpus-and-add-parser-regression-gate.md
  - docs/backlog/tasks/task-274-implement-digiexam-dxe-parser-fixtures-and-result-pdf-answer-enrichment-gate.md
  - docs/backlog/tasks/task-276-implement-digiexam-dxe-embedded-asset-ir-support.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
---

## Purpose

Define the canonical DigiExam exam-artifact and item-type evidence for EPIC-10
implementation work. This document owns what each observed DigiExam artifact
contains, what it does not contain, and how that evidence may be used in the
migration model.

Do not duplicate these item-type truths in backlog tasks or renderer docs. Link
to this reference, then add task-specific acceptance criteria on top.

## Source Artifact Registry

| Evidence ID | File | SHA-256 | Artifact class | Use |
|---|---|---|---|---|
| `DXE-2026-05-07-structure` | `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/1772718003-test-samma-prov-i-digiexam.dxe` | `9a24b363b0066499ee574b118764f7f93361d7528f13ea9dc013ec06e24aaff5` | DigiExam `.dxe` JSON export | Canonical structure source for the observed 7-question mixed-type exam |
| `DXE-2026-05-07-duplicate` | `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/1772718003-test-duplicate.dxe` | `9b4b35fab0e22675805e9ec70c1bf5f99c3c4d3c43d7f5fbec3eeec641491c38` | DigiExam `.dxe` JSON export | Same schema and question content as `DXE-2026-05-07-structure`; only checksum/timestamp metadata differs |
| `BLANK-PDF-2026-05-07` | `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/DigiExam-Test-som-nedladdningsbar.pdf` | `2c66ff8ad84ddb4300091c04c87ed397ca6927ae0443cd208399055081b86ab8` | Blank/student-view jsPDF export | Visual and text parity evidence for the same 7-question exam |
| `RESULT-PDF-2026-05-07-SANITIZED` | `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/graded-student-result-sanitized.pdf` | `cf0e333ab65f08a21e5345fcc37f8d431c066cdc6b77dcc646e31f35a71e8664` | Sanitized graded student-result jsPDF export | Optional correct-answer enrichment for machine-marked items only |
| `DXE-2026-05-11-SANITIZED-EMBEDDED-IMAGE` | `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/sanitized-embedded-image.dxe` | `abf3c12065928946df68f0105788ceddb300fcea1bdde716755c90bc59459309` | Minimal sanitized `.dxe` JSON export | Embedded `question.images[]` PNG plus `data-image-id` binding fixture for Task 276 |
| `DXE-CORPUS-MANIFEST-2026-05-12` | `inputs/examples/digiexam-evidence/digiexam-dxe-validation-corpus-2026-05-12.manifest.json` | `035957d69f83c2eba625190370adea013e7b00cbe04cac220121ebf9dbaf8167` | Metadata-only `.dxe` validation-corpus manifest | Task 281 parser/IR regression evidence for the then-local raw OneDrive corpus; contains counts and hashes only |
| `DXE-FIXTURE-CORPUS-2026-05-12` | `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/` | See per-file `validation-corpus-manifest.json` | Versioned raw DigiExam `.dxe` fixture corpus | Task 309 live-validation fixture set promoted from the former local OneDrive corpus |
| `PDF-ECOLOGY-2026-04-25` | `inputs/examples/digiexam-exports/_-25cEkologiprov51-55.pdf` | `bc1ef30b8f378e193fc42746d91e849dcc5face4117b5dbea448610fa40f6873` | Blank/student-view jsPDF export | Legacy Task 267 open-ended PDF parser fixture |
| `PDF-CHEMISTRY-2026-04-25` | `inputs/examples/digiexam-exports/_-Kemikapitel2ht2525dECA.pdf` | `8a2e2a72915861f62981d2db7087e3363621c6087b4eb7ab1442046e0b3b6a7e` | Blank/student-view jsPDF export | Legacy Task 267 mixed PDF parser fixture with MCQ, matching, and open-ended items |

## Local Untracked Asset Evidence

A colleague-provided `.dxe` export named `1776888013-ak7-lag-och-ratt.dxe`
showed that a question can contain base64 PNG data under `question.images[]`
and bind it from `bodyHTML` with `<img data-image-id="0">`. The raw export also
contains unnecessary metadata such as user, organization, encryption, and timing
fields, so it must remain local-private and ignored. Task 276 used it only to
derive the tracked minimal sanitized fixture
`DXE-2026-05-11-SANITIZED-EMBEDDED-IMAGE`.

The observed embedded asset shape is:

- source array: `question.images[]`;
- prompt binding: `data-image-id`;
- observed media: PNG;
- required parser behavior: decode, hash, type, size, bind, and fail closed on
  invalid or unbound asset data, including `data-image-id` references when
  `question.images[]` is empty or absent.

## Versioned Live-validation DXE Corpus

On 2026-05-12, a larger local `.dxe` validation package was added. Task 309
promoted those pure DigiExam exports into the versioned fixture root:

```text
inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/
```

Initial metadata-only parser smoke found:

- 23 `.dxe` JSON exports;
- all 23 parse with status `success`;
- 317 total items;
- item-type breakdown: 273 open-ended, 27 single-choice, 4 multiple-response,
  and 13 gap-fill;
- 8 embedded image assets;
- 44 `missing_answer_key_provenance` warnings and no other warning codes.

Task 305 rechecked every `.dxe` file available under `inputs/` on
2026-05-15, including tracked fixtures, local-private evidence, and the then
ignored OneDrive validation corpus. The combined local pool contained 27 `.dxe` files,
340 parsed items, 21 gap-fill items, and 113 total gap placeholders. Every
observed gap placeholder was represented by a `.dxe` `blanks[]` entry with
only `guid` and `validations`, every observed `validations` array was empty,
and every observed gap GUID was bound back into `bodyHTML` through a
`span dx-wg-id` prompt binding. No raw prompt text, raw `.dxe`, owner metadata,
student data, or embedded payload was promoted into committed evidence.

Task 281 originally classified the raw package as local-only validation
material and retained only the metadata manifest
`DXE-CORPUS-MANIFEST-2026-05-12`. Task 309 supersedes that retention decision
for this corpus only: the pure `.dxe` files are now tracked as governed live
validation fixtures, with `validation-corpus-manifest.json` freezing source
SHA, item fingerprints, item type, eligibility, skip reason, and provider
output mode. Live prompts, provider responses, Hemma reports, and generated
validation artifacts remain outside git.

## Source Policy

The production migration flow should require a `.dxe` file as the canonical
structure source. The `.dxe` carries question order, titles, prompt HTML,
question type codes, maximum scores, alternative text, gap identifiers, and
some grading-policy fields.

A graded student-result PDF is an optional companion source. It may contribute
only correct answer data for machine-marked items:

- correct single-choice alternatives;
- correct multiple-response alternatives;
- correct gap-fill words or accepted values when they are present in the
  result PDF.

The migration model must not retain the student's incorrect answers, free-text
student answers, per-student scores, or student-performance history. Result
PDFs are answer-key evidence only.

Blank/student-view PDFs are optional visual and extraction parity evidence for
DigiExam migration, and separate source evidence for Exam.net or
teacher-authored PDF artifact lanes when the source role is declared. They are
not the parser baseline when `.dxe` is available. Treat their matching
structure as non-DXE evidence and route future keyed matching semantics through
the governed Exam.net/authoring IR path, not through DigiExam `.dxe`.

## Item-Type Evidence Matrix

| Item type | Evidence files | Contains | Does not contain | Migration handling |
|---|---|---|---|---|
| Free text / open-ended | `DXE-2026-05-07-structure`, `BLANK-PDF-2026-05-07`, `RESULT-PDF-2026-05-07-SANITIZED`, `PDF-ECOLOGY-2026-04-25`, `PDF-CHEMISTRY-2026-04-25` | `.dxe` type `0`, title, prompt `bodyHTML`/`about`, `maxScore`, and optional text-length cap fields. Blank PDFs expose prompt text, answer area, and point markers. Result PDFs expose one student's answer and awarded points. | No teacher rubric, marking matrix, model answer, accepted answer list, or reusable free-text answer key was observed. | Preserve as a manual-marking item. Mark answer-key/rubric provenance as absent or `manual_marking_required` according to the target format. Do not promote a student's response into the migrated exam. |
| Single-choice MCQ | `DXE-2026-05-07-structure`, `BLANK-PDF-2026-05-07`, `RESULT-PDF-2026-05-07-SANITIZED` | `.dxe` type `1`, title, prompt, `maxScore`, and ordered alternatives. Result PDF labels identify correct alternatives with `(Korrekt svar)` or `(Korrekt alternativ)`. | In the observed `.dxe`, every alternative has `right: false`; blank PDF contains no hidden correct-answer metadata. Result PDF may show a student's wrong selection as `(Fel svar)`. | Use `.dxe` for structure. Use result-PDF labels only for correct-answer enrichment. Discard `(Fel svar)` and all student-result history. Without result-PDF evidence, mark answer-key provenance absent and require manual answer entry. |
| Multiple-response MCQ | `DXE-2026-05-07-structure`, `BLANK-PDF-2026-05-07`, `RESULT-PDF-2026-05-07-SANITIZED` | `.dxe` type `2`, title, prompt, `maxScore`, ordered alternatives, `gradingType`, `isAlternativeChoiceLimitEnabled`, and `alternativeChoiceLimit`. Result PDF labels identify correct alternatives. | In the observed `.dxe`, every alternative has `right: false`. Blank PDF contains no correct-answer metadata. One result PDF does not prove the full score function for every possible response combination. | Use `.dxe` for structure and policy fields. Use result-PDF labels only for correct answers. Discard wrong selections. Treat scoring policy as source metadata, but require target-specific validation before claiming full automatic marking parity. |
| Gap-fill / lucktext | `DXE-2026-05-07-structure`, `DXE-CORPUS-MANIFEST-2026-05-12`, `BLANK-PDF-2026-05-07`, `RESULT-PDF-2026-05-07-SANITIZED` | `.dxe` type `3`, prompt `bodyHTML`, `span dx-wg-id` bindings, `blanks[]` gap GUIDs, `maxScore`, and `gradingType`. Blank PDF renders numbered gaps. Result PDF exposes correct gap words in the checked result view. | Observed `.dxe` gap `validations` arrays are empty across the current local input pool. The test prompt also contains answer-like words as visible prompt text; that is not hidden answer-key provenance. | Use `.dxe` for gap structure. Map gap GUIDs, display order, and prompt bindings into source-neutral `ExamAuthoringIR v1` gap/open-cloze interactions. Use result-PDF correct gap words only as answer-key enrichment. Ignore wrong student gap values. Without result-PDF or populated validations, require manual accepted answers. |
| Matching-styled gap/open-cloze workaround | `PDF-CHEMISTRY-2026-04-25` | Student-view PDF exposes a titled `Para ihop` item, numbered prompt rows, lettered target-like options, and a blank-row artifact such as `1 = 1. 2 = 2. 3 = 3. 4 = 4.` | Canonical DigiExam `.dxe` sources do not carry matching items. Student-view PDF carries no correct matches. | Treat as non-canonical PDF artifact evidence in the current DigiExam parser path. Task 305 defines the neutral gap/open-cloze contract available to future source adapters when source evidence is sufficient. Target validators/exporters, not the source parser, decide whether matching remapping, degraded manual/free-text output, omission, or manual recreation guidance is safe. |

## Chemistry PDF Artifact Regression Fixture

`PDF-CHEMISTRY-2026-04-25` remains a Task 267 PDF parser regression fixture.
It is the same blank/student-view artifact class as
`BLANK-PDF-2026-05-07`, so it must not be treated as the EPIC-10 parser
baseline after the `.dxe` source-policy decision. Parser tests may keep this
exact ordered stream only to preserve PDF-only fallback behavior:

| Order | Header/title | Expected type | Point marker | Source note |
|---|---|---|---|---|
| 1 | `Materia` | multiple choice | absent | Student-view PDF options only; answer key absent |
| 2 | `Para ihop` | unknown | absent | Non-canonical matching-styled gap/open-cloze workaround evidence; answer key absent |
| 3 | `Grundämnen` | multiple choice | absent | Student-view PDF option text crosses a page boundary |
| 4 | `Atomen` | open ended | `Max poäng : 4` | Student-view PDF subparts `a)` through `d)` |
| 5 | `Ämnen` | open ended | `Max poäng : 4` | Student-view PDF subparts `a)` through `c)` |
| 6 | `Joner` | multiple choice | absent | Student-view PDF options only; answer key absent |
| 7 | `Emulsion` | open ended | `Max poäng : 2` | Student-view PDF single prompt |
| 8 | `Separera` | open ended | `Max poäng : 3` | Student-view PDF subparts plus instruction line |
| 9 | `Reaktion` | open ended | `Max poäng : 3` | Student-view PDF subparts `a)` through `c)` |
| 10 | `Förklara` | open ended | `Max poäng : 3` | Student-view PDF single prompt |
| 11 | `Te` | open ended | `Max poäng : 3` | Student-view PDF single prompt |
| 12 | `Dela upp färg` | open ended | `Max poäng : 3` | Student-view PDF subparts `a)` through `c)` |

The corresponding parser contract is:

- total item count is 12;
- ordered headers/titles match the table above;
- item-type breakdown is 3 multiple-choice, 1 unknown, and 8 open-ended;
- point-marker evidence is present exactly where the table lists a marker;
- multiple-choice answer-key provenance is absent, while the `Para ihop` item
  is marked `not_applicable` because it is not a supported DigiExam source
  item type;
- the `Para ihop` item preserves visible source lines only in the current
  DigiExam parser path; Task 305 now provides the neutral gap/open-cloze
  authoring IR contract that future source adapters can use when evidence is
  sufficient, but target-specific matching remapping remains a
  validator/exporter decision.

## Unsupported Or Unobserved Item Types

No observed artifact in this reference set proves true/false, ordering,
image-based, table-based, math-heavy, attachment, grid/categorise, or QTI-native
item semantics. These shapes must fail closed or require a new fixture-backed
task before renderer or bulk workflow support.

## Parser Contract Implications

- `.dxe` parsing is the primary implementation path and parser baseline for
  future EPIC-10 structure work.
- PDF-only parsing remains useful for legacy Task 267 regression fixtures,
  last-resort fallback, and parity checking, but must not be treated as the
  primary structure path when `.dxe` is available.
- Answer-key provenance must name the source class: `.dxe_populated_key`,
  `graded_result_pdf_correct_labels`, `manual_teacher_key`, or `absent`.
- Result-PDF extraction must explicitly discard wrong selections and
  per-student result data.
- Any future `.dxe` fixture with `right: true` or non-empty gap `validations`
  must be added as a new evidence row before parser behavior treats `.dxe` as
  answer-key provenance.
