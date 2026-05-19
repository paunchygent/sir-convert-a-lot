---
id: task-315-extract-exam-net-pdf-item-rendering-policy-strategies-from-item-type-branch-ladder
title: Extract Exam.net PDF item rendering policy strategies from item-type branch ladder
type: task
status: ready
priority: high
created: '2026-05-15'
last_updated: '2026-05-20'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries.md
  - docs/backlog/tasks/task-313-audit-solid-domain-coupling-and-implementation-branch-hotspots-across-exam-converter-surfaces.md
  - docs/reference/ref-exam-converter-solid-domain-coupling-audit.md
  - scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf_items.py
labels:
  - solid
  - ddd
  - exam-converter
  - examnet-pdf
  - target-policy
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extract Exam.net PDF item rendering policy from the centralized
`DigiExamItemType` branch ladder in `digiexam_examnet_pdf_items.py` into
explicit item-rendering strategies.

The goal is not to remove all conditionals. The goal is to stop one function
family from owning item-type support, answer-key trust, warning semantics,
target support, and HTML assembly at the same time.

The governing boundary is full separation of concerns: export policy consumes
IR or effective-IR state, but it must never own, mutate, or redefine that state.
Source/parser IR owns source structure and provenance. Effective IR owns
accepted authoring corrections such as teacher-provided answer keys, reviewed
answer-key completion, item text changes, point corrections, and gap/choice
corrections. The Exam.net PDF target profile owns only export/layout decisions:
supported render shapes, target warnings, and target-specific formatting.

`accept_current_state_for_export` is not durable IR or effective-IR state. Task
337 has removed accepted-current-state from the current authoring/correction,
ingestion-overlay, correction-replay, artifact-availability, and
target-readiness runtime. This task must not preserve it inside the extracted
PDF strategy boundary. If a future product decision reintroduces best-effort
incomplete export, the input must be an export-only request policy consumed by
the PDF target profile, not an overlay, correction, or effective-IR field.

The strategy contract should be deliberately small:

```text
Exam.net PDF item semantics + target profile context
  -> PDF item sections
  -> typed PDF target warnings/manual-follow-up signals
```

Strategies may choose PDF layout sections and warnings. They must not produce
or mutate source IR, effective IR, target-readiness rows, bundle manifests, QTI
items, or ingestion/correction overlay state.

The core PDF exam item protocol must remain target-agnostic. It must not carry
Exam.net import needs, supported-shape decisions, or degraded target-shaping
rules. Exam.net-specific reshaping is allowed, and often required, but it
belongs in an Exam.net PDF target extension/profile invoked only when the
requested output target is Exam.net-oriented PDF. That extension may reshape a
gap/open-cloze item into a target-compatible PDF presentation, but the reshaping
must be explicit target policy with provenance-preserving labels, warnings, and
manual-follow-up signals. It must not rewrite source IR, effective IR, or the
neutral PDF protocol's item semantics.

## PR Scope

- Introduce a domain-facing rendering strategy/protocol for Exam.net PDF item
  rendering, keyed by target profile and source-neutral item semantics in one
  owned registry.
- Move choice, multiple-response, gap-fill, open-ended, and unsupported item
  policy decisions out of `_render_item` while preserving the existing artifact
  contract.
- Keep prompt rendering, escaping, and HTML shell helpers pure and local.
- Preserve current post-Task-337 output behavior: keyed/teacher-reviewed items
  render as today, missing-key machine-marked items stay blocked, and
  unsupported item types fail closed with typed warnings.
- If gap/open-cloze-to-free-text-style rendition moves in this slice, relocate
  it into the Exam.net PDF target extension/profile rather than the core PDF
  item protocol. Rendering may reshape for Exam.net, but that reshape must stay
  target-specific and provenance-preserving.
- Keep strategy inputs read-only with respect to source IR and effective IR:
  strategies may inspect item structure, provenance, answer-key state, and
  target profile context, but must emit PDF sections and target warnings rather
  than IR/effective-IR updates.
- Do not expand supported item types, alter target readiness semantics, or
  change artifact availability in this task.
- Do not introduce an export-only incomplete/best-effort request policy in this
  task; only keep the strategy seam capable of accepting one later if a
  governed contract approves it.

## Deliverables

- [ ] Exam.net PDF item-renderer strategy/protocol.
- [ ] Registry or factory selected by domain item kind/target profile.
- [ ] Existing choice, multiple-response, gap-fill, open-ended, missing-key
  blocker, and unsupported rendering paths moved behind the strategy boundary.
- [ ] Focused tests proving rendered output and warnings are unchanged.
- [ ] Regression tests proving no accepted-current-state input or strategy path
      is introduced.
- [ ] Regression tests proving gap/open-cloze reshaping, when used, is owned by
      the Exam.net PDF target extension/profile and does not leak into the core
      PDF item protocol or mutate source/effective IR semantics.

## Acceptance Criteria

- [ ] Adding a new governed PDF item profile does not require widening
  `_render_item` with another item-type branch.
- [ ] Answer-key trust and target-specific export decisions for PDF rendering
  live in policy objects, not ad hoc renderer branches.
- [ ] No export strategy writes parser/source IR, effective IR, manifest source
  summaries, answer-key provenance, or overlay lineage fields.
- [ ] Legacy manual/unkeyed accepted-current-state rendering is absent from the
  active strategy model. If a future export-only incomplete policy is added, it
  must enter through a governed target-profile request context, not IR state.
- [ ] Core PDF item semantics remain target-agnostic; Exam.net target
  reshaping, including gap/open-cloze free-text-style presentation, is isolated
  in the Exam.net PDF target profile with provenance-preserving labels,
  warnings, and manual-follow-up state.
- [ ] Unsupported item types still fail closed with typed warnings.
- [ ] No source IR, effective IR, QTI, bundle manifest, or target-readiness
  behavior changes are introduced.

## Suggested Implementation Order

1. Introduce immutable result/value types for PDF item strategy output: item
   sections, warnings, and manual-follow-up signals.
2. Define the strategy protocol and target-profile context without changing
   rendered output.
3. Move one item family at a time behind the registry, starting with
   open-ended/unsupported paths, then choice/multiple-response, then gap-fill.
4. Collapse `_render_item` into registry lookup plus result-to-HTML assembly.
5. Keep artifact availability and target-readiness untouched; they remain
   Task 316's boundary.

## Validation Slice

- Focused PDF renderer tests for keyed choice, multiple-response, gap-fill,
  reviewed multi-gap, missing-key blockers, unsupported item warnings, source
  label blockers, and embedded-asset blockers.
- Focused PDF renderer tests proving gap/open-cloze reshaping is explicit
  Exam.net target-profile behavior and does not alter neutral PDF item protocol
  semantics, source IR, or effective IR.
- Focused bundle tests that prove PDF availability and manual-follow-up output
  do not drift.
- `pdm run typecheck-all`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
