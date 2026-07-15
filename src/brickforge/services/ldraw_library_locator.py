"""
BrickForge LDraw Library Locator

Detects an installed LDraw library: an LDRAW_LIBRARY_PATH environment
variable override, then common Windows install locations. Returns None
if nothing is found -- callers fall back to the permanent seed catalog.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

ENV_VAR = "LDRAW_LIBRARY_PATH"

STANDARD_LOCATIONS = [
    Path(r"C:\LDraw"),
    Path(r"C:\Program Files\LDraw"),
    Path(r"C:\Program Files (x86)\LDraw"),
]


def find_ldraw_library() -> Path | None:
    """
    Search for an installed LDraw library.

    LDRAW_LIBRARY_PATH, if set, takes priority. If it's set but doesn't
    point at a real directory, a warning is logged and detection falls
    through to the standard locations rather than failing outright.
    """

    override = os.environ.get(ENV_VAR)

    if override:

        override_path = Path(override)

        if override_path.exists():
            return override_path

        logger.warning(
            "%s is set to %r, but that path does not exist; "
            "falling back to automatic detection.",
            ENV_VAR,
            override,
        )

    for location in STANDARD_LOCATIONS:

        if location.exists():
            return location

    return None
