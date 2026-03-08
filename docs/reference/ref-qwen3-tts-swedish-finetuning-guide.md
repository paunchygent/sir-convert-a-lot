---
type: reference
id: REF-qwen3-tts-swedish-finetuning-guide
title: Qwen3-TTS Swedish Finetuning Guide for General Language Support
status: active
created: 2026-03-08
owners:
  - Olof
---

## Background, Target, and Hard Constraints

The goal is **general Swedish language support** in `Qwen/Qwen3-TTS-12Hz-1.7B-Base` within the Sir Convert-a-Lot environment (ROCm, containers, on-prem "Hemma" + scale-up on H100 in Colab), using **full finetuning** and **AdamW**, and achieving **multi-speaker** capability (not just a shortcut to a single custom voice).

The most grounded public starting point is that Qwen themselves publish a **single-speaker recipe chain** (`train_raw.jsonl -> prepare_data.py -> sft_12hz.py`), explicitly noting that multi-speaker finetuning is not yet supported "in the current release" (but is planned).

In practice, this means the task is:

- to **translate** Qwen's single-speaker pipeline into a **multi-speaker pipeline that primarily trains language**, not cloning,
- to do so in a way that is **defensible in data policy** (Swedish sources have varying degrees of "verbatim truth"),
- and to design an **evaluation** that captures Swedish text-to-speech quality (intelligibility/pronunciation/robustness) rather than "how well it mimics a specific voice".

Qwen's own TTS report also highlights a relevant principle: they run multiple training phases and emphasize **quality stratification** to reduce hallucinations from noisy data. This is directly transferable to Swedish "parliamentary data" where transcripts are not always verbatim.

## Annotated Source Collection and Reusability

Below is a curated collection of sources where each source has a short, fielded annotation.

**Qwen3-TTS finetuning README + file chain**
**Source Type:** Official repo README + example command.
**Why important for your repo:** This is the closest "publicly documented path" for how Qwen intends the Base model (12Hz) to be fine-tuned today. It also exactly defines which fields must exist in the JSONL and how to build `audio_codes`.
**Says about…**
Curation: Requires text+audio pairs. No quality filtering described.
Preprocess: `prepare_data.py` creates `audio_codes` with `Qwen3-TTS-Tokenizer-12Hz`.
Training: `sft_12hz.py` with example LR and epochs, and `speaker_name` (single speaker). Note: there is a hyperparameter mismatch between the README (batch_size 32, lr 2e-6, num_epochs 10) and the script defaults (batch_size 2, lr 2e-5, num_epochs 3). This requires local sweeps.
Runtime: Assumes GPU device and batched encoding (`BATCH_INFER_NUM=32`).
Evaluation: Suggests "quick inference test" with `generate_custom_voice`.
**Directly reusable?** Partially. The chain is directly reusable; but single-speaker assumptions in the training script must be removed/reshaped for multi-speaker.

**sft_12hz.py**
**Source Type:** Official code (reference implementation).
**Why important:** It shows exactly what is actually optimized (AdamW, weight decay), how speaker embedding is injected, and how they "materialize" a custom voice during checkpoint saving via a hardcoded `spk_id`.
**Says about…**
Curation: Assumed to already be "clean" via prepared JSONL.
Preprocess: Expects `audio_codes` already in the data.
Training: `Accelerator(... mixed_precision="bf16", gradient_accumulation_steps=4)` + `AdamW(... weight_decay=0.01)`, and loss = talker-loss + 0.3 * sub-talker-loss.
Runtime: Assumes BF16 and FlashAttention-2 flag in model init (may require ROCm adaptation).
Evaluation: Not built-in here; just checkpoint writing.
**Directly reusable?** Yes as a base, but the checkpoint logic (single speaker -> `spk_id=3000`) is an anti-pattern for multi-speaker language expansion and must be replaced.

**dataset.py**
**Source Type:** Official code.
**Why important:** It defines your "manifest contract" in practice: which fields are read, how `ref_audio` is used, and a hard requirement of **24 kHz** for mel extraction.
**Says about…**
Curation: No quality control; it is your responsibility.
Preprocess: `ref_audio` is loaded via `librosa.load`, and `extract_mels` has `assert sr == 24000`.
Training: The `audio` field is read, but the actual training batch is primarily built on `text_ids`, `audio_codes`, `ref_mel`.
Runtime: If you do not standardize the sample rate to 24k, training will crash.
Evaluation: Indirectly: everything regarding `ref_audio` in eval must follow the same 24k contract.
**Directly reusable?** Yes, but it clearly shows where you must place your own data contract validation (24k, file formats, etc.).

**prepare_data.py**
**Source Type:** Official code.
**Why important:** This is the most robust "paper-as-code" bridge: it shows you should prepare `audio_codes` offline by running the tokenizer on your Swedish wavs in batch.
**Says about…**
Preprocess: `Qwen3TTSTokenizer.encode(batch_audios)` and writes `audio_codes` back to JSONL.
Runtime: batch size 32; you can scale this on H100.
**Directly reusable?** Yes. For Swedish runs, the key is that your "target audio" (`audio` field) must be in a format the tokenizer accepts, and you must standardize the sample rate consistently with the rest of the chain.

**Qwen/Qwen3-TTS-12Hz-1.7B-Base model card**
**Source Type:** Official model documentation.
**Why important:** It documents how Qwen themselves evaluate (e.g., WER) and that the Base model is intended to be fine-tuned, as well as that they sometimes run `language="auto"` in evaluation. This helps you choose evaluations that harmonize with upstream.
**Says about…**
Training: Base is described as the fine-tune target.
Evaluation: They report WER, and describe `language="auto"` on some test sets.
**Directly reusable?** As a "north star" for eval metrics (WER thinking), yes. For Swedish expansion, however, you need a Swedish ASR chain.

**Qwen finetuning format: single speaker + ref_audio recommendation**
**Source Type:** Official instruction.
**Why important:** Qwen explicitly states that single-speaker training should have the same `ref_audio` for all samples for stability. In multi-speaker, the most defensible generalization is: **same `ref_audio` per speaker** (not per row).
**Directly reusable?** Yes, as a principle.

**KBLab/rixvox dataset card**
**Source Type:** Official dataset documentation.
**Why important:** It provides Swedish scale (≈5493 h) and rich speaker metadata, but contains a crucial warning: the transcript text is **not always verbatim** but can be "intent-based", and alignment is automatic. This is central to your filtering policy in TTS.
**Says about…**
Curation: alignment is run automatically (e.g., `aeneas`), minimal dedup; certain phrases are removed because they are often not pronounced despite being in the protocol.
Evaluation/anti-pattern: "non-verbatim + auto-alignment" is exactly the type of noise Qwen themselves say can drive hallucinations and instability if not quality-sorted.
**Directly reusable?** Partially: metadata and volume are useful, but requires strict filtering for TTS.

**RixVox background article (KBLab blog)**
**Source Type:** Curator blog (method + statistics).
**Why important:** Gives numbers relevant for sampling strategy: many speakers (≈1194) and long observations (up to 30s) -> you must decide how to avoid "parliamentary style" dominating Swedish prosody.
**Directly reusable?** Indirectly: helps you design speaker balancing and dedup policy.

**google/fleurs dataset card**
**Source Type:** Dataset documentation.
**Why important:** FLEURS has ~10 hours train per language, separate speakers between train and dev/test, and is read-speech. It is almost "perfect" for an early Swedish **pilot signal test** and for a clean, reproducible eval split.
**Directly reusable?** Yes: excellent as a "high-trust" Swedish baseline + eval.

**KTH/waxholm dataset card**
**Source Type:** Dataset documentation + history.
**Why important:** For TTS, the big win here is that the transcription according to the card is based on manual orthographic input (listen and type), and that phoneme alignment has manual correction; additionally, some files lack labels and explicitly should not be used. This provides a clear "trust policy" for selection.
**Directly reusable?** Yes, especially as "clean Swedish" for pilot and pipeline validation.

**FLEURS-R (Interspeech 2024)**
**Source Type:** Paper + dataset idea.
**Why important:** It establishes an explicit pattern: "restoration/cleaning + retained semantics" to make a read-speech corpus more useful for generation. This kind of "quality-first cleaning" is relevant when you want to mix in noisier Swedish sources.
**Directly reusable?** Indirectly (pipeline principles), not "copy-paste".

**LibriTTS-R: ASR-based error list**
**Source Type:** Dataset page + practice note.
**Why important:** They describe a practical and published anti-pattern: restoration can create transcript mismatch; therefore they run ASR and list files above a WER threshold as likely errors. That is exactly the kind of transparency you need when filtering RixVox for TTS.
**Directly reusable?** Yes as a method: ASR-WER filter + explicit "exclude list".

**Nord-Parl-TTS (arXiv 2509.17988, ICASSP 2026)**
**Source Type:** Paper (dataset + pipeline) with Swedish subset.
**Why important:** Shows a fresh Nordic dataset pattern (parliamentary speech) that explicitly contains: (a) large hours of Swedish data, (b) unified eval sets, (c) in the dataset format examples that they calculate WER between transcript and a Whisper-ASR and store it per sample. It is a direct argument for exactly the filtering axis you need for RixVox.
**Directly reusable?** The method is reusable. The dataset itself is access-controlled and has terms you must review separately.

**GPU Operations on Hemma (HuleEdu runbook)**
**Source Type:** Internal runbook (devops).
**Why important:** It gives practical "flawless" operation rules relevant to your TTS FT: (1) verify ROCm visibility in container, (2) avoid docker-snap if mounting `/srv/scratch/...`, (3) pin ROCm base images and avoid pip-installing the wrong torch wheel.
**Directly reusable?** Yes for reproducibility and cache stability.

**KBLab/kb-whisper-large**
**Source Type:** Model card on Hugging Face.
**Why important:** This should be your default Swedish ASR backend for filtering and WER evaluation. It is trained on 50,000+ hours of Swedish speech and reports materially better Swedish WER than `whisper-large-v3` across FLEURS, Common Voice, and NST.
**Directly reusable?** Yes, as the most reproducible ASR choice.

**mozi1924/Qwen3-TTS-EasyFinetuning**
**Source Type:** Third-party GitHub repository.
**Why important:** This is an indirect engineering reference, not a recipe to copy. It is the clearest public code example of building a `spk_id_map`, carrying per-sample `speaker_ids`, applying the text-projection fix, and writing multiple speaker embeddings back into the codec table. It is CUDA/Docker-oriented and voice-product-centric.
**Directly reusable?** Partially, as an engineering reference.

## Best Public Patterns for Multi-Speaker Language Expansion from Qwen's Single-Speaker Recipe

Here is the most defensible translation from "single-speaker custom voice" to "multi-speaker language expansion" based on what Qwen actually does in their code.

### The Core Observation Driving the Design

Qwen's pipeline has two separate mechanisms that are often confused:

1. **Speaker conditioning during training**: `speaker_encoder(ref_mels)` provides a speaker embedding per sample, and it is injected into embeddings (they place it in a specific time step/slot in `input_codec_embedding`). This happens regardless of whether the data is single-speaker or multi-speaker.
1. **Materialization of a "CustomVoice speaker" at checkpoint**: the script writes a `talker_config["spk_id"]` that maps `speaker_name` to a fixed id (3000), and replaces one row in `codec_embedding.weight` with *one* embedding (`target_speaker_embedding`) picked from the first batch.

The second step is exactly what makes Qwen's recipe single-speaker in practice.

### Patterns That Work for Swedish Language Expansion

**Pattern A: Keep Base behavior (voice clone ability) and train language across many speakers**
This is the "language first" track.

- Train as Qwen does (full finetune with AdamW) but **stop rewriting the model into a single-speaker CustomVoice** at save.
- Keep `speaker_encoder` in the checkpoint (i.e., remove the logic that drops `speaker_encoder` from `state_dict` at save).
- Let each training row have a `ref_audio` that represents the specific speaker talking (see manifest strategy below). Qwen's `dataset.py` reads `ref_audio` and builds `ref_mel`, and the entire training script uses `speaker_encoder(ref_mels)` per batch.

**Why this is best for your goal:** You train the model to map Swedish text to audio token sequences across varying speaker embeddings, which is exactly what you want if the goal is "Swedish works" rather than "one voice works". The pattern also follows Qwen's own ChatML idea (standardized inputs), but you replace "one speaker id" with "many ref embeddings".

**Pattern B: Build a "multi-speaker CustomVoice variant" (Swedish voice profiles)**
This is the "product reasons" track if you want to be able to say `generate_custom_voice(... speaker="SV_07")` in serving.

- Create a **speaker table** where each speaker gets an id (e.g., 3000…3000+N-1). Qwen's script already shows how `spk_id` is injected into config and how an embedding row can be written.
- For each speaker: calculate a stable embedding (e.g., mean of embeddings from several `ref_audio` clips) for robustness. Qwen's single-speaker script takes the first batch's embedding; in multi-speaker, you should instead take a **controlled speaker bank**.
- This requires you to define exactly which voices are included in the "Swedish package", and evaluate language separately (so that "one voice sounds good" is not mistaken for "Swedish works").

**Why this is secondary:** It risks once again becoming a "voice profile product" where quality can be driven by which speakers happen to be included. For language expansion, you still want to evaluate on held-out speakers.

### Anti-Patterns to Explicitly Avoid

- **Mixing "language expansion" with Qwen's single-speaker checkpoint rewrite** (spk_id=3000 + one embedding) — it sabotages the multi-speaker goal and makes eval/interpretation misleading.
- **Feeding RixVox without ASR match filters**: the dataset card says transcripts are not always verbatim. For TTS, that is a direct path to "text-audio mismatch" which typically causes pronunciation errors and unstable mapping.
- **Ignoring the sample rate contract**: Qwen's `extract_mels` requires 24 kHz; if `ref_audio` is not 24k you will crash, and if you resample inconsistently you get hard-to-reproduce quality.

## Data Curation for Rixvox + Fleurs + Waxholm in a TTS Setting

The most defensible policy is to explicitly divide data into **trust levels** and train in phases (quality progression). This also aligns with Qwen's own narrative of a "high-quality stage" to reduce hallucinations from noise.

### Trust Levels and Suggested Role in Training

**High trust: FLEURS (sv_SE) & Waxholm – "clean read speech & manual orthographic text"**
These are excellent as high-trust signal tests, but too small to be the main training backbone.
Policy: use FLEURS and Waxholm strictly for smoke tests, controls, and held-out evaluation. Wherever possible, prefer their native dataset splits over a generic custom 80/20 split.

**Medium/Low trust: RixVox – "massive volume, but not always verbatim"**
RixVox is large (≈5493 h) and already has speaker-disjoint splits, making it the most viable training backbone. However, transcript text is not always verbatim speech.
Policy: use filtered RixVox as the **first real training backbone**, but only **after** you have implemented transcript match filters (e.g. ASR-WER based mismatch detection).

### A Defensible Filtering Policy for RixVox

Here you should copy a proven public idea: **ASR-based "mismatch detection"**.

- Nord-Parl-TTS explicitly shows they calculate WER between the given transcript and Swedish Whisper-large, storing it per sample for Swedish data.
- LibriTTS-R describes creating lists of files over a WER threshold after ASR, since restoration/processing can create mismatches.

Translated to RixVox:

- Run a Swedish ASR (minimum requirement: stable model + deterministic decoding) on each segment.
- Normalize both ASR text and protocol text (lowercase, trim whitespace, standardize numbers if you do it in any direction).
- Filter strictly in the pilot: start with e.g., `WER <= 0.15` as a **quality gate** (adjust after observation). This is not a "magic number"; the point is you need **an explicit mismatch axis** for TTS.
- Deduplicate formulaic phrases more aggressively than RixVox does, since the dataset card itself says minimal dedup was done and phrases like "Fru talman" can be misaligned to audio.

### Preprocessing Contracts That Must Be True in the Qwen Chain

This is binary: either you follow the contract or training becomes brittle.

- **Swedish Orthography:** Feed standard Swedish orthography directly. Qwen handles text with the standard Qwen tokenizer, while the 12Hz tokenizer handles speech codes separately; do not add a phonemizer in the first pass unless evaluation later shows a clear homograph problem.
- **Punctuation:** Maintain strict, clear punctuation (commas, periods). The model relies heavily on these to structure prosody and breathing boundaries, since there is no intermediate phoneme layer.
- **24 kHz**: `ref_audio` must be 24k for `extract_mels`.
- **JSONL fields**: every row must have `audio`, `text`, `ref_audio`; after the prepare step, also `audio_codes`.
- **Length policy**: RixVox can be up to 30s; Qwen's pipeline can technically handle it, but you should set a max length in the pilot (e.g., 2–15s) for faster iteration and less risk of alignment drift.
- **Inert `language` field:** Do not assume the JSONL `language` field affects training in the current public finetune stack; it is read by `dataset.py` but not propagated into the returned batch.

## Reference Audio and Manifest Strategy for Multi-Speaker Swedish Runs

Qwen's own single-speaker advice is: use the same `ref_audio` for all samples to increase stability.
In multi-speaker, you do exactly the same thing — but **per speaker**.

### Manifest Contract: Two Levels

#### Level 1: Raw JSONL (before audio_codes)

This matches Qwen's "Input JSONL format".

```jsonl
{"audio": "wavs/train/sv/spk_001/utt_000123.wav", "text": "Jag vill åka härifrån.", "ref_audio": "refs/sv/spk_001/ref_03s.wav"}
{"audio": "wavs/train/sv/spk_017/utt_000045.wav", "text": "Det här är ett test av svenska.", "ref_audio": "refs/sv/spk_017/ref_03s.wav"}
```

#### Level 2: Training JSONL (after prepare_data.py)

Here `audio_codes` are added, which `prepare_data.py` writes via `Qwen3TTSTokenizer.encode`.

```jsonl
{"audio": "...", "text": "...", "ref_audio": "...", "audio_codes": [[...16 ints...], [...]]}
```

### The Most Defensible Reference Audio Strategy

**Contract:**

- `ref_audio` must be (a) 24kHz, (b) single-speaker, (c) **5–10 seconds canonical anchor**, (d) representative of the person's voice timbre, and (e) stably reused across all rows for the same speaker.

**Why this seems best given Qwen's implementation:**

- `dataset.py` uses `ref_audio` to create a mel, and the training script takes `speaker_encoder(ref_mels)` for embedding. This means `ref_audio` practically acts as your "speaker key" during training. If `ref_audio` randomly varies between poor clips, you inject noise into the speaker conditioning.

**Defensive variant (recommended for larger datasets):**

- A small "ref bank" per speaker (e.g., 3 clips) where you *deliberately* choose high-quality clips, but use the same clip for all utterances within an epoch. Qwen's dataset code accepts lists but takes the first element; thus, you must patch it if you want to randomize among several.

## Pilot Design and Evaluation for Swedish Language Support

### Pilot Scope: Hours and Speakers that Provide the "First Real Answer"

You want to quickly answer: *"Does the model learn Swedish orthography/pronunciation so that Swedish text becomes intelligible and stable?"*

A robust pilot (Hemma) should therefore be:

- **At least ~15–30 hours total Swedish speech data**, where the majority is high-trust (FLEURS + Waxholm), and where RixVox only comes in as a small, strictly filtered spice at the end of the pilot if you already have mismatch filters in place.
- **At least 12–25 speakers** total (to avoid "Swedish = one voice"), where you explicitly make an evaluation split:
  - **Train speakers:** ~80%
  - **Held-out speakers:** ~20% (reference audio from speakers never used in training)

This split is important because your goal is not cloning: if Swedish quality only works on "seen speakers", you have likely overfit the speaker conditioning instead of learning the text-to-audio mapping. Qwen's own eval thinking uses WER as a "content consistency" measure, which you can mirror in a Swedish environment, but now with held-out voices.

### Evaluation Design: Measure Language, Not Cloning Degree

Qwen uses WER as the main metric for "content consistency" in their speech generation benchmarks.
Take that idea and make it Swedish-specific:

### Primary Automatic Metrics

- **ASR-WER (or CER) on synthetic speech vs text prompt**:

- Generate speech from a fixed eval set of Swedish text.

- Run Swedish ASR on the generated audio.

- Calculate WER/CER following a clear normalization policy.
  This follows Qwen's own eval philosophy but makes it Swedish and reproducible.

#### Quality proxy (DNSMOS/similar)

Nord-Parl-TTS shows that DNSMOS P.835-OVL is used as sample metadata in the Swedish part. Even if you don't copy their pipeline, it is strong "proof of practice" to have a QoE score as a filter and trend indicator.

### Secondary Checks to Avoid Misinterpretation

- **Speaker collapse indicator**: measure speaker embedding similarity between generated speech and ref audio (cosine similarity) and compare intra-speaker vs inter-speaker; Qwen reports speaker similarity in their multilingual test set.
- **Stress texts** (hand-built):
  - Words heavy on å/ä/ö, "sj-sounds", "skj-", long compound words, numbers, dates, abbreviations.
  - Text with parentheses, quotation marks, and mixed punctuation, since Qwen emphasizes robustness against "noisy input text".

### Eval Sets that are "Cheap but Strong"

- **FLEURS dev/test for Swedish**: because the speakers differ from train and are standardized sentences. It gives you a quick, comparable yardstick.
- **A small held-out Waxholm set** (if speaker metadata allows) to see if the model handles dialog-style material better than read speech. The Waxholm description indicates highly structured material, fitting as a "clean control".

## Recommendation Memo for Your Exact Setup

### Do This First on Hemma

**Build a "Pilot-A" that is quality-protected and stresses language, not volume.**

1. **Data Contract + Validation Before Training**

   - Resample EVERYTHING to 24 kHz. This is non-negotiable due to `assert sr == 24000` in Qwen dataset code.
   - Create raw JSONL with `audio/text/ref_audio` for:
     - FLEURS Swedish train (as high-trust base)
     - Waxholm label-safe files (as additional high-trust)
   - Add a "fail-closed" preflight early: count how many rows lack a wav, how many ref_audios are not 24k, how many utts are >15s, etc. (This is an operational principle; the Huleedu runbook argues for fail-closed and cache stability in GPU workloads.)

1. **Run Qwen's `prepare_data.py` locally on Hemma for the pilot size**

   - This provides `audio_codes` and isolates the training run from costly tokenization.
   - If GPU time is expensive on Hemma: do just the encode step on H100 (see below) and move the JSONL back. But start with a local pilot to confirm the contract.

1. **Patch the Official Training Stack (sft_12hz.py and dataset.py)**
   Minimum patch (language expansion):

   - **sft_12hz.py**: Keep multi-speaker training but **remove**:
     - `talker_config["spk_id"] = { speaker_name: 3000 }` rewrite
     - overwriting of `codec_embedding.weight[3000]`
     - dropping of `speaker_encoder` from `state_dict`
   - Ensure the configuration parameter `tts_model_type` remains or is reverted to `"base"` rather than being overwritten to `"custom_voice"`. This is crucial because "custom_voice" disables In-Context Learning (ICL) and zero-shot voice cloning capabilities in downstream inference.
   - **sft_12hz.py**: Include the community text-projection fix to ensure language adaptation behaves correctly.
   - **dataset.py**: Patch the dataloader to parse multiple speakers, build a `spk_id_map`, and carry a dataset-scoped `speaker_id` through the training loop. *(Note: This patch is strictly for metadata tracking, governance, and evaluation, or if you intend to export named speakers (Pattern B). The actual forward path conditions purely on `ref_mel -> speaker_encoder(ref_mels)` and does not use `speaker_id`.)*
     Otherwise, you risk exporting an artificial "single speaker" even if training succeeds.

1. **Inference on Multi-Speaker Checkpoint**

   - Because you kept `tts_model_type` as "base" and preserved the `speaker_encoder`, do **not** use `generate_custom_voice.py` for inference.
   - After a base-like fine-tune, validate inference with `generate_voice_clone.py` or `create_voice_clone_prompt` + `generate_voice_clone`.
   - Reserve `generate_custom_voice.py` strictly for checkpoints intentionally exported as CustomVoice models.

1. **Run a short, but not trivial, training loop**

   - 1–2 epochs on Pilot-A, with a checkpoint per epoch (as Qwen does).
   - After each epoch, run a fixed eval suite (FLEURS dev/test + your stress texts) with ASR-WER.

**Why this order?**
It separates "pipeline works" from "RixVox works". You don't want to hide a quality problem in RixVox behind a runtime problem in the Qwen chain.

### Scale This on Colab H100

The H100 track should be used for what is **expensive but parallelizable**:

1. **Bulk tokenization (`prepare_data.py`) for large amounts of Swedish audio**

   - The script is already batched (32 per batch). H100 will do this dramatically faster than Hemma.

1. **RixVox mismatch filtering with ASR**

   - If you plan to use hundreds of hours of RixVox, you need an ASR pipeline at scale (transcribe -> WER -> filter lists). Nord-Parl-TTS and LibriTTS-R show that "ASR-WER as filter metadata" is a published and reasonable pattern.

1. **Phase-2 Training (Volume)**

   - When Pilot-A shows clear improvement in Swedish WER and listening quality: mix in filtered RixVox at a controlled ratio (e.g., 70% high-trust, 30% filtered RixVox initially; adjust after regression control).
     Qwen's own report describes using quality stratification to reduce hallucinations—this is a strong argument not to let low-trust dominate early.

### Avoid This

- **"Notebook-fragile" one-offs lacking data contracts and fail-closed preflights**: you run containers + ROCm and want reproducibility. Follow the runbook principle: pin base images, avoid docker-snap mount issues, mount caches.
- **Voice-cloning-centric eval** (e.g., only speaker similarity) when the goal is Swedish language ability. Speaker metrics should be a sanity check, not the main signal. Qwen themselves use WER as a content metric; take that idea but make it Swedish.
- **Using RixVox "raw"**. The dataset states that protocols are not always verbatim; it is dangerous for TTS unless you filter.

### A Concrete "First Run" I Recommend

#### Pilot-A (Hemma)

- Data (Smoke Run & First Language Pilot):

  - **Smoke Run:** 8–12 hours of high-confidence filtered `rixvox` (or FLEURS/Waxholm) from 12–16 speakers.
  - **First Language Pilot:** 24–36 hours of filtered `rixvox` train data, spread across 24–40 speakers.

- Speakers:

  - Apply a hard cap per speaker so the biggest parliamentary voices do not dominate. Evaluate on untouched `rixvox` validation/test, Swedish `fleurs` validation/test, and labeled `waxholm`.

- Preprocess:

  - resample->24k, build raw JSONL, run `prepare_data.py`, validate `ref_audio` is always 24k.

- Training:

  - full fine-tune with AdamW as Qwen does, but patched save logic (no transformation to single-speaker).

- Eval:

  - ASR-WER/CER on FLEURS dev/test + stress texts; log per epoch so you can answer "did it get better?" without subjective bias.

#### Phase-2 (Colab H100)

- Scale up to **100–300 filtered hours** from `rixvox` train under the same per-speaker and quality policy.
- Reuse the same manifests, same held-out sets, and same evaluation scripts. Keep checkpoint cadence denser than normal due to upstream resume bugs.
- Retrain (or continue training) with a controlled mix ratio and run the same eval suite, plus a "parliament-style" eval to see if prosody becomes too formal.
