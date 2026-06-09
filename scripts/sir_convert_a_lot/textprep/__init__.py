"""Text preprocessing helpers for benchmark-only experimental flows.

Purpose:
    Group optional text-transformation tools that can be used in bounded
    benchmark and research slices without changing the main sidecar contract.

Relationships:
    - Used by benchmark-only devops runners such as the Chatterbox eSpeak experiment Chatterbox
      eSpeak preprocessing experiment.
    - Intentionally separate from the production TTS sidecar runtime package.
"""
