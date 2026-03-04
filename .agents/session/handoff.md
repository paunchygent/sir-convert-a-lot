# Session Handoff

## Next Session Goals (2026-03-04)

- Execute `T67`: progress-aware timeout semantics in v2 client polling (heartbeat-only fallback when
  progress fields are absent/`null`).
- Execute `T68`: publish ADR locking progress + partial artifacts + cancel-with-save + resume
  semantics (contract-first; no implementation drift).
- Then proceed with `T69` -> `T70` -> `T71` (API progress fields; checkpoints/partials; cancel+resume).
- Preserve GPU-first governance (no silent CPU fallback when GPU is requested/required).
- After each task: run validators and only then update checkboxes/statuses per Epic 06 closeout
  checklist.
