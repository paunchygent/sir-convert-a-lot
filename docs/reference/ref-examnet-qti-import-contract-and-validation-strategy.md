---
type: reference
id: REF-examnet-qti-import-contract-and-validation-strategy
title: Exam.net QTI Import Contract And Validation Strategy
status: active
created: 2026-05-12
updated: 2026-05-15
owners:
  - platform
tags:
  - examnet
  - qti
  - exam-migration
  - validation
  - authoring
links:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md
---

## Purpose

Define the QTI target boundary and validation strategy for Exam.net-oriented
exam artifacts in Sir Convert.

This reference records the current vendor-reported Exam.net direction and the
validator ladder that future QTI tasks must satisfy before claiming QTI output
is ready for teachers.

## Authoritative Schema Sources

The full QTI schema text is not copied into this repository. The authoritative
schema files remain the source of truth and must be used by implementation
tasks, validators, and reviews:

| Version | Authoritative schema source | Sir Convert use |
| --- | --- | --- |
| QTI 2.1 | `https://www.imsglobal.org/xsd/imsqti_v2p1.xsd` | Initial Exam.net package floor and current sample generator target. |
| QTI 3.0 item schema | `https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_itemv3p0p1_v1p0.xsd` | Compatibility/reference target for later QTI 3 package decisions. |

Schema requirements Sir Convert depends on:

- QTI 2.1 `assessmentItem` permits zero or more `responseDeclaration`
  elements and zero or one `responseProcessing` element.
- QTI 2.1 `responseDeclaration` permits zero or one `correctResponse`; the
  schema documentation states that `correctResponse` is optional and must be
  omitted when no optimal value is defined.
- QTI 2.1 `correct` expression semantics allow `NULL` when no correct value was
  declared.
- QTI 3.0 `qti-assessment-item` permits zero or more
  `qti-response-declaration` elements and zero or one
  `qti-response-processing` element.
- QTI 3.0 `qti-response-declaration` permits zero or one
  `qti-correct-response`; the `correct` expression semantics allow `NULL` when
  no correct value was declared.
- Interactive item types still have binding requirements when interactions are
  present. For example, choice-like interactions bind to identifier response
  variables, and matching-style interactions bind to directed-pair response
  variables. Omitting a correct response is not the same as proving a
  automatically evaluated item.

Contract consequence: bare QTI schema validity does not universally require a
machine-marked answer key. Sir Convert target readiness is intentionally
stricter than schema validity whenever the selected profile claims an item is
automatically evaluated or Exam.net-import-ready.

## Vendor-Reported Exam.net Import Direction

Exam.net has reported that it is building a self-service QTI import feature.
The exact supported details are still under development. Current reported
future support:

- QTI 2.1 and later.
- At least multiple-choice and free-text questions.
- Many embedded resources, including images, are expected to carry over when
  Exam.net supports the resource type.
- Audio files, PDFs, and tools such as GeoGebra are not expected to carry over
  automatically because they belong to exam tools/resources outside the exam
  content itself.
- Unsupported resources must be added manually after import.
- Exam.net welcomes sample QTI files for test imports while the feature is in
  late development.

Treat this as vendor-reported roadmap evidence, not as a shipped public API.
Implementation must remain fail-closed and fixture-backed until live import
proof exists.

## Initial QTI Target Profile

Use QTI 2.1 as the first generated package floor because Exam.net reports
support for QTI 2.1 and later. Later tasks may add QTI 2.2 or QTI 3 variants
only after a governed compatibility decision.

Initial supported interactions:

| Sir Convert item type | QTI interaction target | Exam.net status |
| --- | --- | --- |
| Single-choice multiple choice | `choiceInteraction`, single cardinality | Vendor-reported minimum area: MCQ. |
| Multiple-response multiple choice | `choiceInteraction`, multiple cardinality | Treat as MCQ family; must be proven with Exam.net sample import. |
| Free text / essay | `extendedTextInteraction` | Vendor-reported minimum area: free text. |
| Matching | `matchInteraction` | QTI 2.1 conformance tests include match interaction, but Exam.net support is not yet vendor-confirmed; keep behind explicit sample proof. |
| Short answer | `textEntryInteraction` or equivalent profile | Not part of the vendor-stated minimum; require sample proof. |
| Gap fill | `textEntryInteraction` in item body | Not promoted; require sample proof. |

Images may be packaged as item resources only when the source IR has
renderer-neutral image assets and the QTI package manifest references them
deterministically.

Do not include these resource classes in generated QTI packages for Exam.net
phase 1:

- audio;
- PDF attachments;
- GeoGebra or other tool resources;
- arbitrary external web resources;
- media or tool dependencies that are not part of the item content Exam.net
  says it can carry.

When source content contains unsupported resources, the package must emit
manual follow-up records and omit the unsupported resource from the Exam.net QTI
target rather than hiding it in the package.

## Machine-marked Versus Manual/unkeyed Policy

A machine-marked key is trusted correct-response data that lets Sir Convert
assert how a learner response should be evaluated automatically. Examples
include correct choice identifiers for choice items, reviewed matching pairs,
accepted gap-fill values, or another source/manual/reviewed effective answer
key that maps the item's QTI response variable to correct values.

A missing machine-marked key means that no such trusted correct-response data
exists for a machine-markable item in the source IR or effective layer. It does
not mean the question content is missing, and it does not apply to open-ended
manual items that are intentionally teacher-marked.

In the current Exam.net QTI profile, choice, matching, gap-fill, and other
machine-markable target shapes require a source, manual, or reviewed effective
answer key before `qti_package` can be marked exportable as an automatically
evaluated item. This is a Sir Convert target-readiness rule, not a universal
QTI schema rule.

Teacher `accept_current_state_for_export` decisions do not currently enable QTI
for missing machine-marked keys. They can only clear teacher-review blockers
for targets that Sir Convert can create and validate under an accepted policy.

Task 303 owns the later unkeyed/manual profile. That profile must define the
exact QTI 2.1 and, if promoted, QTI 3.0 representation for accepted-current
items that have no machine-marked key. It must prove package/XML/schema
validation, local semantic smoke where available, target readiness semantics,
and Exam.net import behavior before QTI export can be enabled by acceptance
alone.

### Task 303 Manual/unkeyed Preservation Direction

The product direction for Task 303 is preservation-first: missing
machine-marked keys must remove Sir Convert's automatic-evaluation claim, not
remove the teacher-visible question from QTI or PDF output.

For single-choice and multiple-response items, the first unkeyed/manual profile
must preserve prompt text, all visible alternatives, allowed media/resources,
and the response cardinality needed by the visible interaction. The generated
QTI must omit `correctResponse`/`qti-correct-response` and automatic
evaluation `responseProcessing` when no trusted answer key exists. In this
profile, omitting automatic evaluation means Sir Convert does not declare a
correct answer, response-processing template, or automatic correct/incorrect
rule for the item. The report must identify the item as manual/unkeyed so
Skriptoteket and teachers do not mistake the package for an automatically
evaluated export.

Matching, gap-fill, and similar item shapes are priority preservation cases,
not automatic blockers. Task 303 must define deterministic manual/unkeyed QTI
representations that keep their visible question content in the package when
schema/profile validation allows it. It is acceptable for Exam.net to import
these as free-text/manual items or to require teacher cleanup after import, but
the package must not fail merely because such items exist. The target readiness
and validation report must state the original item type, the chosen manual QTI
representation, whether automatic evaluation was omitted, and any teacher
follow-up needed after import.

Only items that cannot be represented without dropping visible content,
violating the QTI/package profile, including forbidden resources, or producing
malformed XML may keep `qti_package` unavailable under this profile. Unsupported
for automatic evaluation is not the same state as unavailable for
manual/unkeyed export:

- Unsupported for automatic evaluation means Sir Convert can preserve the
  visible item in a schema/profile-valid package, but it does not assert a
  correct answer or automatic evaluation rule. Target readiness may become
  `ready_after_accepted_current_state` after teacher acceptance, and the report
  must carry item-level manual/unkeyed follow-up.
- Unavailable for manual/unkeyed export means Sir Convert cannot produce a
  valid preservation package for the item or target without dropping visible
  content, violating package/profile rules, including forbidden resources, or
  emitting malformed XML. Teacher acceptance must not enable `qti_package` in
  that state.

Exam.net has explicitly asked for real Sir Convert QTI exam files so it can
support realistic imported exams rather than curated Exam.net-specific samples.
Task 303 should therefore proceed with local package/schema/profile proof and
record Exam.net import proof as a vendor-unproven external dependency until an
Exam.net import test path is available. The generated samples should be
realistic preservation cases, not simplified files that hide difficult item
types.

## Validation Ladder

Future QTI generation tasks must define and automate a layered validation
strategy.

### 1. Package And XML Schema Validation

Validate that each generated package is a well-formed IMS content package with:

- valid `imsmanifest.xml`;
- deterministic resource identifiers and hrefs;
- every referenced item XML and image asset present in the package;
- no unreferenced required files;
- no forbidden resource classes for the Exam.net profile.

This layer may use local XML/XSD validation as a fast preflight, but it is not
enough to claim QTI interoperability.

### 2. 1EdTech Validator Or Certification-Suite Validation

1EdTech is the standards authority. Its public QTI pages describe the QTI
specification as an exchange format for assessment content and results, and
state that an online validation tool exists for testing against the
specification. They also state that QTI 2.1 certification is retired for new
products, while the QTI 2.1 standard and online validator remain available.

Preferred validator authority:

- 1EdTech supplied validator for the selected QTI version.

If access to the official validator is member-gated, the implementation task
must record that as an external validation dependency and use local validation
only as provisional evidence.

### 3. Local Semantic Smoke

Use an open-source local runner or verifier where practical to catch semantic
mistakes before sending packages to Exam.net.

Candidate:

- QTIWorks for QTI 2.1 item/test verification and delivery smoke, because it is
  documented as an open-source system for managing, verifying, and delivering
  QTI v2.1 assessment items and tests.

QTIWorks is a secondary smoke gate, not a replacement for 1EdTech validation or
Exam.net import proof.

### 4. Exam.net Import Proof

Because Exam.net's importer is still under development, the final promotion
gate is vendor/import proof:

- produce a minimal sample package for each supported item type;
- include image resource samples;
- include unsupported-resource samples that prove manual-follow-up reporting;
- send or import packages through Exam.net's available test path;
- record accepted, partially accepted, and rejected behavior in this reference
  or a follow-on review artifact.

No QTI item type is production-supported for Exam.net until it has this proof.

## Required Sample Packages

Task 280 is the first QTI implementation gate and should create small
deterministic sample packages for:

- single-choice MCQ;
- multiple-response MCQ;
- free text;
- MCQ with embedded image;
- free text with embedded image;
- matching with exact pairs;
- short answer with accepted variants;
- unsupported audio/PDF/tool resource omission with manual follow-up.

The MCQ and free-text packages form the minimum Exam.net-aligned proof set.
Matching, short answer, and gap-fill remain optional/promoted only after
Exam.net sample acceptance.

Task 280 starts with MCQ, free text, image-bearing MCQ/free text, and
proof-gated matching. The unsupported-resource omission sample may land in Task
280 if it fits the slice; otherwise it remains a required follow-on before any
production QTI service exposure.

### Task 280 Implemented Sample Gate

Task 280 implemented the first deterministic QTI 2.1 package gate under
`inputs/examples/examnet-qti-samples/task-280/`.

Each sample directory contains:

- `qti-package.zip`;
- `qti-validation-report.json`.

The sample set is:

| Sample | Status | Exam.net proof status |
| --- | --- | --- |
| `single-choice-mcq` | `passed` | `vendor_reported_unproven` |
| `multiple-response-mcq` | `passed` | `vendor_reported_unproven` |
| `free-text` | `passed` | `vendor_reported_unproven` |
| `image-single-choice-mcq` | `passed` | `vendor_reported_unproven` |
| `image-free-text` | `passed` | `vendor_reported_unproven` |
| `matching-proof-gated` | `passed` | `not_proven` |
| `unsupported-resource-omission` | `passed` | `vendor_reported_unproven` |

The reusable generator surface is:

- `scripts/sir_convert_a_lot/domain/examnet_qti_contracts.py`;
- `scripts/sir_convert_a_lot/domain/examnet_qti_xml.py`;
- `scripts/sir_convert_a_lot/domain/examnet_qti_package.py`;
- `scripts/sir_convert_a_lot/domain/examnet_qti_validation.py`;
- `scripts/sir_convert_a_lot/domain/examnet_qti_samples.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_examnet_qti_adapter.py`;
- `scripts/sir_convert_a_lot/infrastructure/examnet_qti_package_writer.py`.

Use `pdm run examnet-qti-samples` to regenerate the deterministic sample
packages and reports.

Current package hashes:

| Sample | QTI package SHA-256 |
| --- | --- |
| `single-choice-mcq` | `2f8748685e19a347e2521b49941f6c2bd154b55eacce5bad59f2da8e25e89a46` |
| `multiple-response-mcq` | `6561073ef7f962f4ad85326e669f9561e89a0d5316eee1a3ae436fa3e5600c65` |
| `free-text` | `0bfcd851d820b8a71c443f97dd7e6f72b1d8b1adfc2bc450bc30dd1c6a90c59c` |
| `image-single-choice-mcq` | `fda63d3a002003b616e84231767424065d376f3512fc12537e57235ba6210c1d` |
| `image-free-text` | `917dba37c29e44147826ac508942fafcd536d78cd3fcc552d1106bc0072d13e8` |
| `matching-proof-gated` | `846818e5a2985be23e48077835b8ead3f49f7275182aef2f511ce79ffbca52bc` |
| `unsupported-resource-omission` | `81f89c05149239d9d0c484bab82882af9ea9b3cb01eb7c4804a778c494440def` |

### Task 303 Manual/unkeyed Sample Gate

Task 303 adds deterministic QTI 2.1 manual/unkeyed preservation samples under
`inputs/examples/examnet-qti-samples/task-303/`.

Use `pdm run examnet-qti-task-303-samples` to regenerate the samples and
reports.

The single-choice, multiple-response, and gap-fill samples are derived from the
tracked DigiExam `.dxe` fixture
`inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/1772718003-test-samma-prov-i-digiexam.dxe`.
The current tracked `.dxe` fixture set does not include a real matching item.
The matching sample is therefore a Task-298-aware contract sample: it proves the
manual/free-text preservation shape without claiming reviewed matching
answer-pair support, automatic evaluation, or IR v3 application.

| Sample | Source | Profile | Status | Exam.net proof status |
| --- | --- | --- | --- | --- |
| `unkeyed-single-choice-preserved` | real DXE `item-002` | `unkeyed_manual_qti_2_1_v1` | `passed` | `vendor_reported_unproven` |
| `unkeyed-multiple-response-preserved` | real DXE `item-004` | `unkeyed_manual_qti_2_1_v1` | `passed` | `vendor_reported_unproven` |
| `manual-gap-fill-preserved-as-free-text` | real DXE `item-007` | `unkeyed_manual_qti_2_1_v1` | `passed` | `vendor_reported_unproven` |
| `manual-matching-preserved-as-free-text` | contract sample pending real matching DXE fixture | `unkeyed_manual_qti_2_1_v1` | `passed` | `vendor_reported_unproven` |

Current Task 303 package hashes:

| Sample | QTI package SHA-256 |
| --- | --- |
| `unkeyed-single-choice-preserved` | `caba9ee65040f0879f1ef02694b18883f85bd00663a5d525d0cf77deef0e2faf` |
| `unkeyed-multiple-response-preserved` | `60be8c1442baabf24f11d250fba1d2fd2cb9a827844c01fb83461d2e92318fc6` |
| `manual-gap-fill-preserved-as-free-text` | `f064a580919ee27d8efd20020103df700468ae10db10415c9d1a40e9a122036a` |
| `manual-matching-preserved-as-free-text` | `055f41e4ff11e109af8290037dc48aeebeeec9051ba9e36d6dcef606347e192b` |

The `qti_validation_report` schema version is
`examnet_qti_validation_report_v1`. Reports include package filename/hash, QTI
version, generator version, local package/XML preflight, official 1EdTech
validator dependency status, QTIWorks local-smoke status, Exam.net proof status,
warnings, errors, and item-addressable manual follow-up records.

The local preflight is only a provisional integrity gate. It validates package
zip readability, `imsmanifest.xml`, item XML well-formedness, manifest href
resolution, image href resolution, and absence of forbidden phase-1 resource
classes. It does not replace official 1EdTech validation or live Exam.net
import proof.

## Contract Consequences

- QTI generation must be a named artifact in both DigiExam migration bundles
  and Exam.net authoring bundles.
- `qti_package` availability must stay machine-readable:
  `available`, `blocked`, `not_implemented`, or `not_supported_by_examnet`.
- Unsupported resources must appear in the manual-follow-up report with item
  references and reason codes.
- QTI validation results should be emitted as a separate artifact, for example
  `qti-validation-report.json`, containing validator name, version, QTI version,
  package hash, warnings, errors, and Exam.net import-proof status when known.
