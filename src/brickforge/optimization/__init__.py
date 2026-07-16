"""
BrickForge Optimization Package

Importing this package populates the Optimizer registry -- each known
optimizer module is imported here for its registration side effect.
registry.py itself stays optimizer-agnostic; this is the one place
that knows which concrete optimizers exist.
"""

from brickforge.optimization import brick_merge_optimizer  # noqa: F401
