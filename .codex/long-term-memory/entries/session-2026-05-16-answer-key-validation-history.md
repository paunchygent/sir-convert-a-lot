---
type: agent_session_long_term_memory
date: '2026-05-16'
scope: Task 309 answer-key completion live validation history from Granite/vLLM demotion through Qwen3.6 evaluation
---

## Task 309 Validation History

### 2026-05-15 — Granite/vLLM First Live Run

Task 309 launched persistent Granite/vLLM on Hemma at `127.0.0.1:8017`.
Provider preflight passed for ROCm, cache paths, localhost-only exposure,
disabled request logging, `/v1/models`, and no CPU fallback. All three
structured-output microprobes passed. Detached resource monitor showed full-corpus
advisory run was GPU-bound (median GPU busy `100%`, memory `94%`).

In-process advisory corpus run over 23 files / 317 items in `86919.444ms`:
36 suggested, 8 manual follow-up, 273 skipped. Golden evaluation found
12 correct suggestions and **24 wrong-but-valid suggestions** — blocks promotion.

Direct follow-up probes with improved consumer-friendly item messages did not
change conclusion. A 10-item sample from failed rows produced 1 correct, 3
wrong-but-valid, 6 invalid-output. Temperature `0.1` chat experiment on a
word-bank gap-fill reached 7/10 in full-question framing, 1/10 gap-by-gap.

### 2026-05-16 — Granite/vLLM Demotion

Granite/vLLM demoted for answer-key completion. Hemma GPU capacity cleared by
stopping `sir-convert-task309-granite-vllm`, `huleedu_rst_parser_service`,
`huleedu_essay_embed_offload`, and `sir_convert_a_lot_prod`. Post-stop
verification: GPU use `0%`, VRAM `0%`, no KFD PIDs.

### 2026-05-16 — Devstral Small Launch And Evaluation

Hemma `active.gguf` resolved to `Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf`,
but `llama-server-rocm.service` was inactive and `llama.cpp-rocm:7.2.0` image
was missing. BuildKit rebuild using `68717eac3c081eec00bbb961c0e0e3c129a1790f`
reached HIP compilation, then Hemma became unreachable over Tailscale/SSH before
any live Devstral request or corpus validation.

A later Devstral-Small-2-24B-Instruct-2512-UD-Q6_K_XL run completed against
the full Task 309 corpus through `llama-server` on `127.0.0.1:8082`.
Final: **34 correct, 8 wrong-but-valid, 2 manual-follow-up** out of 44 eligible.
It failed Swedish curriculum terminology and genetics items that Qwen3.6
answered correctly, so Devstral is demoted for this route.

### 2026-05-16 — Qwen3.6-27B-Q6_K Live Validation

Local `llama-server` run on `127.0.0.1:8082` with `llama-cpp-json-schema`.
`temperature=0.15` (task-optimal; card-default `0.7` gave 38/4). Schema
simplification removed `decision_state` enum. Synonym-aware evaluator added.

Final: **39 correct, 3 wrong-but-valid, 2 manual-follow-up** out of 44 eligible.
Promotion gate `wrong_but_valid_count == 0` not met. Operator decision: settle
on Qwen3.6 as the current guarded model of choice for answer-key validation,
without treating it as automatic answer-key promotion.
