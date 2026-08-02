---
type: adr
id: ADR-SIRCON-0012
title: Speech-to-Text Sidecar and Audio Ingestion Governance
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: accepted
deciders:
- platform
links:
  governing: []
retired_ids:
- ADR-0013
---

## Purpose

Record the accepted architecture and governance boundary for speech-to-text
audio ingestion before runtime work begins.

## Status

- Accepted
- Date: 2026-06-09

This decision is accepted architecture and governance authority for the
speech-to-text sidecar direction. It does not register a runtime route, expose
OpenAPI fields, or authorize implementation without PR-sized governed tasks.

The retained readiness review at
`docs/backlog/reviews/review-25-ruthless-review-of-adr-0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
approved the remediated decision text on 2026-06-09. This status-change slice
promotes ADR-0013 to `accepted`; implementation still remains gated by Epic 12
stories and route-specific tasks.

## Context

Sir Convert-a-Lot already exposes conversion work through Service API v2,
supports a HuleEdu Gateway `/sir-convert` product edge, and has accepted
sidecar-only governance for text-to-speech. Speech-to-text has similar runtime
pressure but a distinct product contract:

- inputs are uploaded audio files or video containers with audio streams;
- outputs are editable transcripts, not audio artifacts;
- speaker diarization is core product behavior;
- 120-minute recordings require stable batch or chunked processing;
- downstream products need durable transcript persistence, while Sir Convert
  must keep short operational retention for large media and artifacts.

The main Sir Convert service image is already responsible for Docling,
Pandoc/WeasyPrint, job persistence, idempotency, and artifact authorization. STT
model, diarization, and codec-runtime dependencies must not be added directly to
that image without a specific accepted exception.

## Decision

Adopt a sidecar-backed speech-to-text architecture for the planned
`audio -> transcript_bundle` Service API v2 route.

### Main Service Boundary

The main Sir Convert service owns:

- canonical Service API v2 job lifecycle;
- upload admission, idempotency, correlation, and retention;
- owner-scoped job, result, and artifact authorization;
- named artifact bundle persistence;
- route validation and public/provider-neutral API semantics;
- internal sidecar capability checks and deterministic error mapping.

The main service must not absorb STT model, diarization, or broad codec runtime
dependencies as in-process libraries for the first implementation.

### Sidecar Boundary

The STT sidecar owns:

- media probing and audio stream selection through a proven codec boundary;
- deterministic audio normalization for transcription;
- speech-to-text model runtime;
- speaker diarization runtime;
- segment alignment between transcription and diarization output;
- bounded capability reporting.

The sidecar runs only on the internal Docker network. It is not a public
internet surface and is not exposed directly to browsers or downstream apps.

### STT Sidecar Trust And Capability Contract

The STT sidecar must expose one Sir-owned internal adapter contract, not a
backend-native API. Every deployable STT sidecar profile must implement:

- `GET /health` for liveness/readiness, returning at least `status`,
  `ready`, `backend_profile_id`, `backend_version`, `gpu_ready`, and
  `capability_version`.
- `GET /capabilities` for machine-readable runtime truth, returning at least:
  - adapter contract version;
  - `network_scope = "internal_only"`;
  - `published_port_allowed = false`;
  - GPU requirement, acceleration family, and acceleration truth fields;
  - accepted media limits and normalized audio format;
  - supported language intent values and day-one language guarantees;
  - supported diarization modes, including exact speaker count and min/max
    speaker range when the selected diarization backend supports them;
  - bounded backend profile labels for transcription and diarization;
  - cache family plus host/container cache roots;
  - required secret names without secret values.
- `POST /transcribe` for a normalized transcription/diarization request,
  accepting one local-upload-derived media file or normalized audio file plus a
  structured metadata payload.

The sidecar must be reachable only by the main Sir Convert service over the
internal Docker network. It must not publish a host port, accept browser or
product credentials, authorize jobs, persist user-owned artifacts, or derive
artifact ownership. Any defense-in-depth sidecar token must be a runtime
secret supplied outside the image and must never appear in logs, artifacts, or
capability responses.

The main service owns all v2 job ids, idempotency keys, correlation ids,
authorization decisions, artifact names, artifact persistence, and retention.
The sidecar may receive a request-scoped internal handle and the
`X-Correlation-ID`; it must not treat either as owner identity.

Sidecar errors must be deterministic JSON with stable error codes. Backend
metadata returned to the main service must be bounded and provider-neutral:
runtime reports may include profile labels such as `stt_profile`,
`diarization_profile`, `acceleration_used`, and `normalization_profile`, but
must not expose raw model ids, tokens, filesystem secrets, prompt fragments, or
backend-native tuning knobs in public artifacts.

Sidecar cancellation must be observable. When the main service cancels a job,
the current sidecar request must stop further media processing, terminate child
codec/model work when safe, return or record a canceled result, and allow the
main service to purge incomplete sidecar outputs under the route retention
policy.

### Codec Boundary

The implementation must rely on FFmpeg/ffprobe or an equivalent proven media
runtime for common audio and video containers. Sir Convert must not build
container-specific decoders by hand.

Because uploaded media is untrusted input, the first runtime slice must enforce
an ingestion safety contract before sidecar registration:

- maximum upload size: `500 MiB` by default for this route;
- maximum probed media duration: `7200` seconds;
- maximum accepted audio streams: select one deterministic stream and ignore
  the rest;
- probe timeout: `30` seconds per uploaded source;
- normalization timeout: `max(300 seconds, 2 * media_duration_seconds + 120)`,
  capped at `1800` seconds for a 120-minute source;
- input protocols: local uploaded files only; remote URLs, playlists, network
  protocols, device inputs, and recursive includes are out of scope;
- container allowlist: the route contract owns the day-one set and the sidecar
  capabilities must report the deployed set;
- deterministic audio stream selection: first usable audio stream in container
  order unless a later accepted contract adds explicit stream selection;
- normalized audio: mono `16 kHz` signed `16-bit` PCM WAV unless the accepted
  sidecar profile declares a stricter compatible format;
- codec subprocess policy: no stdin, bounded stderr capture, error-level logs
  by default, and child-process cleanup on timeout or cancellation;
- temporary storage: source copies, probe files, normalized audio, and chunks
  live under the job/sidecar scratch roots and are purged by the retention
  policy;
- corrupt, unsupported, over-limit, timeout, and no-audio cases map to stable
  v2 error codes.

URL ingestion, remote fetch, user-selected media streams, and larger
video-first uploads require a separate accepted decision.

### Diarization Boundary

Diarization is required for the core route. Implementation must evaluate and
use a real diarization library or backend adapter where feasible. The first
candidate family is `pyannote.audio`, which supports pretrained diarization
pipelines, GPU execution, exact speaker counts, min/max speaker constraints,
and exclusive speaker diarization output suitable for transcription alignment.

For this route, diarization is fail-closed. A successful
`transcript_bundle` must contain truthful speaker labels produced by the
selected diarization backend and aligned to transcript segments. If the backend
is unavailable, the requested speaker constraint cannot be honored, or segment
alignment cannot be validated, the job must fail deterministically. It must not
return an undiarized transcript, placeholder speaker labels, or
`diarization_unavailable` as a successful artifact state.

Partial or undiarized transcript delivery is out of scope until a separate
accepted contract defines artifact completeness, UI labeling, formatter
restrictions, and downstream save semantics.

### Transcription Boundary

The public API remains provider-neutral. Backends such as Faster-Whisper,
Whisper-family models, or later provider adapters may be evaluated behind the
sidecar capability contract, but public request fields must not expose raw model
ids, model sizes, vendor task names, or low-level decoding knobs.

The first implementation must use backend profiles chosen by deployment
configuration and reported through `/capabilities`. Public requests may express
language intent and diarization hints, but they must not choose raw model ids,
model paths, beam sizes, quantization modes, prompts, VAD internals, or
backend-native alignment knobs.

### Model, Cache, And Secret Governance

STT and diarization backends must follow Hemma's persistent-cache discipline:

- no backend may rely on container-local model downloads as the steady-state
  path;
- Hugging Face-backed profiles must use the canonical shared cache family and
  declare both host and container roots in `/capabilities`;
- Docker-restricted hosts may expose the canonical cache through the approved
  home-mount compatibility path, but the capability response must still name
  the canonical cache family;
- required model artifacts must be present in the configured cache before the
  production profile is marked ready;
- missing tokens, inaccessible gated models, unwritable cache roots, or missing
  model files must make the sidecar fail readiness rather than downloading
  unpredictably or falling back to CPU;
- model access tokens and sidecar trust tokens must come from runtime secrets
  or secret files, never from images, checked-in env files, capability payloads,
  logs, metrics, transcript artifacts, or benchmark reports.

Benchmark reports may include bounded profile labels and cache hit/miss
evidence, but not raw access tokens, private model paths, or user transcript
content.

### Output Boundary

The first stable output authority is structured JSON:

- text segments;
- timestamps;
- speaker labels;
- language evidence;
- warnings and best-effort quality metadata.

Plain text, Markdown, VTT, and SRT are formatter strategies over the JSON core.
They must be modularized behind small domain/application components and wired
with DI where route composition benefits from it.

### Access Boundary

Product/browser traffic enters through HuleEdu Gateway
`/sir-convert/v2/convert/...` and carries HuleEdu
`InternalIdentityContextV1` with audience `sir-convert-a-lot`. The local
operator lane remains the sanctioned tunnel API.

No anonymous public STT route, public grant lane, direct browser Sir Convert
credential, or direct sidecar ingress is part of this decision.

### Audio Long-Job Boundary

The `audio -> transcript_bundle` route extends ADR-0005 deliberately rather
than overloading PDF page counters.

For 120-minute sources, implementation must define audio chunk units before
runtime registration. Chunk boundaries must be duration-based, deterministic,
overlap-aware when needed for model accuracy, and recorded in route-specific
checkpoint metadata.

Progress must remain monotonic and observable through polling and any accepted
push surface. Audio progress must include:

- `audio_total_media_seconds` after probing succeeds;
- `audio_processed_media_seconds`, never decreasing and never greater than
  total;
- `audio_percent_complete`, derived from processed duration and capped at
  `100`;
- `audio_current_chunk_index` and `audio_total_chunks` when chunked execution
  is active;
- heartbeat freshness at least once every `30` seconds while codec,
  transcription, diarization, or alignment work is active.

Checkpoint metadata must be persisted after each completed chunk and must be
sufficient to prevent duplicate segment persistence on retry. A final artifact
must not be persisted until transcription, diarization, and alignment validate
across all chunks.

Main-service cancellation must propagate to codec subprocesses and sidecar
model work, then purge incomplete normalized audio, chunks, and partial
transcript state according to the retention policy. Resume from checkpoint is
out of scope for the first STT runtime slice; if added later, it must create a
new job id and prove deterministic merge behavior before acceptance.

Transient retry is allowed only for failures classified as retryable by the
main service. Replayed work must be idempotent under the v2 job fingerprint and
must not duplicate transcript segments or expose partial artifacts as terminal
success.

### Retention Boundary

Sir Convert must keep short operational retention for STT media and transcript
artifacts. Product-facing durable transcript retention belongs in Skriptoteket
or another consuming product after artifact download or save-to-user-files
persistence.

This route does not introduce special Sir Convert PII classification, but audio
recordings and transcripts are user content and must be treated as sensitive
for logging, ownership, redaction, and retention. Logs, metrics, traces,
errors, and benchmark summaries must not include transcript text, source
filenames as labels, speaker utterances, raw model prompts, media hashes as
labels, or audio-derived content.

Initial retention classes:

| Class | Examples | Sir Convert retention |
| --- | --- | --- |
| Source media | uploaded audio/video | purge at terminal job cleanup and no later than 24h |
| Normalized audio | WAV/PCM intermediates | purge at terminal job cleanup and no later than 24h |
| Sidecar temp chunks | probe files, split audio, alignment scratch | purge on success/failure/cancel and sweep no later than 24h |
| Canonical transcript JSON | `transcript_json` artifact | expire with v2 job result TTL, capped at 24h unless a later accepted contract allows pinning |
| Formatter artifacts | future `txt`, `md`, `vtt`, `srt` | same as transcript JSON |
| Failed/canceled partials | incomplete transcripts, chunk checkpoints | purge at terminal cleanup; partial retrieval is out of scope for the first STT slice |
| Logs/metrics/traces | operational metadata only | bounded metadata only; no content payload retention |
| Benchmark fixtures | sanitized or operator-owned fixtures | governed by the benchmark task/runbook, never by live product retention |

`retention.pin=true` is not accepted for `audio -> transcript_bundle` until a
later retention contract defines what pinning means for source media,
normalized audio, transcript artifacts, and product-owned saves.

## Consequences

Positive:

- isolates fast-moving STT and diarization dependencies from the main service;
- preserves the existing v2 async job, idempotency, and artifact model;
- makes 120-minute processing feasible through batch/chunked sidecar execution;
- keeps Skriptoteket/HuleEdu access aligned with the existing Gateway edge.

Tradeoffs:

- adds another internal runtime component and health/capability surface;
- requires Hemma benchmark evidence before route defaults can be locked;
- requires careful alignment between transcript and diarization segments;
- delays `txt`, `md`, `vtt`, and `srt` until JSON core behavior is proven.

## Follow-Up

- Publish or accept the route-specific converter contract:
  `docs/reference/ref-sircon-general-audio-transcription-service-api-artifact-contract-audio-transcription-service-api-artifact-contract.md`.
- Scaffold implementation stories and tasks under Epic 12, starting with
  route-level concurrency/admission caps before runtime registration.
- Benchmark codec probing, transcription, diarization, and 120-minute batch
  processing on Hemma before production route registration.
- Update HuleEdu Gateway route docs/tests when the generic Sir Convert product
  edge is widened from DigiExam-only wording to governed conversion routes.
