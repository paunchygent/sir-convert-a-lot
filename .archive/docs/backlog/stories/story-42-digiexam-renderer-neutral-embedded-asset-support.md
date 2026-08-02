---
id: story-42-digiexam-renderer-neutral-embedded-asset-support
title: DigiExam renderer-neutral embedded asset support
type: story
status: completed
priority: high
created: '2026-05-09'
last_updated: '2026-05-12'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/tasks/task-276-implement-digiexam-dxe-embedded-asset-ir-support.md
  - docs/backlog/stories/story-40-digiexam-dxe-source-parser-and-answer-key-provenance.md
  - docs/backlog/stories/story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
labels:
  - exam-migration
  - digiexam
  - assets
  - intermediate-representation
  - renderer-neutral
---

Implementation slice with acceptance-driven scope.

## Objective

Extend the DigiExam `.dxe` parser and renderer-neutral IR so embedded question
images become explicit assets instead of opaque `bodyHTML` placeholders. This
story sits after the completed `.dxe` parser and IR lanes and before any PDF,
QTI, Exam.net, or bulk-renderer implementation.

## Source Evidence

A colleague-provided `.dxe` export, `1776888013-ak7-lag-och-ratt.dxe`, showed
that DigiExam questions can contain base64-encoded PNG values under
`question.images[]` while `bodyHTML` binds them with `<img data-image-id="0" .../>`. The observed sample parsed successfully as 8 items, including 5
gap-fill items, 1 multiple-response item, 2 open-ended items, and one embedded
PNG on the third question.

The raw colleague export is local evidence only and must remain outside tracked
fixtures. Before implementation closes, derive a sanitized fixture or a minimal
fixture that preserves the same asset structure without retaining unnecessary
export metadata such as user, organization, encryption, or timing fields.

## Scope

- Extract `.dxe` `question.images[]` entries as renderer-neutral asset records.
- Bind each asset to its `bodyHTML` `data-image-id` reference and source item.
- Compute stable asset identifiers, content hashes, media type, byte length,
  and image dimensions when cheaply available from decoded bytes.
- Preserve prompt HTML with image references while exposing assets separately
  in the parser result and IR.
- Extend the IR manifest with ordered asset summaries for exam-level and
  item-level parity checks, not counts alone.
- Define renderer handoff semantics: future PDF/QTI renderers must either carry
  referenced assets or fail closed with typed blocking asset warnings.
- Keep answer-key, rubric, renderer, Exam.net upload, QTI package, and bulk
  workflow behavior out of this story.

## Acceptance Criteria

- [x] A sanitized `.dxe` image fixture or minimal synthetic fixture proves
  `question.images[]` extraction without retaining unnecessary colleague export
  metadata, and validation proves the raw colleague export is not tracked by
  `git ls-files`.
- [x] Parser output exposes embedded image assets with stable item binding,
  source image index, asset id, SHA-256, media type, byte length, and dimensions.
- [x] Parser output validates every `<img data-image-id="N">` reference against
  `question.images[N]` and fails closed on missing, undecodable, unsupported,
  or unused image data.
- [x] Asset failures use exact blocking warning codes
  `invalid_embedded_asset_base64`,
  `unsupported_embedded_asset_media`,
  `missing_embedded_asset_reference`,
  `unused_embedded_asset_payload`, and
  `ambiguous_embedded_asset_binding`.
- [x] Repeated `<img data-image-id="N">` references are valid multiple
  references to one asset and are modeled as ordered references separately from
  asset records.
- [x] IR output preserves embedded assets separately from item prompt HTML and
  keeps renderer-neutral schema semantics under explicit v2 schema identifiers.
- [x] Manifest output reports deterministic ordered asset summaries alongside
  existing item summaries, including `asset_id`, `source_image_index`, `sha256`,
  `media_type`, `byte_length`, dimensions, and reference count/order.
- [x] Tests prove future renderer consumers can detect whether assets are
  present before rendering and that missing assets produce exact typed blocking
  warnings.
- [x] No PDF renderer, QTI package writer, Exam.net import syntax, service/API
  route, or bulk workflow is introduced.

## Test Requirements

- [x] Fixture-backed `.dxe` parser test covers one question with an embedded
  PNG referenced by `data-image-id`.
- [x] Negative parser tests cover broken base64, unsupported media bytes, and
  `bodyHTML` image references that do not bind to `question.images[]`.
- [x] Negative parser tests assert exact asset warning codes and
  `renderer_ready=false`.
- [x] IR tests assert asset records are carried from parser output to IR without
  embedding target-renderer syntax.
- [x] Manifest tests assert ordered asset summaries, reference ordering, and
  hash identity rather than only aggregate counts.
- [x] Regression tests confirm `.dxe` files without images still parse with
  empty asset summaries and unchanged answer-key provenance behavior.

## Done Definition

Story 42 is done when Task 276 lands the renderer-neutral embedded-asset
contract, fixture-backed parser and IR tests pass, generated docs are
synchronized, and EPIC-10 still reserves PDF/QTI/Exam.net rendering for later
governed stories.

Review 11's zero-payload remediation is included in the completed contract:
`bodyHTML` references now fail closed with
`missing_embedded_asset_reference` when `question.images[]` is empty or absent,
and focused regression tests cover both cases.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
