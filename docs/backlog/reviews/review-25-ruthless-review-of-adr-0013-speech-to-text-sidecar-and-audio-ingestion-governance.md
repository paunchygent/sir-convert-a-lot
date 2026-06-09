---
id: 'review-25-ruthless-review-of-adr-0013-speech-to-text-sidecar-and-audio-ingestion-governance'
title: 'Ruthless review of ADR-0013 speech-to-text sidecar and audio ingestion governance'
type: 'review'
status: 'completed'
priority: 'high'
created: '2026-06-09'
last_updated: '2026-06-09'
related:
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - review
  - adr
  - adr-0013
  - stt
  - audio
  - sidecar
  - diarization
  - gateway
---
Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless docs-as-code readiness review of ADR-0013 as the
  proposed speech-to-text sidecar and audio ingestion governance decision.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/_meta/docs-contract.yaml`
  - `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
  - `docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md`
  - `docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md`
  - `docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md`
  - `docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md`
  - `docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md`
- Scope under review:
  - ADR-0013 proposed decision text.
  - Epic 12 as the governing capability increment.
  - `docs/converters/audio-transcription-service-api-artifact-contract.md` as
    the delegated draft route and artifact contract.
  - Current v2, downstream, and internal-adapter contract references that
    expose the proposed route as draft-only.
- Public or operational surfaces affected:
  - Future Service API v2 `audio -> transcript_bundle` route.
  - HuleEdu Gateway `/sir-convert/v2/convert/...` product edge.
  - Internal STT sidecar health, capability, and transcription calls.
  - Uploaded source media, normalized audio, transcript JSON, and formatter
    artifacts.
  - Future Skriptoteket/HuleEdu transcript persistence flows.
- Compatibility posture:
  - Docs-only readiness review. ADR-0013 is `proposed`; this review does not
    accept the ADR, register a runtime route, change OpenAPI, or implement code.
  - Any future implementation must remain a governed v2 route-specific
    extension. It must not add legacy route aliases, public anonymous STT
    lanes, direct sidecar ingress, or provider-native public request fields.
- Third-party evidence checked:
  - Context7 pyannote.audio docs confirm pretrained diarization pipelines,
    `num_speakers` / `min_speakers` / `max_speakers`, GPU transfer, exclusive
    diarization output, and Hugging Face token/gated-model setup.
  - Context7 faster-whisper docs confirm backend-native model size, device,
    compute type, beam/VAD/word timestamp, and language-detection knobs that
    must stay behind a provider-neutral Sir Convert contract.
  - Context7 FFmpeg docs confirm explicit stream mapping and audio output
    options; uploaded-media safety still needs repo-owned limits and sandboxing
    policy.

## Findings

1. [x] `high` - ADR-0013 says "internal Docker network" but does not define the
   STT sidecar trust or capability contract.

   Evidence:

   - ADR-0013 gives the main service "internal sidecar capability checks and
     deterministic error mapping" at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:80`.
   - It gives the sidecar "bounded capability reporting" at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:94`.
   - It then relies on "internal Docker network" and no direct public exposure at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:96`.
   - The accepted TTS sidecar pattern is more concrete: ADR-0007 requires
     normalized internal endpoints, capability fields, cache roots, and benchmark
     proof at
     `docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md:108`.

   Why it matters:
   Internal-only is not an interface contract. Without a Sir-owned STT adapter
   shape, implementation can drift into backend-native HTTP calls, untyped
   health checks, direct model identifiers, unbounded sidecar metadata, or a
   sidecar that accidentally receives artifact authority it must not own. It
   also leaves lateral internal callers and Compose port exposure as "probably
   fine" rather than fail-closed invariants.

   Required fix:
   Before ADR acceptance, add or link a route-specific STT sidecar contract
   analogous to ADR-0007. It should define `GET /health`, `GET /capabilities`,
   and the normalized transcription/diarization request endpoint; internal auth
   or caller restriction; published-port prohibition; correlation propagation;
   cancellation semantics; deterministic error mapping; bounded backend profile
   metadata; acceleration truth; model/cache fields; and the rule that job,
   owner, artifact, and retention authority stays in the main service.

   Proof requirement:
   Future implementation must add contract tests for capability parsing,
   fail-closed sidecar-unavailable behavior, no public sidecar route exposure,
   no backend-native public request fields, and Compose/runtime proof that the
   sidecar port is not published. Run the route implementation's focused tests
   plus `pdm run docs-sync`, `pdm run docs-validate`,
   `pdm run skills-validate`, `pdm run handoff-validate`, and
   `git diff --check`.

   Re-review disposition:
   Resolved on 2026-06-09. ADR-0013 now defines a Sir-owned STT sidecar
   contract with `GET /health`, `GET /capabilities`, normalized
   `POST /transcribe`, internal-only reachability, published-port prohibition,
   bounded metadata, deterministic errors, ownership separation, and
   cancellation propagation at
   `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:106`.
   The delegated route contract repeats the concrete endpoint shapes and
   capability payload at
   `docs/converters/audio-transcription-service-api-artifact-contract.md:176`.

1. [x] `high` - The FFmpeg/ffprobe boundary is named but untrusted media
   processing is not safety-governed.

   Evidence:

   - ADR-0013 assigns media probing and audio stream selection to the sidecar at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:89`.
   - It says to rely on FFmpeg/ffprobe or equivalent at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:101`.
   - The draft audio contract accepts common audio files and video containers at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:124`
     and requires deterministic probing/selection at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:135`.
   - The example allows `max_duration_seconds: 7200` and
     `document_timeout_seconds: 7200` at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:97`.

   Why it matters:
   Uploaded media is attacker-controlled parser input. "Use FFmpeg" prevents
   hand-written decoders, but it does not by itself define max file size,
   stream-count limits, probe timeouts, allowed protocols, local-file-only
   handling, temp-space limits, corrupt-container behavior, or deterministic
   multi-audio-stream selection. A 120-minute route without those limits can
   become a denial-of-service lane or a surprising network/protocol expansion
   through media tooling.

   Required fix:
   ADR-0013 or the route contract must add an ingestion safety contract: maximum
   upload size, maximum duration, probe timeout, normalization timeout,
   permitted container/protocol set, local-upload-only rule, deterministic
   stream-selection ordering, normalized audio format/sample rate/channels,
   temp-storage root and cleanup rule, bounded stderr/log capture, corrupt-file
   error mapping, and resource caps for concurrent sidecar jobs. If a later
   route wants URL ingestion, it needs a separate accepted decision.

   Proof requirement:
   Future implementation must include behavioral tests for no-audio files,
   multi-audio-stream files, oversized/duration-exceeded media, corrupt media,
   ffprobe timeout, and unsupported codec failures. Command-construction tests
   are acceptable only where the FFmpeg invocation flags themselves are the
   governed contract. Run the focused route tests and a Hemma live fixture proof
   before route registration.

   Re-review disposition:
   Resolved on 2026-06-09. ADR-0013 now defines upload size, media duration,
   probe timeout, normalization timeout, local-upload-only input protocols,
   deterministic stream selection, normalized PCM WAV shape, bounded subprocess
   behavior, scratch cleanup, and stable error mapping at
   `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:155`.
   The route contract includes matching safety limits and error codes at
   `docs/converters/audio-transcription-service-api-artifact-contract.md:147`.
   The first implementation task still must choose concrete route-level
   concurrency/admission caps before runtime registration.

1. [x] `high` - Diarization is simultaneously required and allowed to become
   "unavailable" under a later contract.

   Evidence:

   - ADR-0013 states "Diarization is required for the core route" at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:107`.
   - It then says a selected backend that cannot diarize may "fail
     deterministically or mark diarization as unavailable according to a later
     accepted contract" at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:113`.
   - Epic 12 makes diarization core product behavior at
     `docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md:52`.
   - The draft route contract promises speaker labels in the canonical JSON at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:198`
     but lists both diarization-unavailable and diarization-failed errors at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:257`.

   Why it matters:
   This is the most dangerous product-contract ambiguity in the ADR. If
   diarization is required, a successful `transcript_bundle` without truthful
   speaker labels is a false success. If undiarized transcripts are allowed,
   that is a different success shape and needs explicit UI/downstream semantics,
   not a later escape hatch hidden inside an accepted "required diarization"
   ADR.

   Required fix:
   Pick one day-one rule. The strict rule is cleaner: if diarization cannot run
   or segment alignment cannot produce truthful speaker labels, the job fails
   deterministically with stable error codes and no successful transcript JSON.
   If product wants partial success, define a separate explicit result state or
   artifact completeness flag, required warning fields, downstream UI behavior,
   and formatter restrictions before acceptance. Do not accept ADR-0013 with
   both semantics open.

   Proof requirement:
   Future route tests must prove sidecar diarization-unavailable,
   diarization-failed, and alignment-failed cases cannot return a normal
   `succeeded` transcript bundle unless an accepted partial-success contract
   exists. Add conformance tests that every successful day-one segment has a
   truthful speaker label or an explicitly governed non-diarized state.

   Re-review disposition:
   Resolved on 2026-06-09. ADR-0013 now makes diarization fail-closed for the
   day-one route and forbids successful undiarized or placeholder-speaker
   transcript bundles at
   `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:190`.
   The route contract mirrors that rule at
   `docs/converters/audio-transcription-service-api-artifact-contract.md:319`
   and keeps partial or undiarized transcript delivery behind a separate future
   accepted contract.

1. [x] `high` - Model access, cache, and secret governance are left to
   implementation discretion.

   Evidence:

   - ADR-0013 names `pyannote.audio` as the first diarization candidate at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:109`.
   - ADR-0013 allows Faster-Whisper, Whisper-family models, or later adapters
     behind the sidecar contract at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:119`.
   - Accepted ADR-0007 requires sidecar cache roots and cache-family visibility
     for TTS at
     `docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md:227`.
   - The Hemma runbook requires model caches and long-lived generated state to
     stay on `/srv/scratch` or `/srv/storage` instead of the OS disk at
     `docs/runbooks/runbook-hemma-devops-and-gpu.md:59`.

   Why it matters:
   Current pyannote pretrained diarization usage requires Hugging Face token and
   gated-model setup, while Faster-Whisper exposes backend-native model size,
   device, compute type, VAD, beam, and timestamp knobs. Without explicit
   governance, the implementation can accidentally require online model
   downloads at runtime, bake secrets into images, use container-local caches,
   leak raw model identifiers into public metadata, or make Hemma benchmark
   evidence non-reproducible.

   Required fix:
   Add an STT model/runtime governance section before acceptance. It should
   require backend profiles with bounded public labels, explicit model/cache
   roots, no container-local steady-state downloads, secret source and absence
   from images/logs, startup failure when required model access is missing,
   benchmark evidence for the exact profile on Hemma, and a rule that
   backend-native tuning knobs remain internal unless a later route contract
   promotes them.

   Proof requirement:
   Benchmark tasks must prove cold/warm cache behavior, capability metadata,
   missing-token failure, GPU/acceleration truth, and bounded backend metadata.
   Add tests that reject raw model ids/model sizes/vendor task names in public
   request payloads and artifacts. Run the focused tests plus the Hemma benchmark
   wrapper named by the future implementation task.

   Re-review disposition:
   Resolved on 2026-06-09. ADR-0013 now defines backend profile selection,
   cache-family/root reporting, no container-local steady-state downloads,
   fail-closed readiness for missing model access/cache/GPU, and no token/path
   leakage at
   `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:223`.
   The delegated route contract carries the same capability and readiness rules
   at `docs/converters/audio-transcription-service-api-artifact-contract.md:196`.

1. [x] `high` - Retention and PII handling are too vague for uploaded recordings
   and transcripts.

   Evidence:

   - ADR-0013 says Sir Convert "should keep short operational retention" for
     source media, normalized audio, transcript bundles, and formatter artifacts
     at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:150`.
   - The draft JSON artifact includes source filename, source media hash,
     normalized audio hash, speaker labels, transcript text, language evidence,
     warnings, and runtime metadata at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:191`.
   - Product/browser traffic ownership is tied to verified
     `InternalIdentityContextV1` at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:274`.
   - ADR-0005's retention rule is explicit for checkpoints and partials
     expiring with jobs at
     `docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md:188`.

   Why it matters:
   Audio recordings and transcripts are high-PII artifacts. "Short operational
   retention" is not enough for source media, normalized derivatives, partial
   chunks, sidecar temp files, transcript text, speaker labels, logs, and
   product handoff. It also uses "should", which is too weak for accepted
   retention policy.

   Required fix:
   Define concrete retention classes and TTLs before acceptance: uploaded
   source, normalized audio, sidecar temp chunks, transcript JSON, formatter
   artifacts, failed-job artifacts, canceled-job artifacts, logs, and benchmark
   fixtures. State purge behavior for `retention.pin=false`, pin behavior if
   supported, product-owned durable save handoff, owner-scoped artifact access,
   log redaction rules, and cleanup proof. Replace retention "should" with
   normative "must" once the policy is chosen.

   Proof requirement:
   Future implementation must include retention tests proving source media,
   normalized audio, sidecar temp files, transcript artifacts, and failed/canceled
   partials expire or are purged according to the route contract. Add auth tests
   proving a verified identity context owns transcript artifacts and another
   identity cannot read them.

   Re-review disposition:
   Resolved on 2026-06-09. ADR-0013 now defines sensitive-content logging
   prohibitions, retention classes, 24-hour caps, failed/canceled partial purge,
   benchmark fixture scope, and `retention.pin=true` rejection for the first STT
   slice at
   `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:310`.
   The route contract mirrors the retention table at
   `docs/converters/audio-transcription-service-api-artifact-contract.md:488`.

1. [x] `medium` - The 120-minute batch claim lacks route-specific progress,
   checkpoint, cancellation, and retry semantics.

   Evidence:

   - ADR-0013 says 120-minute recordings require stable batch or chunked
     processing at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:57`.
   - The sidecar owns segment alignment at
     `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:93`.
   - The draft contract only recommends stage markers at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:229`
     and says existing PDF page counters remain `null` at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:245`.
   - The implementation gate asks for 120-minute batch tests at
     `docs/converters/audio-transcription-service-api-artifact-contract.md:291`
     but does not define what retry, resume, or cancel means for chunked audio.

   Why it matters:
   Long-running STT jobs need more than stage names. Without chunk boundaries,
   processed-duration counters, heartbeat rules, sidecar cancellation, retry
   idempotency, and partial artifact semantics, a two-hour job can stall after
   transcription, duplicate work on retry, leak temp files after cancel, or
   return misaligned diarization without a recoverable checkpoint.

   Required fix:
   Add an audio long-job extension that deliberately reuses or extends ADR-0005.
   Define audio chunk units, monotonic progress fields, checkpoint granularity,
   sidecar cancellation behavior, idempotent replay rules, retry classification,
   partial transcript availability if any, and alignment validation before final
   artifact persistence. If resume is out of scope, state that explicitly and
   prove clean cancel/purge instead.

   Proof requirement:
   Future implementation must include tests for heartbeat freshness,
   cancellation propagation, retry after transient sidecar failure, no duplicate
   segment persistence, no final artifact when alignment is invalid, and a Hemma
   120-minute fixture or synthetic-duration proof through the real job lifecycle.

   Re-review disposition:
   Resolved on 2026-06-09. ADR-0013 now extends ADR-0005 deliberately with
   route-specific audio duration progress, chunk metadata, heartbeat freshness,
   chunk checkpoints, cancellation cleanup, no first-slice resume, and retry
   idempotency at
   `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md:271`.
   The route contract includes matching progress fields and checkpoint/cancel
   rules at `docs/converters/audio-transcription-service-api-artifact-contract.md:382`.

## Decision

approved

## Response

ADR-0013 is directionally right on the big architectural move: STT belongs in a
sidecar, the main service owns v2 job/artifact/authorization semantics, the
public API stays provider-neutral, and formatter artifacts should sit on top of
structured JSON.

The initial version was not acceptance-ready because the risky parts were soft:
untrusted media parsing, sidecar trust/capability shape, diarization failure
semantics, model/cache/secret governance, transcript/media retention, and
long-job behavior.

### 2026-06-09 Remediation Response

ADR-0013 and the draft audio converter contract were amended to address the six
readiness findings without changing ADR-0013 out of `proposed` state.

Remediation added:

1. A concrete STT sidecar trust/capability contract with `GET /health`,
   `GET /capabilities`, normalized `POST /transcribe`, internal-only exposure,
   published-port prohibition, bounded metadata, deterministic errors, and
   cancellation propagation.
1. An untrusted-media ingestion safety contract covering upload size, duration,
   probe and normalization timeouts, local-upload-only input protocols,
   deterministic stream selection, normalized audio shape, bounded subprocess
   output, scratch roots, cleanup, and stable error mapping.
1. A fail-closed diarization rule: successful `transcript_bundle` artifacts must
   contain truthful aligned speaker labels; unavailable diarization,
   unsupported speaker constraints, or failed alignment are terminal failures.
1. Model/cache/secret governance for backend profiles, cache roots, startup
   readiness failure, no container-local steady-state model downloads, and no
   token/model/path leakage in logs, capabilities, artifacts, or benchmarks.
1. Retention classes and TTLs for source media, normalized audio, sidecar temp
   chunks, transcript JSON, future formatter artifacts, failed/canceled
   partials, logs, and benchmark fixtures, with `retention.pin=true` rejected
   until a later accepted contract.
1. Audio long-job semantics for duration-based chunks, audio progress fields,
   heartbeat freshness, chunk checkpoints, clean cancel/purge, retry
   idempotency, and no first-slice resume or partial-terminal artifact.

The base v2 contract and Epic 12 acceptance criteria were also updated to point
to the remediated draft and retain Review 25 as the re-review gate.

### 2026-06-09 Re-Review Response

Re-review approves the remediated ADR-0013 direction. The changes resolve the
six retained readiness findings while keeping ADR-0013 in `proposed` state.
This approval means the decision is ready for the repo's separate ADR acceptance
step; it does not register a runtime route or authorize implementation without a
PR-sized governed task.

## Follow-up Actions

1. Before runtime registration, the first implementation task must define
   concrete route-level concurrency/admission caps in addition to the per-upload
   safety limits already in the draft contract.
1. Scaffold the first Epic 12 story/task only after ADR-0013 is accepted and the
   route contract retains the STT sidecar contract, media safety policy, and
   long-job/retention proof gates.
1. Future implementation review must require focused tests for capability
   parsing, fail-closed diarization, media safety limits, owner-scoped reads,
   cleanup/retention, retry idempotency, cancellation propagation, and
   120-minute batch behavior.

## Completion

Initial ruthless review completed on 2026-06-09 with `changes_requested`.
ADR-0013 remains `proposed`; this review does not accept or amend the decision.
Remediation response recorded on 2026-06-09; ADR-0013 still requires
independent re-review before acceptance.

Re-review completed on 2026-06-09 with `approved`. ADR-0013 remains `proposed`
until a separate accepted decision/status-change task promotes it.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
