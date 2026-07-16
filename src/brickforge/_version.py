"""
StudWorks Version and Branding Constants

The one place the application-facing name, version, and build label are
defined. main_window.py's window title, the splash screen, and the
render context's startup banner all import from here rather than each
hardcoding their own copy -- this is what previously let the window
title ("v0.1.0") drift out of sync with pyproject.toml's own version
("0.1.0-alpha.1"). pyproject.toml's [project].version is maintained
separately (it must be static TOML), but should be kept matching this
value by hand at each release.

This intentionally does not rename the Python package itself
(brickforge) or any import path -- see Package_020.5's completion notes
for why that is deferred to a dedicated future package.
"""

APP_NAME = "StudWorks"
APP_VERSION = "0.2.0"
BUILD_LABEL = "Preview"


def display_version() -> str:
    """e.g. "Preview 0.2.0" -- the label shown to users."""

    return f"{BUILD_LABEL} {APP_VERSION}"


def window_title() -> str:
    """e.g. "StudWorks Preview 0.2.0" -- the main window's title bar text."""

    return f"{APP_NAME} {display_version()}"
