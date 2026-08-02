---
type: reference
id: REF-SIRCON-GENERAL-exam-authoring-corrections-apply-contract
title: Exam Authoring Corrections Apply Contract
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: general
retired_ids:
- CONV-exam-authoring-corrections-apply-contract
summary: Exam Authoring Corrections Apply Contract
---

## Overview

State the subject, why it is useful, and the boundary of the retained context.

## Facts And Semantics

Define terms and record durable facts, ownership, relationships, and evidence
interpretation. Distinguish confirmed facts from mutable interpretation. Link
to a runbook for ordered execution and to backlog items for work state.

## Decisions And Interpretation

Record current interpretation and its practical consequences. Route accepted
architecture or governance rationale to an ADR, material planning choices to a
`decisions` reference, and implementation authority to the backlog.

## Historical Source Summary

This source-neutral contract defines the Sir Convert-owned
`POST /v2/exam-authoring/corrections/apply` route and the producer-owned
`POST /v2/exam-authoring/corrections/source-state/issue` route. The apply request
uses `exam_authoring_corrections_apply_request_v1`; the result uses
`exam_authoring_corrections_apply_result_v1`. A request binds one signed,
producer-issued source state to an ordered typed correction batch. Every entry is
validated before effective state, target readiness, or artifact availability is
projected. The initial runtime is batch-blocking: one rejected entry prevents
correction-derived readiness until a valid batch is resubmitted.

### Ownership and source binding

Consumers remain source-neutral across DigiExam, Exam.net, CSV, DOCX, Markdown, and
future producers. Source adapters own ingestion and mapping; Sir Convert owns
validation, source binding, effective-state projection, readiness recomputation,
and artifact availability. Browser-local state is never authoritative. The issuer
resolves a succeeded server-side producer job, canonicalizes
`source_authoring_state`, computes `source_state_sha256`, and signs the
`source_binding`. Consumers echo the signed bundle and must not mint signatures or
submit source state for signing. Missing, inaccessible, failed, stale, forged, or
non-canonical source state fails closed.

The sanitized source state contains only bounded item identity/sequence/type,
visible text, score bounds, nested interaction IDs, answer-key provenance,
validated advisory-candidate lineage, and source/effective digests. It excludes
raw source files or text, provider payloads/prompts, credentials, identity,
student data, earned scores, wrong selections, and browser drafts. DigiExam emits
choice/gap source structures but no canonical matching interactions; matching
corrections require a separately governed matching-capable producer.

### Typed correction union

Entries use strict discriminators and producer-returned item/interaction binding:

- `item_text_patch` changes bounded renderer input only and cannot create key or
  readiness evidence.
- `point_correction` accepts a strict positive integer `max_score` only.
- `manual_choice_answer_key` validates existing choice IDs and single- versus
  multi-response cardinality.
- `manual_gap_open_cloze_answer_key` validates every gap and requires accepted
  values for required gaps.
- `manual_matching_answer_key` uses directed `source_id`/`target_id` pairs; retired
  aliases, unknown IDs, duplicates, association violations, and opaque provenance
  fail closed.
- Reviewed candidate keys carry bounded lineage and digest checks; accepted
  candidates become `reviewed`, edited candidates become `teacher_provided`.
- `candidate_suppression` hides a candidate only; it does not apply a key, clear
  readiness blockers, or unlock artifacts.

Unknown fields, untyped patches, adapter-specific overlays, retired aliases,
stale fingerprints, and generic metadata escape hatches are invalid. Validation
order is schema and signed binding, optional source-job authorization, item and
interaction binding, entry semantics, then ordered application and readiness
recomputation. Any rejection stops mutation and readiness projection.

### Projection, replay, and errors

The result returns producer-owned effective state, accepted/rejected entry reports,
compact answer-key review state, target readiness, and typed artifact availability.
Reports expose bounded IDs, reason codes, message keys, applied fields, teacher
action, and retryability; they never echo raw submitted payloads. Source-bound
replay requires the source job before exportable readiness, artifact rows, or replay
references are advertised. Missing jobs return `409
exam_authoring_correction_source_job_unavailable`; unauthorized access returns
`403 exam_authoring_correction_replay_access_denied`.

Correction replay artifacts are immutable request-scoped sets under
`correction-replays/{artifact_set_id}/`, downloaded through the typed nested
artifact route. Each reference carries schema, job/set/key, target, content hash,
request and source/correction/target digests, replay profile, and creation time.
Missing sets return `404`; mismatched references return `409`. The service never
falls back to latest source-job bytes.

### Hard cut, sequencing, and privacy

The retired Task 324 matching-specific route is removed rather than retained as an
adapter, alias, wrapper, or compatibility layer. Its semantics map into the
unified typed entry only where directly implemented. Task 330 owns the route hard
cut; Task 331 owns producer-state/privacy/readiness blockers; Task 332 owns a real
matching-capable producer; Task 333 owns DigiExam-backed non-matching runtime
families. HuleEdu and Skriptoteket migrate only after their corresponding runtime
and producer contracts exist.

The contract forbids raw `.dxe`, PDF text, overlay/provider payloads, prompts,
credentials, identity markers, student results, scores, wrong selections, free-text
answers, and per-student history in requests or reports. Validation errors expose
only bounded diagnostic shape. Effective authoring state and renderer input are
durable; accepted-current-state or export decisions are not correction entries.
