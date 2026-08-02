---
id: task-276-implement-digiexam-dxe-embedded-asset-ir-support
title: Implement DigiExam dxe embedded asset IR support
type: task
status: completed
priority: high
created: '2026-05-09'
last_updated: '2026-05-12'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md
  - docs/backlog/tasks/task-274-implement-digiexam-dxe-parser-fixtures-and-result-pdf-answer-enrichment-gate.md
  - docs/backlog/tasks/task-275-implement-digiexam-intermediate-exam-representation-and-manifest-schema-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
labels:
  - exam-migration
  - digiexam
  - assets
  - parser
  - intermediate-representation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement renderer-neutral embedded asset support for DigiExam `.dxe` parser
outputs and the DigiExam IR/manifest contract. The implementation should make
base64 image payloads explicit and auditable without choosing PDF, QTI,
Exam.net, API, or bulk-workflow rendering behavior.

## PR Scope

- Add typed asset value objects to the DigiExam parser contract for decoded
  question images.
- Decode `question.images[]`, infer supported media type from bytes, compute
  SHA-256 and byte length, and capture dimensions for PNG/JPEG where available.
- Bind assets to item-local `data-image-id` references found in `bodyHTML`.
- Model asset records separately from ordered asset references. Repeated
  `<img data-image-id="N">` occurrences are valid multiple references to the
  same asset, not duplicate-asset errors.
- Extend `.dxe` parser behavior to fail closed on:
  - invalid base64;
  - unsupported image signatures;
  - `data-image-id` references without a matching `question.images[]` value;
  - unused image payloads that cannot be traced to prompt HTML.
- Add explicit blocking warning codes:
  `invalid_embedded_asset_base64`,
  `unsupported_embedded_asset_media`,
  `missing_embedded_asset_reference`,
  `unused_embedded_asset_payload`, and
  `ambiguous_embedded_asset_binding`.
- Extend `DigiExamIrItem` and manifest item summaries with renderer-neutral
  asset fields and ordered asset summaries.
- Version the IR contract as `digiexam_intermediate_exam_v2` and the manifest
  contract as `digiexam_ir_manifest_v2`; do not add required asset fields to
  the completed v1 schemas.
- Update `docs/converters/digiexam-intermediate-exam-representation-contract.md`
  and `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md` with
  the observed `.dxe` asset contract.
- Promote only sanitized or minimal fixture evidence. Do not commit raw
  colleague export metadata such as user, organization, encryption, or timing
  fields unless a governed evidence decision explicitly allows it.

## Out Of Scope

- PDF image placement or visual layout policy.
- QTI package generation or assessment-item XML.
- Exam.net upload/import behavior.
- Service/API routes and bulk migration workflow.
- Answer-key synthesis or rubric extraction.
- OCR of embedded images.

## Suggested Implementation Plan

1. Create or sanitize a fixture that preserves a `.dxe` question with
   `images[0]` and matching `<img data-image-id="0">`.
1. Add `DigiExamEmbeddedAsset` and `DigiExamEmbeddedAssetReference` style value
   objects to the domain contract, keeping names aligned with the existing
   parser/IR naming style.
1. Implement a sibling domain module, `digiexam_embedded_assets.py`, with a
   Google-style module docstring for decoding, signature parsing, dimensions,
   and HTML `data-image-id` reference binding. Do not fold this logic into
   `digiexam_dxe_parser.py`.
1. Extend parser warnings with exact blocking asset-specific warning codes
   rather than silently dropping image data or reusing generic malformed-source
   warnings.
1. Add v2 IR fields that carry asset records and ordered references by item
   without rewriting prompt HTML into renderer-specific syntax.
1. Add manifest asset summaries for exam-level and per-item parity so
   consumers can compare `asset_id`, `source_image_index`, `sha256`,
   `media_type`, `byte_length`, dimensions, and reference order before
   rendering.
1. Update docs and close validation.

## Deliverables

- [x] Sanitized or minimal `.dxe` fixture with an embedded image reference, plus
  proof that the raw colleague export is ignored and absent from `git ls-files`.
- [x] Typed parser contract for embedded DigiExam assets.
- [x] `digiexam_embedded_assets.py` extraction and validation helper.
- [x] IR v2 and manifest v2 asset fields and ordered summaries.
- [x] Fixture-backed parser and IR regression tests.
- [x] Converter contract and evidence-reference updates.

## Acceptance Criteria

- [x] Parser and IR contracts expose embedded asset values without `Any`,
  `typing.cast`, `# type: ignore`, or lint-ignore shortcuts.
- [x] Image assets are identified by deterministic ids and SHA-256 hashes, not
  by unstable array positions alone.
- [x] `data-image-id` references bind to exactly one decoded image asset, while
  repeated references to the same source image index remain valid ordered
  references.
- [x] Invalid or unbound asset references make the parser result blocked and
  `renderer_ready=false`.
- [x] Asset failures use exact warning codes
  `invalid_embedded_asset_base64`,
  `unsupported_embedded_asset_media`,
  `missing_embedded_asset_reference`,
  `unused_embedded_asset_payload`, and
  `ambiguous_embedded_asset_binding`; tests assert those codes and
  `renderer_ready=false`.
- [x] Manifest summaries include deterministic ordered asset summaries for the
  exam and each item, not counts alone.
- [x] Manifest tests assert `asset_id`, `source_image_index`, `sha256`,
  `media_type`, `byte_length`, dimensions, and reference count/order.
- [x] IR and manifest schema constants are bumped to v2, while no-image
  regression tests prove existing `.dxe` fixtures map to empty asset summaries
  and unchanged answer-key provenance.
- [x] Existing no-image `.dxe` and PDF artifact fallback tests remain green.
- [x] The implementation does not add renderer-specific PDF/QTI/Exam.net
  syntax.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py -q`
- [x] 2026-05-12 Review 11 remediation:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py -q`
  (`28 passed`), including `images=[]` and absent `images` regression tests
  for `bodyHTML` `data-image-id` references.
- [x] `test -z "$(git ls-files | rg '1776888013|ak7-lag' || true)"` proves
  there is no tracked raw colleague fixture path, unless a later governed
  evidence decision explicitly promotes a sanitized/minimal derivative.
- [x] `pdm run coverage-gate`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Stop Conditions

- Stop and ask before committing the raw colleague `.dxe` export if it still
  contains unnecessary metadata or any material that should remain local.
- Stop before adding a new third-party image parser dependency; use standard
  library byte parsing first or open a separate dependency decision.
- Stop before changing renderer/API/bulk behavior.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
