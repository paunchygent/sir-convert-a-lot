---
id: task-195-land-an-explicit-task-101-text-embedding-mask-policy-and-text-span-only-mitigation
title: Land an explicit Task 101 text-embedding mask policy and text-span-only mitigation
type: task
status: completed
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-194-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - mask-policy
  - stability
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add an explicit Task 101 text-embedding mask policy to the committed Qwen
training runtime and make `text_span_only` the primary mitigation candidate for
the codec-span text-pad instability proven from `state-step-00001406`.

## PR Scope

- Introduce one runtime/control-plane policy with supported values:
  - `legacy_codec_span`
  - `text_span_only`
- Keep `legacy_codec_span` available so the repo can still reproduce the old
  failure contract when needed.
- Implement `text_span_only` so the active text-embedding path covers only the
  true text span and not the codec-span text-pad positions.
- Surface the effective policy in:
  - launch metadata
  - status/report payloads
  - replay bundle artifacts
  - `talker_runtime` or equivalent runtime fingerprint artifacts
- Keep the mitigation inside the bounded Story 28 package owners rather than
  reintroducing broad loop-local policy branching.

## Deliverables

- [x] One committed text-embedding mask policy surface exists for Task 101.
- [x] The dataset/runtime contract can run in both legacy reproduction mode and
  mitigation mode.
- [x] Machine-readable artifacts expose the active policy so every bounded
  proof is self-describing.
- [x] The training reference ledger records that `text_span_only` is now the
  first structural mitigation under test.

## Acceptance Criteria

- [x] Focused tests prove `legacy_codec_span` preserves the old behavior.
- [x] Focused tests prove `text_span_only` removes the codec-span text-pad
  positions from the active text-embedding path.
- [x] Focused tests prove the effective policy is visible in status/report or
  replay artifacts.
- [x] The implementation does not silently change unrelated training surfaces
  beyond the explicit mask policy.

## Notes

- The committed policy contract lives in
  `scripts/sir_convert_a_lot/ml/qwen/training/text_embedding_mask_policy.py`.
- Fresh `qwen-train launch` runs now default to `text_span_only`.
- Backward-compatible replay, resume, capture, diagnose, eval, and schedule
  flows still load older launch metadata as `legacy_codec_span` unless an
  explicit override is passed.
- Runtime fingerprint, detached launch metadata, standalone eval artifacts, and
  reporting payloads now expose the effective policy so bounded Story 29 proofs
  are self-describing.
- `legacy_codec_span` remains in the repo only as a bounded RCA reproduction
  surface until Story 29 proves the winning mitigation; once that proof closes,
  the legacy mask surface must be removed before the clean restart task
  proceeds.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
