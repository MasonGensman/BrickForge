"""
BrickForge Image Resource

Represents one loaded image, normalized to an RGBA uint8 array. Pure data
-- independent of engine/, render/, and any AI concept -- so any future
consumer (a texture uploader, an AI analysis pipeline, a UI preview) works
from the same representation.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(slots=True)
class ImageResource:
    """One loaded, normalized image."""

    path: Path
    width: int
    height: int
    format: str

    #
    # Always RGBA uint8, shape (height, width, 4), regardless of source
    # format or original channel count.
    #
    pixels: np.ndarray

    #
    # SHA-256 of the raw source file bytes (not the normalized pixels) --
    # a stable identifier for "this exact imported file", for future
    # caching and AI analysis.
    #
    content_hash: str
