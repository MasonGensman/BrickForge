"""
BrickForge LDraw Library Locator

Detects the best available LDraw library, in priority order:

1. LDRAW_LIBRARY_PATH environment variable override.
2. Standard Windows LDraw installation locations.
3. The project-root ldraw/ directory (development builds only -- this
   tier is skipped entirely in a frozen/packaged build, where there is
   no "project root" to look relative to).
4. The bundled fallback library shipped inside the application itself
   -- always present, so this function only fails to find a library if
   even that bundled fallback directory is somehow missing.

Every caller (PartCatalog, Renderer) goes through this single function,
so a developer, a user with LDraw already installed, and a bare Preview
build all consistently resolve to the richest library actually
available -- without any caller needing to know which tier matched.
"""

import logging
import os
import sys
from pathlib import Path

from brickforge.resources import resource_path

logger = logging.getLogger(__name__)

ENV_VAR = "LDRAW_LIBRARY_PATH"

STANDARD_LOCATIONS = [
    Path(r"C:\LDraw"),
    Path(r"C:\Program Files\LDraw"),
    Path(r"C:\Program Files (x86)\LDraw"),
]


def _project_root_ldraw() -> Path | None:
    """
    The project-root ldraw/ directory, for development builds only --
    meaningless in a frozen build, where there is no "project root"
    relative to a packaged executable, so this tier is skipped
    entirely when running frozen.
    """

    if getattr(sys, "frozen", False):
        return None

    return Path(__file__).resolve().parents[3] / "ldraw"


def _is_valid_library(path: Path) -> bool:

    return path.is_dir()


def find_ldraw_library() -> Path | None:
    """
    Search for the best available LDraw library, trying each tier
    above in order and returning the first one that actually exists.

    Succeeds in practice for every caller, since tier 4 (the bundled
    fallback) ships with the application itself -- returns None only
    if that bundled directory is somehow missing too.
    """

    override = os.environ.get(ENV_VAR)

    if override:

        override_path = Path(override)

        if _is_valid_library(override_path):
            return override_path

        logger.warning(
            "%s is set to %r, but that path does not exist; "
            "falling back to automatic detection.",
            ENV_VAR,
            override,
        )

    for location in STANDARD_LOCATIONS:

        if _is_valid_library(location):
            return location

    project_root_ldraw = _project_root_ldraw()

    if (
        project_root_ldraw is not None
        and _is_valid_library(project_root_ldraw)
    ):
        return project_root_ldraw

    bundled = resource_path("ldraw", "ldraw")

    if _is_valid_library(bundled):
        return bundled

    return None
