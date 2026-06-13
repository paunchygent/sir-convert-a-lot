---
type: agent_session_long_term_memory
date: '2026-06-12'
scope: STT JSON runtime proof and Story 54 formatter lane setup
---

# Session History: STT JSON Runtime And Formatter Lane

Date: 2026-06-12

## Retained Context

- Review 40 approved the deployed FasterWhisper ROCm plus pyannote STT
  sidecar proof, including Swedish/English fixtures, exact and min/max speaker
  hints, GPU-required execution, and human transcript-review acceptance.
- Task 355 and Review 41 accepted Service API v2 `audio -> transcript_bundle`
  admission for API-key tunnel and Gateway signed-identity create-job requests.
- Task 356 and Review 42 accepted sidecar-backed runtime execution and
  canonical `transcript_json` persistence through the public v2 lifecycle.
- Task 357 and Review 43 accepted service-owned chunk planning, checkpointed
  execution, truthful numeric audio progress, sidecar cleanup, and live tunnel
  proof at deployed revision `00f9d7ab700ff4dbeea9f8e6da65caa5c49e1cfa`.
- Story 54 / Task 358 is complete and accepted in Review 44. Product-neutral
  TXT, Markdown, WebVTT, and SRT formatter artifacts are implemented over
  canonical `transcript_json`.

## Carry-Forward Boundary

Sir Convert owns deterministic standard-format transcript artifacts over
canonical JSON. Downstream apps own product meaning, durable saves, filenames,
teacher-facing UX, search, sharing, and workflow-specific derivatives.
