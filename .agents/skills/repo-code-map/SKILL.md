---
name: repo-code-map
description: "Sir Convert-a-Lot repo-local entry point for platform discovery. Use when orienting in the repository: where the v2 conversion service layers, CLI and HTTP interfaces, sidecars, container lanes, benchmarking harnesses, and docs surface live, which layer owns a change, and how local and Hemma execution lanes differ. Triggers on questions about how this repository is organized, where a concern lives, or which boundary a change crosses."
type: "skill"
created: "2026-08-03"
last_updated: "2026-08-03"
scope: "repo"
---

# Sir Convert-a-Lot Code-Map Router

Read
`.codex/skills/repo-code-map/references/platform-discovery-overview.md` for the
repository's topology, layer boundaries, and execution lanes. It is the first
read for orientation and the only map in this lane.

| Surface                  | Map                                                                     |
| ------------------------ | ----------------------------------------------------------------------- |
| Whole-Platform Discovery | `.codex/skills/repo-code-map/references/platform-discovery-overview.md` |

The overview states topology and links onward. It does not restate routes,
commands, or policy. For those, read the authority directly:

- Repository routes, invariants, and command policy: `AGENTS.md`.
- Human quickstart, conversion routes, and core commands: `README.md`.
- Client usage from other repositories: the shared `sir-convert-a-lot-client`
  skill.
- Hemma deploys and GPU/offload lanes: the shared `hemma-devops` skill plus
  `.codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md`.
- Durable docs and generated indexes: `docs/index.md`.

After a structural change to `scripts/sir_convert_a_lot/`, `services/`,
`containers/`, or the docs topology, update the overview and refresh its as-of
line.
