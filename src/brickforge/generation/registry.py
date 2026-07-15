"""
BrickForge Generation Mode Registry

Discovers available LEGO model generation modes. Deliberately knows
nothing about any specific mode -- not mosaics, not any future mode.
Modes register themselves (see flat_mosaic_registration.py for the
pattern); this module only stores and looks them up.
"""

from brickforge.generation.generation_mode import GenerationMode

_registry: dict[str, GenerationMode] = {}


def register_mode(mode: GenerationMode) -> None:
    """
    Register one GenerationMode. Raises ValueError on a duplicate id --
    a collision here is a real bug (two modes claiming the same
    identity), not something to silently paper over.
    """

    if mode.id in _registry:

        raise ValueError(
            f"GenerationMode id {mode.id!r} is already registered."
        )

    _registry[mode.id] = mode


def list_modes() -> list[GenerationMode]:
    """All registered modes, in registration order."""

    return list(_registry.values())


def get_mode(mode_id: str) -> GenerationMode | None:
    """Look up one registered mode by id, or None if not found."""

    return _registry.get(mode_id)
