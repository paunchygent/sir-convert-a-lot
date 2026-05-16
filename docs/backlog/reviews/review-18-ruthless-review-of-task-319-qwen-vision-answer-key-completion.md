---
id: review-18-ruthless-review-of-task-319-qwen-vision-answer-key-completion
title: Ruthless review of Task 319 Qwen vision answer-key completion
type: review
status: completed
priority: high
created: '2026-05-16'
last_updated: '2026-05-16'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters.md
  - docs/backlog/tasks/task-319-enable-qwen3-6-vision-capable-advisory-answer-key-completion-in-the-main-pipeline.md
  - docs/runbooks/runbook-answer-key-local-model-operator-guide.md
labels:
  - review
  - task-319
  - answer-key-completion
  - qwen
  - vision
  - llama-cpp
  - changes-requested
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless post-implementation review of Task 319.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/000-rule-index.md`
  - `docs/backlog/tasks/task-319-enable-qwen3-6-vision-capable-advisory-answer-key-completion-in-the-main-pipeline.md`
  - `docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md`
  - `docs/backlog/tasks/task-317-unify-answer-key-eligibility-and-source-evidence-mapping-decisions-across-manifests-and-adapters.md`
  - `docs/runbooks/runbook-answer-key-local-model-operator-guide.md`
- Primary files reviewed:
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_vision_assets.py`
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py`
  - `scripts/sir_convert_a_lot/infrastructure/answer_key_local_model_profiles.py`
  - `scripts/sir_convert_a_lot/infrastructure/structured_llm_config.py`
  - `scripts/sir_convert_a_lot/infrastructure/structured_llm_payloads.py`
  - `scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion.py`
  - `scripts/sir_convert_a_lot/domain/digiexam_answer_key_completion_candidates.py`
  - `tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py`
  - `tests/sir_convert_a_lot/test_structured_llm_provider_composition.py`
  - `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`
- Public surfaces affected:
  - `answer_key_completion_report_v1` production artifact.
  - Structured LLM provider environment contract.
  - llama.cpp Chat Completions request payloads with multimodal `image_url`
    parts.
  - Task 309 live-validation command and provider launch/status surfaces.
- Compatibility posture:
  - Structured-provider execution remains opt-in and advisory only.
  - Default `source_evidence_only`, text-only providers, and reviewed apply
    mode must not call the provider for embedded-asset rows.
  - Vision-enabled rows must fail closed when assets are unsupported,
    unresolved, or inaccessible to the selected provider.
- Evidence reviewed:
  - Line-numbered inspection of Task 319 production/runtime code, task docs,
    runbook docs, and focused tests.
  - Context7 lookup for current llama.cpp multimodal Chat Completions request
    shape confirmed OpenAI-compatible `image_url` content parts are supported.
  - Context7 lookup for current llama.cpp multimodal launch behavior confirmed
    `-hf` can enable multimodal for supported model repos, `--mmproj` can
    provide an explicit projector, and `--no-mmproj` disables projector loading.
  - Live Hemma status probe using the pre-Task-319 remote runner:
    `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation provider-status --provider-profile qwen36-llama-cpp --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local --timeout-seconds 2`.
  - Focused validation command recorded below.

## Findings

1. [x] `blocker` - The production service writes image files under each job's
   artifact directory, but the structured-provider config has no media-root
   contract that makes those files readable by the persistent llama.cpp server.

   Evidence:

   - The main bundle path always passes
     `artifacts_dir / "answer-key-vision-assets"` into the completion runtime
     at
     `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py:83`.
   - The vision exporter writes relative files below that path and returns
     `file://{asset.relative_path}` URLs, for example
     `file://item-001/assets/<asset>.png`, at
     `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_vision_assets.py:65`
     and
     `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_vision_assets.py:170`.
   - The service structured-provider config only loads provider profile,
     base URL, headers, timeout, and capability fields. It has no
     `vision_media_path`, `media_root`, or equivalent field tying the job
     artifact directory to the provider process at
     `scripts/sir_convert_a_lot/infrastructure/structured_llm_config.py:68`.
   - The llama.cpp launch surface sets `--media-path` from the Task 309
     operator output root, not from service job artifact directories, at
     `scripts/sir_convert_a_lot/devops/answer_key_llama_provider_launch.py:60`.
   - The default Qwen process-arg gate hard-codes the Task 309 eval media root
     in
     `scripts/sir_convert_a_lot/infrastructure/answer_key_local_model_profiles.py:131`.
   - The route test only monkeypatches `HttpStructuredChatProvider` and asserts
     the URL string starts with `file://item-001/assets/`; it does not prove a
     real provider launched with the configured `--media-path` can resolve the
     production job file at
     `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py:296`.

   Why it matters:
   Task 319 claims the main `digiexam_dxe -> examnet_migration_bundle` pipeline
   can use Qwen3.6 vision-capable advisory completion. With the current wiring,
   a real persistent llama.cpp server can receive the correct-looking
   multimodal request but still fail to read the image because the URL is
   relative to the provider's launch-time `--media-path`, while the service
   wrote the file in a per-job artifact directory that the provider was never
   configured to use. That turns the main production path into a mocked success:
   tests prove request shape, not provider-accessible assets.

   Required fix:
   Add an explicit vision media-root contract to the structured-provider
   runtime config, and require it whenever the selected local provider declares
   `supports_multimodal_vision`. The service should materialize provider-facing
   assets under that configured media root, scoped by job id to avoid
   cross-job collisions, and emit image URLs relative to the same root that the
   llama.cpp server receives via `--media-path`. Alternatively, keep
   per-job providers out of scope and fail closed for vision-capable production
   jobs until a governed media-root bridge exists. Update the launch/status
   docs and process-arg checks so the service config and provider runtime prove
   the same media root.

   Proof requirement:
   Add a focused service/runtime test that constructs a vision-capable
   structured config with a media root, runs an image-bearing advisory job, and
   asserts the provider receives an `image_url` that resolves to an existing
   file under the configured provider media root. Add a negative test proving a
   vision-capable provider without media-root config fails closed and does not
   call the provider. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py tests/sir_convert_a_lot/test_structured_llm_provider_composition.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_advisory_completion_allows_valid_embedded_image_item`.

   Remediation assessment:
   Addressed in the local Task 319 remediation pass. The service structured
   LLM runtime config now has a provider-readable vision media-root contract via
   `SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_PATH`, requires an absolute
   path when the primary provider declares multimodal vision support, and writes
   production vision assets below that root with job-scoped relative paths.
   Route tests now prove the provider receives a `file://<job-id>/...` URL that
   resolves to an existing file under the configured media root, and a
   vision-capable provider without a media root fails closed without a provider
   call.

1. [ ] `blocker` - The current Hemma runtime does not prove a running
   vision-enabled Qwen llama.cpp provider, and the status gate is not strong
   enough to prove projector/vision readiness from launch flags alone.

   Evidence:

   - The committed launch plan builds a Qwen llama.cpp command with `-hf`,
     `-hff`, `--alias`, localhost bind, `--ctx-size 32768`,
     `--n-gpu-layers all`, `--fit off`, `--flash-attn on`, `--jinja`,
     `--reasoning off`, `--temp 0.15`, `--offline`, `--media-path`, and
     `--log-file` at
     `scripts/sir_convert_a_lot/devops/answer_key_llama_provider_launch.py:61`.
   - The Qwen profile marks vision assets as permitted at
     `scripts/sir_convert_a_lot/infrastructure/answer_key_local_model_profiles.py:174`,
     and the profile records the media path in required process args at
     `scripts/sir_convert_a_lot/infrastructure/answer_key_local_model_profiles.py:131`.
   - Current llama.cpp docs say multimodal can be enabled with `-hf` for a
     supported model repo, or explicitly with `--mmproj`; the current launch
     command has no explicit `--mmproj` and the status gate does not verify that
     a projector was loaded or that an image request succeeds.
   - The existing microprobe code can write a tiny PNG and send an image URL at
     `scripts/sir_convert_a_lot/devops/answer_key_provider_microprobes.py:299`,
     but Task 319 closeout did not include a successful live Qwen vision
     microprobe.
   - The live Hemma provider-status probe retained at
     `/srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local/provider-status.json`
     reported `ready=false`, `container_present=false`,
     `container_running=false`, `tcp_reachable=false`,
     `localhost_tcp_listener=false`, `expected_model_present=false`,
     `llama_process_present=false`, `llama_required_args_present=false`, and
     `no_cpu_fallback_proved=false` at `2026-05-16T17:39:22Z`.
   - The Hemma checkout reached by `pdm run run-hemma -- git rev-parse HEAD`
     is `3b39174113ede9b98f3b0d82cddd8af43fdd3c23`, while the local reviewed
     Task 319 commit is `1ceef5e14ab474866114d22269b9492b6843a56b`; that
     remote checkout still has the old `task309_*` runner files and lacks the
     current Task 319 `answer_key_*`/`digiexam_*` runner split.

   Why it matters:
   The launch-plan defaults look directionally correct, but they are not the
   same as runtime proof. For this lane, "vision enabled" requires evidence
   that the currently launched provider has the expected model loaded, is
   localhost-only, is GPU-backed without CPU fallback, has the required media
   root, and can complete at least one structured image request. Without that,
   Task 319 can pass unit tests while the deployed Hemma provider is absent,
   stale, or launched without working multimodal support.

   Required fix:
   Sync the Hemma checkout to the Task 319 revision through the merge-only
   workflow, then launch the Qwen provider through the current sanctioned
   runner. Strengthen the readiness closeout so approval requires
   provider-status plus a successful Qwen vision microprobe, not only a dry-run
   launch command. If the selected Qwen repo requires an explicit projector,
   add a governed `mmproj` setting to the provider profile and status gate; if
   `-hf` auto-loads the projector, retain proof from the live provider log or a
   successful image microprobe.

   Proof requirement:
   Run the current runner on Hemma after sync:
   `pdm run run-hemma -- pdm run answer-key-live-validation digiexam provider-status --provider-profile qwen36-llama-cpp --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local --fail-on-blocked`
   and
   `pdm run run-hemma -- pdm run answer-key-live-validation digiexam microprobes --provider-profile qwen36-llama-cpp --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local --fail-on-blocked`.
   The retained reports must show `ready=true`, expected model present,
   localhost-only exposure, required args present, no CPU fallback proved, and
   a successful multimodal image microprobe.

## Verified Checks

- Asset validation reuses the existing PDF asset preparation path and rejects
  unsupported media, missing payload, invalid base64, SHA mismatch, and broken
  references before provider calls in
  `tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py:603`.
- Text-only providers still leave embedded-asset rows as manual follow-up
  without provider calls in
  `tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py:484`.
- Default artifact routing still makes no structured-provider calls, and
  reviewed apply mode still returns before provider composition in
  `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py:72`.
- Normal completion reports still retain bounded candidate-lineage fields and
  do not retain raw/base64 image payloads, raw prompts, or raw provider
  responses in the focused tests reviewed.
- `evaluate-advisory-corpus` now embeds a `coverage_proof` object that compares
  validation-manifest item keys with retained report item keys. This proves
  whether all corpus items and all eligible model-facing items were exercised,
  and serializes missing/unexpected refs when coverage is partial.
- The Hemma-retained Qwen3.6 evaluation was regenerated with this coverage
  proof. It reports 23 per-file reports, 317 report rows, 317 manifest items,
  44 provider-aware eligible items, `all_manifest_items_reported=true`,
  `all_eligible_items_reported=true`, and zero missing or unexpected item refs.
- The static launch plan includes the core expected Qwen llama.cpp settings:
  localhost bind, `--ctx-size 32768`, full GPU layers, `--fit off`,
  `--flash-attn on`, `--jinja`, `--reasoning off`, `--temp 0.15`,
  `--offline`, `--media-path`, and a persistent log file. This is not accepted
  as runtime proof until the live status and vision microprobe pass.

## Decision

changes_requested

## Response

Partial remediation has been applied after the original review pass.

Task 319 now has the local service media-root contract needed for a persistent
vision-capable llama.cpp provider to read production job images. The remaining
approval blocker is live Hemma runtime proof: the current Hemma checkout and
provider process still need to be synced/launched through the merge-only
workflow and verified with provider-status plus a successful Qwen vision
microprobe.

## Follow-up Actions

1. Sync Hemma to the reviewed Task 319 revision, launch or verify the
   `qwen36-llama-cpp` provider, and retain provider-status plus vision
   microprobe reports that prove the actual runtime settings.

## Completion

Review retained on 2026-05-16 with `changes_requested`.

Validation evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py tests/sir_convert_a_lot/test_structured_llm_provider_composition.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_advisory_completion_allows_valid_embedded_image_item`
  -> 29 passed.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_answer_key_completion.py tests/sir_convert_a_lot/test_structured_llm_provider_composition.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_advisory_completion_allows_valid_embedded_image_item tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_vision_provider_without_media_root_fails_closed`
  -> 32 passed.
- `git rev-parse HEAD`
  -> `fc965b21326e4cebb7505fb95b02239d9672375c`.
- `pdm run run-hemma -- git rev-parse HEAD`
  -> `fc965b21326e4cebb7505fb95b02239d9672375c`.
- `pdm run run-hemma -- pdm run answer-key-live-validation digiexam evaluate-advisory-corpus --provider-profile qwen36-llama-cpp --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local --reports-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local/advisory-corpus-reports`
  -> regenerated `advisory-golden-evaluation.json` and `.md` with
  `coverage_proof.all_manifest_items_reported=true`,
  `coverage_proof.all_eligible_items_reported=true`,
  `coverage_proof.missing_manifest_item_count=0`,
  `coverage_proof.missing_eligible_item_count=0`, and
  `coverage_proof.unexpected_report_item_count=0`.
- `pdm run run-hemma -- jq '{schema_version, report_count, report_item_count, correct_suggestion_count, wrong_but_valid_count, manual_follow_up_count, skipped_count, coverage_proof}' /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local/advisory-golden-evaluation.json`
  -> `report_count=23`, `report_item_count=317`,
  `correct_suggestion_count=41`, `wrong_but_valid_count=3`,
  `manual_follow_up_count=0`, `skipped_count=273`, and complete coverage.
- `pdm run run-hemma -- shasum -a 256 /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local/advisory-golden-evaluation.json /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local/advisory-golden-evaluation.md`
  -> JSON
  `79a6d3349fe43c1add67b515b1070cbc797184fb5da6cbe18bba633c5cfcf551`,
  Markdown
  `fd39ef97525ed31f267849bfe5cdd7a8c063836dfda0e9582de03389a4e78713`.
- `pdm run run-hemma -- pdm run python -m scripts.sir_convert_a_lot.devops.run_task309_granite_answer_key_live_validation provider-status --provider-profile qwen36-llama-cpp --output-root /srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local --timeout-seconds 2`
  -> wrote provider status with `ready=false`; no Qwen llama.cpp container,
  process, listener, expected model, required args, or no-CPU-fallback proof was
  present.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [ ] Review closed
