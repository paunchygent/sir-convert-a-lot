# DigiExam DXE Fixture Corpus 2026-05-12

This directory is the Task 309 versioned DigiExam `.dxe` fixture corpus moved
from `inputs/examples/digiexam-evidence/OneDrive_1_5-12-2026/`.

Retention decision:

- The raw `.dxe` exports are intentionally tracked as governed fixtures.
- The corpus is scoped to pure DigiExam exports for answer-key live validation.
- Non-DigiExam, ignored, private, or mixed-source evidence is excluded.
- Provider prompts, provider responses, full validation reports, and Hemma run
  artifacts stay outside git.

Tracked metadata:

- `validation-corpus-manifest.json` freezes source SHA, item fingerprint,
  item type, eligibility, skip reason, and provider output mode.
- `expected-answer-worklist.json` lists the 42 eligible items that still need
  teacher-verified goldens before scoring.

Use `pdm run task-309-answer-key-live prepare-manifests` to regenerate the
tracked manifest/worklist, or pass `--output-root build/verification/...` for
scratch copies during live-run preparation.
