---
type: converter
id: CONV-audio-transcription-service-api-artifact-contract
title: Audio Transcription Service API Artifact Contract
status: active
created: 2026-06-09
updated: 2026-06-14
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

Define the Service API v2 route contract for speech-to-text jobs that
ingest uploaded audio or video sources and produce a diarized transcript bundle.

This is the active route-specific JSON-core contract. Task 355 registers
Service API v2 create-job admission for `audio -> transcript_bundle`, including
request-shape, owner-scope, local-upload, public-option, capacity,
GPU-required, and `retention.pin=false` checks. Task 356 deploys and Review 42
accepts the first sidecar-backed runtime execution slice for stage heartbeat,
cancellation cleanup, and canonical `transcript_json` persistence. Story 54 is
now active for formatter work, with Task 358 defining the first product-neutral
formatter implementation slice.

Task 356's accepted runtime authority covered canonical JSON transcript
delivery only. Task 358 adds product-neutral formatter artifacts over that
canonical JSON authority; downstream products still own durable saves,
presentation labels, product filenames, search, sharing, and workflow-specific
derivatives.

Story 56 extends this authority with stateless formatter replay from saved
canonical transcript JSON plus typed speaker display-name overlays. The replay
route is settled as a Service API v2 conversion job with
`source.format = transcript_json` and
`conversion.output_format = transcript_bundle`; no bespoke formatter endpoint
or downstream browser-local formatter is part of the contract.

Task 357 hardens the current progress gap by making Sir Convert own chunk
planning, checkpointed chunk execution, and monotonic numeric audio progress
during active transcription. The local implementation introduces a clean
internal sidecar contract transition to `probe-media`, `diarize`,
`transcribe-chunk`, and `finalize`; Review 43 accepts deployed Hemma/live
tunnel proof for this Task 357 contract at revision
`00f9d7ab700ff4dbeea9f8e6da65caa5c49e1cfa`.

The retained readiness review at
`docs/backlog/reviews/review-25-ruthless-review-of-adr-0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
approved the remediated contract direction on 2026-06-09. Review 42 accepted
sidecar runtime behavior and canonical transcript artifact persistence through
the public route on 2026-06-10.

## Relationship To Existing V2 API

Audio transcription uses the existing Service API v2 lifecycle:

- `POST /v2/convert/jobs`
- `GET /v2/convert/jobs/{job_id}`
- `GET /v2/convert/jobs/{job_id}/result`
- `GET /v2/convert/jobs/{job_id}/artifacts`
- `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`
- `POST /v2/convert/jobs/{job_id}/cancel`

The route key is:

```json
{
  "source.format": "audio",
  "conversion.output_format": "transcript_bundle"
}
```

Video files are accepted through this route only when the uploaded container has
an audio stream. They still use `source.format = "audio"` because the domain
source authority is the extracted audio stream, not video analysis.

## Formatter Replay Request Shape

Story 56 / Task 359 define the overlay-aware formatter replay route as the
existing Service API v2 lifecycle with this route key:

```json
{
  "source.format": "transcript_json",
  "conversion.output_format": "transcript_bundle"
}
```

Replay accepts one uploaded canonical `transcript_json_v1` payload and the
following typed options object:

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "saved-transcript.json",
    "format": "transcript_json"
  },
  "conversion": {
    "output_format": "transcript_bundle"
  },
  "transcript_formatter_options": {
    "schema_version": "transcript_formatter_replay_v1",
    "requested_artifacts": ["txt", "md", "vtt", "srt"],
    "speaker_label_overrides": [
      {
        "canonical_speaker_label": "SPEAKER_00",
        "display_name": "Anna Andersson"
      }
    ]
  },
  "retention": {
    "pin": false
  }
}
```

Replay `requested_artifacts` is a closed enum of exact lowercase values:
`txt`, `md`, `vtt`, and `srt`. Replay does not request `json`; the uploaded
JSON remains the canonical source truth. Returned artifact keys are
`transcript_txt`, `transcript_md`, `transcript_vtt`, and `transcript_srt`.

`canonical_speaker_label` values are case-sensitive exact inventory keys from
the uploaded canonical transcript JSON. Display names are trimmed of ordinary
surrounding whitespace only after raw control-character validation.

Replay job specs reject `pdf_options` and `execution`; those fields are not
ignored, normalized, or folded out of idempotency fingerprints.

Replay `/result` returns the normal Service API v2 result envelope; its
`result.artifact` metadata points at the primary
`transcript_replay_bundle_manifest.json` artifact by filename, size, digest, and
content type, but `/result` does not inline the replay `artifacts[]` manifest.
Singular `/artifact` streams the content-safe
`transcript_formatter_replay_result_v1` bundle manifest body. That primary
manifest contains operational artifact metadata only; it must not include
transcript text, utterances, display names, source content, or a reissued
canonical JSON payload. The named replay artifact list also omits
`transcript_json`.

Speaker overrides apply only to formatter display labels. The replay route must
reject unknown canonical speaker labels, duplicate override labels, empty
display names, duplicate display names, control characters, malformed JSON,
partial transcript state, unsupported requested artifacts, and
`retention.pin=true`. The replay route must not call STT, diarization,
alignment, sidecar, codec, source-audio, or model-provider code.

Task 363 makes replay a producer-owned fast lane under the existing Service
API v2 job contract. An admitted replay request is persisted as a normal v2 job
and executed immediately outside the generic heavy conversion worker queue, so
`POST /v2/convert/jobs?wait_seconds=0` returns a terminal replay job: `200`
with `job.status="succeeded"` when artifacts were produced or `200` with
`job.status="failed"` for fail-closed replay execution errors such as malformed
canonical JSON or unknown speaker labels. Request-shape validation failures
still return the existing v2 error envelope before job creation. Replay timing
telemetry records bounded admission and execution durations using route/job
metadata only; transcript text, utterances, speaker display names, source
content, credentials, and signed headers are not logged or used as metric
labels.

The product/browser route is HuleEdu Gateway-owned:

- browser/product entry: `/sir-convert/v2/convert/...`
- downstream Sir Convert service route: `/v2/convert/...`

Sir Convert must not implement a separate `/sir-convert/v2/...` route family.
The direct public `convert.hule.education` host remains reserved/fail-closed for
browser product traffic unless a separate accepted decision changes that
posture.

HuleEdu only forwards `/sir-convert/v2/convert/jobs*` through the Gateway edge
and must not rewrite Sir Convert replay responses. Skriptoteket owns durable
saved transcript records, speaker overlay intent, filenames, download/save UX,
search, sharing, and product workflow semantics.

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
    "required_secret_names": ["HF_TOKEN"],
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

### Chunked Execution Endpoints

Task 357 Service API v2 runtime uses the current chunked internal sidecar
contract. The main service must not use the retired blocking `/transcribe` path
for `audio -> transcript_bundle` execution.

#### `POST /probe-media`

The request carries one request-scoped local upload handle, language and
diarization options, duration limits, output schema version, and correlation
metadata. On success, the sidecar probes duration, normalizes the selected audio
stream, and returns provider-neutral media metadata:

```json
{
  "status": "succeeded",
  "media": {
    "duration_seconds": 600.0,
    "normalized_audio_sha256": "sha256:...",
    "normalized_audio_handle": "sir-stt-normalized:..."
  },
  "runtime_metadata": {
    "acceleration_used": "rocm",
    "normalization_profile": "mono_16khz_s16_wav"
  },
  "warnings": []
}
```

`normalized_audio_handle` is an opaque sidecar-owned capability, not a
caller-controlled filesystem path. The sidecar must remember the issued handle
with the `request_handle`, normalized media path, job-scoped scratch directory,
and `normalized_audio_sha256`.

#### `POST /diarize`

The request carries the original `request_handle`, the opaque
`normalized_audio.handle`, and the `normalized_audio.sha256` returned by
`/probe-media`. The sidecar must reject unknown, mismatched, stale, or
hash-mismatched handles before running diarization. A successful response
contains global diarization windows for the normalized media, and diarization
failure remains job failure.

#### `POST /transcribe-chunk`

The request carries the original `request_handle`, the same normalized audio
handle and SHA-256, and one deterministic chunk window. The sidecar must verify
the handle and SHA-256 before trimming/transcribing the chunk. A successful
response contains only that chunk's transcript segments and bounded language
metadata.

#### `POST /finalize`

The request carries `request_handle`. The sidecar removes the whole
job-scoped normalized-media directory and untracks all handles for that request
idempotently. The main service calls finalize on success, terminal failure, and
cancellation. Sidecar cancel may also finalize internally, but cleanup must
remain idempotent.

#### `POST /cancel`

Cancellation records the request handle as canceled, stops future sidecar work,
and triggers the same job-scoped normalized-media cleanup. Repeated cancel or
finalize calls must be safe.

All sidecar endpoints must return deterministic JSON on success or failure.
The sidecar must not own v2 job ids, artifact keys, artifact retention, user
identity, or authorization.

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

The implementation requires canonical JSON authority for every audio
transcription request:

- `json`

Callers may optionally request formatter artifacts:

- `txt`
- `md`
- `vtt`
- `srt`

Formatter artifacts must be produced by modular downstream strategies wired by
the audio bundle packaging layer after the JSON core is stable and persisted.
They must not duplicate transcription, diarization, or segment-alignment logic.
`json` is normalized into `audio_transcription_options.output_artifacts` even
when the caller requests only formatter aliases; unsupported artifact aliases
fail admission with `audio_public_options_unsupported`.

### Formatter Ownership Boundary

Sir Convert owns product-neutral standard-format transformations over
canonical transcript JSON:

- plain text transcript export;
- neutral Markdown transcript export;
- WebVTT subtitle/caption export;
- SubRip/SRT subtitle export.

Downstream products own product meaning and presentation decisions, including
button placement, teacher-facing labels, filenames, durable saves, search,
sharing, lesson-material workflows, subtitle-workbench behavior, and any
product-specific Markdown derivatives. Sir Convert formatter implementations
must not add Skriptoteket-specific headings, classroom workflow labels, durable
user-file semantics, or source-audio reprocessing.

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

The JSON contract is the artifact authority for formatter artifacts.
The transcript JSON must not include raw model ids, access tokens, local cache
paths, sidecar trust tokens, backend-native tuning knobs, or unbounded stderr.

## Named Artifacts

Successful jobs expose named artifacts:

| Artifact key | Required | Content type | Notes |
| --- | --- | --- | --- |
| `transcript_json` | yes | `application/json` | Canonical structured transcript bundle. |
| `transcript_txt` | optional requested artifact | `text/plain` | Product-neutral formatter strategy over canonical JSON. |
| `transcript_md` | optional requested artifact | `text/markdown` | Neutral transcript Markdown over canonical JSON; product-specific Markdown remains downstream. |
| `transcript_vtt` | optional requested artifact | `text/vtt` | WebVTT formatter over canonical JSON timestamps and speaker labels. |
| `transcript_srt` | optional requested artifact | `application/x-subrip` | SubRip/SRT formatter over canonical JSON timestamps and speaker labels. |

Available formatter artifacts use stable filenames:
`transcript_txt.txt`, `transcript_md.md`, `transcript_vtt.vtt`, and
`transcript_srt.srt`. Requested available formatter manifest entries include
`availability="available"`, `content_type`, `filename`, `size_bytes`, `sha256`,
and `retrieval_path`. Unrequested formatter artifacts are represented
explicitly as `availability="unrequested"` with
`audio_transcript_artifact_unavailable` rather than silently omitted.

For `transcript_json -> transcript_bundle` replay jobs:

- `transcript_json` is not emitted as a named artifact and requests for it fail
  with `transcript_replay_artifact_unavailable`;
- only requested `transcript_txt`, `transcript_md`, `transcript_vtt`, and
  `transcript_srt` artifacts appear as available named artifacts;
- the primary result artifact is the content-safe
  `transcript_formatter_replay_result_v1` manifest, not the uploaded canonical
  JSON and not overlay truth;
- the named artifact manifest and named artifact endpoints are the downstream
  authority for available replay outputs.

## Progress Semantics

Required stage markers:

- `queued`
- `starting`
- `probing_media`
- `normalizing_audio`
- `diarizing`
- `transcribing`
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
| `audio_pipeline_percent_complete` | `float | null` | Additive whole-pipeline measured estimate; monotonic; range `0..100`; advances only on explicit phase transitions and accepted chunk checkpoints. |
| `audio_pipeline_eta_seconds` | `int | null` | Additive whole-pipeline ETA estimate; nonnegative; updated only with explicit progress or phase timing events. |

Heartbeat freshness must update at least every `30` seconds while codec,
transcription, diarization, alignment, or packaging work is active. Heartbeats
do not advance numeric audio progress or whole-pipeline estimates.

The existing `audio_total_media_seconds`, `audio_processed_media_seconds`,
`audio_percent_complete`, `audio_current_chunk_index`, and
`audio_total_chunks` fields are observed media/chunk facts. They must remain
truthful to accepted chunk checkpoints and must not claim work for an active
but unfinished chunk.

The additive `audio_pipeline_percent_complete` and
`audio_pipeline_eta_seconds` fields are measured estimates for the full audio
pipeline. They are allowed to move from `probing_media` into `diarizing`
before any transcription chunk is accepted, but only because a real phase
transition occurred. They must never advance from `last_heartbeat_at`, polling
freshness, or elapsed wall time alone. Terminal successful audio jobs set
`audio_pipeline_percent_complete=100.0` and `audio_pipeline_eta_seconds=0`;
failed jobs retain the last explicit measured estimate.

Canonical audio timing keys in `job.progress.phase_timings_ms`:

- `audio_probe_normalize_ms`
- `audio_diarization_ms`
- `audio_transcription_ms`
- `audio_alignment_ms`
- `audio_packaging_ms`

These keys are additive with the existing `final_artifact_persist_ms` and
`conversion_total_ms` counters. Timing telemetry must use only bounded
job/route/correlation metadata and must not include transcript text,
utterances, speaker display names, raw filenames as labels, media hashes as
labels, signed headers, credentials, secrets, or artifact bytes.

### Checkpoints, Retry, And Cancellation

The Task 357 sidecar execution implementation defines deterministic
duration-based audio chunks after probe succeeds. Chunk checkpoints record
enough metadata to prevent duplicate transcript segment persistence on retry:

- source media hash and normalized audio hash;
- chunk index, start/end seconds, overlap seconds, and processing profile;
- transcription segment ids already accepted for the chunk;
- diarization window ids already accepted for the chunk;
- alignment validation state.

Final `transcript_json` persistence is allowed only after all chunks complete
and cross-chunk transcription/diarization alignment validates. Public numeric
audio progress advances only after a chunk has been accepted and checkpointed:
`audio_processed_media_seconds` advances to the accepted chunk's end, and
`audio_current_chunk_index` reflects the most recently accepted chunk. During a
blocked active chunk, the stage may remain `transcribing` with fresh heartbeat
timestamps while numeric progress remains unchanged.

Cancel must be clean and idempotent: the main service stops further chunk
scheduling, propagates cancellation to the sidecar, finalizes the sidecar
request, then purges incomplete checkpoints and partial transcript state.
Successful jobs, non-retryable terminal failures, retryable failures that
become terminal for the current execution attempt, and canceled jobs must not
leave sidecar-owned normalized media tracked or present on disk. Failed or
canceled jobs must not expose partial transcripts as terminal artifacts.

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
| Formatter artifacts | requested `txt`, `md`, `vtt`, `srt` | same as transcript JSON |
| Failed/canceled partials | incomplete transcript/checkpoint state | purge at terminal cleanup |
| Logs/metrics/traces | operational metadata only | no transcript text, source content, utterances, tokens, or media bytes |
| Benchmark fixtures | sanitized/operator-owned fixtures | governed by the benchmark task/runbook |

`retention.pin=true` is rejected for `audio -> transcript_bundle` until a later
accepted retention contract defines pin semantics for source media, normalized
audio, transcript artifacts, and product-owned saves.

## Implementation State

Task 356 is the first PR-sized runtime implementation linked to this contract.
It defines and deploys:

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

Review 42 accepts this implementation as the runtime authority for the
canonical JSON core. Story 54 formatter artifacts and downstream
save/product-delivery work remain separate governed work.

Task 357 local implementation state on 2026-06-11:

- Service API v2 audio transcript runtime uses service-owned chunk planning,
  global sidecar diarization, chunk transcription, checkpoint replay, and
  canonical `transcript_json` packaging.
- The current internal sidecar contract is `/probe-media`, `/diarize`,
  `/transcribe-chunk`, `/finalize`, and `/cancel`; the main v2 runtime does not
  use blocking `/transcribe`.
- Normalized media is represented by an opaque sidecar-issued capability and
  verified against `request_handle` and SHA-256 before diarization or chunk
  transcription.
- The main runtime finalizes sidecar-owned normalized media on success,
  terminal failure, and cancellation, and suppresses cleanup errors when needed
  to preserve the original governed terminal error.
- Local focused proof exists in Task 357 test lanes. Hemma deploy and live
  tunnel evidence for the chunked progress contract is retained at
  `build/verification/hemma-deploy-verify/report.md` and
  `build/verification/task-357-live-progress-proof-00f9d7a/proof.md`; Review 43
  accepted this deployed proof on 2026-06-11.
