---
type: reference
id: REF-story-58-live-proof-operator-manifest-contract
title: Story 58 Live Proof Operator Manifest Contract
status: active
created: 2026-06-30
updated: 2026-06-30
owners:
  - platform
tags:
  - story-58
  - live-proof
  - service-api-v2
  - idempotency
  - correction-apply
  - redaction
links:
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md
  - docs/runbooks/runbook-hemma-service-ops.md
---

## Purpose

Define the operator-supplied manifest and private-input contract for the Story
58 final live proof. This reference exists so final closeout can run through
real Dev and Prod Service API or Gateway routes while retaining only approved
metadata.

This document is not proof by itself. It is the checklist for producing proof.

## Redaction Boundary

Retained evidence may include job ids, route id/key, replay action/reason,
schema versions, request id, source-binding digest, source-state digest,
correction-request digest, artifact-set id, artifact key, content hash, HTTP
status/error code, service revision, timestamps, and screenshots.

Retained evidence must not include raw exam content, source text, uploaded
bytes, idempotency keys, API keys, private header-file paths, identity/grant
envelopes, source-state signatures, provider prompts, or private filesystem
paths.

## Required Private Inputs

The proof runner can execute the full matrix only when the operator supplies
these private inputs out of band:

| Input | Purpose | Retention Rule |
|---|---|---|
| Service API key | Authenticate each proof run. | Never retained; pass by env or CLI only. |
| Hule identity/grant headers | Prove same-owner DigiExam and correction routes. | Load through `header_env` or `headers_file_env`; never inline. |
| Historical `ak7` idempotency key | Reuse the stale production idempotency scope. | Never retained; use `header_env`. |
| Matching `ak7` source bytes and job spec | Reproduce same-owner stale incompatible replay. | Do not retain uploaded bytes or private source paths. |
| Signed source-state/correction request bodies | Prove correction apply and replay cases. | Store as private JSON files; retained evidence stores only approved metadata. |
| Live log captures or monitoring pointers | Prove service responses during the test window. | Capture after live requests; redact before retention. |

If any input is missing, the corresponding case must remain
`requires_governed_setup`. Do not mutate production idempotency records,
artifacts, source jobs, or signatures to manufacture proof.

## Case Matrix

| Case | Required Live Response |
|---|---|
| `compatible_strict_digiexam_replay` | `200` create response with `idempotency.state = strict_replay` plus matching DigiExam route metadata from `route_id` or v2 result `route_key`. |
| `stale_incompatible_digiexam_replay` | Fresh service admission under an existing stale scope with `idempotency.state = service_reattempt`, `idempotency.reason = terminal_artifact_contract_incompatible`, and matching DigiExam route metadata. |
| `missing_source_correction_apply_fail_closed` | `409` response with `error.code = exam_authoring_correction_source_job_unavailable`. |
| `exact_duplicate_correction_retry_reuses_artifact_set` | Two successful correction apply responses that resolve to the same request-scoped artifact-set identity. |
| `distinct_correction_applies_distinct_artifact_sets` | Two successful correction apply responses that resolve to distinct request-scoped artifact-set identities. |
| `stale_mismatched_nested_correction_artifact_download_fail_closed` | `404 correction_replay_artifact_set_not_found` or `409 correction_replay_artifact_reference_mismatch` from the nested artifact route. |
| `generic_idempotency_preservation_smoke` | Safe generic `fresh_admission` followed by `strict_replay`, or an explicit delegated evidence pointer. |

## Manifest Shape

The manifest schema is `story58_live_replay_case_manifest_v1`. Request bodies
come from `json_file`; multipart uploads come from `multipart.file_path` and
`multipart.job_spec_file`. Dependent requests may extract scalar values from
redacted responses and interpolate them into later `path`, `query`, or inline
non-secret `headers`.

Body interpolation is not part of the approved Task 379 contract. When a case
needs signed bodies, generate prepared private JSON request files before the
run and reference them with `json_file`.

Skeleton:

```json
{
  "schema_version": "story58_live_replay_case_manifest_v1",
  "cases": [
    {
      "case_id": "compatible_strict_digiexam_replay",
      "label": "compatible strict DigiExam replay",
      "requests": [
        {
          "label": "fresh compatible DigiExam admission",
          "method": "POST",
          "path": "/v2/convert/jobs",
          "query": { "wait_seconds": "60" },
          "headers_file_env": "STORY58_PRIVATE_HEADERS_FILE",
          "header_env": { "Idempotency-Key": "STORY58_COMPATIBLE_IDEMPOTENCY_KEY" },
          "multipart": {
            "file_path": "private/compatible-source.dxe",
            "job_spec_file": "private/compatible-job-spec.json",
            "content_type": "application/octet-stream"
          },
          "expect": { "http_status": 200 }
        },
        {
          "label": "strict replay of compatible DigiExam admission",
          "method": "POST",
          "path": "/v2/convert/jobs",
          "query": { "wait_seconds": "60" },
          "headers_file_env": "STORY58_PRIVATE_HEADERS_FILE",
          "header_env": { "Idempotency-Key": "STORY58_COMPATIBLE_IDEMPOTENCY_KEY" },
          "multipart": {
            "file_path": "private/compatible-source.dxe",
            "job_spec_file": "private/compatible-job-spec.json",
            "content_type": "application/octet-stream"
          },
          "expect": {
            "http_status": 200,
            "idempotency_state": "strict_replay"
          },
          "extract": { "strict_job_id": "idempotency.active_job_id" }
        },
        {
          "label": "result metadata for strict replayed DigiExam job",
          "method": "GET",
          "path": "/v2/convert/jobs/{strict_job_id}/result",
          "headers_file_env": "STORY58_PRIVATE_HEADERS_FILE",
          "expect": {
            "http_status": 200,
            "route_key": "digiexam_dxe_to_examnet_migration_bundle"
          }
        }
      ]
    }
  ]
}
```

The skeleton is intentionally incomplete. Operators should add all matrix cases
and use private paths outside retained evidence. The runner's code-owned
invariants still decide whether a case may pass; manifest expectations can add
checks but cannot weaken Story 58 requirements.

## Command Shapes

Dev:

```bash
pdm run proof:story58-live-replay \
  --service-url http://127.0.0.1:8085 \
  --case-manifest <redacted-dev-manifest.json> \
  --output-root build/verification/story-58-live-replay-proof-dev-full
```

Prod:

```bash
pdm run proof:story58-live-replay \
  --service-url http://127.0.0.1:28085 \
  --case-manifest <redacted-prod-manifest.json> \
  --output-root build/verification/story-58-live-replay-proof-prod-full
```

Retain Docker or service log evidence by passing redacted log-capture inputs or
monitoring pointers for the same test window. Prefer file log evidence when
available; monitoring pointers are secondary.

## Closeout Rule

Story 58 final closeout requires Dev and Prod evidence bundles whose
`overall_status` is `passed`, plus downstream product proof for each touched
application that uses the idempotency or replay code path. A task approval,
generic smoke run, filesystem lineage artifact, or product-only incident proof
does not close the story.
