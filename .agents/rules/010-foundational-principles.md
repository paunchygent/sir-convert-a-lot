---
trigger: always_on
rule_id: RULE-010
title: Foundational Principles
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - architecture
  - quality
scope: repo
---

- Contract-first delivery: API/docs contracts are normative and code follows them.
- GPU-first rollout for heavy PDF workloads; no silent fallback drift.
- Keep modules SRP-focused; split before files exceed 500 LoC.
- Do not introduce ad hoc converters outside canonical Sir Convert-a-Lot surfaces.
- Prefer deterministic outputs and machine-readable manifests.
- All behavior changes require task/story documentation under `docs/backlog/`.
- Planning hierarchy invariant: `programme -> epic -> story -> task` (tasks are PR-sized and may be standalone).
