"""Internal speech-to-text sidecar package.

Purpose:
    Host the isolated STT HTTP adapter used by audio transcript-bundle runtime
    jobs while keeping FasterWhisper, pyannote, and GPU-only dependencies out of
    the main Sir Convert service image.

Relationships:
    - `app_factory` owns the normalized HTTP boundary.
    - `runtime` binds the boundary to the accepted FasterWhisper plus pyannote
      Hemma profile.
"""
