---
type: reference
id: REF-SIRCON-GENERAL-exam-net-pdf-to-exam-swedish-renderer-profile
title: Exam.net PDF-to-Exam Swedish Renderer Profile
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: general
retired_ids:
- REF-examnet-pdf-to-exam-swedish-renderer-profile
summary: Exam.net PDF-to-Exam Swedish Renderer Profile
---

## Overview

## Facts And Semantics

## Decisions And Interpretation

## Historical Source Content

### Purpose

Define the canonical Swedish text profile for PDFs intended for Exam.net's
PDF-to-exam converter, and define how that profile fits the broader teacher
authoring artifact direction.

This reference is not limited to DigiExam migration. It is the shared renderer
profile for any Sir Convert route that emits a PDF for Exam.net's
best-effort PDF-to-exam converter.

### Current Evidence Boundary

The profile below is based on local empirical Exam.net converter trials and
the current product direction that teachers upload a PDF, Exam.net converts it
into best-effort exam items, and the teacher manually validates and completes
the imported exam.

Public Exam.net material supports the broad premise that teachers can create
exams by uploading existing PDFs and can work with auto-marked question types.
It does not publish a parser specification, an import API, or a complete QTI
contract. Treat the exact labels and item-shape recognition below as empirical
converter behavior that must stay fixture-backed.

### API Family Direction

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

### Canonical Swedish PDF Profile

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

### Policy Ownership Boundary

This profile owns Exam.net PDF export policy only. It may consume source IR or
effective IR state, but it must not define, mutate, or serialize that state.

- Source IR owns parsed source structure, source evidence, source provenance,
  stable item identity, and renderer-neutral embedded assets.
- Effective IR owns accepted authoring corrections such as manual answer keys,
  reviewed answer-key completion, item text changes, point corrections, and
  gap/choice corrections.
- The Exam.net PDF target profile owns supported export shapes, Swedish layout
  labels, item-level target warnings, and PDF-specific formatting.
- Accepted-current-state is not source IR or effective IR state. The historical
  manual/degraded accepted-current-state PDF path is removed from current
  authoring/correction runtime by Task 337. A future
  best-effort incomplete PDF export, if approved, must be modeled as an
  export-only request policy consumed by this target profile.
- The core PDF exam item protocol must not carry Exam.net import needs.
  Exam.net-specific reshaping is allowed only inside the Exam.net PDF target
  profile. A source item may therefore be presented through a
  target-compatible alternate layout when the requested output is
  Exam.net-oriented PDF, but that reshape must be explicit target policy with
  provenance-preserving labels, warnings, and manual-follow-up signals. The
  current Exam.net PDF profile must not present open-cloze/`Lucktext` as
  `Fritext`; it must keep the `Lucktext` label or block the item with typed
  warnings. Target shaping must not rewrite source IR, effective IR, or neutral
  PDF item semantics.
- The Exam.net target-profile context is a read-only export policy value, not
  an IR or correction layer. It may carry target identity/version, Swedish label
  policy, Exam.net shaping permissions, target-support decisions, warning codes,
  manual-follow-up semantics, and importer-facing formatting constraints,
  including removal of generic helper instructions that degrade import quality.
  It must not carry parser/source fields, effective IR mutations, overlay or
  correction payloads, target-readiness rows, artifact availability, QTI policy,
  accepted-current-state decisions, service job state, HTML shell details, or
  WeasyPrint/filesystem concerns.
- The WeasyPrint adapter owns HTML/CSS materialization into PDF bytes. It must
  stay infrastructure-only and must not decide item support, answer-key trust,
  accepted-current-state behavior, or readiness semantics.

### Supported Item Profiles

### Flerval, Ett Rätt Svar

```text
Fråga 1
Poängvärde: 4
Typ: Flerval

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

- ordered source prompts;
- ordered target options;
- explicit pairings as exact text.
- no source prompt mapped to more than one target option;
- no matched target option reused by more than one source prompt;
- optional extra target options that are not matched to any source prompt,
  treated as distractors.

If the source has source/target structure but no correct pairings, preserve the
structure and emit `manual_answer_key_required`; do not synthesize pairings.

Avoid letter-pair keys such as `1=b; 2=a` as the default. Exact text pairing is
the canonical renderer profile.

This Exam.net PDF profile is intentionally narrower than the Sir Convert
intermediary IR and general QTI. The IR may represent many-left-to-one or
left-to-many matching through QTI-style association constraints, but this PDF
target profile must report those shapes as not ready for keyed Exam.net PDF
export until product explicitly promotes that PDF target shape. This is a
target-profile question, not a DigiExam-source restriction.

### Gap/Open-cloze PDF Target Profile

Gap-fill PDF-to-exam native auto-evaluation support is not promoted yet.
Reviewed/source/teacher accepted values must still be included in the PDF
artifact. The current supported PDF shape for keyed gap/open-cloze items keeps
the item labeled as `Lucktext` and lists the accepted values in the artifact.

Task 337 supersedes the former Task 303/308 accepted-current-state export path.
Missing-key single-choice, multiple-response, and gap/open-cloze items remain
blocked for Exam.net PDF export until a real reviewed/source/teacher answer-key
correction supplies the required key data. The current renderer must not emit a
manual/unkeyed accepted-current-state fallback, must not relabel `Lucktext` as
`Fritext`, and must not claim automatic evaluation without trusted keys.

The live ecology fixture `item-013` is a DigiExam `Lucktext`/gap item with five
blanks, an embedded image, and no accepted values in blank validations. In the
current profile this item remains blocked until reviewed/source/teacher
accepted values are supplied. Target readiness must preserve item-specific
missing-key and native-target limitation reasons so consumers can show the
correct teacher action.

Task 308 is historical for the retired missing-key manual/unkeyed PDF profile.
Task 321 remains current for keyed output: when accepted values exist, the PDF must
include them even for multi-gap items.

Preferred native experiment profile:

```text
Fråga 8
Poängvärde: 4
Typ: Lucktext

Cellens kortsiktiga energivaluta är [ATP].
```

Alternative native label experiment:

```text
Fråga 9
Poängvärde: 5
Typ: Fyll i luckorna

Vid cellandning reagerar [glukos] med [syre] och bildar [koldioxid] och [vatten].
```

No separate `Rätt svar:`, `Rätta svar:`, or `Facit:` line should be used in
the next gap-fill experiment.

Historical Task 308 missing-key fallback profile is superseded by Task 337 and
is not part of the current template.
Task 337 removes it from current authoring/correction and migration-bundle
runtime. Missing-key PDF export now remains unavailable until real source,
manual, or reviewed effective key state exists. A future content-preserving
incomplete PDF export would need a separate export-only contract.

### Authoring Bundle Direction

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
- matching source/target lists and exact pairs when present;
- accepted short-answer variants;
- free-text instructions and sidecar rubric metadata;
- warnings and manual-follow-up requirements.

### Follow-Up Proof Requirements

Before implementation promotes this profile for unattended production use, add
fixture-backed proof for:

- single-answer flerval import with `Flera val = av`;
- semicolon short-answer variants as separate accepted answers;
- matching import with exact-text `Rätta par`;
- matching import with unmatched right-side distractors;
- negative matching fixtures for left-to-many and right-to-many keyed pairs;
- Exam.net-origin PDF/Word source classification;
- QTI export/import mapping for matching;
- QTI 2.1 package validation through the selected validator ladder;
- editable DOCX round-trip clarity for teachers.
