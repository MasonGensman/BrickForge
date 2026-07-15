"""
BrickForge Generation Package

Importing this package populates the GenerationMode registry -- each
known mode module is imported here for its registration side effect.
registry.py itself stays mode-agnostic; this is the one place that
knows which concrete modes exist.
"""

from brickforge.generation import flat_mosaic_registration  # noqa: F401
