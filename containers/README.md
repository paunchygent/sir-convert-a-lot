# TTS Container Lifecycle

This directory contains both deployable-candidate and experiment-only
container surfaces for Sir Convert-a-Lot TTS work.

Current lifecycle policy:

- `tts-sidecar-chatterbox/`
  - status: Hemma production candidate
  - deployable on Hemma: yes
  - purpose:
    - Story 22 English-first sidecar delivery candidate
    - Story 23 Swedish cloning candidate
- `tts-sidecar-openvoice/`
  - status: experimental benchmark sidecar
  - deployable on Hemma: no
  - purpose:
    - preserved only for future benchmark reruns and comparison work
- `tts-sidecar-f5/`
  - status: experimental benchmark sidecar
  - deployable on Hemma: no
  - purpose:
    - preserved only for future benchmark reruns and comparison work
- `textprep-espeak-phonemizer/`
  - status: experimental helper image
  - deployable on Hemma: no
  - purpose:
    - saved-text preprocessing experiments outside the Chatterbox sidecar

Operational rule:

- only `tts-sidecar-chatterbox/` is the current Hemma production-candidate
  container surface in this repo
- all other TTS-related containers in this directory are experiment-only and
  must not be treated as deploy targets for Hemma production service work
