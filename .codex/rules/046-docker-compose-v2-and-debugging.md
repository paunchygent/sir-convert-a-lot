---
trigger: model_decision
rule_id: RULE-046
title: Docker Compose v2 and Container Debugging
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - docker
  - compose
scope: repo
---

- Use Docker Compose v2 syntax (`docker compose`, never `docker-compose`).
- Keep service definitions deterministic and environment-driven.
- Prefer explicit compose file layering in commands; avoid hidden shell aliases.
- Healthcheck endpoints are mandatory for service readiness.
- For container debugging, capture:
  - `docker compose ps`
  - `docker compose logs --tail=200 <service>`
  - `docker compose config`
- Hemma deploy/debug commands should run through `pdm run run-hemma -- ...` wrappers.
