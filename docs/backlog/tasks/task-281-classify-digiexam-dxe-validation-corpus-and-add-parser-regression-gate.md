---
id: task-281-classify-digiexam-dxe-validation-corpus-and-add-parser-regression-gate
title: Classify DigiExam DXE validation corpus and add parser regression gate
type: task
status: completed
priority: high
created: '2026-05-12'
last_updated: '2026-05-12'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-40-digiexam-dxe-source-parser-and-answer-key-provenance.md
  - docs/backlog/stories/story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema.md
  - docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/tasks/task-274-implement-digiexam-dxe-parser-fixtures-and-result-pdf-answer-enrichment-gate.md
  - docs/backlog/tasks/task-275-implement-digiexam-intermediate-exam-representation-and-manifest-schema-contract.md
  - docs/backlog/tasks/task-276-implement-digiexam-dxe-embedded-asset-ir-support.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
labels:
  - digiexam
  - dxe
  - parser
  - validation-corpus
  - privacy
  - fixture-manifest
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Classify the newly added local DigiExam `.dxe` validation package and turn it
into a governed parser/IR regression gate without accidentally tracking raw
teacher exports that contain unnecessary metadata.

The local package is:

```text
inputs/examples/digiexam-evidence/OneDrive_1_5-12-2026/
```

Initial smoke on 2026-05-12 found:

- 23 `.dxe` JSON exports;
- all 23 parsed with status `success`;
- 317 total items;
- item breakdown: 273 open-ended, 27 single-choice, 4 multiple-response, and
  13 gap-fill;
- 8 embedded image assets;
- 44 `missing_answer_key_provenance` warnings, all on machine-marked or gap
  items where no accepted answer source is present.

This task decides what can be retained as metadata-only evidence, what must
stay local-private, and what sanitized fixtures should be derived.

## PR Scope

- Inspect the local validation package without printing or committing raw exam
  content.
- Classify each `.dxe` export for retention safety:
  - raw local-only source;
  - metadata-only manifest entry;
  - candidate for sanitized/minimal fixture derivation;
  - blocked from retention because it exposes unnecessary metadata or private
    content.
- Build a metadata-only corpus manifest that records, per file:
  - filename;
  - SHA-256;
  - byte size;
  - parse status;
  - item count;
  - item-type counts;
  - warning-code counts;
  - embedded asset count and asset hashes only;
  - answer-key provenance counts.
- Add a parser/IR regression gate that can run over the corpus manifest and
  local raw corpus path without committing raw exports.
- Preserve the previous Task 276 privacy boundary: raw `.dxe` files containing
  user, organization, encryption, timing, or other unnecessary metadata must
  not be promoted as tracked fixtures.
- Derive sanitized/minimal fixtures only when they are needed to cover a new
  parser behavior, such as embedded assets, populated `.dxe` answer keys, new
  question type codes, or previously unseen malformed-but-valid structures.
- Update `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`
  with the metadata-only corpus summary and retention decision.
- Do not change parser behavior except for discrete fixes discovered by this
  corpus and covered by tests.
- Do not implement QTI, DOCX, service runtime, or Skriptoteket UI behavior in
  this task.

## Deliverables

- [x] Metadata-only validation-corpus manifest for the OneDrive `.dxe` package.
- [x] Parser corpus runner or test helper that reads local raw files by explicit
  path and emits only metadata-safe summaries.
- [x] Focused regression test proving the current corpus parses with the
  expected status, item-type counts, warning-code counts, and embedded asset
  count.
- [x] Sanitized/minimal fixture decision recorded: none were derived because
  the corpus exposed no new parser edge beyond metadata-only regression
  coverage.
- [x] Updated DigiExam artifact/item-type evidence reference with the corpus
  summary and retention policy.
- [x] Handoff update naming the corpus as a local validation source, not a
  tracked raw fixture set.

## Acceptance Criteria

- [x] Raw OneDrive `.dxe` files are not committed unless a later explicit
  retention decision approves a sanitized/minimal subset.
- [x] The corpus gate can be run locally against
  `inputs/examples/digiexam-evidence/OneDrive_1_5-12-2026/` without exposing
  prompt text, user metadata, organization metadata, timing data, or raw image
  payloads in logs or tracked artifacts.
- [x] The current corpus baseline is metadata-backed: 23 files, 317 items,
  8 embedded assets, and only expected `missing_answer_key_provenance` warnings
  unless implementation finds and documents a corrected baseline.
- [x] Any parser failure, blocking warning, unknown question type, asset binding
  failure, or unexpected answer-key provenance state becomes either a fixed
  parser regression or an explicit manual-follow-up/unsupported-shape record.
- [x] The parser/IR gate remains renderer-neutral and does not encode
  Exam.net PDF or QTI syntax.
- [x] The QTI Task 280 implementation can reference this corpus only through
  parser/IR outputs or metadata-safe manifests, not by treating raw files as
  bundled product artifacts.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] Focused parser corpus smoke over the OneDrive `.dxe` package:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_corpus_manifest.py -q`
- [x] Focused DigiExam parser tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_parser.py -q`
- [x] Focused DigiExam IR tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py -q`
- [x] `pdm run typecheck-all`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Stop Conditions

- Stop before committing raw `.dxe` files from the OneDrive package without an
  explicit governed retention decision.
- Stop before logging or tracking raw prompt text, student/user metadata,
  organization metadata, encryption metadata, timing fields, or raw image
  payloads from the package.
- Stop before changing QTI, DOCX, service API runtime, or Skriptoteket code.
- Stop before weakening existing privacy constraints around sanitized
  result-PDF enrichment or raw `.dxe` retention.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
