# Sir Convert-a-Lot Platform Discovery Overview

As of 2026-08-03; authored from repository state on that date. Counts and lane
names below are bound to that date. Every rule this document names is stated in
full by the authority it links to; read the authority before acting on a
boundary.

## 1. What This Repository Is

Sir Convert-a-Lot is the canonical document-conversion platform of the estate:
one v2 service that turns PDF, DOCX, HTML, Markdown, and audio into
LLM-friendly, deterministic, auditable outputs, plus the CLI that drives it and
the exam-migration workflows built on top. It is a single Python/PDM project
(`requires-python = ">=3.12,<3.14"`), not a service fan-out — the one directory
under `services/` holds ownership-scoped tests, not a second deployable.

Conversion is GPU-first: the laptop lane exists for debugging, and Hemma is the
canonical execution surface.

Top-level layout:

| Path                 | Holds                                                                     |
| -------------------- | ------------------------------------------------------------------------- |
| `AGENTS.md`          | Repository route list and command policy; the boot router                 |
| `README.md`          | Human quickstart, conversion routes, and core commands                    |
| `scripts/`           | All application code, plus the docs-as-code and devops entry points       |
| `services/`          | Ownership-scoped test packages (`api_gateway_service/tests`)              |
| `containers/`        | Sidecar and finetune container definitions                                |
| `docker/`            | Public-edge and service-dependency image lanes                            |
| `qwen/`              | Isolated Qwen research dependency boundary with its own lock and tests    |
| `colab_ml_training/` | Colab notebook and proof inputs for portable ML slices                    |
| `tests/`             | Root unit and fixture suites                                              |
| `docs/`              | Governed docs-as-code surface plus generated indexes and OpenAPI          |
| `build/`             | Generated benchmark, evaluation, and proof artifact trees                 |
| `data/`, `inputs/`   | Corpus and sample inputs used by conversion and benchmark runs            |
| `.codex/`            | Repo-local agent lane: skills, handoff, long-term memory                  |
| `.archive/`          | Retired governed documents                                                |

Deploy surfaces are `compose.yaml` (prod), `compose.local.yaml` (CPU-only
laptop debug), and `compose.remote-proof.yaml`, with `Dockerfile`,
`Dockerfile.deps`, `Dockerfile.local`, and `Dockerfile.qwen-provider`.

## 2. `scripts/sir_convert_a_lot/` — The Application

Despite sitting under `scripts/`, this package is the product. It follows a
layered shape with the v2 contract as the stable seam:

| Layer             | Holds                                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `domain/`         | Conversion contracts, policies, and the DigiExam answer-key model: completion, GBNF grammar, projections, live-validation goldens |
| `application/`    | Use cases: exam-authoring corrections, answer-key review state, correction replay artifacts and overlays, source-state projection |
| `infrastructure/` | Adapters: answer-key provider profiles (OpenAI, DeepSeek, local), audio transcript chunking, merging, alignment, checkpoints, bundles |
| `interfaces/`     | The delivery surface: `http_api.py` and `http_routes_*_v2.py` for the REST v2 API, `cli_app.py` and `cli_*_v2.py` for the CLI     |
| `integrations/`   | Adapter profiles for downstream consumers                                                                                       |
| `benchmarking/`   | PDF throughput, OCR runtime preflight, runtime parity, and scientific-corpus harnesses                                          |
| `stt_sidecar/`    | The speech-to-text sidecar application: factory, runtime, model lifecycle, media and audio normalization                        |
| `ml/`             | Qwen model work that stays inside the main dependency boundary                                                                  |
| `service.py`      | The service entry point, with `service_local.py` and `service_remote_proof.py` variants                                         |

`scripts/docs_as_code/` and `scripts/devops/` sit beside it: the governance
entry points and the named shell wrappers for compose, Hemma commands, prod
recreation, and runtime repair. Long-running remote work goes through those
committed wrappers, never ad hoc SSH.

## 3. Conversion Routes And Job Model

The v2 service executes to-Markdown (`pdf`, `docx`, `html`), to-PDF (`docx`,
`html`, `md`), and to-DOCX (`pdf`, `html`, `md`) natively; `md -> wav` is an
approved future route backed by a TTS sidecar. Audio input is transcribed
through the STT sidecar.

Jobs are asynchronous and idempotent, with correlation tracking, checkpoints,
partial artifact retrieval, cancel and resume, resource bundles for CSS and
images, and DOCX templates. `README.md` states the current route table and its
implementation status; `pdm run convert-a-lot routes` prints it from the running
service. The generated contract lives under `docs/_generated/openapi/`.

## 4. Sidecars And Container Lanes

`containers/` holds the out-of-process runtimes: `stt-sidecar-benchmark`,
`tts-sidecar-chatterbox`, `tts-sidecar-f5`, `tts-sidecar-openvoice`,
`textprep-espeak-phonemizer`, and `qwen-finetune-hemma`. `docker/` holds
`public-edge` and `service-deps`. `qwen/` is a separate dependency boundary with
its own `pyproject.toml` and `pdm.lock` so research dependencies never leak into
the service environment.

## 5. Execution Lanes

- Local debug: the CPU-only Docker service on `:8085`, started with
  `pdm run dev-start` and `compose.local.yaml`. Running
  `uvicorn scripts.sir_convert_a_lot.service:app` directly is not a supported
  lane.
- Hemma tunnel: `127.0.0.1:28085`, the default target for downstream app
  integration.
- Public: `convert.hule.education`.

Hemma work runs through `pdm run run-hemma -- ...`; from a client session it
SSHes to Hemma, and from the canonical Hemma Server repo it executes locally
after host and skill-repository checks. GPU and offload work is GPU-first and
decision-governed. The shared `sir-convert-a-lot-client` skill is the authority
for calling this platform from another repository, including lane selection and
the transcript and answer-key contract boundaries.

## 6. `docs/` — Governed Docs Surface

`docs/index.md` is the generated doorway. Lanes: `backlog/` (`epics`, `stories`,
`tasks`, `prs`, `reviews`, plus a generated `INDEX.md`), `decisions/` (14
documents), `reference/` (52 documents), `runbooks/` (10 documents),
`_generated/openapi/`, and `_meta/docs-contract.yaml`. Retired documents move to
`.archive/docs/` through `pdm run archive-documents`.

Generated indexes are refreshed by `pdm run docs-sync` and enforced by
`pdm run docs-validate`; both scan `docs/` only, so `AGENTS.md` and `.codex/`
sit outside them. Scaffold governed documents with `pdm run new-task`,
`new-story`, `new-epic`, `new-review`, and `new-doc`; never author frontmatter
by hand.

## 7. Ownership Boundaries

- `.codex/skills/` is the repo-local skill lane, holding Sir Convert-specific
  workflow and domain skills only: this map, the Hemma devops skill, the Qwen
  finetuning skill, the speech-model finetuning skill, and the Colab/Hemma
  orchestration skill. Shared workflows come from the canonical skill
  repository; repo facts belong in a shared skill's Sir Convert-a-Lot reference,
  never in a copied shared-skill body.
- `.claude/skills` is a symlink to `.codex/skills`, so the Claude harness
  discovers this lane at session start. The sanctioned symlink direction is
  local skill source into a harness configuration folder; installing
  shared-skill shims into this repository stays forbidden.
- `build/`, `data/`, and generated artifact trees are evidence, not scratch. Do
  not prune, reset, or delete them without an authorizing task.
- Production behavior changes need backlog authority; externally visible
  contracts need ADR, API, or reference authority.

## 8. Validation Surfaces

`pdm run format`, `lint`, `typecheck`, `test`, and `check` for Python, with
focused `pytest-root` runs and `coverage-gate` where conversion-core coverage
applies; `docs-sync` and `docs-validate` for the `docs/` contract;
`git diff --check` for diff hygiene. `AGENTS.md` states which set a given change
closes on.

Two gaps are current, as of this document's date, and are named here so they are
not mistaken for passing coverage:

- `pdm run check-md` and `format-md` fail repo-wide with
  `The required 'gfm' extension is not available`, so markdown formatting is
  unenforced. Recorded as deferred by TASK-SIRCON-REP-0026; no repair task
  exists yet.
- This repository binds no `skills-validate` or `handoff-validate` script, so
  `.codex/skills/` and `.codex/handoff.md` have no structural validator, even
  though the shared governance reference names those commands.
