---
type: reference
id: REF-examnet-pdf-to-exam-swedish-renderer-profile
title: Exam.net PDF-to-Exam Swedish Renderer Profile
status: active
created: 2026-05-12
updated: 2026-05-12
owners:
  - platform
tags:
  - examnet
  - exam-migration
  - pdf-to-exam
  - qti
  - docx
  - swedish
links:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/tasks/task-277-implement-digiexam-exam-net-oriented-pdf-renderer-and-live-validation.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
---

## Purpose

Define the canonical Swedish text profile for PDFs intended for Exam.net's
PDF-to-exam converter, and define how that profile fits the broader teacher
authoring artifact direction.

This reference is not limited to DigiExam migration. It is the shared renderer
profile for any Sir Convert route that emits a PDF for Exam.net's
best-effort PDF-to-exam converter.

## Current Evidence Boundary

The profile below is based on local empirical Exam.net converter trials and
the current product direction that teachers upload a PDF, Exam.net converts it
into best-effort exam items, and the teacher manually validates and completes
the imported exam.

Public Exam.net material supports the broad premise that teachers can create
exams by uploading existing PDFs and can work with auto-marked question types.
It does not publish a parser specification, an import API, or a complete QTI
contract. Treat the exact labels and item-shape recognition below as empirical
converter behavior that must stay fixture-backed.

## API Family Direction

Sir Convert should expose one shared service API v2 job lifecycle for teacher
exam artifacts, with separate route contracts:

- `digiexam_dxe -> examnet_migration_bundle` for legacy DigiExam migration.
- `examnet_artifact -> teacher_authoring_bundle` for normal teacher-owned
  Exam.net artifacts that should become QTI packages and editable DOCX files.

Do not overload the DigiExam route with Exam.net-origin PDFs or Word exports.
The source authority differs:

- DigiExam migration uses `.dxe` as canonical structure and optional sanitized
  result PDFs only as correct-answer evidence.
- Exam.net artifact authoring uses teacher-owned Exam.net-compatible PDFs or
  Word exports as the source artifact and must classify whether the source is a
  student view, key view, teacher export, or manually supplied answer source.

Both routes may emit an Exam.net PDF-to-exam converter PDF, QTI, editable DOCX,
IR, warnings, QTI validation reports, and manual-follow-up reports through the
same named artifact bundle pattern. QTI package semantics and validation are
owned by
`docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md`.

## Canonical Swedish PDF Profile

Use Swedish labels and exact-text answer keys:

```text
Fråga N
Poängvärde: N
Typ: [frågetyp]

[Frågetext]
```

Preferred labels:

| Function | Label |
| --- | --- |
| Question number | `Fråga N` |
| Points | `Poängvärde: N` |
| Item type | `Typ: ...` |
| Alternatives | `Svarsalternativ:` |
| Single correct answer | `Rätt svar:` |
| Multiple correct answers | `Rätta svar:` |
| Matching left side | `Vänster sida:` |
| Matching right side | `Höger sida:` |
| Matching key | `Rätta par:` |

Avoid:

- `Score: N`
- `Totalpoäng: N`
- source-side alternative labels such as `A.`, `B.`, `a)`, or `1.` unless a
  later fixture proves they are required.

Alternatives should be indented plain text. Exam.net owns any final option
labels and may reshuffle alternatives.

## Supported Item Profiles

### Flerval, Ett Rätt Svar

```text
Fråga 1
Poängvärde: 4
Typ: Flerval
Välj ett svar.

Vilket påstående är den starkaste tesen?

Svarsalternativ:
    Sociala medier används av många människor.
    Den här texten handlar om sociala medier.
    Även om sociala medier kan ge unga bättre tillgång till nyheter, kan de också förvränga debatten genom att belöna snabbhet framför belägg.
    Nyheter är viktiga i samhället.

Rätt svar: Även om sociala medier kan ge unga bättre tillgång till nyheter, kan de också förvränga debatten genom att belöna snabbhet framför belägg.
```

Post-import teacher check remains required:

- `Flera val` is off.
- Point value is correct.
- The intended answer is selected.

Until the single-choice `Flera val = av` behavior is fully proven, single
answer multiple choice is supported with a manual validation warning.

### Flerval, Flera Rätta Svar

```text
Fråga 2
Poängvärde: 5
Typ: Flerval
Välj alla korrekta svar.

Vilka drag stärker vanligtvis ett källkritiskt svar om information på nätet?

Svarsalternativ:
    Svaret använder relevanta belägg.
    Svaret kopplar beläggen till huvudfrågan.
    Svaret byter ämne mitt i resonemanget.
    Svaret skiljer mellan fakta, tolkning och värdering.

Rätta svar: Svaret använder relevanta belägg.; Svaret kopplar beläggen till huvudfrågan.; Svaret skiljer mellan fakta, tolkning och värdering.
```

Semicolon-separated keys are the promoted shape for multiple correct answers.
The renderer must use exact option text, not letter keys.

### Kort Svar

```text
Fråga 3
Poängvärde: 3
Typ: Kort svar

Vilken molekyl används som cellens kortsiktiga energivaluta?

Rätta svar: ATP; adenosintrifosfat; adenosine triphosphate
```

Post-import validation must still check whether semicolon-separated accepted
answers became separate accepted values or one literal string.

### Fritext

```text
Fråga 5
Poängvärde: 9
Typ: Fritext

Resonera kring hur sociala medier både kan förbättra tillgången till information och förvränga den offentliga debatten.

Skriv 250-400 ord. Använd minst ett konkret exempel och utveckla en tydlig tankegång.
```

Do not include a `Rätt svar:` or `Rätta svar:` line for free-text items. Rubrics
and marking guides belong in sidecar metadata, not in the PDF submitted to
Exam.net's converter.

### Matcha Ihop / Para Ihop

```text
Fråga 6
Poängvärde: 4
Typ: Matcha ihop

Para ihop varje cellstruktur med rätt funktion.

Vänster sida:
    kloroplast
    mitokondrie
    ribosom
    cellkärna

Höger sida:
    fotosyntes
    ATP-produktion
    proteinsyntes
    genetisk information

Rätta par:
kloroplast = fotosyntes
mitokondrie = ATP-produktion
ribosom = proteinsyntes
cellkärna = genetisk information
```

`Typ: Para ihop` is an accepted synonym to test and may be used where it better
matches source wording.

Matching is promoted as a supported target shape only when source evidence
contains:

- ordered left prompts;
- ordered right options;
- explicit pairings as exact text.

If the source has left/right structure but no correct pairings, preserve the
structure and emit `manual_answer_key_required`; do not synthesize pairings.

Avoid letter-pair keys such as `1=b; 2=a` as the default. Exact text pairing is
the canonical renderer profile.

## Not Yet Promoted: Lucktext / Gap Fill

Gap-fill PDF-to-exam support is not promoted yet. Current evidence suggests
external answer-key lists can be misread as matching or short-answer content.

Next experiment profile:

```text
Fråga 8
Poängvärde: 4
Typ: Lucktext

Cellens kortsiktiga energivaluta är [ATP].
```

or:

```text
Fråga 9
Poängvärde: 5
Typ: Fyll i luckorna

Vid cellandning reagerar [glukos] med [syre] och bildar [koldioxid] och [vatten].
```

No separate `Rätt svar:`, `Rätta svar:`, or `Facit:` line should be used in
the next gap-fill experiment.

## Authoring Bundle Direction

Editable DOCX must be generated from normalized exam authoring IR, not from a
generic PDF-to-DOCX visual conversion. QTI and DOCX should share the same
semantic source:

```text
source artifact
-> normalized exam authoring IR
-> QTI package
-> editable DOCX
-> Exam.net PDF-to-exam converter PDF
-> QTI validation report
```

The authoring IR must preserve:

- item order;
- item type;
- prompt body;
- point value;
- alternatives;
- matching left/right lists and exact pairs when present;
- accepted short-answer variants;
- free-text instructions and sidecar rubric metadata;
- warnings and manual-follow-up requirements.

## Follow-Up Proof Requirements

Before implementation promotes this profile for unattended production use, add
fixture-backed proof for:

- single-answer flerval import with `Flera val = av`;
- semicolon short-answer variants as separate accepted answers;
- matching import with exact-text `Rätta par`;
- Exam.net-origin PDF/Word source classification;
- QTI export/import mapping for matching;
- QTI 2.1 package validation through the selected validator ladder;
- editable DOCX round-trip clarity for teachers.
