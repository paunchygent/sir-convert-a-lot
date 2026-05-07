---
title: DigiExam Mixed Question Type Evidence 2026-05-07
type: reference
status: active
created: '2026-05-07'
last_updated: '2026-05-07'
---

# DigiExam Mixed Question Type Evidence 2026-05-07

Fixture and evidence packet for EPIC-10 DigiExam migration research and parser
work. This directory groups the teacher-exported artifacts for the same
seven-question mixed-type DigiExam test.

The canonical evidence contract is
`docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`.

## Files

| Evidence ID | File | SHA-256 | Artifact class | Tracking policy |
|---|---|---|---|---|
| `DXE-2026-05-07-structure` | `1772718003-test-samma-prov-i-digiexam.dxe` | `9a24b363b0066499ee574b118764f7f93361d7528f13ea9dc013ec06e24aaff5` | DigiExam `.dxe` JSON export | Shared fixture |
| `DXE-2026-05-07-duplicate` | `1772718003-test-duplicate.dxe` | `9b4b35fab0e22675805e9ec70c1bf5f99c3c4d3c43d7f5fbec3eeec641491c38` | DigiExam `.dxe` JSON export | Shared fixture |
| `BLANK-PDF-2026-05-07` | `DigiExam-Test-som-nedladdningsbar.pdf` | `2c66ff8ad84ddb4300091c04c87ed397ca6927ae0443cd208399055081b86ab8` | Blank/student-view jsPDF export | Shared fixture |
| `RESULT-PDF-2026-05-07-SANITIZED` | `graded-student-result-sanitized.pdf` | `cf0e333ab65f08a21e5345fcc37f8d431c066cdc6b77dcc646e31f35a71e8664` | Sanitized graded student-result jsPDF export | Shared fixture |

## Private Original

`local-private/` is intentionally ignored. It may contain the original
student-result PDF with the real student name for local re-verification only.
Do not commit files from `local-private/`.

The sanitized result PDF redacts the real name to `Example Student` while
preserving the DigiExam result labels needed for parser evidence:

- `(Korrekt svar)`
- `(Korrekt alternativ)`
- `(Fel svar)`
- `Erhållen poäng : N`
