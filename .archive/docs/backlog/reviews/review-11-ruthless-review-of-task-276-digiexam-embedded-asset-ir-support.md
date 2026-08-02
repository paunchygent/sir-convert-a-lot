---
id: review-11-ruthless-review-of-task-276-digiexam-embedded-asset-ir-support
title: Ruthless review of Task 276 DigiExam embedded asset IR support
type: review
status: completed
priority: high
created: '2026-05-11'
last_updated: '2026-05-12'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md
  - docs/backlog/tasks/task-276-implement-digiexam-dxe-embedded-asset-ir-support.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
labels:
  - digiexam
  - embedded-assets
  - accepted
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Governing authority: Story 42 and Task 276 under EPIC-10.
- Code under review:
  `scripts/sir_convert_a_lot/domain/digiexam_contracts.py`,
  `scripts/sir_convert_a_lot/domain/digiexam_embedded_assets.py`,
  `scripts/sir_convert_a_lot/domain/digiexam_dxe_parser.py`, and
  `scripts/sir_convert_a_lot/domain/digiexam_ir_contracts.py`.
- Tests under review:
  `tests/sir_convert_a_lot/test_digiexam_dxe_parser.py` and
  `tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py`.
- Docs under review: EPIC-10, Story 42, Task 276, the DigiExam IR converter
  contract, the DigiExam evidence reference, generated docs indexes, and
  `.codex/handoff.md`.
- Public surface affected: renderer-neutral DigiExam parser output, IR schema
  version `digiexam_intermediate_exam_v2`, and manifest schema version
  `digiexam_ir_manifest_v2`.

## Findings

- [x] [blocker] `scripts/sir_convert_a_lot/domain/digiexam_embedded_assets.py:78`
  returns success for a `bodyHTML` image reference when `question.images[]` is
  absent or empty. The helper exits before `_body_html_references(...)`, so
  `<img data-image-id="0">` with no payload produces no asset warning, leaves
  `embedded_asset_references=()`, and lets the parser report
  `status=success`/`renderer_ready=true`. That violates Story 42 and Task 276's
  requirement that every `data-image-id` bind to `question.images[N]` or fail
  closed with `missing_embedded_asset_reference`. Proof command:
  `pdm run run-local-pdm python -c '...'` using the sanitized fixture with
  `images=[]` returned `success True` and only the unrelated non-blocking
  `missing_answer_key_provenance` warning. Fix: always inspect `bodyHTML`
  references even when the image payload list is empty, emit the exact blocking
  `missing_embedded_asset_reference` warning for any referenced index without a
  payload, and add focused regression tests for both `images=[]` and the missing
  `images` field.

  Resolved on 2026-05-12. `extract_digiexam_embedded_assets(...)` now validates
  `_body_html_references(...)` before returning for zero payloads, and focused
  tests cover both `images=[]` and an absent `images` field with
  `<img data-image-id="0">`.

- [x] [low] `tmp/pdfs/digiexam-new-sample/page-1.png` and
  `tmp/pdfs/digiexam-new-sample/page-2.png` remain untracked in an unignored
  `tmp/` tree. They are not part of the Task 276 deliverables, and a later
  broad `git add -A` would promote generated proof artifacts without governed
  retention authority. Fix: remove the transient tree or move any required proof
  under an intentionally ignored/provenance-described surface, then make
  `git status --short tmp` clean.

  Resolved on 2026-05-12. The generated `tmp/` PNGs were removed, and
  `git status --short tmp` is clean.

- [x] [low] Closeout metadata still lags the claimed 2026-05-11 completion:
  `.codex/handoff.md:6`, Story 42 frontmatter, Task 276 frontmatter, the IR
  converter contract, and the evidence reference remain stamped `2026-05-09`
  even though the body and validation evidence now record the 2026-05-11 Task
  276 closeout. This is not a runtime failure, but it weakens the governed
  closeout trail in exactly the area the previous re-review flagged. Fix:
  update the touched authority frontmatter in the same remediation slice and
  rerun `pdm run docs-sync` plus docs/handoff validation.

  Resolved on 2026-05-12. Story 42, Task 276, Review 11, the embedded-asset
  evidence reference, and `.codex/handoff.md` now carry the remediation date and
  current validation evidence.

## Decision

Accepted after remediation.

## Response

The core split is good: asset extraction is in a sibling domain helper, the
parser and IR stay renderer-neutral, schema versions are explicitly bumped, the
raw colleague export is not tracked, and the focused tests cover the happy path,
repeated references, invalid base64, unsupported bytes, out-of-range references,
unused payloads, and ambiguous duplicate bindings.

The missing-reference fail-open class is fixed: references with zero payloads
now produce the exact blocking `missing_embedded_asset_reference` warning.

## Follow-up Actions

1. [x] Patch `extract_digiexam_embedded_assets(...)` so empty or absent
   `question.images[]` still validates all `bodyHTML` `data-image-id`
   references and fails closed on any referenced index.
1. [x] Add regression tests for `images=[]` and a missing `images` field with an
   image reference in `bodyHTML`.
1. [x] Clean the untracked `tmp/` proof artifacts or move them to an approved
   ignored/provenance surface.
1. [x] Refresh closeout frontmatter metadata for the authority docs touched by Task
   276\.

## Completion

Review opened on 2026-05-11 with `changes_requested`.

Review closed on 2026-05-12 after remediation.

Validation run during review:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py -q`:
  `26 passed`.
- `pdm run typecheck-all`: success, `594 source files`.
- `pdm run coverage-gate`: `1110 passed, 5 skipped`, total coverage `95.47%`.
- `pdm run docs-validate`: `Validated 346 backlog files`;
  `Validated docs=401 rules=11`.
- `pdm run skills-validate`: ok.
- `pdm run handoff-validate`: ok.
- `git diff --check`: clean.

Remediation validation:

- `pdm run format-all`: `651 files left unchanged`.
- `pdm run lint-fix`: passed.
- `pdm run typecheck-all`: success, `602 source files`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_parser.py -q`:
  `22 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py -q`:
  `28 passed`.
- `pdm run coverage-gate`: `1117 passed, 5 skipped`, total coverage `95.55%`.
- `pdm run docs-sync`; `pdm run docs-validate`: `Validated docs=409 rules=11`,
  `Validated 350 backlog files`.
- `pdm run skills-validate`: ok.
- `pdm run handoff-validate`: ok.
- `git status --short tmp`: clean.
- `git diff --check`: clean.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up actions resolved
- [x] Review closed
