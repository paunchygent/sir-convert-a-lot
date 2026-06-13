---
type: agent_session_long_term_memory
date: '2026-06-13'
scope: Formula lane handoff compaction
---

# Session History: Formula Lane Handoff Compaction

Date: 2026-06-13

## Retained Context

- Task 344 localized the slow page-window chunk to Docling formula VLM
  generation and fixed the deterministic Granite-Docling repetition loop with
  governed stop strings and deterministic Transformers generation controls.
- Task 345 is the active formula follow-up: source-layer formula evidence must
  be authoritative when usable, VLM output must be advisory or rejected unless a
  governed source-backed gate accepts it, and every formula region needs an
  explicit artifact representation decision.
- The 2026-06-06 Task 345 scrutiny gate passed in qualified form: PyMuPDF gave
  coordinate-backed source evidence on incident pages `13-16`, Poppler bbox
  extraction crashed on page `14`, and implementation must preserve explicit
  `usable`, `partial_or_unusable`, and `absent` states.
- By the 2026-06-10 checkpoint, source-backed formula authority skipped formula
  VLM before generation when PyMuPDF evidence was `usable`, emitted safe
  `formula_authority` metadata, preserved absent-source generated-candidate
  behavior, and surfaced accepted page-window metadata through backend results,
  `ConversionMetadata`, replay reports, and the v2 CLI manifest.
- Task 346/350 candidate evaluation left PaddleOCR AMD lanes blocked on Hemma
  ROCm, rejected the current DeepSeek-OCR-2 vLLM ROCm lane for incoherent
  repeated output, and kept DeepSeek-OCR-2 HF eager only as a possible governed
  future advisory integration behind Task 345 source-backed authority.

## Carry-Forward Boundary

Task 342 presents formula-authority metadata, Task 343 later consumes it for
conversion decisioning, and future OCR/VLM production integration must not
overwrite born-digital source-backed formula evidence.
