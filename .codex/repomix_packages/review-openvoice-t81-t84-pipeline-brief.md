---
title: OpenVoice Task 81/T84 Pipeline Review Brief
created: '2026-03-06'
status: active
purpose: external-ruthless-review
---

# OpenVoice Task 81/T84 Pipeline Review Brief

## Review Goal

Assess whether the proposed implementation choices, remediation steps, and analysis demonstrate a
correct understanding of:

- the current Sir Convert-a-Lot TTS sidecar pipeline on Hemma,
- the actual live benchmark state for `T81`,
- the correct handling boundaries for OpenVoice V2, the Swedish base model, and Hemma cache/runtime
  constraints.

## Scope

Review the planning docs, ADRs, Docker/runtime code, benchmark harness, tests, and live evidence
for:

- `T81` OpenVoice benchmark implementation,
- `T84` root-cause remediation task,
- the normalized ADR-0007 sidecar contract,
- current Hemma evidence and remaining blocker chain.

## Primary Questions

1. Does the implementation reflect the real current pipeline accurately?
1. Are the proposed remediations targeted at the actual root causes rather than symptoms?
1. Is the model handling technically sound?
   - OpenVoice V2 role
   - Swedish base-speaker role
   - reference-preprocessing path
   - sample-rate handling
   - cache and runtime dependency strategy
1. Is the benchmark harness reasoning correct about what counts as:
   - technical success,
   - partial evidence,
   - validated end-to-end evidence?
1. Are there signs that the analysis overreaches, misunderstands upstream model behavior, or
   misreads the current Hemma runtime truth?

## Findings Requested

Please prioritize:

- incorrect pipeline analysis,
- incorrect model-handling assumptions,
- false claims about current benchmark state,
- remediation steps that do not logically address the real blocker,
- missing tests or evidence that should exist before trusting the result.

Please keep any summary brief and put concrete findings first.
