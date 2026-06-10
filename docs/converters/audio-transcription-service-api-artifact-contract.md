---
type: converter
id: CONV-audio-transcription-service-api-artifact-contract
title: Audio Transcription Service API Artifact Contract
status: draft
created: 2026-06-09
updated: 2026-06-10
owners:
  - platform
tags:
  - api
  - v2
  - audio
  - transcription
  - stt
  - diarization
  - artifact-bundle
  - gateway
  - skriptoteket
links:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/reviews/review-25-ruthless-review-of-adr-0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Purpose

Define the draft Service API v2 route contract for speech-to-text jobs that
ingest uploaded audio or video sources and produce a diarized transcript bundle.

This is a draft route-specific contract. Task 355 registers Service API v2
create-job admission for `audio -> transcript_bundle`, including request-shape,
owner-scope, local-upload, public-option, capacity, GPU-required, and
`retention.pin=false` checks. Full sidecar execution, audio progress,
cancellation cleanup, `transcript_json` persistence, and formatter outputs are
not implemented until later governed Story 53 and Story 54 tasks land.

The retained readiness review at
`docs/backlog/reviews/review-25-ruthless-review-of-adr-0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
approved the remediated contract direction on 2026-06-09. This contract remains
draft until later implementation tasks prove sidecar runtime behavior and
canonical transcript artifact persistence through the public route.

## Relationship To Existing V2 API

Audio transcription uses the existing Service API v2 lifecycle:

- `POST /v2/convert/jobs`
- `GET /v2/convert/jobs/{job_id}`
- `GET /v2/convert/jobs/{job_id}/result`
- `GET /v2/convert/jobs/{job_id}/artifacts`
- `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`
- `POST /v2/convert/jobs/{job_id}/cancel`

The proposed route key is:

```json
{
  "source.format": "audio",
  "conversion.output_format": "transcript_bundle"
}
```

Video files are accepted through this route only when the uploaded container has
an audio stream. They still use `source.format = "audio"` because the domain
source authority is the extracted audio stream, not video analysis.

The product/browser route is HuleEdu Gateway-owned:

- browser/product entry: `/sir-convert/v2/convert/...`
- downstream Sir Convert service route: `/v2/convert/...`

Sir Convert must not implement a separate `/sir-convert/v2/...` route family.
The direct public `convert.hule.education` host remains reserved/fail-closed for
browser product traffic unless a separate accepted decision changes that
posture.

## Initial Request Shape

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "recording.m4a",
    "format": "audio"
  },
  "conversion": {
    "output_format": "transcript_bundle"
  },
  "audio_transcription_options": {
    "language": "auto",
    "diarization": {
      "mode": "auto",
      "num_speakers": null,
      "min_speakers": null,
      "max_speakers": null
    },
    "max_duration_seconds": 7200,
    "output_artifacts": ["json"]
  },
  "execution": {
    "acceleration_policy": "gpu_required",
    "priority": "normal",
    "document_timeout_seconds": 7200
  },
  "retention": {
    "pin": false
  }
}
```

## Product Semantics

- The first product promise is a best-effort editable transcript.
- Swedish and English are the day-one language targets.
- Language detection defaults to `auto`; the service may expose explicit
  language override once validation and runtime behavior are proven.
- Diarization is required in the core capability, not a later optional add-on.
  A successful `transcript_bundle` must include truthful speaker labels aligned
  to transcript segments.
- Source recordings up to 120 minutes must be handled through stable batch or
  chunked processing.
- Sir Convert uses short operational retention for source media and generated
  artifacts. Durable transcript storage and user-facing retention live in
  Skriptoteket or the consuming product.

## Accepted Source Inputs

The runtime must use a codec boundary such as FFmpeg/ffprobe rather than
embedding source-specific decoder logic.

Expected day-one containers and codecs, subject to deployment evidence:

- audio files: `wav`, `mp3`, `m4a`, `aac`, `flac`, `ogg`, `opus`, `webm`,
  `aiff`;
- video containers with an audio stream: `mp4`, `mov`, `mkv`, `webm`.

The implementation must probe the upload, select one audio stream
deterministically, normalize audio for the STT sidecar, and fail with a
deterministic error when no usable audio stream exists.

### Ingestion Safety Limits

The first runtime registration must enforce these route defaults unless a later
accepted contract changes them:

| Limit | Initial value | Failure code |
| --- | --- | --- |
| Upload size | `500 MiB` | `audio_upload_size_exceeded` |
| Media duration | `7200` seconds | `audio_duration_exceeded` |
| Probe timeout | `30` seconds | `audio_probe_timeout` |
| Normalization timeout | `max(300s, 2 * media_duration_seconds + 120s)`, capped at `1800s` | `audio_normalization_timeout` |
| Stream selection | first usable audio stream in container order | `audio_stream_missing` |
| Input protocols | local uploaded files only | `audio_input_protocol_unsupported` |
| Normalized audio | mono `16 kHz` signed `16-bit` PCM WAV | `audio_normalization_failed` |

Runtime rules:

- Remote URLs, playlists, network protocols, device inputs, recursive includes,
  and caller-supplied filesystem paths are out of scope.
- FFmpeg/ffprobe subprocesses must run without stdin, with bounded stderr
  capture and error-level logging by default.
- Video containers are accepted only as uploaded files with an audio stream;
  video analysis is out of scope.
- Corrupt files, unsupported containers, unsupported codecs, no-audio
  containers, timeouts, and over-limit uploads must map to stable v2 errors.
- Source media, normalized audio, probe outputs, chunks, and sidecar scratch
  files must live under job-scoped scratch roots and be cleaned according to
  the retention policy.

### Route-Level Admission Caps

Story 51 locks the first concrete admission policy before runtime route
registration. A service instance must reject, not queue, new audio jobs when
any cap is exhausted:

| Cap | Initial value | Failure code |
| --- | --- | --- |
| Active STT jobs per service instance | `2` | `audio_route_capacity_exceeded` |
| Active probe/normalization workers | `2` | `audio_route_capacity_exceeded` |
| Active sidecar transcription/diarization requests | `1` | `audio_route_capacity_exceeded` |
| GPU slots per service instance | `1` | `audio_route_capacity_exceeded` |
| Queue behavior | reject immediately; no internal wait queue in the first slice | `audio_route_capacity_exceeded` |

These caps are route-local and do not authorize runtime registration. They are
the admission contract for later worker, sidecar-client, and Gateway slices.

## STT Sidecar Internal Contract

The public v2 route integrates with one Sir-owned internal adapter contract.
The main service must not call backend-native STT or diarization APIs directly.

### `GET /health`

Required response fields:

```json
{
  "status": "ok",
  "ready": true,
  "backend_profile_id": "stt_sv_en_primary",
  "backend_version": "2026-06-09",
  "gpu_ready": true,
  "capability_version": "stt-sidecar-v1"
}
```

### `GET /capabilities`

Required response shape:

```json
{
  "adapter_contract_version": "stt-sidecar-v1",
  "runtime": {
    "network_scope": "internal_only",
    "published_port_allowed": false,
    "gpu_required": true,
    "acceleration_family": "rocm",
    "acceleration_ready": true
  },
  "media": {
    "max_upload_bytes": 524288000,
    "max_duration_seconds": 7200,
    "accepted_containers": [
      "wav",
      "mp3",
      "m4a",
      "aac",
      "flac",
      "ogg",
      "opus",
      "webm",
      "aiff",
      "mp4",
      "mov",
      "mkv"
    ],
    "input_protocols": ["local_upload"],
    "normalized_audio": {
      "container": "wav",
      "sample_rate_hz": 16000,
      "channels": 1,
      "sample_format": "s16"
    }
  },
  "transcription": {
    "profile_label": "stt_sv_en_primary",
    "languages": ["auto", "sv", "en"],
    "word_timestamps_supported": true
  },
  "diarization": {
    "profile_label": "diarization_sv_en_primary",
    "required_for_success": true,
    "modes": ["auto", "known_speaker_count", "speaker_range"],
    "exclusive_speaker_segments_supported": true
  },
  "cache": {
    "cache_family": "huggingface",
    "host_root": "/srv/scratch/sir-convert-a-lot/cache/huggingface",
    "container_root": "/cache/huggingface",
    "cache_roots_ready": true,
    "model_artifacts_present": true
  },
  "secrets": {
    "required_secret_names": ["HUGGINGFACE_TOKEN"],
    "required_secrets_present": true,
    "values_exposed": false
  }
}
```

Rules:

- Capability profile labels must be bounded and provider-neutral.
- Raw model ids, model paths, access tokens, prompts, backend-native beam sizes,
  compute types, and tuning knobs must not become public request or artifact
  fields.
- Missing model files, inaccessible gated model artifacts, missing required
  secrets, unwritable cache roots, or GPU unavailability must make the sidecar
  fail readiness.
- The sidecar must not publish a host port and must accept requests only from
  the main Sir Convert service on the internal Docker network.
- `cache_roots_ready`, `model_artifacts_present`, and
  `required_secrets_present` are readiness truth fields. Missing or false
  values fail closed before a job can be admitted.

### `POST /transcribe`

The normalized sidecar request receives:

- one local-upload-derived media or normalized audio file;
- a structured metadata payload with language intent, diarization mode, speaker
  hints, duration limits, output schema version, and request-scoped handle;
- `X-Correlation-ID` for trace correlation.

The sidecar must return deterministic JSON on success or failure. It must not
own v2 job ids, artifact keys, artifact retention, user identity, or
authorization. Cancellation from the main service must stop further sidecar
work and allow scratch cleanup.

## Audio Transcription Options

### Language

Allowed initial values:

- `auto`
- `sv`
- `en`

`auto` is the default and must detect Swedish and English as first-class
targets. Other languages may appear in model output as best-effort evidence, but
they are not day-one product guarantees.

### Diarization

Allowed modes:

- `auto`
- `known_speaker_count`
- `speaker_range`

Field rules:

- `mode = "auto"` requires `num_speakers`, `min_speakers`, and `max_speakers`
  to be `null`.
- `mode = "known_speaker_count"` requires `num_speakers >= 1` and forbids
  `min_speakers` / `max_speakers`.
- `mode = "speaker_range"` requires `min_speakers >= 1`,
  `max_speakers >= min_speakers`, and forbids `num_speakers`.

These fields map cleanly to established diarization libraries that accept exact
speaker counts or min/max speaker constraints. The implementation must not
hand-roll diarization.

Diarization failure is route failure. The service must not return a successful
artifact with placeholder speakers, missing speakers, or
`diarization_unavailable`. A future partial or undiarized mode requires a
separate accepted contract.

### Output Artifacts

Day-one implementation must require:

- `json`

Planned formatter artifacts:

- `txt`
- `md`
- `vtt`
- `srt`

Formatter artifacts must be produced by modular downstream strategies wired by
DI after the JSON core is stable. They must not duplicate transcription,
diarization, or segment-alignment logic.

### Public Backend Control Exclusion

Public request options are limited to language intent, diarization mode/hints,
duration guardrails, and requested artifact families. Browser, Gateway,
Skriptoteket, and local-operator callers must not pass raw model ids, model
paths, device choices, beam sizes, VAD internals, quantization/compute types,
cache paths, prompts, or backend-native alignment knobs. Such fields fail
admission with `audio_public_options_unsupported`.

## Transcript Bundle JSON

The canonical JSON artifact must include:

- schema version;
- source filename, source media SHA-256, and normalized audio SHA-256 inside
  owner-scoped artifact metadata only;
- language detection result and confidence/probability where available;
- diarization mode requested and diarization mode used;
- ordered transcript segments with:
  - segment id;
  - start/end seconds;
  - speaker label;
  - text;
  - language when available;
  - confidence/probability fields only when the chosen backend exposes them
    truthfully;
- warnings and best-effort quality notes;
- runtime metadata, including bounded backend profile labels and acceleration
  used.

The JSON contract is the artifact authority for later formatters.
The transcript JSON must not include raw model ids, access tokens, local cache
paths, sidecar trust tokens, backend-native tuning knobs, or unbounded stderr.

## Named Artifacts

Initial successful jobs must expose named artifacts:

| Artifact key | Required in first runtime slice | Content type | Notes |
| --- | --- | --- | --- |
| `transcript_json` | yes | `application/json` | Canonical structured transcript bundle. |
| `transcript_txt` | no | `text/plain` | Formatter strategy after JSON core stabilizes. |
| `transcript_md` | no | `text/markdown` | Formatter strategy after JSON core stabilizes. |
| `transcript_vtt` | no | `text/vtt` | Formatter strategy after JSON core stabilizes. |
| `transcript_srt` | no | `application/x-subrip` | Formatter strategy after JSON core stabilizes. |

Unrequested or not-yet-implemented formatter artifacts must be represented
explicitly in bundle metadata rather than silently omitted when the route
advertises them.

## Progress Semantics

Required stage markers:

- `queued`
- `starting`
- `probing_media`
- `normalizing_audio`
- `transcribing`
- `diarizing`
- `aligning_segments`
- `packaging`
- `succeeded`
- `failed`
- `canceled`

Existing PDF-only page counters remain `null` for this route. Audio progress
must use route-specific fields rather than overloading page counters.

Required audio progress fields:

| Field | Type | Rules |
| --- | --- | --- |
| `audio_total_media_seconds` | `float | null` | Set after probe succeeds. |
| `audio_processed_media_seconds` | `float | null` | Monotonic; never greater than total. |
| `audio_percent_complete` | `float | null` | Monotonic; range `0..100`. |
| `audio_current_chunk_index` | `int | null` | Set during chunked execution. |
| `audio_total_chunks` | `int | null` | Set when chunk plan is known. |

Heartbeat freshness must update at least every `30` seconds while codec,
transcription, diarization, alignment, or packaging work is active.

### Checkpoints, Retry, And Cancellation

The first sidecar execution implementation must define deterministic
duration-based audio chunks before sidecar-backed processing is enabled. Chunk
checkpoints must record enough metadata to prevent duplicate transcript segment
persistence on retry:

- source media hash and normalized audio hash;
- chunk index, start/end seconds, overlap seconds, and processing profile;
- transcription segment ids already accepted for the chunk;
- diarization window ids already accepted for the chunk;
- alignment validation state.

Final `transcript_json` persistence is allowed only after all chunks complete
and cross-chunk transcription/diarization alignment validates.

Resume from checkpoint is out of scope for the first STT runtime slice. Cancel
must be clean and idempotent: the main service stops further chunk scheduling,
propagates cancellation to the sidecar, then purges incomplete normalized
audio, sidecar temp chunks, and partial transcript state. Failed or canceled
jobs must not expose partial transcripts as terminal artifacts.

Transient retry is allowed only for main-service-classified retryable sidecar
failures. Replayed work must be idempotent under the v2 request fingerprint and
must not duplicate transcript segments, diarization windows, or artifacts.

## Error Policy

Required deterministic errors:

- `audio_route_disabled`
- `audio_route_capacity_exceeded`
- `audio_upload_size_exceeded`
- `audio_input_protocol_unsupported`
- `audio_stream_missing`
- `audio_container_unsupported`
- `unsupported_audio_codec`
- `audio_duration_exceeded`
- `audio_probe_failed`
- `audio_probe_timeout`
- `audio_normalization_failed`
- `audio_normalization_timeout`
- `audio_sidecar_unavailable`
- `audio_transcription_backend_unavailable`
- `audio_diarization_backend_unavailable`
- `audio_model_cache_unavailable`
- `audio_model_access_denied`
- `audio_gpu_required_unavailable`
- `audio_transcription_failed`
- `audio_diarization_failed`
- `audio_segment_alignment_failed`
- `audio_sidecar_canceled`
- `audio_transcript_artifact_unavailable`
- `audio_diarization_options_invalid`
- `audio_public_options_unsupported`
- `audio_retention_pin_unsupported`

The service must not return empty transcript artifacts as success.
The service must not return diarization-unavailable artifacts as success.

## Authentication And Ownership

Current transport remains aligned with Service API v2:

- `X-API-Key` remains the transport credential where still required.
- `Idempotency-Key` is required for job creation.
- `X-Correlation-ID` is optional but strongly recommended and returned by the
  service.

Authenticated product/browser traffic must enter through HuleEdu Gateway
`/sir-convert/v2/convert/...`. Gateway signs
`InternalIdentityContextV1` with audience `sir-convert-a-lot` and the relevant
Sir Convert grants. Sir Convert must derive job and artifact ownership from the
verified identity context, not from `X-API-Key`.

The sidecar receives only request-scoped internal handles and correlation
metadata. It must not receive browser cookies, HuleEdu identity headers,
service API keys, or artifact-owner authority unless a later accepted contract
requires a narrower defense-in-depth token.

## Retention And Logging

Sir Convert treats recordings and transcripts as user content even when this
route does not introduce special Sir Convert PII classification. Retention is
short and operational; durable user-facing transcript retention belongs in
Skriptoteket or the consuming product after artifact download or save.

Initial retention classes:

| Class | Examples | Sir Convert retention |
| --- | --- | --- |
| Source media | uploaded audio/video | purge at terminal job cleanup and no later than 24h |
| Normalized audio | WAV/PCM intermediates | purge at terminal job cleanup and no later than 24h |
| Sidecar temp chunks | probe files, split audio, alignment scratch | purge on success/failure/cancel and sweep no later than 24h |
| Canonical transcript JSON | `transcript_json` | expire with v2 job result TTL, capped at 24h |
| Formatter artifacts | future `txt`, `md`, `vtt`, `srt` | same as transcript JSON |
| Failed/canceled partials | incomplete transcript/checkpoint state | purge at terminal cleanup |
| Logs/metrics/traces | operational metadata only | no transcript text, source content, utterances, tokens, or media bytes |
| Benchmark fixtures | sanitized/operator-owned fixtures | governed by the benchmark task/runbook |

`retention.pin=true` is rejected for `audio -> transcript_bundle` until a later
accepted retention contract defines pin semantics for source media, normalized
audio, transcript artifacts, and product-owned saves.

## Implementation Gate

Runtime implementation must not start until a PR-sized task or story links this
contract and defines:

- route model changes in `domain.specs_v2`;
- route policy and create-job handler changes in `domain.service_routes_v2` and
  `interfaces.http_create_job_routes_v2`;
- sidecar capability and health checks;
- FFmpeg/ffprobe safety limits and subprocess timeout tests;
- model/cache/secret readiness tests;
- fixture and live Hemma validation strategy;
- OpenAPI export and downstream consumer contract updates;
- red-first tests for route validation, idempotency, owner-scoped reads,
  diarization options, media safety limits, fail-closed diarization,
  cancellation cleanup, retry idempotency, retention cleanup, and 120-minute
  batch behavior.
