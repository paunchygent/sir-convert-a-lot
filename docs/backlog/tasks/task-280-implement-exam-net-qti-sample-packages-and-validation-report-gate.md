---
id: task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate
title: Implement Exam.net QTI sample packages and validation report gate
type: task
status: completed
priority: high
created: '2026-05-12'
last_updated: '2026-05-12'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-281-classify-digiexam-dxe-validation-corpus-and-add-parser-regression-gate.md
  - docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
labels:
  - examnet
  - qti
  - implementation
  - validation
  - artifact-bundle
  - deterministic-fixtures
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first QTI package-generation slice behind the accepted
Exam.net/DigiExam artifact contracts.

This task creates deterministic QTI 2.1 sample packages and a validation-report
artifact for the Exam.net target profile. It starts with the vendor-reported
minimum and safest shared artifacts:

- multiple-choice QTI samples;
- free-text QTI samples;
- image-bearing multiple-choice and free-text QTI samples;
- matching as an explicit proof-gated sample that cannot be promoted as
  Exam.net-supported until live import proof exists.

The implementation is a package/validation gate, not a service-runtime route or
Skriptoteket UI slice.

## PR Scope

- Implement a small, modular QTI package-generation surface that can consume
  the existing renderer-neutral exam item data and can later be fed by the
  Exam.net authoring IR without changing the QTI contract.
- Generate deterministic QTI 2.1 packages for:
  - single-choice MCQ;
  - multiple-response MCQ;
  - free text / essay;
  - single-choice MCQ with an embedded image;
  - free text / essay with an embedded image.
- Generate a matching sample only behind an explicit proof-gated mode:
  - it may validate structurally as QTI `matchInteraction`;
  - it must report `examnet_proof_status: not_proven`;
  - it must not be advertised as production-supported for Exam.net.
- Emit `qti_validation_report` JSON for every generated package, including:
  - package filename and SHA-256;
  - QTI version;
  - generator version/schema;
  - validator name/version for each validation layer that ran;
  - package/XML validation status;
  - 1EdTech validation status or a recorded external dependency when access is
    not available;
  - optional QTIWorks/local semantic-smoke status when available;
  - Exam.net import proof status;
  - warnings and errors with item references.
- Package image resources only when they are renderer-neutral IR assets with
  deterministic manifest references, content type, byte size, and hash.
- Omit unsupported resource classes from the Exam.net QTI target and emit
  item-addressable manual-follow-up records instead of silently carrying them.
- Update the DigiExam and Exam.net artifact bundle contracts only where needed
  to keep `qti_package` and `qti_validation_report` semantics aligned.
- Keep modules focused and below the repo's strict SRP/LoC targets. New or
  materially changed Python modules must have Google-style module docstrings
  describing domain purpose and relationships.
- Do not implement source PDF/Word parsing, full Exam.net authoring IR,
  editable DOCX generation, service API routes, Skriptoteket adapter/UI, or
  Exam.net browser upload automation in this task.
- Do not use the raw OneDrive `.dxe` validation package as QTI fixture input.
  If real DigiExam corpus evidence is needed, consume Task 281 metadata-safe
  parser/IR outputs or sanitized fixtures.

## Deliverables

- [x] Deterministic QTI package generator for MCQ and free-text samples.
- [x] Deterministic QTI package generator support for image-bearing MCQ and
  free-text samples.
- [x] Proof-gated matching sample package with explicit
  `examnet_proof_status: not_proven`.
- [x] `qti_validation_report` JSON schema or typed contract, with tests.
- [x] Local package/XML validation preflight for generated samples.
- [x] 1EdTech validation integration decision recorded in the report:
  integrated when available, otherwise a typed external-dependency status.
- [x] Optional local semantic smoke gate wired only if it can be installed and
  run reproducibly without broadening the task.
- [x] Bundle contract and reference docs updated for any changed artifact keys,
  status values, sample-package names, or validation semantics.
- [x] Deterministic fixture/sample package tests that compare stable package
  structure, manifest hrefs, item XML, image resource references, and hashes.

## Acceptance Criteria

- [x] Generated packages are deterministic: repeated generation from the same
  input produces the same package hash and stable manifest/item/resource paths.
- [x] MCQ packages encode correct response cardinality explicitly:
  single-choice and multiple-response are not conflated.
- [x] Free-text packages do not invent answer keys or rubrics; rubrics remain
  sidecar/manual metadata until a governed QTI rubric mapping exists.
- [x] Image-bearing packages include only source-proven renderer-neutral image
  assets and every manifest reference resolves inside the package.
- [x] Matching generation is structurally validated but proof-gated: the report
  and bundle status prevent calling it Exam.net-supported until live Exam.net
  import proof is captured.
- [x] Unsupported resources such as audio, PDF attachments, GeoGebra, or tool
  resources are omitted from the Exam.net QTI package and surfaced through
  manual follow-up.
- [x] `qti_validation_report` is emitted for successful, blocked, proof-gated,
  and validation-failed QTI attempts.
- [x] Tests cover package generation, XML/manifest validation, image resources,
  validation-report statuses, and manual-follow-up output.
- [x] No service API runtime route, Skriptoteket UI, editable DOCX generation,
  or Exam.net browser automation is implemented.

## Implementation Result

Task 280 landed as a bounded package/validation gate, not a service route:

- reusable contracts in
  `scripts/sir_convert_a_lot/domain/examnet_qti_contracts.py`;
- item XML serialization in
  `scripts/sir_convert_a_lot/domain/examnet_qti_xml.py`;
- deterministic package planning in
  `scripts/sir_convert_a_lot/domain/examnet_qti_package.py`;
- validation-report assembly in
  `scripts/sir_convert_a_lot/domain/examnet_qti_validation.py`;
- deterministic sample inputs in
  `scripts/sir_convert_a_lot/domain/examnet_qti_samples.py`;
- DigiExam IR adapter in
  `scripts/sir_convert_a_lot/domain/digiexam_examnet_qti_adapter.py`;
- filesystem writer in
  `scripts/sir_convert_a_lot/infrastructure/examnet_qti_package_writer.py`;
- repeatable sample generation command:
  `pdm run examnet-qti-samples`.

Generated sample artifacts live under
`inputs/examples/examnet-qti-samples/task-280/`:

| Sample | QTI package SHA-256 | Report SHA-256 |
| --- | --- | --- |
| `single-choice-mcq` | `2f8748685e19a347e2521b49941f6c2bd154b55eacce5bad59f2da8e25e89a46` | `816ce634b0d3deed09439a3c2d19d61220b25dd559d3ec079105621c2b306514` |
| `multiple-response-mcq` | `6561073ef7f962f4ad85326e669f9561e89a0d5316eee1a3ae436fa3e5600c65` | `030488fe4a2e266df4143fc604a07697591cafa33b1ea7f5de880d949c73a850` |
| `free-text` | `0bfcd851d820b8a71c443f97dd7e6f72b1d8b1adfc2bc450bc30dd1c6a90c59c` | `95466c7b918de8bf756dedbda4796c975362a30c8b56e4a1d862f9ca2c8d6921` |
| `image-single-choice-mcq` | `fda63d3a002003b616e84231767424065d376f3512fc12537e57235ba6210c1d` | `cd0228cbdd41835712ebec6b5bcf44baf01a2d52f469443f1bda70c03f6a2b76` |
| `image-free-text` | `917dba37c29e44147826ac508942fafcd536d78cd3fcc552d1106bc0072d13e8` | `06024331341b3d2994d2ff166b3b4d15049bcec497828806bc971efe97e3ae5f` |
| `matching-proof-gated` | `846818e5a2985be23e48077835b8ead3f49f7275182aef2f511ce79ffbca52bc` | `e89fd3fbed620bbb6d333529997f2d04cac1086b0733589665dbfc458de78760` |
| `unsupported-resource-omission` | `81f89c05149239d9d0c484bab82882af9ea9b3cb01eb7c4804a778c494440def` | `426fbe9a61e013923ffcde9c64d58308c5caed6f9cecfc23e0362c95950f5699` |

The local preflight validates zip readability, `imsmanifest.xml`, item XML
well-formedness, manifest href resolution, item image references, and absence
of forbidden Exam.net phase-1 resource classes. The report records the official
1EdTech validator as `external_validator_unavailable` for this local gate and
QTIWorks as `not_run` because it was not installed in this bounded slice.

## Implementation Notes

Prefer a small domain package over a monolithic renderer. Expected boundaries:

- QTI contracts/value objects;
- item XML serialization for supported interactions;
- manifest/resource planning;
- deterministic zip/package writing;
- validation report assembly;
- optional infrastructure adapter for external validators.

The implementation should align with:

- `docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md`
- `docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md`
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`

Treat 1EdTech as the validation authority. If official validator access is
member-gated or unavailable in local automation, record a typed
`external_validator_unavailable` status and keep local validation provisional.

## Test Requirements

- [x] Unit tests for deterministic package paths and hashes.
- [x] Unit tests for QTI XML generation for single-choice MCQ,
  multiple-response MCQ, free text, image-bearing MCQ, image-bearing free text,
  and proof-gated matching.
- [x] Validation-report tests for `passed`, `blocked`, `not_proven`,
  `external_validator_unavailable`, and `failed` states.
- [x] Package integrity tests that unzip the generated samples and verify
  `imsmanifest.xml`, item XML files, resource files, hrefs, content types, and
  hash metadata.
- [x] Regression tests that unsupported resource classes are omitted and
  represented as manual-follow-up entries.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] Focused QTI package/validation tests through `pdm run pytest-root ...`
- [x] Focused DigiExam/Exam.net artifact contract tests touched by this slice
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Stop Conditions

- Stop before claiming Exam.net production support for matching, short answer,
  or gap fill without live Exam.net import proof.
- Stop before adding service runtime routes or named artifact endpoints.
- Stop before changing Skriptoteket code or authenticated file persistence.
- Stop before adding broad external dependencies without a validator selection
  note in the task or QTI validation reference.
- Stop before silently embedding unsupported resource classes in QTI packages.
- Stop before changing DigiExam parser or IR semantics except through a narrow
  adapter needed by this QTI package generator.
- Stop before treating raw `.dxe` files from the OneDrive validation package as
  tracked QTI fixtures.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
