---
id: task-269-reconcile-pdf-ocr-metadata-contract-across-docs-runtime-and-tests
title: Reconcile PDF OCR metadata contract across docs runtime and tests
type: task
status: completed
priority: high
created: '2026-04-27'
last_updated: '2026-04-29'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md
  - docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md
  - docs/backlog/tasks/task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - scripts/sir_convert_a_lot/application/contracts_v2.py
  - scripts/sir_convert_a_lot/domain/specs_v2.py
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py
  - scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py
labels:
  - ocr
  - contract
  - metadata
  - docs
  - api
  - tests
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Repair the active/completed OCR contract drift introduced by Story 21 / Task
77: completed docs still claim OCR metadata fields such as
`ocr_languages_requested` and `ocr_acceleration_used`, while the active
`ConversionMetadataV2` and v2 API docs expose only `ocr_enabled`,
`ocr_engine_used`, and `ocr_languages_used`.

Selected decision: Outcome B. Keep the active v2 result contract limited to the
fields implemented today and edit Story 21, Task 77, Story 39, API docs, smoke
docs, and tests so `ocr_languages_requested` and `ocr_acceleration_used` are no
longer presented as completed/current guarantees.

Rationale:

- `ocr_languages_requested` is request/configuration echo already represented by
  `pdf_options.ocr_languages`; result metadata should continue to report the
  effective OCR languages as `ocr_languages_used`.
- `ocr_acceleration_used` is not currently observed as a separate OCR-stage
  runtime fact. Reporting it from configured intent would be inferred metadata,
  not execution evidence.

Do not add those two fields in this task. If they remain desired, create or link
follow-up authority that defines requested input, resolved configuration, and
observed OCR-stage execution as separate concepts. A mixed state is not allowed:
the fields may not remain checked off in completed acceptance criteria unless
runtime code and tests serialize and verify them.

## PR Scope

- Start with a code-backed inventory of OCR metadata producers, consumers,
  docs, smoke reports, and tests.
- Apply selected Outcome B everywhere: mark both missing fields as
  deferred/superseded everywhere they are still presented as completed
  guarantees.
- Repair completed Story 21 and Task 77 docs so their completed state no longer
  publishes a false active contract.
- Align Story 39, Epic 06, v2 API docs, CLI docs, runtime metadata models,
  smoke verification, and tests with the chosen contract.
- Preserve strict v2 model semantics: any new public field must be documented,
  typed, tested, and serialized through the normal v2 result metadata surface.
- Do not leave "decide later" language in active acceptance criteria.

## Entry Points

- `docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md`
- `docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md`
- `docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/sir_convert_a_lot.md`
- `scripts/sir_convert_a_lot/application/contracts_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/job_store_manifest_v2.py`
- `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py`
- `tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
- `tests/sir_convert_a_lot/test_ocr_preflight_v2.py`

## Deliverables

- [x] OCR metadata inventory naming every active producer/consumer/doc surface.
- [x] Selected Outcome B applied consistently across docs, runtime, and tests.
- [x] Completed Story 21 and Task 77 no longer claim unsupported fields as
  completed runtime guarantees.
- [x] API/contract tests prove the final metadata shape.

## Acceptance Criteria

- [x] `rg "ocr_languages_requested|ocr_acceleration_used" docs scripts tests`
  shows no false completed contract claims. Any remaining occurrences must be
  in explicit deferred/superseded follow-up text or implemented/tested active
  fields.
- [x] `ConversionMetadataV2`, job store persistence, API docs, CLI docs, smoke
  evidence, and tests agree on the same OCR metadata fields and null/list
  semantics.
- [x] Story 21 and Task 77 completed checkboxes remain true only for behavior
  that is actually supported by runtime code and tests.
- [x] Story 21 and Task 77 explicitly mark the old field claims as deferred or
  superseded.
- [x] No completed/current contract language presents either field as active
  runtime behavior.
- [x] Follow-up authority is linked if either field is still desired.

## Test Requirements

- [x] API contract test for the final `conversion_metadata` OCR field set.
- [x] Smoke report helper test if verification output changes; not applicable
  because the smoke report shape already emitted only active fields and did not
  change in this slice.
- [x] Docs grep or focused validator check proving no stale active contract
  claims remain.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

Outcome B is now applied as the active contract:

- active v2 result metadata fields are `ocr_enabled`, `ocr_engine_used`, and
  `ocr_languages_used`,
- `ocr_languages_used` uses `[]` for PDF jobs where OCR was applicable but not
  executed, and `null` only for non-PDF routes where OCR is not applicable,
- `ocr_languages_requested` is superseded as result metadata because requested
  languages already live in `pdf_options.ocr_languages`,
- `ocr_acceleration_used` is deferred because the runtime does not observe OCR
  acceleration as a separate execution fact from backend `acceleration_used`,
- Story 21 and Task 77 keep their completed state only for the implemented OCR
  selection, preflight, smoke, and active metadata behavior.

Inventory checked in this slice:

- Producers and persistence:
  - `scripts/sir_convert_a_lot/application/contracts_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_models_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`
  - `scripts/sir_convert_a_lot/infrastructure/pdf_checkpoint_metadata_v2.py`
- Consumers and smoke evidence:
  - `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
  - `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py`
  - `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions_helpers.py`
- Contract docs:
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/sir_convert_a_lot.md`
  - Story 21, Story 39, and Task 77 backlog authority.

Focused regression coverage:

- `tests/sir_convert_a_lot/test_ocr_metadata_contract.py` proves
  `ConversionMetadataV2` accepts the active OCR result fields and rejects the
  deferred legacy result fields.
- `tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
  proves serialized PDF-to-Markdown result metadata omits both deferred fields
  and uses `ocr_languages_used=[]` for no-OCR PDF results.

Remaining occurrences of the two old field names are retained only in
superseded/deferred governance text or in Task 269 acceptance text that explains
the repair.

## Closeout

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run pytest-root tests/sir_convert_a_lot/test_ocr_metadata_contract.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py -q` (pass; includes no-OCR PDF `ocr_languages_used=[]` contract)
- `pdm run docs-sync` (pass)
- `pdm run docs-validate` (pass)
- `pdm run skills-validate` (pass)
- `pdm run handoff-validate` (pass)
- `git diff --check` (pass)
