# Qwen Architecture and Experiment Contract

## Architecture

- Keep Qwen training and control-plane hot-path modules at or below 400 lines:
  `scripts/sir_convert_a_lot/cli/ml/qwen_train.py`,
  `scripts/sir_convert_a_lot/ml/qwen/training/control_plane/`,
  `detached_runtime/`, `reporting/`, and
  `scripts/devops/qwen_finetuning_patches/sft_12hz*.py`.
- CLI entrypoints parse arguments, dispatch commands, and return exit codes.
  Domain validation, path policy, bundle integrity, and detached orchestration
  belong in their owning modules.
- Keep detached runtime responsibilities split across identity/snapshots,
  path/container helpers, command construction, launch, inspection, freshness,
  and stop services.
- Keep reporting split across configuration, live status, payload construction,
  report building, failure projection, step semantics, artifact I/O, and runtime
  version helpers.
- Keep patched runtime split across bootstrap/resume, optimizer-step execution,
  phase/checkpoint/eval/stop control, observer/tracking emission, and terminal
  summary projection.
- Do not add compatibility wrappers, deprecated aliases, pass-through shims, or
  duplicated bundle/path/artifact/optimizer policy. Update internal imports in
  one pass.
- Keep tests aligned with the module that owns the behavior.

## Experiment Evidence

- Classify each active run as exactly one of `provenance`, `mechanism`, or
  `recovery`.
- One run answers one primary question.
- Declare the full comparison state in the Qwen progress ledger before treating
  results as comparable: class, question, surface, code revision, image, bundle,
  sampling/batching, seed/shuffle, batch and accumulation sizes, embedding
  assembly and mask policies, stabilizer, step/eval limits, input artifacts,
  promotion target, status, and interpretation.
- Make causal claims only for one-factor changes within one experiment lane.
- Promote through: local gate, short bounded fresh-start run, then longer governed
  proof.
- Treat a lane that cannot answer its assigned question as historical evidence.

The progress ledger owns the current surface matrix and run state. The Qwen
runbook owns all operator commands and recovery procedure.
