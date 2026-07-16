"""
StudWorks Resource Locator

Resolves paths to bundled runtime assets (shaders, the application
icon, the bundled fallback LDraw library) so that every subsystem
finds them the same way, whether running from source or from a
PyInstaller-frozen executable.

PyInstaller extracts bundled data files to a temporary directory at
sys._MEIPASS at runtime; this module is the one place that knows to
check for it, so no other module needs to duplicate that check.

resource_root() always resolves to "the brickforge package root" --
in source form that is this file's own directory; in a frozen build it
is sys._MEIPASS/brickforge, which the PyInstaller spec's `datas`
entries must mirror (see StudWorks.spec). resource_path() joins onto
that root using the same relative layout the source tree already uses
(e.g. resource_path("render", "shaders") finds render/shaders in both
cases), so call sites don't need their own frozen/unfrozen branching.

This does not centralize LDraw library discovery -- that already has
its own, different-shaped concern (searching *outside* the package
first, then falling back to a bundled copy) handled by
services.ldraw_library_locator.find_ldraw_library(). Merging the two
would blur two genuinely different resolution strategies rather than
simplify anything.
"""

import sys
from pathlib import Path


def resource_root() -> Path:
    """The brickforge package root, in source or frozen form."""

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "brickforge"

    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Resolve a path relative to the brickforge package root."""

    return resource_root().joinpath(*parts)
