---
type: reference
id: REF-review-02-qwen-dataloader-io-bottleneck-evidence
title: Review 02 Qwen Dataloader I/O Bottleneck Evidence
status: active
created: '2026-03-09'
owners:
  - platform
updated: '2026-03-09'
related:
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture.md
---

## Purpose

Preserve the code-level evidence behind Review 02's dataloader bottleneck
finding without forcing the evidence file itself to satisfy the backlog review
package shape.

**Source:** `scripts/devops/qwen_finetuning_patches/dataset.py`
**Lines:** `184-203`

This code demonstrates that raw audio loading via `librosa` and
Mel-spectrogram extraction are executed synchronously on the CPU inside the
PyTorch `Dataset.__getitem__` method. This runs for every single item on every
epoch, which introduces a potential CPU-bound risk during training.

```python
    def __getitem__(self, idx: int) -> DatasetItem:
        item = self.data_list[idx]
        text = self._build_assistant_text(item["text"])
        text_ids = self._tokenize_texts(text)
        audio_codes = torch.tensor(item["audio_codes"], dtype=torch.long)

        speaker_id = item.get("speaker_id", "default_speaker")
        mapped_speaker_id = self.spk_id_map[speaker_id]

        ref_audio_value = item["ref_audio"]
        normalized_audio_inputs = self._normalize_audio_inputs(ref_audio_value)
        waveform, sample_rate = normalized_audio_inputs[0]
        ref_mel = self.extract_mels(audio=waveform, sample_rate=sample_rate)

        return {
            "text_ids": text_ids[:, :-5],
            "audio_codes": audio_codes,
            "ref_mel": ref_mel,
            "speaker_id": mapped_speaker_id,
        }
```

**Context in `_normalize_audio_inputs` (lines `114-119`):**

```python
    def _load_audio_to_np(self, path: str) -> AudioWithRate:
        audio, sample_rate = librosa.load(path, sr=None, mono=True)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=-1)
        normalized_audio = audio.astype(np.float32, copy=False)
        return normalized_audio, int(sample_rate)
```
